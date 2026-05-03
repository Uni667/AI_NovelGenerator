"""
GenerationContext — 统一配置数据类，取代散落的 20+ 单独参数。
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LLMConfig:
    interface_format: str = "OpenAI"
    api_key: str = ""
    base_url: str = ""
    model_name: str = ""
    temperature: float = 0.7
    max_tokens: int = 8192
    timeout: int = 600

    @classmethod
    def from_dict(cls, d: dict) -> "LLMConfig":
        return cls(
            interface_format=d.get("interface_format", "OpenAI"),
            api_key=d.get("api_key", ""),
            base_url=d.get("base_url", ""),
            model_name=d.get("model_name", ""),
            temperature=d.get("temperature", 0.7),
            max_tokens=d.get("max_tokens", 8192),
            timeout=d.get("timeout", 600),
        )


@dataclass
class EmbeddingConfig:
    interface_format: str = "OpenAI"
    api_key: str = ""
    base_url: str = ""
    model_name: str = ""
    retrieval_k: int = 4

    @classmethod
    def from_dict(cls, d: dict) -> "EmbeddingConfig":
        if not d:
            return cls()
        return cls(
            interface_format=d.get("interface_format", "OpenAI"),
            api_key=d.get("api_key", ""),
            base_url=d.get("base_url", ""),
            model_name=d.get("model_name", ""),
            retrieval_k=d.get("retrieval_k", 4),
        )


@dataclass
class ChapterParams:
    """当前章节的元信息，从章节蓝图中解析或由用户指定。"""
    chapter_number: int = 0
    chapter_title: str = ""
    chapter_role: str = ""
    chapter_purpose: str = ""
    suspense_level: str = "中等"
    foreshadowing: str = "无"
    plot_twist_level: str = "★☆☆☆☆"
    chapter_summary: str = ""
    characters_involved: str = ""
    key_items: str = ""
    scene_location: str = ""
    time_constraint: str = ""
    word_number: int = 3000
    user_guidance: str = ""


@dataclass
class ProjectConfig:
    """项目级别的全局配置。"""
    topic: str = ""
    genre: str = ""
    category: str = ""
    platform: str = "tomato"
    num_chapters: int = 0
    word_number: int = 3000
    language: str = "zh"
    user_guidance: str = ""


@dataclass
class GenerationContext:
    """一次生成操作所需的全部配置上下文。"""
    llm: LLMConfig = field(default_factory=LLMConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    filepath: str = ""
    project_id: str = ""

    @property
    def is_english(self) -> bool:
        return False

    @classmethod
    def from_dicts(
        cls,
        llm_dict: dict,
        emb_dict: Optional[dict] = None,
        filepath: str = "",
        project_id: str = "",
    ) -> "GenerationContext":
        return cls(
            llm=LLMConfig.from_dict(llm_dict),
            embedding=EmbeddingConfig.from_dict(emb_dict or {}),
            filepath=filepath,
            project_id=project_id,
        )
