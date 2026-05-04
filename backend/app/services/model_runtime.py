"""
ModelRuntimeService — 统一模型调用层。

解析链:
  project_id + purpose → project_model_assignment → model_profile_id
  → model_profile (type, model, api_credential_id, params)
  → api_credential → decrypt api_key
  → call LLM / embedding

所有生成/向量化/知识库操作必须通过此服务。
"""

from __future__ import annotations

import datetime
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

from backend.app.database import get_db
from backend.app.utils.crypto import decrypt_api_key, mask_api_key

logger = logging.getLogger(__name__)

PURPOSE_MAP = {
    "architecture": "architecture_profile_id",
    "worldbuilding": "worldbuilding_profile_id",
    "character": "character_profile_id",
    "outline": "outline_profile_id",
    "draft": "draft_profile_id",
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
    "anthropic": "https://api.anthropic.com/v1",
    "custom": "",
    "local": "http://localhost:11434",
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
    supports_streaming: bool = True
    supports_json: bool = True
    purpose: str = "general"
    extra_headers: dict = field(default_factory=dict)


def get_runtime_config(
    user_id: str,
    purpose: str = "general",
    project_id: str | None = None,
) -> RuntimeConfig:
    """
    获取指定用途的完整运行时配置。

    解析顺序:
    1. 项目模型分配 (project_model_assignment)
    2. 用户默认模型 (model_profile.is_default=1 AND purpose match)
    3. 兜底：任意可用模型
    4. 以上都无 → ConfigError
    """
    profile_id = None

    # Step 1: 查项目模型分配
    if project_id and purpose in PURPOSE_MAP:
        field = PURPOSE_MAP[purpose]
        with get_db() as conn:
            row = conn.execute(
                f"SELECT {field} FROM project_model_assignment WHERE project_id=?",
                (project_id,),
            ).fetchone()
            if row and row[0]:
                profile_id = row[0]

    # Step 2: 查用户默认模型
    if not profile_id:
        with get_db() as conn:
            row = conn.execute(
                """SELECT id FROM model_profile
                   WHERE user_id=? AND is_default=1 AND is_active=1 AND purpose=?
                   LIMIT 1""",
                (user_id, purpose),
            ).fetchone()
            if row:
                profile_id = row[0]

    # Step 3: 任意可用模型
    if not profile_id:
        expected_type = _purpose_to_type(purpose)
        with get_db() as conn:
            row = conn.execute(
                """SELECT id FROM model_profile
                   WHERE user_id=? AND is_active=1 AND type=? LIMIT 1""",
                (user_id, expected_type),
            ).fetchone()
            if row:
                profile_id = row[0]

    if not profile_id:
        raise ConfigError(
            f"阶段「{purpose}」没有配置可用模型，请先创建模型配置并在项目参数中选择。"
        )

    return _build_runtime(profile_id, purpose)


def _build_runtime(profile_id: str, purpose: str) -> RuntimeConfig:
    with get_db() as conn:
        profile = conn.execute(
            "SELECT * FROM model_profile WHERE id=?", (profile_id,)
        ).fetchone()
        if not profile:
            raise ConfigError("模型配置不存在")
        profile = dict(profile)

    if not profile.get("is_active"):
        raise ConfigError(f"模型配置「{profile['name']}」已禁用")

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
            "SELECT * FROM api_credential WHERE id=?", (cred_id,)
        ).fetchone()
        if not cred:
            raise ConfigError(f"API 凭证不存在或已被删除")
        cred = dict(cred)

    if cred.get("status") == "disabled":
        raise ConfigError(f"API 凭证「{cred['name']}」已禁用")

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
            pass

    return RuntimeConfig(
        api_credential_id=cred_id,
        model_profile_id=profile_id,
        provider=cred["provider"],
        base_url=cred["base_url"] or PROVIDER_DEFAULTS.get(cred["provider"], ""),
        api_key=api_key,
        model=profile["model"],
        type=profile["type"],
        temperature=profile.get("temperature") or 0.7,
        max_tokens=profile.get("max_tokens") or 8192,
        top_p=profile.get("top_p"),
        supports_streaming=bool(profile.get("supports_streaming", 1)),
        supports_json=bool(profile.get("supports_json", 1)),
        purpose=purpose,
        extra_headers=extra_headers,
    )


def call_chat(
    user_id: str,
    prompt: str,
    *,
    purpose: str = "general",
    project_id: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    cancel_token=None,
) -> str:
    """统一聊天模型调用。"""
    cfg = get_runtime_config(user_id, purpose, project_id)
    return _invoke_chat(user_id, cfg, prompt, temperature, max_tokens, cancel_token)


def call_embedding(
    user_id: str,
    text: str,
    *,
    project_id: str | None = None,
) -> list[float]:
    """统一向量化调用。"""
    cfg = get_runtime_config(user_id, "embedding", project_id)
    return _invoke_embedding(user_id, cfg, text)


def create_chat_adapter(
    user_id: str,
    purpose: str = "general",
    project_id: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    cancel_token=None,
):
    """创建一个已配置好的聊天适配器。"""
    cfg = get_runtime_config(user_id, purpose, project_id)
    return _build_chat_adapter(cfg, temperature, max_tokens, cancel_token)


def create_embedding_adapter(
    user_id: str,
    project_id: str | None = None,
):
    """创建一个已配置好的向量化适配器。"""
    cfg = get_runtime_config(user_id, "embedding", project_id)
    return _build_embedding_adapter(cfg)


def get_runtime(user_id: str) -> RuntimeConfig:
    """兼容旧接口：返回 general purpose 的运行时配置。"""
    return get_runtime_config(user_id, "general")


def mark_used(user_id: str, cred_id: str = "", profile_id: str = "") -> None:
    """标记 API 和模型最近使用时间。"""
    now = datetime.datetime.now().isoformat()
    logger.info("ModelRuntime mark_used [user=%s cred=%s profile=%s]", user_id, cred_id, profile_id)
    with get_db() as conn:
        if cred_id:
            conn.execute(
                "UPDATE api_credential SET last_used_at=?, updated_at=? WHERE id=?",
                (now, now, cred_id),
            )
        if profile_id:
            conn.execute(
                "UPDATE model_profile SET last_used_at=?, updated_at=? WHERE id=?",
                (now, now, profile_id),
            )


def log_invocation(
    user_id: str,
    cfg: RuntimeConfig,
    input_chars: int = 0,
    output_chars: int = 0,
    latency_ms: int = 0,
    success: bool = True,
    error_code: str = "",
    error_message: str = "",
    project_id: str = "",
    task_id: str = "",
) -> None:
    """记录模型调用日志。"""
    log_id = uuid.uuid4().hex
    now = datetime.datetime.now().isoformat()
    try:
        with get_db() as conn:
            conn.execute(
                """INSERT INTO model_invocation_log
                   (id, user_id, project_id, task_id, api_credential_id,
                    model_profile_id, provider, model, purpose,
                    input_chars, output_chars, latency_ms,
                    success, error_code, error_message, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (log_id, user_id, project_id or "", task_id or "",
                 cfg.api_credential_id, cfg.model_profile_id,
                 cfg.provider, cfg.model, cfg.purpose,
                 input_chars, output_chars, latency_ms,
                 1 if success else 0,
                 error_code, error_message,
                 now),
            )
    except Exception:
        pass


# ── 内部实现 ──

def _purpose_to_type(purpose: str) -> str:
    if purpose in ("embedding",):
        return "embedding"
    if purpose in ("rerank",):
        return "rerank"
    return "chat"


def _build_chat_adapter(cfg: RuntimeConfig, temperature: float | None, max_tokens: int | None, cancel_token=None):
    from llm_adapters import create_llm_adapter

    t = temperature if temperature is not None else (cfg.temperature or 0.7)
    mt = max_tokens if max_tokens is not None else (cfg.max_tokens or 8192)

    return create_llm_adapter(
        interface_format=_provider_to_interface(cfg.provider),
        base_url=cfg.base_url,
        model_name=cfg.model,
        api_key=cfg.api_key,
        temperature=t,
        max_tokens=mt,
        timeout=600,
        cancel_token=cancel_token,
    )


def _invoke_chat(user_id: str, cfg: RuntimeConfig, prompt: str, temperature: float | None, max_tokens: int | None, cancel_token=None) -> str:
    masked = mask_api_key(cfg.api_key) if cfg.api_key else "N/A"
    logger.info(
        "ModelRuntime chat [user=%s cred=%s profile=%s provider=%s model=%s key=%s]",
        user_id, cfg.api_credential_id, cfg.model_profile_id, cfg.provider, cfg.model, masked,
    )

    adapter = _build_chat_adapter(cfg, temperature, max_tokens, cancel_token)
    start = time.time()
    result = adapter.invoke(prompt)
    elapsed = int((time.time() - start) * 1000)

    if result:
        mark_used(user_id, cfg.api_credential_id, cfg.model_profile_id)
        log_invocation(user_id, cfg,
                       input_chars=len(prompt), output_chars=len(result),
                       latency_ms=elapsed, success=True)
    else:
        err = getattr(adapter, "last_error", "")
        _update_health(cfg.model_profile_id, "invalid", err)
        log_invocation(user_id, cfg,
                       input_chars=len(prompt), latency_ms=elapsed,
                       success=False, error_code="MODEL_CALL_FAILED", error_message=err)

    return result


def _build_embedding_adapter(cfg: RuntimeConfig):
    from embedding_adapters import create_embedding_adapter
    return create_embedding_adapter(
        interface_format=_provider_to_interface(cfg.provider),
        api_key=cfg.api_key,
        base_url=cfg.base_url,
        model_name=cfg.model,
    )


def _invoke_embedding(user_id: str, cfg: RuntimeConfig, text: str) -> list[float]:
    masked = mask_api_key(cfg.api_key) if cfg.api_key else "N/A"
    logger.info(
        "ModelRuntime embedding [cred=%s profile=%s provider=%s model=%s key=%s]",
        cfg.api_credential_id, cfg.model_profile_id, cfg.provider, cfg.model, masked,
    )
    adapter = _build_embedding_adapter(cfg)
    start = time.time()
    result = adapter.embed_query(text)
    elapsed = int((time.time() - start) * 1000)

    if result:
        mark_used(user_id, cfg.api_credential_id, cfg.model_profile_id)
        log_invocation(user_id, cfg, input_chars=len(text), output_chars=len(result),
                       latency_ms=elapsed, success=True)
    else:
        err = getattr(adapter, "last_error", "")
        _update_health(cfg.model_profile_id, "invalid", err)
        log_invocation(user_id, cfg, input_chars=len(text), latency_ms=elapsed,
                       success=False, error_code="EMBEDDING_FAILED", error_message=err)

    return result


def _provider_to_interface(provider: str) -> str:
    mapping = {
        "openai": "OpenAI", "deepseek": "OpenAI", "qwen": "OpenAI",
        "anthropic": "OpenAI", "custom": "OpenAI", "local": "Ollama",
    }
    return mapping.get(provider, "OpenAI")


def _update_health(profile_id: str, status: str, error: str) -> None:
    now = datetime.datetime.now().isoformat()
    with get_db() as conn:
        conn.execute(
            "UPDATE model_profile SET health_status=?, last_error=?, last_tested_at=?, updated_at=? WHERE id=?",
            (status, (error or "")[:500], now, now, profile_id),
        )
