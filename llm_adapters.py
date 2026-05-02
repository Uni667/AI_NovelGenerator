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
    """统一的 LLM 接口基类"""
    def __init__(self):
        self.last_error: str = ""

    def invoke(self, prompt: str) -> str:
        raise NotImplementedError("Subclasses must implement .invoke(prompt) method.")


class OpenAICompatibleAdapter(BaseLLMAdapter):
    """通用 OpenAI 兼容接口适配器（DeepSeek / OpenAI / Ollama / ML Studio 等）"""
    def __init__(self, api_key: str, base_url: str, model_name: str,
                 max_tokens: int, temperature: float = 0.7,
                 timeout: Optional[int] = 600):
        super().__init__()
        _ensure_openai()
        self._client = _ChatOpenAI(
            model=model_name,
            api_key=api_key or 'ollama',
            base_url=check_base_url(base_url),
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout
        )

    def invoke(self, prompt: str) -> str:
        try:
            response = self._client.invoke(prompt)
            if not response:
                self.last_error = "No response from LLM"
                return ""
            return response.content
        except Exception as e:
            self.last_error = str(e)
            logging.error(f"API 调用失败: {e}")
            return ""


class OpenAIDirectAdapter(BaseLLMAdapter):
    """通用 OpenAI 直连适配器（火山引擎 / 硅基流动 / Grok 等）"""
    def __init__(self, api_key: str, base_url: str, model_name: str,
                 max_tokens: int, temperature: float = 0.7,
                 timeout: Optional[int] = 600,
                 system_prompt: str = "You are a helpful assistant."):
        super().__init__()
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout
        self.system_prompt = system_prompt
        _ensure_direct_openai()
        self._client = _OpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout
        )

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
            logging.error(f"API 调用失败: {e}")
            return ""


class GeminiAdapter(BaseLLMAdapter):
    """适配 Google Gemini 接口"""
    def __init__(self, api_key: str, base_url: str, model_name: str,
                 max_tokens: int, temperature: float = 0.7,
                 timeout: Optional[int] = 600):
        super().__init__()
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature
        _ensure_google()
        self._client = _genai.Client(api_key=api_key)

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
            logging.error(f"Gemini API 调用失败: {e}")
            return ""


class AzureOpenAIAdapter(BaseLLMAdapter):
    """适配 Azure OpenAI 接口"""
    def __init__(self, api_key: str, base_url: str, model_name: str,
                 max_tokens: int, temperature: float = 0.7,
                 timeout: Optional[int] = 600):
        super().__init__()
        match = re.match(
            r'https://(.+?)/openai/deployments/(.+?)/chat/completions\?api-version=(.+)',
            base_url
        )
        if not match:
            raise ValueError("Invalid Azure OpenAI base_url format")
        _ensure_openai()
        self._client = _AzureChatOpenAI(
            azure_endpoint=f"https://{match.group(1)}",
            azure_deployment=match.group(2),
            api_version=match.group(3),
            api_key=api_key,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout
        )

    def invoke(self, prompt: str) -> str:
        try:
            response = self._client.invoke(prompt)
            if not response:
                self.last_error = "No response from Azure OpenAI"
                return ""
            return response.content
        except Exception as e:
            self.last_error = str(e)
            logging.error(f"Azure OpenAI API 调用失败: {e}")
            return ""


class AzureAIAdapter(BaseLLMAdapter):
    """适配 Azure AI Inference 接口"""
    def __init__(self, api_key: str, base_url: str, model_name: str,
                 max_tokens: int, temperature: float = 0.7,
                 timeout: Optional[int] = 600):
        super().__init__()
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
            logging.error(f"Azure AI Inference API 调用失败: {e}")
            return ""


def create_llm_adapter(
    interface_format: str,
    base_url: str,
    model_name: str,
    api_key: str,
    temperature: float,
    max_tokens: int,
    timeout: int
) -> BaseLLMAdapter:
    """工厂函数：根据 interface_format 返回不同的适配器实例"""
    fmt = interface_format.strip().lower()

    if fmt in ("deepseek", "openai", "ollama", "ml studio", "阿里云百炼", "alibaba bailian"):
        return OpenAICompatibleAdapter(api_key, base_url, model_name, max_tokens, temperature, timeout)

    if fmt in ("火山引擎", "volcengine"):
        return OpenAIDirectAdapter(api_key, base_url, model_name,
                                   max_tokens, temperature, timeout,
                                   system_prompt="你是 DeepSeek，是一个 AI 人工智能助手")

    if fmt in ("硅基流动", "siliconflow"):
        return OpenAIDirectAdapter(api_key, base_url, model_name,
                                   max_tokens, temperature, timeout,
                                   system_prompt="你是 DeepSeek，是一个 AI 人工智能助手")

    if fmt == "grok":
        return OpenAIDirectAdapter(api_key, base_url, model_name,
                                   max_tokens, temperature, timeout,
                                   system_prompt="You are Grok, created by xAI.")

    if fmt == "azure openai":
        return AzureOpenAIAdapter(api_key, base_url, model_name, max_tokens, temperature, timeout)

    if fmt == "azure ai":
        return AzureAIAdapter(api_key, base_url, model_name, max_tokens, temperature, timeout)

    if fmt == "gemini":
        return GeminiAdapter(api_key, base_url, model_name, max_tokens, temperature, timeout)

    raise ValueError(f"Unknown interface_format: {interface_format}")
