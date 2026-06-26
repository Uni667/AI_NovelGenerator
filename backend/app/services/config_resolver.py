"""
Config Resolver Service — 解析模型运行时配置，从数据库组装参数。
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from backend.app.database import get_db
from backend.app.errors import (
    base_url_invalid,
    model_config_incomplete,
    model_name_invalid,
)
from backend.app.utils.crypto import decrypt_api_key

logger = logging.getLogger(__name__)

PURPOSE_MAP = {
    "architecture": "architecture_profile_id",
    "worldbuilding": "worldbuilding_profile_id",
    "character": "character_profile_id",
    "outline": "outline_profile_id",
    "draft": "draft_profile_id",
    "blueprint_polish": "outline_profile_id",
    "architecture_polish": "review_profile_id",
    "voice_polish": "polish_profile_id",
    "quality_rewrite": "review_profile_id",
    "polish": "polish_profile_id",
    "review": "review_profile_id",
    "summary": "summary_profile_id",
    "feedback": "feedback_profile_id",
    "embedding": "embedding_profile_id",
    "rerank": "rerank_profile_id",
}

PROVIDER_DEFAULTS = {
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com",
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "anthropic": "https://api.anthropic.com",
    "siliconflow": "https://api.siliconflow.cn/v1",
    "custom": "",
    "local": "http://localhost:11434",
}

PROVIDER_DEFAULT_CHAT_MODELS = {
    "siliconflow": "deepseek-ai/DeepSeek-V3",
    "deepseek": "deepseek-chat",
    "openai": "gpt-4o-mini",
    "qwen": "qwen-plus",
    "anthropic": "claude-3-5-haiku-latest",
    "custom": "",
    "local": "",
}

PROVIDER_DEFAULT_EMBEDDING_MODELS = {
    "siliconflow": "BAAI/bge-m3",
    "openai": "text-embedding-3-small",
    "qwen": "text-embedding-v3",
    "custom": "",
    "local": "",
    # deepseek/anthropic do not have standard embeddings typically configured here
}

SUPPORTED_CHAT_PROVIDERS = {"openai", "deepseek", "qwen", "anthropic", "siliconflow", "custom", "local"}

# 智能路由偏好配置：定义各种用途优先选择的 provider 和 model
SMART_ROUTING_PREFERENCES = {
    "chat": [
        ("deepseek", "deepseek-chat"),
        ("qwen", "qwen-plus"),
        ("siliconflow", "deepseek-ai/DeepSeek-V3"),
        ("openai", "gpt-4o-mini"),
    ],
    "outline": [
        ("deepseek", "deepseek-reasoner"),
        ("openai", "gpt-4o"),
        ("siliconflow", "deepseek-ai/DeepSeek-R1"),
        ("anthropic", "claude-3-5-sonnet-latest"),
    ],
    "embedding": [
        ("siliconflow", "BAAI/bge-m3"),
        ("openai", "text-embedding-3-small"),
        ("qwen", "text-embedding-v3"),
    ],
}


class ConfigError(Exception):
    """用户配置错误，信息可安全返回给前端。"""


@dataclass
class RuntimeConfig:
    api_credential_id: str = ""
    model_profile_id: str = ""
    provider: str = ""
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    type: str = "chat"
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 8192
    top_p: Optional[float] = None
    timeout: int = 600
    supports_streaming: bool = True
    supports_json: bool = True
    purpose: str = "general"
    extra_headers: dict = field(default_factory=dict)


def _is_http_url(value: str) -> bool:
    return bool((value or "").strip().startswith(("http://", "https://")))


def _strip_known_suffixes(base_url: str) -> str:
    url = (base_url or "").strip().rstrip("/")
    for suffix in ("/embeddings", "/chat/completions"):
        if url.endswith(suffix):
            url = url[: -len(suffix)]
    return url


def normalize_base_url(provider: str, base_url: str = "") -> str:
    provider = (provider or "").strip()
    url = _strip_known_suffixes(base_url or PROVIDER_DEFAULTS.get(provider, ""))
    if provider == "siliconflow":
        return PROVIDER_DEFAULTS["siliconflow"]
    return url


def infer_provider(provider: str, base_url: str = "") -> str:
    provider = (provider or "").strip()
    url = (base_url or "").lower()
    if provider == "custom" and "siliconflow.cn" in url:
        return "siliconflow"
    return provider


def _purpose_to_type(purpose: str) -> str:
    if purpose in ("embedding",):
        return "embedding"
    if purpose in ("rerank",):
        return "rerank"
    return "chat"


def _build_runtime(profile_id: str, purpose: str, user_id: str, allow_unhealthy: bool = False) -> RuntimeConfig:
    with get_db() as conn:
        profile = conn.execute(
            "SELECT * FROM model_profile WHERE id=? AND user_id=? AND is_active=1", (profile_id, user_id)
        ).fetchone()
        if not profile:
            raise ConfigError("模型配置不存在")
        profile = dict(profile)

    if not profile.get("is_active"):
        raise ConfigError(f"模型配置「{profile['name']}」已禁用")
    if not allow_unhealthy and profile.get("health_status") in ("disabled", "invalid"):
        raise ConfigError("模型配置异常，请重新测试或清空后重配。")

    expected_type = _purpose_to_type(purpose)
    if profile["type"] != expected_type:
        raise ConfigError(
            f"用途「{purpose}」需要 {expected_type} 类型的模型，"
            f"但「{profile['name']}」是 {profile['type']} 类型"
        )

    # 获取 API 凭证
    cred_id = profile.get("api_credential_id")
    if not cred_id:
        raise ConfigError(f"模型配置「{profile['name']}」没有绑定 API 凭证")

    with get_db() as conn:
        cred = conn.execute(
            "SELECT * FROM api_credential WHERE id=? AND user_id=?", (cred_id, user_id)
        ).fetchone()
        if not cred:
            raise ConfigError(f"API 凭证不存在或已被删除")
        cred = dict(cred)

    if not allow_unhealthy and cred.get("status") != "active":
        raise ConfigError(f"API 凭证「{cred['name']}」不可用，请先测试通过或重新启用。")

    # 解密 API Key
    api_key = ""
    if cred.get("api_key_encrypted"):
        try:
            api_key = decrypt_api_key(cred["api_key_encrypted"])
        except Exception as e:
            raise ConfigError(
                f"API 凭证「{cred['name']}」解密失败，请重新填写 API Key。"
            ) from e

    if profile["type"] != "embedding" and not api_key and cred["provider"] != "local":
        raise ConfigError(f"API 凭证「{cred['name']}」缺少 API Key")

    # 解析 headers
    extra_headers = {}
    if cred.get("headers_encrypted"):
        try:
            import json
            raw = decrypt_api_key(cred["headers_encrypted"])
            extra_headers = json.loads(raw) if raw else {}
        except Exception:
            logger.warning("Failed to decrypt headers for credential %s", cred.get("id", "?"), exc_info=True)

    provider_source = (cred.get("provider", "") or "").strip()
    raw_base_url = (cred.get("base_url", "") or "").strip().rstrip("/")
    provider = infer_provider(provider_source, raw_base_url)
    base_url = normalize_base_url(provider, raw_base_url)
    model_name = (profile["model"] or "").strip()
    
    if not model_name:
        raise ConfigError("当前模型配置不完整，建议清空后重新配置。")
    if model_name.startswith(("http://", "https://")):
        raise ConfigError("模型名配置异常，请清空后重新配置。")
    if (
        not _is_http_url(raw_base_url)
        or raw_base_url.endswith(("/embeddings", "/chat/completions"))
        or (provider == "siliconflow" and raw_base_url != PROVIDER_DEFAULTS["siliconflow"])
        or (provider_source == "custom" and "siliconflow.cn" in raw_base_url.lower())
    ):
        raise ConfigError("服务地址配置异常，请点击修复旧配置或清空后重配。")
    if provider not in SUPPORTED_CHAT_PROVIDERS:
        raise ConfigError("当前模型配置不完整，建议清空后重新配置。")
    if not allow_unhealthy and not profile.get("last_tested_at"):
        raise ConfigError("当前模型配置不完整，建议清空后重新配置。")

    return RuntimeConfig(
        api_credential_id=cred_id,
        model_profile_id=profile_id,
        provider=provider,
        base_url=base_url,
        api_key=api_key,
        model=model_name,
        type=profile["type"],
        temperature=profile.get("temperature") or 0.7,
        max_tokens=profile.get("max_tokens") or 8192,
        top_p=profile.get("top_p"),
        supports_streaming=bool(profile.get("supports_streaming", 1)),
        supports_json=bool(profile.get("supports_json", 1)),
        purpose=purpose,
        extra_headers=extra_headers,
    )


def get_runtime_config(
    user_id: str,
    purpose: str = "general",
    project_id: str | None = None,
) -> RuntimeConfig:
    """获取指定用途的完整运行时配置。"""
    candidates: list[str] = []

    if project_id and purpose in PURPOSE_MAP:
        field = PURPOSE_MAP[purpose]
        with get_db() as conn:
            project = conn.execute(
                "SELECT id FROM project WHERE id=? AND user_id=?",
                (project_id, user_id),
            ).fetchone()
            if not project:
                raise ConfigError("项目不存在或你没有权限访问。")
            row = conn.execute(
                f"SELECT {field} FROM project_model_assignment WHERE project_id=? AND user_id=?",
                (project_id, user_id),
            ).fetchone()
            if row and row[0]:
                candidates.append(row[0])

    with get_db() as conn:
        rows = conn.execute(
            """SELECT id FROM model_profile
               WHERE user_id=? AND is_default=1 AND is_active=1 AND purpose=?
               ORDER BY last_tested_at DESC, updated_at DESC""",
            (user_id, purpose),
        ).fetchall()
        candidates.extend([row[0] for row in rows if row and row[0] not in candidates])

    expected_type = _purpose_to_type(purpose)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id FROM model_profile
               WHERE user_id=? AND is_active=1 AND type=?
               ORDER BY is_default DESC, last_tested_at DESC, updated_at DESC""",
            (user_id, expected_type),
        ).fetchall()
        candidates.extend([row[0] for row in rows if row and row[0] not in candidates])

    last_error = ""
    for profile_id in candidates:
        try:
            return _build_runtime(profile_id, purpose, user_id)
        except ConfigError as exc:
            last_error = str(exc)

    if last_error:
        raise ConfigError(last_error)

    if expected_type == "chat":
        raise ConfigError("你还没有配置文本生成模型，请先完成模型设置。")
    raise ConfigError("当前没有可用的模型配置，请先完成模型设置。")
