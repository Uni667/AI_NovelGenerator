"""
ModelRuntimeService — 统一模型调用层 (Facade)。

解析链:
  project_id + purpose → project_model_assignment → model_profile_id
  → model_profile (type, model, api_credential_id, params)
  → api_credential → decrypt api_key
  → call LLM / embedding
"""

import datetime
import logging
import time

from backend.app.database import get_db
from backend.app.services.config_resolver import (
    ConfigError,
    PROVIDER_DEFAULTS,
    PURPOSE_MAP,
    RuntimeConfig,
    SUPPORTED_CHAT_PROVIDERS,
    _is_http_url,
    _strip_known_suffixes,
    get_runtime_config,
    infer_provider,
    normalize_base_url,
)
from backend.app.services.invocation_logger import log_invocation, mark_used, update_health

logger = logging.getLogger(__name__)

# Keep for compatibility with older imports
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
    from backend.app.utils.crypto import mask_api_key
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
                       latency_ms=elapsed, success=True, project_id=project_id or "", task_id="")
    else:
        err = getattr(adapter, "last_error", "")
        update_health(cfg.model_profile_id, "invalid", err)
        log_invocation(user_id, cfg,
                       input_chars=len(prompt), latency_ms=elapsed,
                       success=False, error_code="MODEL_CALL_FAILED", error_message=err,
                       project_id=project_id or "", task_id="")
    return result


# Helper functions for UI
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
