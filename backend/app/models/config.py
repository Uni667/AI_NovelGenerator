from pydantic import BaseModel, Field
from typing import Optional, List


class LLMConfigCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    api_key: str
    base_url: str = "https://api.openai.com/v1"
    model_name: str = "gpt-4o-mini"
    temperature: float = Field(default=0.7, ge=0, le=2.0)
    max_tokens: int = Field(default=8192, ge=1, le=200000)
    timeout: int = Field(default=600, ge=10, le=3600)
    interface_format: str = "OpenAI"


class LLMConfigUpdate(BaseModel):
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model_name: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    timeout: Optional[int] = None
    interface_format: Optional[str] = None


class LLMConfigResponse(BaseModel):
    name: str
    base_url: str
    model_name: str
    temperature: float
    max_tokens: int
    timeout: int
    interface_format: str
    api_key_masked: str


class EmbeddingConfigCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    api_key: str
    base_url: str = "https://api.openai.com/v1"
    model_name: str = "text-embedding-ada-002"
    retrieval_k: int = Field(default=4, ge=1, le=20)
    interface_format: str = "OpenAI"


class EmbeddingConfigUpdate(BaseModel):
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model_name: Optional[str] = None
    retrieval_k: Optional[int] = None
    interface_format: Optional[str] = None


class EmbeddingConfigResponse(BaseModel):
    name: str
    base_url: str
    model_name: str
    retrieval_k: int
    interface_format: str
    api_key_masked: str


class ConfigTestResponse(BaseModel):
    success: bool
    message: str
