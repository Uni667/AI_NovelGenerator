# llm_adapters.py
# -*- coding: utf-8 -*-
import logging
import re
from typing import Optional

# Lazy imports — only fail when a specific adapter is actually used
_ChatOpenAI = _AzureChatOpenAI = None
_genai = _types = None
__ChatCompletionsClient = _AzureKeyCredential = _SystemMessage = _UserMessage = None
_OpenAI = None
_httpx = None
_CancelToken = None


def _ensure_httpx():
    global _httpx
    if _httpx is None:
        import httpx as _h
        _httpx = _h


def _make_cancel_client(cancel_token, timeout: float) -> object:
    """Build an httpx.Client whose transport checks CancelToken before requests.

    When cancel_token is set, the transport raises so the in-flight request
    fails fast. This is the transport-level counterpart of cooperative checks.
    """
    _ensure_httpx()
    transport = _httpx.HTTPTransport()

    class _CancelTransport(_httpx.BaseTransport):
        def __init__(self, wrapped, token):
            self._wrapped = wrapped
            self._token = token

        def handle_request(self, request):
            # Check BEFORE sending the request
            if self._token is not None and self._token.is_set():
                from novel_generator.task_manager import TaskCancelledError
                raise TaskCancelledError("请求已被用户取消")
            return self._wrapped.handle_request(request)

        def close(self):
            return self._wrapped.close()

    wrapped = _CancelTransport(transport, cancel_token)
    client = _httpx.Client(transport=wrapped, timeout=timeout)
    # Bind so cancel() can force-close all connections
    if cancel_token is not None:
        cancel_token.bind(client)
    return client

def _ensure_openai():
    global _ChatOpenAI, _AzureChatOpenAI
    if _ChatOpenAI is None:
        from langchain_openai import ChatOpenAI, AzureChatOpenAI
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
    global __ChatCompletionsClient, _AzureKeyCredential, _SystemMessage, _UserMessage
    if __ChatCompletionsClient is None:
        from azure.ai.inference import _ChatCompletionsClient as _c
        from azure.core.credentials import AzureKeyCredential as _k
        from azure.ai.inference.models import SystemMessage as _s, UserMessage as _u
        __ChatCompletionsClient = _c
        _AzureKeyCredential = _k
        _SystemMessage = _s
        _UserMessage = _u

def _ensure_direct_openai():
    global _OpenAI
    if _OpenAI is None:
        from openai import OpenAI as _o
        _OpenAI = _o


def check_base_url(url: str) -> str:
    """处理base_url：以#结尾则去除#，否则检查是否需要添加/v1后缀"""
    url = url.strip()
    if not url:
        return url
    if url.endswith('#'):
        return url.rstrip('#')
    if not re.search(r'/v\d+$', url) and '/v1' not in url:
        url = url.rstrip('/') + '/v1'
    return url


class BaseLLMAdapter:
    """统一的 LLM 接口基类，可选绑定 CancelToken 以支持 HTTP abort"""

    def __init__(self, cancel_token=None):
        self.last_error: str = ""
        self._cancel_token = cancel_token

    def invoke(self, prompt: str) -> str:
        raise NotImplementedError("Subclasses must implement .invoke(prompt) method.")

    def cancel(self) -> None:
        """触发传输层中断：关闭底层 httpx client，中断进行中的请求"""
        if self._cancel_token is not None:
            self._cancel_token.cancel()

    @property
    def cancel_token(self):
        return self._cancel_token


class OpenAICompatibleAdapter(BaseLLMAdapter):
    """通用 OpenAI 兼容接口适配器（DeepSeek / OpenAI / Ollama / ML Studio 等）"""
    def __init__(self, api_key: str, base_url: str, model_name: str,
                 max_tokens: int, temperature: float = 0.7,
                 timeout: Optional[int] = 600, cancel_token=None):
        super().__init__(cancel_token=cancel_token)
        _ensure_openai()
        kwargs: dict = dict(
            model=model_name,
            api_key=api_key or 'ollama',
            base_url=check_base_url(base_url),
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
        )
        if cancel_token is not None:
            kwargs["http_client"] = _make_cancel_client(cancel_token, float(timeout or 600))
        self._client = _ChatOpenAI(**kwargs)

    def invoke(self, prompt: str) -> str:
        try:
            response = self._client.invoke(prompt)
            if not response:
                self.last_error = "No response from LLM"
                return ""
            return response.content
        except Exception as e:
            self.last_error = str(e)
            if self._cancel_token and self._cancel_token.is_set():
                logging.info("LLM 调用因用户取消而中断")
            else:
                logging.error(f"API 调用失败: {e}")
            return ""


class OpenAIDirectAdapter(BaseLLMAdapter):
    """通用 OpenAI 直连适配器（火山引擎 / 硅基流动 / Grok 等）"""
    def __init__(self, api_key: str, base_url: str, model_name: str,
                 max_tokens: int, temperature: float = 0.7,
                 timeout: Optional[int] = 600,
                 system_prompt: str = "You are a helpful assistant.",
                 cancel_token=None):
        super().__init__(cancel_token=cancel_token)
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout
        self.system_prompt = system_prompt
        _ensure_direct_openai()
        kwargs: dict = dict(base_url=base_url, api_key=api_key, timeout=timeout)
        if cancel_token is not None:
            kwargs["http_client"] = _make_cancel_client(cancel_token, float(timeout or 600))
        self._client = _OpenAI(**kwargs)

    def invoke(self, prompt: str) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                timeout=self.timeout
            )
            if response and response.choices:
                return response.choices[0].message.content
            self.last_error = "No response from LLM"
            return ""
        except Exception as e:
            self.last_error = str(e)
            if self._cancel_token and self._cancel_token.is_set():
                logging.info("LLM 调用因用户取消而中断")
            else:
                logging.error(f"API 调用失败: {e}")
            return ""


class GeminiAdapter(BaseLLMAdapter):
    """适配 Google Gemini 接口"""
    def __init__(self, api_key: str, base_url: str, model_name: str,
                 max_tokens: int, temperature: float = 0.7,
                 timeout: Optional[int] = 600, cancel_token=None):
        super().__init__(cancel_token=cancel_token)
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature
        _ensure_google()
        # google-genai SDK supports custom httpx client via http_options
        client_kwargs: dict = dict(api_key=api_key)
        if cancel_token is not None:
            _ensure_httpx()
            http_client = _make_cancel_client(cancel_token, float(timeout or 600))
            client_kwargs["http_options"] = {"transport": http_client}
        self._client = _genai.Client(**client_kwargs)

    def invoke(self, prompt: str) -> str:
        try:
            config = _types.GenerateContentConfig(
                max_output_tokens=self.max_tokens,
                temperature=self.temperature,
            )
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )
            if response and response.text:
                return response.text
            self.last_error = "No text response from Gemini API"
            return ""
        except Exception as e:
            self.last_error = str(e)
            if self._cancel_token and self._cancel_token.is_set():
                logging.info("Gemini 调用因用户取消而中断")
            else:
                logging.error(f"Gemini API 调用失败: {e}")
            return ""


class AzureOpenAIAdapter(BaseLLMAdapter):
    """适配 Azure OpenAI 接口"""
    def __init__(self, api_key: str, base_url: str, model_name: str,
                 max_tokens: int, temperature: float = 0.7,
                 timeout: Optional[int] = 600, cancel_token=None):
        super().__init__(cancel_token=cancel_token)
        match = re.match(
            r'https://(.+?)/openai/deployments/(.+?)/chat/completions\?api-version=(.+)',
            base_url
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
        )
        if cancel_token is not None:
            kwargs["http_client"] = _make_cancel_client(cancel_token, float(timeout or 600))
        self._client = _AzureChatOpenAI(**kwargs)

    def invoke(self, prompt: str) -> str:
        try:
            response = self._client.invoke(prompt)
            if not response:
                self.last_error = "No response from Azure OpenAI"
                return ""
            return response.content
        except Exception as e:
            self.last_error = str(e)
            if self._cancel_token and self._cancel_token.is_set():
                logging.info("Azure OpenAI 调用因用户取消而中断")
            else:
                logging.error(f"Azure OpenAI API 调用失败: {e}")
            return ""


class AzureAIAdapter(BaseLLMAdapter):
    """适配 Azure AI Inference 接口（降级取消：仅协作检查，不支持 HTTP abort）"""
    def __init__(self, api_key: str, base_url: str, model_name: str,
                 max_tokens: int, temperature: float = 0.7,
                 timeout: Optional[int] = 600, cancel_token=None):
        super().__init__(cancel_token=cancel_token)
        match = re.match(
            r'https://(.+?)\.services\.ai\.azure\.com(?:/models)?(?:/chat/completions)?(?:\?api-version=(.+))?',
            base_url
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
            timeout=timeout
        )
        self._supports_abort = False  # Azure AI SDK 不暴露底层 HTTP client

    def invoke(self, prompt: str) -> str:
        try:
            response = self._client.complete(
                messages=[
                    _SystemMessage("You are a helpful assistant."),
                    _UserMessage(prompt)
                ]
            )
            if response and response.choices:
                return response.choices[0].message.content
            self.last_error = "No response from Azure AI"
            return ""
        except Exception as e:
            self.last_error = str(e)
            if self._cancel_token and self._cancel_token.is_set():
                logging.info("Azure AI 调用因用户取消而中断")
            else:
                logging.error(f"Azure AI Inference API 调用失败: {e}")
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
    """工厂函数：根据 interface_format 返回不同的适配器实例。

    cancel_token: 可选的 CancelToken，用于支持 HTTP 传输层 abort。
    """
    fmt = interface_format.strip().lower()

    if fmt in ("deepseek", "openai", "ollama", "ml studio", "阿里云百炼", "alibaba bailian"):
        return OpenAICompatibleAdapter(api_key, base_url, model_name, max_tokens, temperature, timeout,
                                       cancel_token=cancel_token)

    if fmt in ("火山引擎", "volcengine"):
        return OpenAIDirectAdapter(api_key, base_url, model_name,
                                   max_tokens, temperature, timeout,
                                   system_prompt="你是 DeepSeek，是一个 AI 人工智能助手",
                                   cancel_token=cancel_token)

    if fmt in ("硅基流动", "siliconflow"):
        return OpenAIDirectAdapter(api_key, base_url, model_name,
                                   max_tokens, temperature, timeout,
                                   system_prompt="你是 DeepSeek，是一个 AI 人工智能助手",
                                   cancel_token=cancel_token)

    if fmt == "grok":
        return OpenAIDirectAdapter(api_key, base_url, model_name,
                                   max_tokens, temperature, timeout,
                                   system_prompt="You are Grok, created by xAI.",
                                   cancel_token=cancel_token)

    if fmt == "azure openai":
        return AzureOpenAIAdapter(api_key, base_url, model_name, max_tokens, temperature, timeout,
                                  cancel_token=cancel_token)

    if fmt == "azure ai":
        return AzureAIAdapter(api_key, base_url, model_name, max_tokens, temperature, timeout,
                              cancel_token=cancel_token)

    if fmt == "gemini":
        return GeminiAdapter(api_key, base_url, model_name, max_tokens, temperature, timeout,
                             cancel_token=cancel_token)

    raise ValueError(f"Unknown interface_format: {interface_format}")
