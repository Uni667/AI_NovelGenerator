# llm_adapters.py
# -*- coding: utf-8 -*-
"""LLM adapter factory and provider-specific implementations."""

from __future__ import annotations

import logging
import re
from typing import Optional

from llm_errors import classify_llm_exception

# Lazy imports: only fail when a specific adapter is actually used.
_ChatOpenAI = _AzureChatOpenAI = None
_genai = _types = None
_ChatCompletionsClient = _AzureKeyCredential = _SystemMessage = _UserMessage = None
_OpenAI = None
_httpx = None

logger = logging.getLogger(__name__)


def _ensure_httpx():
    global _httpx
    if _httpx is None:
        import httpx as _h

        _httpx = _h


def _make_cancel_client(cancel_token, timeout: float) -> object:
    """Build an httpx.Client whose transport checks CancelToken at every level."""
    _ensure_httpx()

    class _CancelByteStream(_httpx.SyncByteStream):
        def __init__(self, stream, token):
            self._stream = stream
            self._token = token

        def __iter__(self):
            for chunk in self._stream:
                if self._token is not None and self._token.is_set():
                    from novel_generator.task_manager import TaskCancelledError

                    raise TaskCancelledError("请求已被用户取消")
                yield chunk

        def close(self):
            self._stream.close()

    class _CancelTransport(_httpx.BaseTransport):
        def __init__(self, wrapped, token):
            self._wrapped = wrapped
            self._token = token

        def handle_request(self, request):
            if self._token is not None and self._token.is_set():
                from novel_generator.task_manager import TaskCancelledError

                raise TaskCancelledError("请求已被用户取消")
            response = self._wrapped.handle_request(request)
            if self._token is not None and hasattr(response, "stream"):
                response.stream = _CancelByteStream(response.stream, self._token)
            return response

        def close(self):
            return self._wrapped.close()

    transport = _httpx.HTTPTransport()
    wrapped = _CancelTransport(transport, cancel_token)
    client = _httpx.Client(transport=wrapped, timeout=timeout)
    if cancel_token is not None:
        cancel_token.bind(client)
    return client


def _ensure_openai():
    global _ChatOpenAI, _AzureChatOpenAI
    if _ChatOpenAI is None:
        from langchain_openai import AzureChatOpenAI, ChatOpenAI

        _ChatOpenAI = ChatOpenAI
        _AzureChatOpenAI = AzureChatOpenAI


def _ensure_google():
    global _genai, _types
    if _genai is None:
        from google import genai as _g
        from google.genai import types as _t

        _genai = _g
        _types = _t


def _ensure_azure():
    global _ChatCompletionsClient, _AzureKeyCredential, _SystemMessage, _UserMessage
    if _ChatCompletionsClient is None:
        from azure.ai.inference import _ChatCompletionsClient as _c
        from azure.ai.inference.models import SystemMessage as _s, UserMessage as _u
        from azure.core.credentials import AzureKeyCredential as _k

        _ChatCompletionsClient = _c
        _AzureKeyCredential = _k
        _SystemMessage = _s
        _UserMessage = _u


def _ensure_direct_openai():
    global _OpenAI
    if _OpenAI is None:
        from openai import OpenAI as _o

        _OpenAI = _o


def check_base_url(url: str) -> str:
    """Normalize OpenAI-compatible base URLs."""
    url = (url or "").strip()
    if not url:
        return url
    if url.endswith("#"):
        return url.rstrip("#")
    if not re.search(r"/v\d+$", url) and "/v1" not in url:
        url = url.rstrip("/") + "/v1"
    return url


class BaseLLMAdapter:
    """Base adapter with structured error tracking."""

    def __init__(self, cancel_token=None, provider: str = "", model_name: str = "", base_url: str = ""):
        self.last_error: str = ""
        self.last_error_info: dict | None = None
        self._cancel_token = cancel_token
        self.provider = provider
        self.model_name = model_name
        self.base_url = base_url

    def _reset_error_state(self) -> None:
        self.last_error = ""
        self.last_error_info = None

    def _record_exception(self, exc: Exception) -> dict:
        info = classify_llm_exception(
            exc,
            provider=self.provider,
            model_name=self.model_name,
            base_url=self.base_url,
        )
        self.last_error = info.detail
        self.last_error_info = info.to_dict()
        return self.last_error_info

    def _log_failure(self, info: dict, exc: Exception, provider_label: str) -> None:
        level = logging.WARNING if info.get("category") in {
            "config_missing",
            "auth_failed",
            "provider_4xx",
            "parse_failure",
        } else logging.ERROR
        logger.log(
            level,
            "%s 调用失败 [category=%s code=%s status=%s provider=%s model=%s base_url=%s]: %s",
            provider_label,
            info.get("category"),
            info.get("code"),
            info.get("status_code"),
            info.get("provider") or self.provider,
            info.get("model_name") or self.model_name,
            info.get("base_url") or self.base_url,
            info.get("detail"),
            exc_info=level >= logging.ERROR,
        )

    def invoke(self, prompt: str) -> str:
        raise NotImplementedError("Subclasses must implement .invoke(prompt) method.")

    def cancel(self) -> None:
        if self._cancel_token is not None:
            self._cancel_token.cancel()

    @property
    def cancel_token(self):
        return self._cancel_token


class OpenAICompatibleAdapter(BaseLLMAdapter):
    """Adapter for OpenAI-compatible chat endpoints."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model_name: str,
        max_tokens: int,
        temperature: float = 0.7,
        timeout: Optional[int] = 600,
        cancel_token=None,
    ):
        normalized_base_url = check_base_url(base_url)
        super().__init__(
            cancel_token=cancel_token,
            provider="OpenAICompatible",
            model_name=model_name,
            base_url=normalized_base_url,
        )
        _ensure_openai()
        kwargs: dict = dict(
            model=model_name,
            api_key=api_key or "ollama",
            base_url=normalized_base_url,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
            max_retries=1,
        )
        if cancel_token is not None:
            kwargs["http_client"] = _make_cancel_client(cancel_token, float(timeout or 600))
        self._client = _ChatOpenAI(**kwargs)

    def invoke(self, prompt: str) -> str:
        self._reset_error_state()
        try:
            response = self._client.invoke(prompt)
            if not response:
                self.last_error = "No response from LLM"
                return ""
            return response.content
        except Exception as exc:
            info = self._record_exception(exc)
            if self._cancel_token and self._cancel_token.is_set():
                logger.info("LLM 调用因用户取消而中断")
            else:
                self._log_failure(info, exc, "OpenAI-compatible")
            return ""


class OpenAIDirectAdapter(BaseLLMAdapter):
    """Adapter for providers better served by the official OpenAI SDK."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model_name: str,
        max_tokens: int,
        temperature: float = 0.7,
        timeout: Optional[int] = 600,
        system_prompt: str = "You are a helpful assistant.",
        cancel_token=None,
    ):
        normalized_base_url = check_base_url(base_url)
        super().__init__(
            cancel_token=cancel_token,
            provider="OpenAIDirect",
            model_name=model_name,
            base_url=normalized_base_url,
        )
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout
        self.system_prompt = system_prompt
        _ensure_direct_openai()
        kwargs: dict = dict(base_url=normalized_base_url, api_key=api_key, timeout=timeout, max_retries=1)
        if cancel_token is not None:
            kwargs["http_client"] = _make_cancel_client(cancel_token, float(timeout or 600))
        self._client = _OpenAI(**kwargs)

    def invoke(self, prompt: str) -> str:
        self._reset_error_state()
        try:
            response = self._client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                timeout=self.timeout,
            )
            if response and response.choices:
                return response.choices[0].message.content
            self.last_error = "No response from LLM"
            return ""
        except Exception as exc:
            info = self._record_exception(exc)
            if self._cancel_token and self._cancel_token.is_set():
                logger.info("LLM 调用因用户取消而中断")
            else:
                self._log_failure(info, exc, "OpenAI-direct")
            return ""


class GeminiAdapter(BaseLLMAdapter):
    """Adapter for Google Gemini."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model_name: str,
        max_tokens: int,
        temperature: float = 0.7,
        timeout: Optional[int] = 600,
        cancel_token=None,
    ):
        super().__init__(
            cancel_token=cancel_token,
            provider="Gemini",
            model_name=model_name,
            base_url=base_url,
        )
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature
        _ensure_google()
        client_kwargs: dict = dict(api_key=api_key)
        if cancel_token is not None:
            http_client = _make_cancel_client(cancel_token, float(timeout or 600))
            client_kwargs["http_options"] = {"transport": http_client}
        self._client = _genai.Client(**client_kwargs)

    def invoke(self, prompt: str) -> str:
        self._reset_error_state()
        try:
            config = _types.GenerateContentConfig(
                max_output_tokens=self.max_tokens,
                temperature=self.temperature,
            )
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config,
            )
            if response and response.text:
                return response.text
            self.last_error = "No text response from Gemini API"
            return ""
        except Exception as exc:
            info = self._record_exception(exc)
            if self._cancel_token and self._cancel_token.is_set():
                logger.info("Gemini 调用因用户取消而中断")
            else:
                self._log_failure(info, exc, "Gemini")
            return ""


class AzureOpenAIAdapter(BaseLLMAdapter):
    """Adapter for Azure OpenAI."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model_name: str,
        max_tokens: int,
        temperature: float = 0.7,
        timeout: Optional[int] = 600,
        cancel_token=None,
    ):
        super().__init__(
            cancel_token=cancel_token,
            provider="AzureOpenAI",
            model_name=model_name,
            base_url=base_url,
        )
        match = re.match(
            r"https://(.+?)/openai/deployments/(.+?)/chat/completions\?api-version=(.+)",
            base_url,
        )
        if not match:
            raise ValueError("Invalid Azure OpenAI base_url format")
        _ensure_openai()
        kwargs: dict = dict(
            azure_endpoint=f"https://{match.group(1)}",
            azure_deployment=match.group(2),
            api_version=match.group(3),
            api_key=api_key,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
            max_retries=1,
        )
        if cancel_token is not None:
            kwargs["http_client"] = _make_cancel_client(cancel_token, float(timeout or 600))
        self._client = _AzureChatOpenAI(**kwargs)

    def invoke(self, prompt: str) -> str:
        self._reset_error_state()
        try:
            response = self._client.invoke(prompt)
            if not response:
                self.last_error = "No response from Azure OpenAI"
                return ""
            return response.content
        except Exception as exc:
            info = self._record_exception(exc)
            if self._cancel_token and self._cancel_token.is_set():
                logger.info("Azure OpenAI 调用因用户取消而中断")
            else:
                self._log_failure(info, exc, "Azure OpenAI")
            return ""


class AzureAIAdapter(BaseLLMAdapter):
    """Adapter for Azure AI Inference."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model_name: str,
        max_tokens: int,
        temperature: float = 0.7,
        timeout: Optional[int] = 600,
        cancel_token=None,
    ):
        super().__init__(
            cancel_token=cancel_token,
            provider="AzureAI",
            model_name=model_name,
            base_url=base_url,
        )
        match = re.match(
            r"https://(.+?)\.services\.ai\.azure\.com(?:/models)?(?:/chat/completions)?(?:\?api-version=(.+))?",
            base_url,
        )
        if not match:
            raise ValueError(
                "Invalid Azure AI base_url format. "
                "Expected: https://<endpoint>.services.ai.azure.com/models/chat/completions?api-version=xxx"
            )
        _ensure_azure()
        self._client = _ChatCompletionsClient(
            endpoint=f"https://{match.group(1)}.services.ai.azure.com/models",
            credential=_AzureKeyCredential(api_key),
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    def invoke(self, prompt: str) -> str:
        self._reset_error_state()
        try:
            response = self._client.complete(
                messages=[
                    _SystemMessage("You are a helpful assistant."),
                    _UserMessage(prompt),
                ]
            )
            if response and response.choices:
                return response.choices[0].message.content
            self.last_error = "No response from Azure AI"
            return ""
        except Exception as exc:
            info = self._record_exception(exc)
            if self._cancel_token and self._cancel_token.is_set():
                logger.info("Azure AI 调用因用户取消而中断")
            else:
                self._log_failure(info, exc, "Azure AI")
            return ""


class AnthropicAdapter(BaseLLMAdapter):
    """Adapter for Anthropic Claude Messages API."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model_name: str,
        max_tokens: int,
        temperature: float = 0.7,
        timeout: Optional[int] = 600,
        cancel_token=None,
    ):
        normalized_base_url = check_base_url(base_url).rstrip("/")
        super().__init__(
            cancel_token=cancel_token,
            provider="Anthropic",
            model_name=model_name,
            base_url=normalized_base_url,
        )
        self.api_key = api_key
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout

    def invoke(self, prompt: str) -> str:
        self._reset_error_state()
        try:
            import requests

            response = requests.post(
                f"{self.base_url}/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.model_name,
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            parts = data.get("content") or []
            text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
            if not text:
                self.last_error = "No text response from Anthropic API"
            return text
        except Exception as exc:
            info = self._record_exception(exc)
            self._log_failure(info, exc, "Anthropic")
            return ""


def create_llm_adapter(
    interface_format: str,
    base_url: str,
    model_name: str,
    api_key: str,
    temperature: float,
    max_tokens: int,
    timeout: int,
    cancel_token=None,
) -> BaseLLMAdapter:
    """Factory that returns an adapter based on ``interface_format``."""
    fmt = (interface_format or "").strip().lower()

    if not fmt:
        raise ValueError("LLM 配置缺少接口类型。")

    requires_api_key = fmt not in {"ollama"}
    requires_base_url = fmt not in {"gemini"}

    if requires_api_key and not (api_key or "").strip():
        raise ValueError(
            f"LLM 配置错误：API Key 为空（模型: {model_name or '未设置'}）。请在设置中填写有效的 API Key。"
        )
    if requires_base_url and not (base_url or "").strip():
        raise ValueError(
            f"LLM 配置错误：Base URL 为空（模型: {model_name or '未设置'}）。请在设置中填写 Base URL。"
        )
    if not (model_name or "").strip():
        raise ValueError("LLM 配置错误：模型名称为空。请在设置中填写模型名称。")

    if (model_name or "").strip().startswith(("http://", "https://")):
        raise ValueError("模型名不能是 URL，请检查 baseUrl 和 model 字段是否传反。")
    if requires_base_url and not (base_url or "").strip().startswith(("http://", "https://")):
        raise ValueError("Base URL 必须以 http:// 或 https:// 开头。")

    if fmt in {"deepseek", "openai", "ollama", "ml studio", "阿里云百炼", "alibaba bailian"}:
        return OpenAICompatibleAdapter(
            api_key,
            base_url,
            model_name,
            max_tokens,
            temperature,
            timeout,
            cancel_token=cancel_token,
        )

    if fmt in {"火山引擎", "volcengine"}:
        return OpenAIDirectAdapter(
            api_key,
            base_url,
            model_name,
            max_tokens,
            temperature,
            timeout,
            system_prompt="你是 DeepSeek，是一个 AI 人工智能助手",
            cancel_token=cancel_token,
        )

    if fmt in {"硅基流动", "siliconflow"}:
        return OpenAIDirectAdapter(
            api_key,
            base_url,
            model_name,
            max_tokens,
            temperature,
            timeout,
            system_prompt="你是 DeepSeek，是一个 AI 人工智能助手",
            cancel_token=cancel_token,
        )

    if fmt == "grok":
        return OpenAIDirectAdapter(
            api_key,
            base_url,
            model_name,
            max_tokens,
            temperature,
            timeout,
            system_prompt="You are Grok, created by xAI.",
            cancel_token=cancel_token,
        )

    if fmt == "azure openai":
        return AzureOpenAIAdapter(api_key, base_url, model_name, max_tokens, temperature, timeout, cancel_token=cancel_token)

    if fmt == "azure ai":
        return AzureAIAdapter(api_key, base_url, model_name, max_tokens, temperature, timeout, cancel_token=cancel_token)

    if fmt == "gemini":
        return GeminiAdapter(api_key, base_url, model_name, max_tokens, temperature, timeout, cancel_token=cancel_token)

    if fmt == "anthropic":
        return AnthropicAdapter(api_key, base_url, model_name, max_tokens, temperature, timeout, cancel_token=cancel_token)

    raise ValueError(f"Unknown interface_format: {interface_format}")
