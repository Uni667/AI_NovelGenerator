# -*- coding: utf-8 -*-
"""Shared retry, cleaning, and logging helpers."""

from __future__ import annotations

import logging
import re
import time
import traceback

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


def invoke_with_cleaning(llm_adapter, prompt: str, max_retries: int = 3, cancel_check=None) -> str:
    """Invoke an LLM and normalize the returned text.

    cancel_check: optional no-arg callback; if it returns True, the task is cancelled.
    """
    if cancel_check and cancel_check():
        raise TaskCancelledError("任务已取消")

    print("\n" + "=" * 50)
    print("发送到 LLM 的提示词:")
    print("-" * 50)
    print(prompt)
    print("=" * 50 + "\n")

    result = ""
    retry_count = 0

    while retry_count < max_retries:
        try:
            if cancel_check and cancel_check():
                raise TaskCancelledError("任务已取消")
            result = llm_adapter.invoke(prompt)
            if cancel_check and cancel_check():
                raise TaskCancelledError("任务已取消")

            print("\n" + "=" * 50)
            print("LLM 返回的内容:")
            print("-" * 50)
            print(result)
            print("=" * 50 + "\n")

            result = result.replace("```", "").strip()
            if result:
                return result

            retry_count += 1
        except TaskCancelledError:
            raise
        except Exception as exc:
            if cancel_check and cancel_check():
                raise TaskCancelledError("任务已取消") from exc
            print(f"调用失败 ({retry_count + 1}/{max_retries}): {str(exc)}")
            retry_count += 1
            if retry_count >= max_retries:
                raise

    return result

