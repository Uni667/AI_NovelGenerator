"""API 凭证管理 — 多凭证、加密存储、测试连接。"""

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
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "anthropic": "https://api.anthropic.com",
    "siliconflow": "https://api.siliconflow.cn/v1",
    "custom": "",
    "local": "http://localhost:11434",
}

# 各 provider 的默认测试模型名（不是 URL！）
PROVIDER_DEFAULT_TEST_MODELS = {
    "openai": "gpt-4o-mini",
    "deepseek": "deepseek-chat",
    "qwen": "qwen-plus",
    "anthropic": "claude-3-5-haiku-latest",
    "siliconflow": "deepseek-v4-flash",
    "custom": "",
    "local": "",
}
REMOVED_LEGACY_MARKERS = ("uni656", "flah", "bge-m3", "bge_m3", "bge m3")


def _validate_model_not_url(model: str) -> None:
    """模型名不能是 URL——通常是 base_url 和 model 字段传反了。"""
    if model and (model.startswith("http://") or model.startswith("https://")):
        raise ValueError(
            f"模型名不能是 URL（{model[:80]}...），请检查字段映射：base_url 和 model 可能传反了。"
        )


def list_credentials(user_id: str) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM api_credential WHERE user_id=? ORDER BY created_at",
            (user_id,),
        ).fetchall()
    result = []
    for row in rows:
        r = dict(row)
        r.pop("api_key_encrypted", None)
        r.pop("api_key_hash", None)
        r.pop("headers_encrypted", None)
        r["is_default"] = bool(r.get("is_default"))
        haystack = f"{r.get('name', '')} {r.get('provider', '')}".lower()
        if any(marker in haystack for marker in REMOVED_LEGACY_MARKERS):
            continue
        result.append(r)
    return result


def get_credential(cred_id: str, user_id: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM api_credential WHERE id=? AND user_id=?", (cred_id, user_id)
        ).fetchone()
        if not row:
            return None
        r = dict(row)
        r.pop("api_key_encrypted", None)
        r.pop("api_key_hash", None)
        r.pop("headers_encrypted", None)
        r["is_default"] = bool(r.get("is_default"))
        return r


def create_credential(user_id: str, data: dict) -> dict:
    name = (data.get("name") or "").strip()
    if not name:
        raise ValueError("凭证名称不能为空")
    provider = data.get("provider", "openai")
    api_key = (data.get("api_key") or "").strip()
    base_url = (data.get("base_url") or "").strip()
    if not base_url:
        base_url = PROVIDER_DEFAULTS.get(provider, "")
    is_local = provider == "local"
    if not is_local and not api_key:
        raise ValueError("API Key 不能为空（本地模型除外）")

    if not base_url.startswith(("http://", "https://")):
        raise ValueError("Base URL 必须以 http:// 或 https:// 开头。")
    # 校验 provider ↔ base_url
    _validate_provider_url(provider, base_url)

    cred_id = uuid.uuid4().hex
    now = datetime.datetime.now().isoformat()

    encrypted_key = encrypt_api_key(api_key) if api_key else ""
    key_last4 = last4(api_key) if api_key else ""
    key_hash = hash_api_key(api_key) if api_key else ""

    # headers encrypt
    headers_raw = data.get("headers")
    headers_enc = ""
    if headers_raw:
        import json
        headers_enc = encrypt_api_key(json.dumps(headers_raw))

    is_default = bool(data.get("is_default"))

    with get_db() as conn:
        if is_default:
            conn.execute(
                "UPDATE api_credential SET is_default=0 WHERE user_id=?",
                (user_id,),
            )
        conn.execute(
            """INSERT INTO api_credential
               (id, user_id, name, provider, api_key_encrypted, api_key_last4, api_key_hash,
                base_url, headers_encrypted, status, is_default, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (cred_id, user_id, name, provider, encrypted_key, key_last4, key_hash,
             base_url, headers_enc, "untested", 1 if is_default else 0, now, now),
        )
    logger.info("User %s created API credential '%s' provider=%s", user_id, name, provider)
    return get_credential(cred_id, user_id)


def update_credential(cred_id: str, user_id: str, data: dict) -> dict:
    existing = get_credential(cred_id, user_id)
    if not existing:
        raise ValueError("凭证不存在")

    sets = []
    params = []
    now = datetime.datetime.now().isoformat()

    for field in ["name", "provider", "base_url", "status"]:
        if field in data and data[field] is not None:
            if field == "base_url" and data[field] and not data[field].startswith(("http://", "https://")):
                raise ValueError("Base URL 必须以 http:// 或 https:// 开头。")
            sets.append(f"{field}=?")
            params.append(data[field])

    if "api_key" in data and (data["api_key"] or "").strip():
        api_key = data["api_key"].strip()
        sets.append("api_key_encrypted=?")
        params.append(encrypt_api_key(api_key))
        sets.append("api_key_last4=?")
        params.append(last4(api_key))
        sets.append("api_key_hash=?")
        params.append(hash_api_key(api_key))

    if "is_default" in data and data["is_default"]:
        with get_db() as conn:
            conn.execute("UPDATE api_credential SET is_default=0 WHERE user_id=?", (user_id,))
        sets.append("is_default=1")

    if not sets:
        return existing

    sets.append("updated_at=?")
    params.append(now)
    params.extend([cred_id, user_id])

    with get_db() as conn:
        conn.execute(
            f"UPDATE api_credential SET {', '.join(sets)} WHERE id=? AND user_id=?", params
        )

    return get_credential(cred_id, user_id)


def delete_credential(cred_id: str, user_id: str, cascade: bool = False) -> None:
    """删除 API 凭证。cascade=True 时同时删除关联的 ModelProfile。"""
    import datetime

    with get_db() as conn:
        # 验证凭证属于当前用户
        row = conn.execute(
            "SELECT id FROM api_credential WHERE id=? AND user_id=?", (cred_id, user_id)
        ).fetchone()
        if not row:
            raise ValueError("凭证不存在或不属于你。")

        # 查找关联的 ModelProfile
        linked = conn.execute(
            "SELECT id FROM model_profile WHERE api_credential_id=? AND user_id=?", (cred_id, user_id)
        ).fetchall()

        if linked and not cascade:
            count = len(linked)
            raise ValueError(
                f"该凭证被 {count} 个模型配置引用，请先删除或更换这些模型配置的绑定"
            )

        if linked and cascade:
            # 清空 ProjectModelAssignment 中引用这些 ModelProfile 的字段
            profile_ids = [row[0] for row in linked]
            profile_fields = [
                "architecture_profile_id", "worldbuilding_profile_id", "character_profile_id",
                "outline_profile_id", "draft_profile_id", "polish_profile_id",
                "review_profile_id", "summary_profile_id", "feedback_profile_id",
                "embedding_profile_id", "rerank_profile_id",
            ]
            now = datetime.datetime.now().isoformat()
            for pid in profile_ids:
                for field in profile_fields:
                    conn.execute(
                        f"UPDATE project_model_assignment SET {field}=NULL, updated_at=? WHERE {field}=? AND user_id=?",
                        (now, pid, user_id),
                    )
            # 删除 ModelProfile
            conn.execute(
                "DELETE FROM model_profile WHERE api_credential_id=? AND user_id=?",
                (cred_id, user_id),
            )

        conn.execute("DELETE FROM api_credential WHERE id=? AND user_id=?", (cred_id, user_id))


def set_status(cred_id: str, user_id: str, status: str) -> dict:
    now = datetime.datetime.now().isoformat()
    with get_db() as conn:
        conn.execute(
            "UPDATE api_credential SET status=?, updated_at=? WHERE id=? AND user_id=?",
            (status, now, cred_id, user_id),
        )
    return get_credential(cred_id, user_id)


def test_credential(cred_id: str, user_id: str) -> dict:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM api_credential WHERE id=? AND user_id=?", (cred_id, user_id)
        ).fetchone()
        if not row:
            return {"success": False, "message": "凭证不存在"}
        cred = dict(row)

    try:
        api_key = decrypt_api_key(cred["api_key_encrypted"]) if cred["api_key_encrypted"] else ""
    except Exception as e:
        return {"success": False, "message": f"解密失败: {e}"}

    if cred["provider"] == "local":
        return _test_local(cred, api_key)

    return _test_chat(cred, api_key)


def _test_chat(cred: dict, api_key: str) -> dict:
    from llm_adapters import create_llm_adapter
    from backend.app.services.model_runtime import _provider_to_interface

    now = datetime.datetime.now().isoformat()
    masked = mask_api_key(api_key)
    provider = cred["provider"]
    base_url = cred["base_url"] or PROVIDER_DEFAULTS.get(provider, "")
    test_model = PROVIDER_DEFAULT_TEST_MODELS.get(provider, "") or "gpt-4o-mini"
    if not base_url.startswith(("http://", "https://")):
        return {"success": False, "message": "服务地址配置异常，请清空后重新配置。"}
    if provider in {"custom", "local"} and not PROVIDER_DEFAULT_TEST_MODELS.get(provider):
        return {"success": False, "message": "自定义凭证测试需要先创建模型配置并填写测试模型。"}

    _validate_model_not_url(test_model)

    try:
        adapter = create_llm_adapter(
            interface_format=_provider_to_interface(provider),
            base_url=base_url,
            model_name=test_model,
            api_key=api_key,
            temperature=0.7,
            max_tokens=32,
            timeout=25,
        )
    except Exception:
        _set_cred_health(cred["id"], "invalid", "模型初始化失败", now)
        return {"success": False, "message": "测试失败，请检查 API Key 和服务商是否匹配。"}

    response = adapter.invoke("Reply exactly: OK")
    if response:
        _set_cred_health(cred["id"], "active", "", now)
        logger.info("Credential %s test PASSED (provider=%s key=%s)", cred["id"], provider, masked)
        return {"success": True, "message": "测试成功"}

    err = getattr(adapter, "last_error", "") or "无响应"
    _set_cred_health(cred["id"], "invalid", err[:500], now)
    logger.warning("Credential %s test FAILED (provider=%s key=%s): %s", cred["id"], provider, masked, err)
    return {"success": False, "message": "测试失败，请检查 API Key 和服务商是否匹配。"}


def _test_local(cred: dict, api_key: str) -> dict:
    import requests
    base_url = cred["base_url"] or "http://localhost:11434"
    try:
        r = requests.get(base_url.rstrip("/"), timeout=10)
        if r.status_code < 500:
            now = datetime.datetime.now().isoformat()
            _set_cred_health(cred["id"], "active", "", now)
            return {"success": True, "message": f"本地服务可达，状态: {r.status_code}"}
        return {"success": False, "message": f"本地服务返回异常: {r.status_code}"}
    except Exception as e:
        now = datetime.datetime.now().isoformat()
        _set_cred_health(cred["id"], "invalid", str(e)[:500], now)
        return {"success": False, "message": f"本地服务不可达: {e}"}


def _set_cred_health(cred_id: str, status: str, error: str, now: str) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE api_credential SET status=?, last_tested_at=?, last_error=?, updated_at=? WHERE id=?",
            (status, now, error[:500], now, cred_id),
        )


def _validate_provider_url(provider: str, url: str) -> None:
    if provider in ("custom", "local"):
        return
    url_lower = url.lower()
    conflicts = {
        "openai": ["deepseek.com", "dashscope.aliyuncs.com", "anthropic.com", "siliconflow.cn"],
        "deepseek": ["openai.com", "dashscope.aliyuncs.com", "anthropic.com", "siliconflow.cn"],
        "qwen": ["openai.com", "deepseek.com", "anthropic.com", "siliconflow.cn"],
        "anthropic": ["openai.com", "deepseek.com", "dashscope.aliyuncs.com", "siliconflow.cn"],
        "siliconflow": ["openai.com", "deepseek.com", "dashscope.aliyuncs.com", "anthropic.com"],
    }
    for indicator in conflicts.get(provider, []):
        if indicator in url_lower:
            raise ValueError(
                f"服务商 ({provider}) 与 Base URL 不匹配: URL 中包含 {indicator}。"
            )
