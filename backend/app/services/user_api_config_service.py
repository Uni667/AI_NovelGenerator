"""用户 API 配置服务 — 每用户一份主配置，AES-256-GCM 加密存储。"""

import datetime
import logging
import uuid

from backend.app.database import get_db
from backend.app.utils.crypto import (
    decrypt_api_key,
    encrypt_api_key,
    hash_api_key,
    last4,
    mask_api_key,
)

logger = logging.getLogger(__name__)

PROVIDER_DEFAULTS = {
    "openai": {"base_url": "https://api.openai.com/v1", "chat_model": "gpt-4o-mini", "emb_model": "text-embedding-ada-002"},
    "deepseek": {"base_url": "https://api.deepseek.com", "chat_model": "deepseek-chat", "emb_model": ""},
    "qwen": {"base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "chat_model": "qwen-plus", "emb_model": "text-embedding-v3"},
    "anthropic": {"base_url": "https://api.anthropic.com/v1", "chat_model": "claude-sonnet-4-6", "emb_model": ""},
    "custom": {"base_url": "", "chat_model": "", "emb_model": ""},
}


def get_user_api_config(user_id: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM user_api_config WHERE user_id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else None


def get_user_api_config_response(user_id: str) -> dict:
    config = get_user_api_config(user_id)
    if not config:
        return {"configured": False}

    try:
        _key = decrypt_api_key(config["api_key_encrypted"])
    except Exception:
        _key = ""

    return {
        "configured": True,
        "provider": config["provider"],
        "api_key_masked": mask_api_key(_key) if _key else "***解密失败***",
        "api_key_last4": config["api_key_last4"],
        "base_url": config["base_url"],
        "default_chat_model": config.get("default_chat_model") or config.get("default_model", ""),
        "default_embedding_model": config.get("default_embedding_model", ""),
        "default_model": config.get("default_model", ""),
        "status": config["status"],
        "last_tested_at": config.get("last_tested_at"),
        "last_used_at": config.get("last_used_at"),
        "updated_at": config["updated_at"],
    }


def save_user_api_config(
    user_id: str,
    provider: str,
    api_key: str,
    base_url: str | None = None,
    default_chat_model: str | None = None,
    default_embedding_model: str | None = None,
    default_model: str | None = None,
) -> dict:
    api_key = (api_key or "").strip()
    if not api_key:
        raise ValueError("API Key 不能为空")

    if provider not in PROVIDER_DEFAULTS:
        provider = "custom"
    defaults = PROVIDER_DEFAULTS[provider]
    effective_base_url = (base_url or "").strip() or defaults["base_url"]
    effective_chat = (default_chat_model or default_model or "").strip() or defaults["chat_model"]
    effective_emb = (default_embedding_model or "").strip() or defaults["emb_model"]

    encrypted = encrypt_api_key(api_key)
    key_last4 = last4(api_key)
    key_hash = hash_api_key(api_key)
    now = datetime.datetime.now().isoformat()

    existing = get_user_api_config(user_id)

    with get_db() as conn:
        if existing:
            conn.execute(
                """UPDATE user_api_config
                   SET provider=?, api_key_encrypted=?, api_key_last4=?, api_key_hash=?,
                       base_url=?, default_model=?, default_chat_model=?, default_embedding_model=?,
                       status='untested', updated_at=?
                   WHERE user_id=?""",
                (provider, encrypted, key_last4, key_hash,
                 effective_base_url, effective_chat, effective_chat, effective_emb, now, user_id),
            )
        else:
            config_id = uuid.uuid4().hex
            conn.execute(
                """INSERT INTO user_api_config
                   (id, user_id, provider, api_key_encrypted, api_key_last4, api_key_hash,
                    base_url, default_model, default_chat_model, default_embedding_model,
                    status, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (config_id, user_id, provider, encrypted, key_last4, key_hash,
                 effective_base_url, effective_chat, effective_chat, effective_emb,
                 "untested", now, now),
            )

    logger.info("User %s saved API config provider=%s chat_model=%s emb_model=%s",
                user_id, provider, effective_chat, effective_emb)
    return get_user_api_config_response(user_id)


def update_user_api_config(user_id: str, updates: dict) -> dict:
    """部分更新 API 配置（不覆盖 API Key）。"""
    existing = get_user_api_config(user_id)
    if not existing:
        raise ValueError("尚未配置 API Key")

    now = datetime.datetime.now().isoformat()
    sets = []
    params = []
    allowed = ["default_chat_model", "default_embedding_model", "base_url", "provider"]

    for field in allowed:
        if field in updates and updates[field] is not None:
            sets.append(f"{field}=?")
            params.append(updates[field])

    if not sets:
        return get_user_api_config_response(user_id)

    sets.append("updated_at=?")
    params.append(now)
    params.append(user_id)

    with get_db() as conn:
        conn.execute(
            f"UPDATE user_api_config SET {', '.join(sets)} WHERE user_id=?",
            params,
        )

    return get_user_api_config_response(user_id)


def test_user_api_config(user_id: str) -> dict:
    """测试当前用户 API 配置是否可用。"""
    from backend.app.services.model_runtime import get_runtime

    try:
        runtime = get_runtime(user_id)
    except Exception as e:
        return {"success": False, "message": str(e)}

    from llm_adapters import create_llm_adapter

    try:
        adapter = create_llm_adapter(
            interface_format=runtime.interface_format,
            base_url=runtime.base_url,
            model_name=runtime.chat_model,
            api_key=runtime.api_key,
            temperature=0.7,
            max_tokens=32,
            timeout=25,
        )
    except Exception as e:
        _update_status(user_id, "invalid")
        return {"success": False, "message": f"初始化失败: {e}"}

    response = adapter.invoke("Reply exactly: OK")
    now = datetime.datetime.now().isoformat()

    if response:
        _update_status(user_id, "active", now)
        logger.info("User %s API config test PASSED", user_id)
        return {"success": True, "message": f"测试成功！回复: {response[:200]}"}

    err = getattr(adapter, "last_error", "") or "未获取到响应"
    _update_status(user_id, "invalid", now)
    masked = mask_api_key(runtime.api_key)
    logger.warning("User %s API config test FAILED (key=%s): %s", user_id, masked, err)
    return {"success": False, "message": f"测试失败（Key: {masked}）: {err}"}


def delete_user_api_config(user_id: str) -> bool:
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM user_api_config WHERE user_id = ?", (user_id,))
        deleted = cursor.rowcount > 0
    if deleted:
        logger.info("User %s deleted API config", user_id)
    return deleted


def _update_status(user_id: str, status: str, tested_at: str | None = None):
    now = datetime.datetime.now().isoformat()
    with get_db() as conn:
        if tested_at:
            conn.execute(
                "UPDATE user_api_config SET status=?, last_tested_at=?, updated_at=? WHERE user_id=?",
                (status, tested_at, now, user_id),
            )
        else:
            conn.execute(
                "UPDATE user_api_config SET status=?, updated_at=? WHERE user_id=?",
                (status, now, user_id),
            )


def mark_used(user_id: str):
    now = datetime.datetime.now().isoformat()
    with get_db() as conn:
        conn.execute(
            "UPDATE user_api_config SET last_used_at=?, updated_at=? WHERE user_id=?",
            (now, now, user_id),
        )


def get_decrypted_api_key(user_id: str) -> str:
    config = get_user_api_config(user_id)
    if not config:
        raise ValueError("未配置 API Key")
    return decrypt_api_key(config["api_key_encrypted"])


def get_full_config_decrypted(user_id: str) -> dict:
    config = get_user_api_config(user_id)
    if not config:
        raise ValueError("你还没有配置 API Key，请先到 API 设置页面配置后再试。")
    try:
        api_key = decrypt_api_key(config["api_key_encrypted"])
    except ValueError as e:
        raise ValueError(
            "当前 API 配置无法读取，可能是服务器加密密钥发生变化，请重新填写 API Key。"
        ) from e
    return {
        "provider": config["provider"],
        "api_key": api_key,
        "base_url": config.get("base_url", ""),
        "model_name": config.get("default_chat_model") or config.get("default_model", ""),
        "embedding_model": config.get("default_embedding_model", ""),
        "status": config["status"],
    }
