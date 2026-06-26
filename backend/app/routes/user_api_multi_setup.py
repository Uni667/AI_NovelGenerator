import datetime
import uuid
from fastapi import APIRouter, Request
from pydantic import BaseModel
from backend.app.auth import get_current_user
from backend.app.database import get_db
from backend.app.utils.crypto import encrypt_api_key, hash_api_key, last4
from backend.app.services.api_credential_service import PROVIDER_DEFAULTS
from backend.app.routes.user_api_config import PROVIDER_DISPLAY_NAMES
from backend.app.services.model_runtime import test_chat_connection, normalize_base_url
from backend.app.services.config_resolver import (
    SMART_ROUTING_PREFERENCES,
    PROVIDER_DEFAULT_CHAT_MODELS,
    PROVIDER_DEFAULT_EMBEDDING_MODELS,
)

router = APIRouter(tags=["model-settings"])

class MultiSetupCredential(BaseModel):
    provider: str
    api_key: str
    base_url: str | None = None

class MultiSetupReq(BaseModel):
    credentials: list[MultiSetupCredential]

@router.post("/api/v1/user/model-multi-setup")
def model_multi_setup(data: MultiSetupReq, request: Request):
    user_id = get_current_user(request)
    
    saved_providers = set()
    cred_ids = {}
    details = []
    
    with get_db() as conn:
        for cred in data.credentials:
            provider = cred.provider.strip()
            api_key = cred.api_key.strip()
            if not api_key or provider not in PROVIDER_DEFAULTS:
                details.append({"provider": provider, "success": False, "message": "不支持的服务商或空密钥"})
                continue
                
            raw_url = (cred.base_url or "").strip()
            if raw_url:
                base_url = normalize_base_url(provider, raw_url)
            else:
                base_url = normalize_base_url(provider, PROVIDER_DEFAULTS[provider])
                
            default_model = PROVIDER_DEFAULT_CHAT_MODELS.get(provider, "")
            if not default_model:
                details.append({"provider": provider, "success": False, "message": "该服务商暂不支持测试"})
                continue
                
            test_res = test_chat_connection(provider, base_url, default_model, api_key, timeout=15)
            if not test_res.get("success"):
                details.append({"provider": provider, "success": False, "message": test_res.get("message", "连接测试失败")})
                continue
                
            now = datetime.datetime.now().isoformat()
            encrypted_key = encrypt_api_key(api_key)
            existing = conn.execute("SELECT id FROM api_credential WHERE user_id=? AND provider=? LIMIT 1", (user_id, provider)).fetchone()
            if existing:
                cred_id = existing[0]
                conn.execute(
                    "UPDATE api_credential SET api_key_encrypted=?, api_key_last4=?, api_key_hash=?, base_url=?, status='active', last_tested_at=?, updated_at=? WHERE id=? AND user_id=?",
                    (encrypted_key, last4(api_key), hash_api_key(api_key), base_url, now, now, cred_id, user_id)
                )
            else:
                cred_id = uuid.uuid4().hex
                conn.execute(
                    "INSERT INTO api_credential (id, user_id, name, provider, api_key_encrypted, api_key_last4, api_key_hash, base_url, status, is_default, last_tested_at, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (cred_id, user_id, PROVIDER_DISPLAY_NAMES.get(provider, provider), provider, encrypted_key, last4(api_key), hash_api_key(api_key), base_url, "active", 0, now, now, now)
                )
            saved_providers.add(provider)
            cred_ids[provider] = cred_id
            details.append({"provider": provider, "success": True, "message": "已保存"})
            
    if not saved_providers:
        return {"success": False, "message": "没有任何有效的 API Key，请检查后重试", "details": details}

    assignments = []
    with get_db() as conn:
        now = datetime.datetime.now().isoformat()
        
        # Build a lookup for base_urls
        base_urls_lookup = {}
        for cred in data.credentials:
            raw_url = (cred.base_url or "").strip()
            if raw_url:
                base_urls_lookup[cred.provider.strip()] = normalize_base_url(cred.provider.strip(), raw_url)
                
        def _upsert_profile(purpose: str, p_type: str, provider: str, model: str):
            cred_id = cred_ids[provider]
            base_url = base_urls_lookup.get(provider, normalize_base_url(provider, PROVIDER_DEFAULTS[provider]))
            existing = conn.execute("SELECT id FROM model_profile WHERE user_id=? AND purpose=? LIMIT 1", (user_id, purpose)).fetchone()
            if existing:
                conn.execute("UPDATE model_profile SET provider=?, base_url=?, model=?, api_credential_id=?, health_status='active', is_active=1, is_default=1, updated_at=? WHERE id=?", (provider, base_url, model, cred_id, now, existing[0]))
            else:
                pid = uuid.uuid4().hex
                conn.execute("INSERT INTO model_profile (id, user_id, name, type, purpose, provider, base_url, model, api_credential_id, is_default, is_active, health_status, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (pid, user_id, f"智能分配: {purpose}", p_type, purpose, provider, base_url, model, cred_id, 1, 1, "active", now, now))
            assignments.append({"purpose": purpose, "provider": provider, "model": model})

        for purpose, prefs in SMART_ROUTING_PREFERENCES.items():
            assigned = False
            for pref_provider, pref_model in prefs:
                if pref_provider in saved_providers:
                    p_type = "embedding" if purpose == "embedding" else "chat"
                    _upsert_profile(purpose, p_type, pref_provider, pref_model)
                    assigned = True
                    break
            if not assigned:
                if purpose == "embedding":
                    for p in saved_providers:
                        m = PROVIDER_DEFAULT_EMBEDDING_MODELS.get(p)
                        if m:
                            _upsert_profile(purpose, "embedding", p, m)
                            break
                else:
                    p = list(saved_providers)[0]
                    m = PROVIDER_DEFAULT_CHAT_MODELS.get(p)
                    if m:
                        _upsert_profile(purpose, "chat", p, m)
    
    return {
        "success": True,
        "message": f"成功保存 {len(saved_providers)} 个 API，并完成智能路由分配",
        "details": details,
        "assignments": assignments
    }
