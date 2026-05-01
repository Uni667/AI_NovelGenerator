# llm_adapters.py
# -*- coding: utf-8 -*-
import logging
import re
from typing import Optional
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from google import genai
from google.genai import types
from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.inference.models import SystemMessage, UserMessage
from openai import OpenAI


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
    def invoke(self, prompt: str) -> str:
        raise NotImplementedError("Subclasses must implement .invoke(prompt) method.")


class OpenAICompatibleAdapter(BaseLLMAdapter):
    """通用 OpenAI 兼容接口适配器（DeepSeek / OpenAI / Ollama / ML Studio 等）"""
    def __init__(self, api_key: str, base_url: str, model_name: str,
                 max_tokens: int, temperature: float = 0.7,
                 timeout: Optional[int] = 600):
        self._client = ChatOpenAI(
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
                logging.warning("No response from OpenAICompatibleAdapter.")
                return ""
            return response.content
        except Exception as e:
            logging.error(f"API 调用失败: {e}")
            return ""


class OpenAIDirectAdapter(BaseLLMAdapter):
    """通用 OpenAI 直连适配器（火山引擎 / 硅基流动 / Grok 等）"""
    def __init__(self, api_key: str, base_url: str, model_name: str,
                 max_tokens: int, temperature: float = 0.7,
                 timeout: Optional[int] = 600,
                 system_prompt: str = "You are a helpful assistant."):
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout
        self.system_prompt = system_prompt
        self._client = OpenAI(
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
            logging.warning("No response from OpenAIDirectAdapter.")
            return ""
        except Exception as e:
            logging.error(f"API 调用失败: {e}")
            return ""


class GeminiAdapter(BaseLLMAdapter):
    """适配 Google Gemini 接口"""
    def __init__(self, api_key: str, base_url: str, model_name: str,
                 max_tokens: int, temperature: float = 0.7,
                 timeout: Optional[int] = 600):
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._client = genai.Client(api_key=api_key)

    def invoke(self, prompt: str) -> str:
        try:
            config = types.GenerateContentConfig(
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
            logging.warning("No text response from Gemini API.")
            return ""
        except Exception as e:
            logging.error(f"Gemini API 调用失败: {e}")
            return ""


class AzureOpenAIAdapter(BaseLLMAdapter):
    """适配 Azure OpenAI 接口"""
    def __init__(self, api_key: str, base_url: str, model_name: str,
                 max_tokens: int, temperature: float = 0.7,
                 timeout: Optional[int] = 600):
        match = re.match(
            r'https://(.+?)/openai/deployments/(.+?)/chat/completions\?api-version=(.+)',
            base_url
        )
        if not match:
            raise ValueError("Invalid Azure OpenAI base_url format")
        self._client = AzureChatOpenAI(
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
                logging.warning("No response from AzureOpenAIAdapter.")
                return ""
            return response.content
        except Exception as e:
            logging.error(f"Azure OpenAI API 调用失败: {e}")
            return ""


class AzureAIAdapter(BaseLLMAdapter):
    """适配 Azure AI Inference 接口"""
    def __init__(self, api_key: str, base_url: str, model_name: str,
                 max_tokens: int, temperature: float = 0.7,
                 timeout: Optional[int] = 600):
        match = re.match(
            r'https://(.+?)\.services\.ai\.azure\.com(?:/models)?(?:/chat/completions)?(?:\?api-version=(.+))?',
            base_url
        )
        if not match:
            raise ValueError(
                "Invalid Azure AI base_url format. "
                "Expected: https://<endpoint>.services.ai.azure.com/models/chat/completions?api-version=xxx"
            )
        self._client = ChatCompletionsClient(
            endpoint=f"https://{match.group(1)}.services.ai.azure.com/models",
            credential=AzureKeyCredential(api_key),
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout
        )

    def invoke(self, prompt: str) -> str:
        try:
            response = self._client.complete(
                messages=[
                    SystemMessage("You are a helpful assistant."),
                    UserMessage(prompt)
                ]
            )
            if response and response.choices:
                return response.choices[0].message.content
            logging.warning("No response from AzureAIAdapter.")
            return ""
        except Exception as e:
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

    if fmt in ("deepseek", "openai", "ollama", "ml studio", "阿里云百炼"):
        return OpenAICompatibleAdapter(api_key, base_url, model_name, max_tokens, temperature, timeout)

    if fmt == "火山引擎":
        return OpenAIDirectAdapter(api_key, base_url, model_name,
                                   max_tokens, temperature, timeout,
                                   system_prompt="你是 DeepSeek，是一个 AI 人工智能助手")

    if fmt == "硅基流动":
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
