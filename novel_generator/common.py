# -*- coding: utf-8 -*-
"""Shared retry, cleaning, and logging helpers."""

from __future__ import annotations

import logging
import re
import time
import traceback

from llm_errors import (
    LLMInvocationError,
    build_empty_response_error,
    classify_llm_exception,
    coerce_error_info,
)
from novel_generator.task_manager import TaskCancelledError

logger = logging.getLogger(__name__)


def call_with_retry(func, max_retries=3, sleep_time=2, fallback_return=None, **kwargs):
    """Call a function with retries and a fallback return value."""
    for attempt in range(1, max_retries + 1):
        try:
            return func(**kwargs)
        except Exception as exc:
            logging.warning("[call_with_retry] Attempt %s failed with error: %s", attempt, exc)
            traceback.print_exc()
            if attempt < max_retries:
                time.sleep(sleep_time)
            else:
                logging.error("Max retries reached, returning fallback_return.")
                return fallback_return


def remove_think_tags(text: str) -> str:
    """Remove <think>...</think> blocks from model output."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)


def debug_log(prompt: str, response_content: str):
    logging.info(
        "\n[#########################################  Prompt  #########################################]\n%s\n",
        prompt,
    )
    logging.info(
        "\n[######################################### Response #########################################]\n%s\n",
        response_content,
    )


def invoke_with_cleaning(
    llm_adapter,
    prompt: str,
    max_retries: int = 3,
    cancel_check=None,
    cancel_token=None,
    operation_name: str = "LLM 调用",
    step: str | None = None,
) -> str:
    """Invoke an LLM and normalize the returned text."""
    if cancel_token is None and hasattr(llm_adapter, "_cancel_token"):
        cancel_token = getattr(llm_adapter, "_cancel_token", None)

    _raise_if_cancelled(cancel_check, cancel_token)

    print("\n" + "=" * 50)
    print("发送到 LLM 的提示词:")
    print("-" * 50)
    print(prompt)
    print("=" * 50 + "\n")

    for attempt in range(1, max_retries + 1):
        try:
            _raise_if_cancelled(cancel_check, cancel_token)
            result = llm_adapter.invoke(prompt)
            error_info = coerce_error_info(getattr(llm_adapter, "last_error_info", None))

            _raise_if_cancelled(cancel_check, cancel_token)

            print("\n" + "=" * 50)
            print("LLM 返回的内容:")
            print("-" * 50)
            print(result)
            print("=" * 50 + "\n")

            cleaned = result.replace("```", "").strip() if isinstance(result, str) else ""
            if cleaned:
                _raise_if_cancelled(cancel_check, cancel_token)
                return cleaned

            if error_info is None and getattr(llm_adapter, "last_error", ""):
                error_info = classify_llm_exception(
                    RuntimeError(llm_adapter.last_error),
                    provider=getattr(llm_adapter, "provider", ""),
                    model_name=getattr(llm_adapter, "model_name", ""),
                    base_url=getattr(llm_adapter, "base_url", ""),
                )

            if error_info is None:
                error_info = build_empty_response_error(
                    provider=getattr(llm_adapter, "provider", ""),
                    model_name=getattr(llm_adapter, "model_name", ""),
                    base_url=getattr(llm_adapter, "base_url", ""),
                )

            if attempt < max_retries and error_info.retryable:
                wait_seconds = min(2 * attempt, 5)
                logger.warning(
                    "LLM 调用失败，准备重试 [attempt=%s/%s category=%s code=%s wait=%ss detail=%s]",
                    attempt,
                    max_retries,
                    error_info.category,
                    error_info.code,
                    wait_seconds,
                    error_info.detail,
                )
                time.sleep(wait_seconds)
                continue

            raise LLMInvocationError(error_info, operation_name=operation_name, step=step)
        except TaskCancelledError:
            raise
        except LLMInvocationError:
            raise
        except Exception as exc:
            _raise_if_cancelled(cancel_check, cancel_token, source_exc=exc)
            error_info = classify_llm_exception(
                exc,
                provider=getattr(llm_adapter, "provider", ""),
                model_name=getattr(llm_adapter, "model_name", ""),
                base_url=getattr(llm_adapter, "base_url", ""),
            )
            if attempt < max_retries and error_info.retryable:
                wait_seconds = min(2 * attempt, 5)
                logger.warning(
                    "LLM 调用异常，准备重试 [attempt=%s/%s category=%s code=%s wait=%ss detail=%s]",
                    attempt,
                    max_retries,
                    error_info.category,
                    error_info.code,
                    wait_seconds,
                    error_info.detail,
                )
                time.sleep(wait_seconds)
                continue
            raise LLMInvocationError(error_info, operation_name=operation_name, step=step) from exc

    raise LLMInvocationError(
        build_empty_response_error(
            provider=getattr(llm_adapter, "provider", ""),
            model_name=getattr(llm_adapter, "model_name", ""),
            base_url=getattr(llm_adapter, "base_url", ""),
        ),
        operation_name=operation_name,
        step=step,
    )


def _raise_if_cancelled(cancel_check=None, cancel_token=None, source_exc: Exception | None = None) -> None:
    if cancel_check and cancel_check():
        raise TaskCancelledError("任务已取消") from source_exc
    if cancel_token is not None and hasattr(cancel_token, "raise_if_set"):
        try:
            cancel_token.raise_if_set()
        except TaskCancelledError as exc:
            raise TaskCancelledError("任务已取消") from source_exc or exc
