# -*- coding: utf-8 -*-
import logging
from backend.app.services.model_runtime import create_chat_adapter_from_config as create_llm_adapter, _provider_to_interface
from backend.app.services.model_runtime import get_runtime_config

logger = logging.getLogger(__name__)


def create_specialized_chat_adapter(ctx, purpose: str, temperature: float | None = None):
    log_ctx = ctx.make_log_ctx() if hasattr(ctx, "make_log_ctx") else None

    if not ctx.project_id or not ctx.user_id:
        adapter = create_llm_adapter(
            interface_format=ctx.llm.interface_format,
            base_url=ctx.llm.base_url,
            model_name=ctx.llm.model_name,
            api_key=ctx.llm.api_key,
            temperature=temperature if temperature is not None else ctx.llm.temperature,
            max_tokens=ctx.llm.max_tokens,
            timeout=ctx.llm.timeout,
            cancel_token=ctx.cancel_token,
        )
        if log_ctx:
            adapter._log_ctx = log_ctx
        return adapter

    try:
        runtime = get_runtime_config(ctx.user_id, purpose, ctx.project_id)
    except Exception:
        runtime = None

    if runtime is None:
        adapter = create_llm_adapter(
            interface_format=ctx.llm.interface_format,
            base_url=ctx.llm.base_url,
            model_name=ctx.llm.model_name,
            api_key=ctx.llm.api_key,
            temperature=temperature if temperature is not None else ctx.llm.temperature,
            max_tokens=ctx.llm.max_tokens,
            timeout=ctx.llm.timeout,
            cancel_token=ctx.cancel_token,
        )
        if log_ctx:
            adapter._log_ctx = log_ctx
        return adapter

    adapter = create_llm_adapter(
        interface_format=_provider_to_interface(runtime.provider),
        base_url=runtime.base_url,
        model_name=runtime.model,
        api_key=runtime.api_key,
        temperature=temperature if temperature is not None else (runtime.temperature or ctx.llm.temperature),
        max_tokens=runtime.max_tokens or ctx.llm.max_tokens,
        timeout=runtime.timeout or ctx.llm.timeout,
        cancel_token=ctx.cancel_token,
    )
    if log_ctx:
        log_ctx["runtime_config"] = runtime
        adapter._log_ctx = log_ctx
    return adapter


