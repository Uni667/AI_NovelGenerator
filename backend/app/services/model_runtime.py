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
from backend.app.errors import (
    base_url_invalid,
    model_config_incomplete,
    model_name_invalid,
)
from backend.app.utils.crypto import decrypt_api_key, mask_api_key

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
    "deepseek": "https://api.deepseek.com/v1",
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "anthropic": "https://api.anthropic.com",
    "siliconflow": "https://api.siliconflow.cn/v1",
    "custom": "",
    "local": "http://localhost:11434",
}

PROVIDER_DEFAULT_CHAT_MODELS = {
    "siliconflow": "deepseek-v4-flash",
    "deepseek": "deepseek-chat",
    "openai": "gpt-4o-mini",
    "qwen": "qwen-plus",
    "anthropic": "claude-3-5-haiku-latest",
}

SUPPORTED_CHAT_PROVIDERS = {"openai", "deepseek", "qwen", "anthropic", "siliconflow", "custom", "local"}


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


def _validate_model_identity(model_name: str) -> None:
    model = (model_name or "").strip()
    if not model:
        raise model_config_incomplete()
    if model.startswith(("http://", "https://")):
        raise model_name_invalid()


def _validate_base_url(base_url: str) -> None:
    url = (base_url or "").strip()
    if not _is_http_url(url):
        raise base_url_invalid()
    if url.endswith(("/embeddings", "/chat/completions")):
        raise base_url_invalid()


def _validate_provider(provider: str) -> None:
    if provider not in SUPPORTED_CHAT_PROVIDERS:
        raise ConfigError("当前模型配置不完整，建议清空后重新配置。")
    return
    if provider not in SUPPORTED_CHAT_PROVIDERS:
        raise ConfigError("模型配置异常，请重新测试或清空后重配。")


def _select_chat_profile(user_id: str, project_id: str | None = None) -> dict | None:
    with get_db() as conn:
        if project_id:
            row = conn.execute(
                """SELECT mp.*, ac.status AS cred_status, ac.base_url AS cred_base_url,
                          ac.provider AS cred_provider, ac.last_tested_at AS cred_last_tested_at
                   FROM project_model_assignment pma
                   JOIN model_profile mp ON mp.id = pma.architecture_profile_id
                        OR mp.id = pma.worldbuilding_profile_id
                        OR mp.id = pma.character_profile_id
                        OR mp.id = pma.outline_profile_id
                        OR mp.id = pma.draft_profile_id
                        OR mp.id = pma.polish_profile_id
                        OR mp.id = pma.review_profile_id
                        OR mp.id = pma.summary_profile_id
                        OR mp.id = pma.feedback_profile_id
                   JOIN api_credential ac ON ac.id = mp.api_credential_id AND ac.user_id = mp.user_id
                   WHERE pma.project_id=? AND pma.user_id=? AND mp.user_id=? AND mp.type='chat' AND mp.is_active=1
                   ORDER BY mp.is_default DESC, mp.last_tested_at DESC, mp.updated_at DESC
                   LIMIT 1""",
                (project_id, user_id, user_id),
            ).fetchone()
            if row:
                return dict(row)

        row = conn.execute(
            """SELECT mp.*, ac.status AS cred_status, ac.base_url AS cred_base_url,
                      ac.provider AS cred_provider, ac.last_tested_at AS cred_last_tested_at
               FROM model_profile mp
               JOIN api_credential ac ON ac.id = mp.api_credential_id AND ac.user_id = mp.user_id
               WHERE mp.user_id=? AND mp.type='chat' AND mp.is_active=1
               ORDER BY mp.is_default DESC, mp.last_tested_at DESC, mp.updated_at DESC
               LIMIT 1""",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None


def _evaluate_chat_profile(profile: dict | None) -> tuple[bool, list[str], dict]:
    if not profile:
        return False, [], {}

    provider_source = (profile.get("cred_provider") or profile.get("provider") or "").strip()
    base_url_source = profile.get("cred_base_url") or profile.get("base_url") or ""
    raw_base_url = (base_url_source or "").strip().rstrip("/")
    provider = infer_provider(provider_source, base_url_source)
    base_url = normalize_base_url(provider, base_url_source)
    model_name = (profile.get("model") or "").strip()
    cred_status = (profile.get("cred_status") or profile.get("status") or "").strip()
    health_status = (profile.get("health_status") or "").strip()

    clean_issues: list[str] = []
    if not profile.get("is_active"):
        clean_issues.append("当前模型配置不完整，建议清空后重新配置。")
    if not provider or provider not in SUPPORTED_CHAT_PROVIDERS:
        clean_issues.append("当前模型配置不完整，建议清空后重新配置。")
    if (
        not _is_http_url(raw_base_url)
        or raw_base_url.endswith(("/embeddings", "/chat/completions"))
        or (provider == "siliconflow" and raw_base_url != PROVIDER_DEFAULTS["siliconflow"])
        or (provider_source == "custom" and "siliconflow.cn" in raw_base_url.lower())
    ):
        clean_issues.append("服务地址配置异常，请点击修复旧配置或清空后重配。")
    if not model_name:
        clean_issues.append("当前模型配置不完整，建议清空后重新配置。")
    elif model_name.startswith(("http://", "https://")):
        clean_issues.append("模型名配置异常，请清空后重新配置。")
    if cred_status != "active":
        clean_issues.append("API Key 尚未通过测试。")
    if not profile.get("cred_last_tested_at"):
        clean_issues.append("API Key 尚未通过测试。")
    if health_status != "active" or not profile.get("last_tested_at"):
        clean_issues.append("模型尚未通过测试。")
    if not profile.get("api_credential_id"):
        clean_issues.append("当前模型配置不完整，建议清空后重新配置。")

    clean_issues = list(dict.fromkeys(clean_issues))
    return len(clean_issues) == 0, clean_issues, {
        "provider": provider,
        "base_url": base_url,
        "model": model_name,
        "credential_id": profile.get("api_credential_id", ""),
        "profile_id": profile.get("id", ""),
        "last_tested_at": profile.get("last_tested_at", ""),
    }


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


def _build_runtime(profile_id: str, purpose: str, user_id: str = "", allow_unhealthy: bool = False) -> RuntimeConfig:
    with get_db() as conn:
        if user_id:
            profile = conn.execute(
                "SELECT * FROM model_profile WHERE id=? AND user_id=? AND is_active=1", (profile_id, user_id)
            ).fetchone()
        else:
            profile = conn.execute(
                "SELECT * FROM model_profile WHERE id=?", (profile_id,)
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
        if user_id:
            cred = conn.execute(
                "SELECT * FROM api_credential WHERE id=? AND user_id=?", (cred_id, user_id)
            ).fetchone()
        else:
            cred = conn.execute(
                "SELECT * FROM api_credential WHERE id=?", (cred_id,)
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
            pass

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
    return _invoke_chat(user_id, cfg, prompt, temperature, max_tokens, cancel_token, project_id=project_id or "")


def call_embedding(
    user_id: str,
    text: str,
    *,
    project_id: str | None = None,
) -> list[float]:
    """统一向量化调用。"""
    cfg = get_runtime_config(user_id, "embedding", project_id)
    return _invoke_embedding(user_id, cfg, text, project_id=project_id or "")


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
                "UPDATE api_credential SET last_used_at=?, updated_at=? WHERE id=? AND user_id=?",
                (now, now, cred_id, user_id),
            )
        if profile_id:
            conn.execute(
                "UPDATE model_profile SET last_used_at=?, updated_at=? WHERE id=? AND user_id=?",
                (now, now, profile_id, user_id),
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
    t = temperature if temperature is not None else (cfg.temperature or 0.7)
    mt = max_tokens if max_tokens is not None else (cfg.max_tokens or 8192)

    return create_chat_adapter_from_config(
        interface_format=_provider_to_interface(cfg.provider),
        base_url=cfg.base_url,
        model_name=cfg.model,
        api_key=cfg.api_key,
        temperature=t,
        max_tokens=mt,
        timeout=600,
        cancel_token=cancel_token,
    )


def _invoke_chat(user_id: str, cfg: RuntimeConfig, prompt: str, temperature: float | None, max_tokens: int | None, cancel_token=None, project_id: str = "", task_id: str = "") -> str:
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
                       latency_ms=elapsed, success=True, project_id=project_id, task_id=task_id)
    else:
        err = getattr(adapter, "last_error", "")
        _update_health(cfg.model_profile_id, "invalid", err)
        log_invocation(user_id, cfg,
                       input_chars=len(prompt), latency_ms=elapsed,
                       success=False, error_code="MODEL_CALL_FAILED", error_message=err,
                       project_id=project_id, task_id=task_id)

    return result


def _build_embedding_adapter(cfg: RuntimeConfig):
    return create_embedding_adapter_from_config(
        interface_format=_provider_to_interface(cfg.provider),
        api_key=cfg.api_key,
        base_url=cfg.base_url,
        model_name=cfg.model,
    )


def _invoke_embedding(user_id: str, cfg: RuntimeConfig, text: str, project_id: str = "", task_id: str = "") -> list[float]:
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
                       latency_ms=elapsed, success=True, project_id=project_id, task_id=task_id)
    else:
        err = getattr(adapter, "last_error", "")
        _update_health(cfg.model_profile_id, "invalid", err)
        log_invocation(user_id, cfg, input_chars=len(text), latency_ms=elapsed,
                       success=False, error_code="EMBEDDING_FAILED", error_message=err,
                       project_id=project_id, task_id=task_id)

    return result


def _provider_to_interface(provider: str) -> str:
    mapping = {
        "openai": "OpenAI",
        "deepseek": "OpenAI",
        "qwen": "OpenAI",
        "anthropic": "Anthropic",
        "siliconflow": "OpenAI",
        "custom": "OpenAI",
        "local": "Ollama",
    }
    return mapping.get(provider, "OpenAI")


def _update_health(profile_id: str, status: str, error: str) -> None:
    now = datetime.datetime.now().isoformat()
    with get_db() as conn:
        conn.execute(
            "UPDATE model_profile SET health_status=?, last_error=?, last_tested_at=?, updated_at=? WHERE id=?",
            (status, (error or "")[:500], now, now, profile_id),
        )


PROVIDER_DISPLAY_NAMES = {
    "siliconflow": "硅基流动",
    "deepseek": "DeepSeek",
    "openai": "OpenAI",
    "qwen": "通义千问",
    "anthropic": "Claude",
    "custom": "自定义",
    "local": "本地模型",
}

CHAT_ASSIGNMENT_FIELDS = [
    "architecture_profile_id",
    "worldbuilding_profile_id",
    "character_profile_id",
    "outline_profile_id",
    "draft_profile_id",
    "polish_profile_id",
    "review_profile_id",
    "summary_profile_id",
    "feedback_profile_id",
]

ALL_ASSIGNMENT_FIELDS = CHAT_ASSIGNMENT_FIELDS + ["embedding_profile_id", "rerank_profile_id"]


def get_default_chat_model(provider: str) -> str:
    return PROVIDER_DEFAULT_CHAT_MODELS.get((provider or "").strip(), "")


def create_chat_adapter_from_config(
    *,
    interface_format: str = "OpenAI",
    base_url: str,
    model_name: str,
    api_key: str,
    temperature: float = 0.7,
    max_tokens: int = 8192,
    timeout: int = 600,
    cancel_token=None,
):
    """Create a chat adapter through the runtime service from explicit config."""
    from llm_adapters import create_llm_adapter

    model = (model_name or "").strip()
    base = _strip_known_suffixes(base_url)
    if not model:
        raise ConfigError("当前模型配置不完整，建议清空后重新配置。")
    if model.startswith(("http://", "https://")):
        raise ConfigError("模型名配置异常，请清空后重新配置。")
    if not _is_http_url(base):
        raise ConfigError("服务地址配置异常，请点击修复旧配置或清空后重配。")

    fmt = (interface_format or "OpenAI").strip()
    if fmt.lower() in {"siliconflow", "custom"}:
        fmt = "OpenAI"

    return create_llm_adapter(
        interface_format=fmt,
        base_url=base,
        model_name=model,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        cancel_token=cancel_token,
    )


def create_embedding_adapter_from_config(
    *,
    interface_format: str = "OpenAI",
    api_key: str,
    base_url: str,
    model_name: str,
):
    """Create an embedding adapter through the runtime service from explicit config."""
    from embedding_adapters import create_embedding_adapter as _create_embedding_adapter

    model = (model_name or "").strip()
    base = _strip_known_suffixes(base_url)
    if not model:
        raise ConfigError("当前模型配置不完整，建议清空后重新配置。")
    if model.startswith(("http://", "https://")):
        raise ConfigError("模型名配置异常，请清空后重新配置。")
    if not _is_http_url(base):
        raise ConfigError("服务地址配置异常，请点击修复旧配置或清空后重配。")

    fmt = (interface_format or "OpenAI").strip()
    return _create_embedding_adapter(fmt, api_key, base, model)


def test_chat_connection(
    *,
    provider: str,
    base_url: str,
    model_name: str,
    api_key: str,
    timeout: int = 25,
) -> dict:
    """Probe a chat model without exposing provider errors or secrets."""
    provider_source = (provider or "").strip()
    raw_base_url = (base_url or "").strip().rstrip("/")
    provider = infer_provider(provider_source, raw_base_url)
    base = normalize_base_url(provider, raw_base_url)
    if provider not in SUPPORTED_CHAT_PROVIDERS:
        return {
            "success": False,
            "code": "MODEL_CONFIG_INVALID",
            "message": "当前模型配置不完整，建议清空后重新配置。",
        }
    if (
        not _is_http_url(raw_base_url)
        or raw_base_url.endswith(("/embeddings", "/chat/completions"))
        or (provider == "siliconflow" and raw_base_url != PROVIDER_DEFAULTS["siliconflow"])
        or (provider_source == "custom" and "siliconflow.cn" in raw_base_url.lower())
    ):
        return {
            "success": False,
            "code": "BASE_URL_INVALID",
            "message": "服务地址配置异常，请点击修复旧配置或清空后重配。",
        }
    if not (api_key or "").strip() and provider != "local":
        return {
            "success": False,
            "code": "API_KEY_INVALID",
            "message": "测试失败，请检查 API Key 和服务商是否匹配。",
        }

    try:
        adapter = create_chat_adapter_from_config(
            interface_format=_provider_to_interface(provider),
            base_url=base,
            model_name=model_name,
            api_key=api_key,
            temperature=0.7,
            max_tokens=32,
            timeout=timeout,
        )
        response = adapter.invoke("Reply exactly: OK")
    except ConfigError as exc:
        message = str(exc)
        code = "MODEL_NAME_INVALID" if "模型名" in message else "BASE_URL_INVALID"
        return {"success": False, "code": code, "message": message}
    except Exception as exc:
        logger.warning("Chat connection test failed [provider=%s model=%s]: %s", provider, model_name, str(exc)[:300])
        return {
            "success": False,
            "code": "API_KEY_INVALID",
            "message": "测试失败，请检查 API Key 和服务商是否匹配。",
        }

    if response:
        return {
            "success": True,
            "message": "测试成功",
            "provider": provider,
            "baseUrl": base,
            "model": model_name,
        }

    logger.warning(
        "Chat connection test returned empty [provider=%s model=%s error=%s]",
        provider,
        model_name,
        getattr(adapter, "last_error", "")[:300],
    )
    return {
        "success": False,
        "code": "API_KEY_INVALID",
        "message": "测试失败，请检查 API Key 和服务商是否匹配。",
    }


def get_chat_model_status(user_id: str) -> dict:
    """Return the current user's real text-generation readiness."""
    profile = _select_chat_profile(user_id)
    ready, issues, snapshot = _evaluate_chat_profile(profile)

    with get_db() as conn:
        total_credentials = conn.execute(
            "SELECT COUNT(*) FROM api_credential WHERE user_id=?",
            (user_id,),
        ).fetchone()[0]
        active_credentials = conn.execute(
            "SELECT COUNT(*) FROM api_credential WHERE user_id=? AND status='active'",
            (user_id,),
        ).fetchone()[0]
        chat_profiles = conn.execute(
            "SELECT COUNT(*) FROM model_profile WHERE user_id=? AND type='chat'",
            (user_id,),
        ).fetchone()[0]
        emb_profile = conn.execute(
            """SELECT 1 FROM model_profile mp
               JOIN api_credential ac ON ac.id = mp.api_credential_id AND ac.user_id = mp.user_id
               WHERE mp.user_id=? AND mp.type='embedding' AND mp.is_active=1
                 AND mp.health_status='active' AND ac.status='active'
                 AND mp.last_tested_at IS NOT NULL
               LIMIT 1""",
            (user_id,),
        ).fetchone()

    has_any_config = bool(total_credentials or chat_profiles)
    if ready:
        state = "ready"
        title = "文本生成已可用"
        description = "可以回到项目页生成小说。"
        message = "文本生成已可用"
    elif has_any_config:
        state = "invalid"
        title = "模型配置异常"
        description = "当前模型配置不完整或不可用，建议重新测试或清空后重配。"
        message = "模型配置异常"
        if not issues:
            issues = ["当前模型配置不完整，建议清空后重新配置。"]
    else:
        state = "empty"
        title = "还没有配置文本生成模型"
        description = "填写 API Key 后，就可以开始生成小说。"
        message = "未完成配置"
        issues = []

    provider = snapshot.get("provider", "") if ready else ""
    chat_model = snapshot.get("model", "") if ready else ""
    last_tested_at = snapshot.get("last_tested_at", "") if ready else ""

    return {
        "chatReady": ready,
        "coreReady": ready,
        "embeddingReady": emb_profile is not None,
        "embeddingMessage": (
            "知识库向量化已配置。"
            if emb_profile
            else "知识库向量化未配置，不影响小说生成。"
        ),
        "state": state,
        "title": title,
        "description": description,
        "message": message,
        "provider": provider,
        "providerLabel": PROVIDER_DISPLAY_NAMES.get(provider, provider),
        "chatProvider": provider,
        "chatModel": chat_model,
        "lastTestedAt": last_tested_at,
        "recentTestedAt": last_tested_at,
        "chatErrors": issues,
        "activeCredentials": active_credentials,
        "hasCredential": total_credentials > 0,
        "hasChatProfile": chat_profiles > 0,
    }


def reset_user_model_settings(user_id: str) -> dict:
    now = datetime.datetime.now().isoformat()
    with get_db() as conn:
        conn.execute(
            f"""UPDATE project_model_assignment SET
                {', '.join(f'{field}=NULL' for field in ALL_ASSIGNMENT_FIELDS)},
                updated_at=?
                WHERE user_id=?""",
            (now, user_id),
        )
        deleted_profiles = conn.execute(
            "DELETE FROM model_profile WHERE user_id=?",
            (user_id,),
        ).rowcount
        deleted_credentials = conn.execute(
            "DELETE FROM api_credential WHERE user_id=?",
            (user_id,),
        ).rowcount

    return {
        "success": True,
        "message": "模型配置已清空，可以重新配置。",
        "details": {
            "deletedProfiles": deleted_profiles,
            "deletedCredentials": deleted_credentials,
        },
    }


def _clear_assignment_profile_refs(conn, user_id: str, profile_ids: list[str], now: str) -> None:
    if not profile_ids:
        return
    for profile_id in profile_ids:
        for field in ALL_ASSIGNMENT_FIELDS:
            conn.execute(
                f"UPDATE project_model_assignment SET {field}=NULL, updated_at=? WHERE user_id=? AND {field}=?",
                (now, user_id, profile_id),
            )


def repair_user_model_settings(user_id: str) -> dict:
    now = datetime.datetime.now().isoformat()
    fixes: list[str] = []

    with get_db() as conn:
        credentials = conn.execute(
            "SELECT * FROM api_credential WHERE user_id=?",
            (user_id,),
        ).fetchall()
        for row in credentials:
            cred = dict(row)
            old_provider = (cred.get("provider") or "").strip()
            old_base_url = (cred.get("base_url") or "").strip()
            new_provider = infer_provider(old_provider, old_base_url)
            new_base_url = normalize_base_url(new_provider, old_base_url)
            if old_provider != new_provider or old_base_url != new_base_url:
                conn.execute(
                    """UPDATE api_credential
                       SET provider=?, base_url=?, status='untested',
                           last_tested_at=NULL, last_error='', updated_at=?
                       WHERE id=? AND user_id=?""",
                    (new_provider, new_base_url, now, cred["id"], user_id),
                )
                conn.execute(
                    """UPDATE model_profile
                       SET provider=?, health_status='untested',
                           last_tested_at=NULL, last_error='', updated_at=?
                       WHERE user_id=? AND api_credential_id=?""",
                    (new_provider, now, user_id, cred["id"]),
                )
                fixes.append("已修正模型服务账号的服务商或服务地址。")

        profiles = conn.execute(
            "SELECT * FROM model_profile WHERE user_id=?",
            (user_id,),
        ).fetchall()
        for row in profiles:
            profile = dict(row)
            model_name = (profile.get("model") or "").strip()
            profile_base_url = (profile.get("base_url") or "").strip()
            normalized_profile_base = _strip_known_suffixes(profile_base_url)
            if profile_base_url and profile_base_url != normalized_profile_base:
                conn.execute(
                    """UPDATE model_profile
                       SET base_url=?, health_status='untested',
                           last_tested_at=NULL, last_error='', updated_at=?
                       WHERE id=? AND user_id=?""",
                    (normalized_profile_base, now, profile["id"], user_id),
                )
                fixes.append("已修正模型配置中的服务地址。")
            if model_name.startswith(("http://", "https://")):
                conn.execute(
                    """UPDATE model_profile
                       SET health_status='invalid', is_active=0,
                           last_error='模型名配置异常，请清空后重新配置。', updated_at=?
                       WHERE id=? AND user_id=?""",
                    (now, profile["id"], user_id),
                )
                fixes.append("已标记模型名异常的配置。")

        orphans = conn.execute(
            """SELECT mp.id FROM model_profile mp
               WHERE mp.user_id=?
                 AND mp.api_credential_id IS NOT NULL
                 AND mp.api_credential_id != ''
                 AND NOT EXISTS (
                    SELECT 1 FROM api_credential ac
                    WHERE ac.id = mp.api_credential_id AND ac.user_id = mp.user_id
                 )""",
            (user_id,),
        ).fetchall()
        orphan_ids = [row[0] for row in orphans]
        if orphan_ids:
            _clear_assignment_profile_refs(conn, user_id, orphan_ids, now)
            conn.executemany(
                "DELETE FROM model_profile WHERE id=? AND user_id=?",
                [(profile_id, user_id) for profile_id in orphan_ids],
            )
            fixes.append("已删除缺少服务账号的模型配置。")

    unique_fixes = list(dict.fromkeys(fixes))
    return {
        "success": True,
        "message": f"修复完成，共处理 {len(unique_fixes)} 项。",
        "details": unique_fixes,
        "status": get_chat_model_status(user_id),
    }
