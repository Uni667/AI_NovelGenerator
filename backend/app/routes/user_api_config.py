import datetime
import uuid

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from backend.app.auth import get_current_user
from backend.app.database import get_db
from backend.app.services.api_credential_service import (
    PROVIDER_DEFAULTS,
    create_credential,
    delete_credential,
    get_credential,
    list_credentials,
    set_status,
    test_credential,
    update_credential,
)
from backend.app.utils.crypto import decrypt_api_key, encrypt_api_key, hash_api_key, last4

router = APIRouter(tags=["model-settings"])

CHAT_PURPOSES = {
    "general", "architecture", "worldbuilding", "character", "outline",
    "draft", "polish", "review", "summary", "feedback",
}
ASSIGNMENT_FIELDS = {
    "architecture_profile_id": "chat",
    "worldbuilding_profile_id": "chat",
    "character_profile_id": "chat",
    "outline_profile_id": "chat",
    "draft_profile_id": "chat",
    "polish_profile_id": "chat",
    "review_profile_id": "chat",
    "summary_profile_id": "chat",
    "feedback_profile_id": "chat",
    "embedding_profile_id": "embedding",
    "rerank_profile_id": "rerank",
}
REMOVED_LEGACY_MARKERS = ("uni656", "flah", "bge-m3", "bge_m3", "bge m3")


class CredentialReq(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    provider: str = "openai"
    api_key: str = ""
    base_url: str = ""
    headers: dict | None = None
    is_default: bool = False


class CredentialUpdateReq(BaseModel):
    name: str | None = None
    provider: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    status: str | None = None
    is_default: bool | None = None


class ModelProfileReq(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    type: str = "chat"
    purpose: str = "general"
    provider: str = "openai"
    model: str = Field(..., min_length=1)
    api_credential_id: str
    temperature: float | None = 0.7
    max_tokens: int | None = 8192
    top_p: float | None = None
    is_default: bool = False
    is_active: bool = True


class ModelProfileUpdateReq(BaseModel):
    name: str | None = None
    type: str | None = None
    purpose: str | None = None
    provider: str | None = None
    model: str | None = None
    api_credential_id: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    top_p: float | None = None
    is_default: bool | None = None
    is_active: bool | None = None


class ProjectAssignmentReq(BaseModel):
    architecture_profile_id: str | None = None
    worldbuilding_profile_id: str | None = None
    character_profile_id: str | None = None
    outline_profile_id: str | None = None
    draft_profile_id: str | None = None
    polish_profile_id: str | None = None
    review_profile_id: str | None = None
    summary_profile_id: str | None = None
    feedback_profile_id: str | None = None
    embedding_profile_id: str | None = None
    rerank_profile_id: str | None = None


def _bools(row) -> dict:
    data = dict(row)
    for key in ("is_default", "is_active", "supports_streaming", "supports_json", "success"):
        if key in data:
            data[key] = bool(data[key])
    return data


def _require_project(user_id: str, project_id: str) -> None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM project WHERE id=? AND user_id=?",
            (project_id, user_id),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="项目不存在或你没有权限访问。")


def _require_credential(conn, user_id: str, cred_id: str) -> None:
    row = conn.execute(
        "SELECT id FROM api_credential WHERE id=? AND user_id=?",
        (cred_id, user_id),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=400, detail="API 凭证不存在或不属于你。")


def _get_profile(conn, user_id: str, profile_id: str) -> dict:
    row = conn.execute(
        "SELECT * FROM model_profile WHERE id=? AND user_id=?",
        (profile_id, user_id),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=400, detail="模型配置不存在或不属于你。")
    return dict(row)


def _validate_profile_payload(data: dict) -> None:
    model = (data.get("model") or "").strip()
    if model.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="模型名不能是 URL，请检查 baseUrl 和 model 字段是否传反。")
    model_type = data.get("type")
    purpose = data.get("purpose")
    if model_type == "embedding" and purpose != "embedding":
        raise HTTPException(status_code=400, detail="Embedding 模型的用途必须是 embedding。")
    if model_type == "rerank" and purpose != "rerank":
        raise HTTPException(status_code=400, detail="Rerank 模型的用途必须是 rerank。")
    if model_type == "chat" and purpose not in CHAT_PURPOSES:
        raise HTTPException(status_code=400, detail="Chat 模型不能用于 embedding 或 rerank。")


def _is_removed_legacy_config(row: dict) -> bool:
    haystack = " ".join(str(row.get(key, "")) for key in ("name", "provider", "model", "credential_name")).lower()
    return any(marker in haystack for marker in REMOVED_LEGACY_MARKERS)


@router.get("/api/user/api-credentials")
def list_api_credentials(request: Request):
    return list_credentials(get_current_user(request))


@router.get("/api/user/api-credentials/{cred_id}")
def get_api_credential(cred_id: str, request: Request):
    cred = get_credential(cred_id, get_current_user(request))
    if not cred:
        raise HTTPException(status_code=404, detail="API 凭证不存在。")
    return cred


@router.post("/api/user/api-credentials")
def create_api_credential(data: CredentialReq, request: Request):
    try:
        return create_credential(get_current_user(request), data.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/api/user/api-credentials/{cred_id}")
def update_api_credential(cred_id: str, data: CredentialUpdateReq, request: Request):
    try:
        return update_credential(cred_id, get_current_user(request), data.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/api/user/api-credentials/{cred_id}")
def delete_api_credential(cred_id: str, request: Request, cascade: bool = False):
    """删除 API 凭证。cascade=true 时同时删除关联的 ModelProfile。"""
    user_id = get_current_user(request)
    try:
        delete_credential(cred_id, user_id, cascade=cascade)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"message": "已删除"}


@router.post("/api/user/api-credentials/{cred_id}/test")
def test_api_credential(cred_id: str, request: Request):
    result = test_credential(cred_id, get_current_user(request))
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "测试失败"))
    return result


@router.post("/api/user/api-credentials/{cred_id}/enable")
def enable_credential(cred_id: str, request: Request):
    return set_status(cred_id, get_current_user(request), "active")


@router.post("/api/user/api-credentials/{cred_id}/disable")
def disable_credential(cred_id: str, request: Request):
    return set_status(cred_id, get_current_user(request), "disabled")


@router.get("/api/user/model-profiles")
def list_model_profiles(request: Request):
    user_id = get_current_user(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT mp.*, ac.name AS credential_name, ac.status AS credential_status
               FROM model_profile mp
               LEFT JOIN api_credential ac ON ac.id=mp.api_credential_id AND ac.user_id=mp.user_id
               WHERE mp.user_id=?
               ORDER BY mp.created_at DESC""",
            (user_id,),
        ).fetchall()
    return [item for row in rows if not _is_removed_legacy_config(item := _bools(row))]


@router.post("/api/user/model-profiles")
def create_model_profile(data: ModelProfileReq, request: Request):
    user_id = get_current_user(request)
    payload = data.model_dump()
    _validate_profile_payload(payload)
    now = datetime.datetime.now().isoformat()
    profile_id = uuid.uuid4().hex
    with get_db() as conn:
        _require_credential(conn, user_id, data.api_credential_id)
        if data.is_default:
            conn.execute("UPDATE model_profile SET is_default=0 WHERE user_id=? AND purpose=?", (user_id, data.purpose))
        conn.execute(
            """INSERT INTO model_profile
               (id, user_id, name, type, purpose, provider, model, api_credential_id,
                temperature, max_tokens, top_p, is_default, is_active, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                profile_id, user_id, data.name, data.type, data.purpose, data.provider,
                data.model.strip(), data.api_credential_id, data.temperature, data.max_tokens,
                data.top_p, 1 if data.is_default else 0, 1 if data.is_active else 0, now, now,
            ),
        )
    return {"id": profile_id, "message": "已创建"}


@router.put("/api/user/model-profiles/{profile_id}")
def update_model_profile(profile_id: str, data: ModelProfileUpdateReq, request: Request):
    user_id = get_current_user(request)
    updates = data.model_dump(exclude_none=True)
    with get_db() as conn:
        current = _get_profile(conn, user_id, profile_id)
        merged = {**current, **updates}
        _validate_profile_payload(merged)
        if updates.get("api_credential_id"):
            _require_credential(conn, user_id, updates["api_credential_id"])
        if updates.get("is_default"):
            conn.execute("UPDATE model_profile SET is_default=0 WHERE user_id=? AND purpose=?", (user_id, merged["purpose"]))
        if not updates:
            return {"message": "无变更"}
        sets = [f"{key}=?" for key in updates]
        params = list(updates.values())
        sets.append("updated_at=?")
        params.extend([datetime.datetime.now().isoformat(), profile_id, user_id])
        conn.execute(f"UPDATE model_profile SET {', '.join(sets)} WHERE id=? AND user_id=?", params)
    return {"message": "已更新"}


@router.delete("/api/user/model-profiles/{profile_id}")
def delete_model_profile(profile_id: str, request: Request):
    user_id = get_current_user(request)
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM model_profile WHERE id=? AND user_id=?", (profile_id, user_id))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="模型配置不存在。")
    return {"message": "已删除"}


@router.post("/api/user/model-profiles/{profile_id}/test")
def test_model_profile(profile_id: str, request: Request):
    user_id = get_current_user(request)
    from backend.app.services.model_runtime import ConfigError, _build_runtime, _invoke_chat, _invoke_embedding

    with get_db() as conn:
        profile = _get_profile(conn, user_id, profile_id)
    purpose = "embedding" if profile["type"] == "embedding" else "rerank" if profile["type"] == "rerank" else "general"
    try:
        cfg = _build_runtime(profile_id, purpose, user_id, allow_unhealthy=True)
        if cfg.type == "embedding":
            vector = _invoke_embedding(user_id, cfg, "test vectorization")
            ok = bool(vector)
            if ok:
                with get_db() as conn:
                    conn.execute("UPDATE model_profile SET health_status='active', last_error='', last_tested_at=?, updated_at=? WHERE id=? AND user_id=?", (datetime.datetime.now().isoformat(), datetime.datetime.now().isoformat(), profile_id, user_id))
            return {"success": ok, "message": f"测试成功，向量维度 {len(vector)}" if ok else "Embedding 返回空向量"}
        if cfg.type == "rerank":
            raise HTTPException(status_code=400, detail="Rerank 测试接口尚未实现。")
        text = _invoke_chat(user_id, cfg, "Reply exactly: OK", None, 32)
        ok = bool(text)
        if ok:
            with get_db() as conn:
                now = datetime.datetime.now().isoformat()
                conn.execute("UPDATE model_profile SET health_status='active', last_error='', last_tested_at=?, updated_at=? WHERE id=? AND user_id=?", (now, now, profile_id, user_id))
        return {"success": ok, "message": f"测试成功: {text[:200]}" if ok else "模型返回空内容"}
    except ConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/api/user/model-profiles/{profile_id}/set-default")
def set_default_profile(profile_id: str, request: Request):
    user_id = get_current_user(request)
    now = datetime.datetime.now().isoformat()
    with get_db() as conn:
        profile = _get_profile(conn, user_id, profile_id)
        conn.execute("UPDATE model_profile SET is_default=0 WHERE user_id=? AND purpose=?", (user_id, profile["purpose"]))
        conn.execute("UPDATE model_profile SET is_default=1, updated_at=? WHERE id=? AND user_id=?", (now, profile_id, user_id))
    return {"message": "已设为默认"}


@router.get("/api/projects/{project_id}/model-assignment")
def get_project_assignment(project_id: str, request: Request):
    user_id = get_current_user(request)
    _require_project(user_id, project_id)
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM project_model_assignment WHERE project_id=? AND user_id=?",
            (project_id, user_id),
        ).fetchone()
    return dict(row) if row else {}


@router.put("/api/projects/{project_id}/model-assignment")
def save_project_assignment(project_id: str, data: ProjectAssignmentReq, request: Request):
    user_id = get_current_user(request)
    _require_project(user_id, project_id)
    payload = data.model_dump()
    with get_db() as conn:
        for field, expected_type in ASSIGNMENT_FIELDS.items():
            profile_id = payload.get(field)
            if not profile_id:
                continue
            profile = _get_profile(conn, user_id, profile_id)
            if profile["type"] != expected_type:
                raise HTTPException(status_code=400, detail=f"{field} 需要 {expected_type} 模型。")
        now = datetime.datetime.now().isoformat()
        existing = conn.execute(
            "SELECT id FROM project_model_assignment WHERE project_id=? AND user_id=?",
            (project_id, user_id),
        ).fetchone()
        if existing:
            sets = [f"{field}=?" for field in ASSIGNMENT_FIELDS if field in payload]
            params = [payload[field] for field in ASSIGNMENT_FIELDS if field in payload]
            sets.append("updated_at=?")
            params.extend([now, project_id, user_id])
            conn.execute(f"UPDATE project_model_assignment SET {', '.join(sets)} WHERE project_id=? AND user_id=?", params)
        else:
            conn.execute(
                f"""INSERT INTO project_model_assignment
                    (id, user_id, project_id, {', '.join(ASSIGNMENT_FIELDS)}, created_at, updated_at)
                    VALUES ({', '.join(['?'] * (3 + len(ASSIGNMENT_FIELDS) + 2))})""",
                [uuid.uuid4().hex, user_id, project_id]
                + [payload.get(field) for field in ASSIGNMENT_FIELDS]
                + [now, now],
            )
    return get_project_assignment(project_id, request)


@router.get("/api/user/model-invocation-logs")
def list_invocation_logs(request: Request, limit: int = 50):
    user_id = get_current_user(request)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM model_invocation_log WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (user_id, min(limit, 200)),
        ).fetchall()
    return [_bools(row) for row in rows]


@router.get("/api/projects/{project_id}/model-invocation-logs")
def list_project_invocation_logs(project_id: str, request: Request, limit: int = 30):
    user_id = get_current_user(request)
    _require_project(user_id, project_id)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM model_invocation_log WHERE project_id=? AND user_id=? ORDER BY created_at DESC LIMIT ?",
            (project_id, user_id, min(limit, 100)),
        ).fetchall()
    return [_bools(row) for row in rows]


# ── SiliconFlow: 读取服务商模型列表 ──

CHAT_KEYWORDS = ("chat", "instruct", "qwen", "deepseek", "glm", "llama", "yi-", "mistral", "mixtral")
EMBED_KEYWORDS = ("bge", "embed", "gte", "jina-embeddings", "e5-", "stella", "m3e")
RERANK_KEYWORDS = ("rerank", "bge-reranker", "jina-reranker")


def _classify_model(model_id: str) -> str:
    lower = model_id.lower()
    if any(kw in lower for kw in EMBED_KEYWORDS):
        return "embedding"
    if any(kw in lower for kw in RERANK_KEYWORDS):
        return "rerank"
    if any(kw in lower for kw in CHAT_KEYWORDS):
        return "chat"
    return "unknown"


@router.get("/api/user/api-credentials/{cred_id}/models")
def fetch_provider_models(cred_id: str, request: Request):
    """读取 SiliconFlow 或其他 OpenAI-compatible 服务商的可用模型列表。"""
    import requests as req

    user_id = get_current_user(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM api_credential WHERE id=? AND user_id=?", (cred_id, user_id)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="API 凭证不存在。")
    cred = dict(row)

    provider = cred["provider"]
    base_url = (cred["base_url"] or PROVIDER_DEFAULTS.get(provider, "")).rstrip("/")

    try:
        api_key = decrypt_api_key(cred["api_key_encrypted"]) if cred.get("api_key_encrypted") else ""
    except Exception:
        raise HTTPException(status_code=400, detail="API 凭证解密失败，请重新填写 API Key。")

    if not api_key:
        raise HTTPException(status_code=400, detail="API 凭证缺少 Key。")

    # SiliconFlow / OpenAI-compatible: GET {base_url}/models
    try:
        resp = req.get(
            f"{base_url}/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15,
        )
        if resp.status_code == 401 or resp.status_code == 403:
            raise HTTPException(status_code=400, detail="硅基流动 API Key 无效，请检查 Key 是否正确。")
        if resp.status_code == 404:
            raise HTTPException(status_code=400, detail="该服务商不支持模型列表接口，请手动填写模型名。")
        resp.raise_for_status()
    except req.RequestException as e:
        raise HTTPException(status_code=400, detail=f"请求模型列表失败: {str(e)[:200]}")

    data = resp.json()

    # 兼容 OpenAI / SiliconFlow 的 /models 响应格式
    raw_models = []
    if isinstance(data, dict):
        raw_models = data.get("data") or data.get("models") or []
        if not raw_models and isinstance(data.get("result"), list):
            raw_models = data["result"]
    elif isinstance(data, list):
        raw_models = data

    normalized = []
    for item in raw_models:
        model_id = (item.get("id") or item.get("model") or "").strip()
        if not model_id:
            continue
        norm_type = _classify_model(model_id)
        normalized.append({
            "id": model_id,
            "name": model_id,
            "type": norm_type,
            "provider": provider,
        })

    # 按类型分组排序：chat 优先，然后 embedding，rerank，unknown
    type_order = {"chat": 0, "embedding": 1, "rerank": 2, "unknown": 3}
    normalized.sort(key=lambda m: (type_order.get(m["type"], 3), m["id"]))

    return {"models": normalized, "provider": provider}


# ── 快速配置：一键创建文本生成模型（不自动创建 Embedding）──

PROVIDER_DISPLAY_NAMES = {
    "openai": "OpenAI",
    "deepseek": "DeepSeek",
    "siliconflow": "硅基流动",
    "qwen": "通义千问",
    "anthropic": "Claude",
}

QUICK_SETUP_CHAT = {
    "siliconflow": {"model": "deepseek-v4-flash"},
    "openai": {"model": "gpt-4o-mini"},
    "deepseek": {"model": "deepseek-chat"},
    "qwen": {"model": "qwen-plus"},
    "anthropic": {"model": "claude-3-5-haiku-latest"},
}

ASSIGNMENT_CHAT_FIELDS = [
    "architecture_profile_id", "worldbuilding_profile_id", "character_profile_id",
    "outline_profile_id", "draft_profile_id", "polish_profile_id",
    "review_profile_id", "summary_profile_id", "feedback_profile_id",
]


class QuickSetupReq(BaseModel):
    provider: str = Field(..., min_length=1)
    api_key: str = Field(..., min_length=1)
    project_id: str | None = None


@router.post("/api/user/model-quick-setup")
def model_quick_setup(data: QuickSetupReq, request: Request):
    """一键配置文本生成模型：选择服务商 + 填 Key → 测试 → 保存。不自动创建 Embedding。"""
    from llm_adapters import create_llm_adapter
    from backend.app.services.model_runtime import _provider_to_interface

    user_id = get_current_user(request)
    provider = data.provider.strip()
    api_key = data.api_key.strip()
    project_id = (data.project_id or "").strip()

    if provider not in PROVIDER_DEFAULTS:
        raise HTTPException(status_code=400, detail=f"不支持的服务商: {provider}")
    if provider not in QUICK_SETUP_CHAT:
        raise HTTPException(status_code=400, detail=f"服务商 {provider} 暂不支持一键配置，请在高级设置中手动创建。")
    if not api_key:
        raise HTTPException(status_code=400, detail="API Key 不能为空。")

    base_url = PROVIDER_DEFAULTS[provider]
    chat_cfg = QUICK_SETUP_CHAT[provider]
    default_model = chat_cfg["model"]

    # 1. 先测试 API Key（不写入数据库）
    try:
        adapter = create_llm_adapter(
            interface_format=_provider_to_interface(provider),
            base_url=base_url,
            model_name=default_model,
            api_key=api_key,
            temperature=0.7,
            max_tokens=32,
            timeout=25,
        )
        response = adapter.invoke("Reply exactly: OK")
        if not response:
            err = getattr(adapter, "last_error", "") or "无响应"
            raise HTTPException(
                status_code=400,
                detail="测试失败，请检查 API Key 和服务商是否匹配。",
            )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="测试失败，请检查 API Key 和服务商是否匹配。",
        )

    # 2. 测试通过，创建或更新 ApiCredential
    now = datetime.datetime.now().isoformat()
    display_name = PROVIDER_DISPLAY_NAMES.get(provider, provider)
    encrypted_key = encrypt_api_key(api_key) if api_key else ""

    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM api_credential WHERE user_id=? AND provider=? LIMIT 1",
            (user_id, provider),
        ).fetchone()

        if existing:
            cred_id = existing[0]
            conn.execute(
                """UPDATE api_credential SET api_key_encrypted=?, api_key_last4=?, api_key_hash=?,
                   base_url=?, status='active', is_default=1, updated_at=?
                   WHERE id=? AND user_id=?""",
                (encrypted_key, last4(api_key), hash_api_key(api_key),
                 base_url, now, cred_id, user_id),
            )
            # 取消该 provider 其他凭证的默认标记
            conn.execute(
                "UPDATE api_credential SET is_default=0 WHERE user_id=? AND id!=?",
                (user_id, cred_id),
            )
        else:
            cred_id = uuid.uuid4().hex
            conn.execute(
                """INSERT INTO api_credential
                   (id, user_id, name, provider, api_key_encrypted, api_key_last4, api_key_hash,
                    base_url, status, is_default, last_tested_at, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (cred_id, user_id, display_name, provider, encrypted_key,
                 last4(api_key), hash_api_key(api_key), base_url, "active", 1, now, now, now),
            )

    # 3. 只创建或更新 Chat ModelProfile（不创建 Embedding）
    chat_profile_id = None
    with get_db() as conn:
        existing_chat = conn.execute(
            "SELECT id FROM model_profile WHERE user_id=? AND provider=? AND type='chat' LIMIT 1",
            (user_id, provider),
        ).fetchone()

        if existing_chat:
            chat_profile_id = existing_chat[0]
            conn.execute(
                """UPDATE model_profile SET model=?, api_credential_id=?, health_status='active',
                   is_default=1, is_active=1, updated_at=?
                   WHERE id=? AND user_id=?""",
                (default_model, cred_id, now, chat_profile_id, user_id),
            )
            # 取消该用户其他 chat 的默认标记
            conn.execute(
                "UPDATE model_profile SET is_default=0 WHERE user_id=? AND type='chat' AND id!=?",
                (user_id, chat_profile_id),
            )
        else:
            conn.execute("UPDATE model_profile SET is_default=0 WHERE user_id=? AND type='chat'", (user_id,))
            chat_profile_id = uuid.uuid4().hex
            conn.execute(
                """INSERT INTO model_profile
                   (id, user_id, name, type, purpose, provider, model, api_credential_id,
                    temperature, max_tokens, is_default, is_active, health_status, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (chat_profile_id, user_id, f"{display_name} 文本模型",
                 "chat", "general", provider, default_model, cred_id,
                 0.7, 8192, 1, 1, "active", now, now),
            )

    # 4. 如果有项目，只绑定 Chat 相关阶段（不处理 embeddingProfileId）
    if project_id:
        try:
            _require_project(user_id, project_id)
            with get_db() as conn:
                existing_pma = conn.execute(
                    "SELECT id FROM project_model_assignment WHERE project_id=? AND user_id=?",
                    (project_id, user_id),
                ).fetchone()
                if existing_pma:
                    set_clauses = [f"{f}=?" for f in ASSIGNMENT_CHAT_FIELDS] + ["updated_at=?"]
                    params = [chat_profile_id] * len(ASSIGNMENT_CHAT_FIELDS) + [now, project_id, user_id]
                    conn.execute(
                        f"UPDATE project_model_assignment SET {', '.join(set_clauses)} WHERE project_id=? AND user_id=?",
                        params,
                    )
                else:
                    all_fields = ["id", "user_id", "project_id"] + ASSIGNMENT_CHAT_FIELDS + ["created_at", "updated_at"]
                    values = [uuid.uuid4().hex, user_id, project_id] + [chat_profile_id] * len(ASSIGNMENT_CHAT_FIELDS) + [now, now]
                    conn.execute(
                        f"INSERT INTO project_model_assignment ({', '.join(all_fields)}) VALUES ({', '.join(['?'] * len(all_fields))})",
                        values,
                    )
        except HTTPException:
            pass

    return {
        "success": True,
        "data": {
            "message": "配置成功，可以开始生成小说。",
            "provider": provider,
            "chatReady": True,
            "embeddingReady": False,
            "chatModel": default_model,
            "embeddingMessage": "知识库向量化未配置，不影响小说生成。",
        },
    }


# ── 模型系统状态查询 ──

@router.get("/api/user/model-settings/status")
def get_model_system_status(request: Request):
    """返回当前用户模型系统的真实可用状态。"""
    user_id = get_current_user(request)

    with get_db() as conn:
        # 查找可用的 Chat ModelProfile
        chat_profile = conn.execute(
            """SELECT mp.*, ac.status AS cred_status, ac.base_url AS cred_base_url,
                      ac.provider AS cred_provider
               FROM model_profile mp
               JOIN api_credential ac ON ac.id = mp.api_credential_id AND ac.user_id = mp.user_id
               WHERE mp.user_id=? AND mp.type='chat' AND mp.is_active=1
                 AND mp.health_status='active' AND ac.status='active'
               ORDER BY mp.is_default DESC, mp.last_tested_at DESC
               LIMIT 1""",
            (user_id,),
        ).fetchone()

        chat_ready = False
        chat_model = ""
        chat_provider = ""
        chat_errors = []

        if chat_profile:
            profile = dict(chat_profile)
            model = (profile.get("model") or "").strip()
            base_url = (profile.get("cred_base_url") or "").strip()
            provider = (profile.get("cred_provider") or "").strip()

            if model.startswith(("http://", "https://")):
                chat_errors.append("模型名被错误设置为 URL，请修复。")
            elif not model:
                chat_errors.append("模型名未设置。")
            elif not base_url.startswith(("http://", "https://")):
                chat_errors.append("Base URL 配置异常。")
            elif base_url.endswith("/embeddings") or base_url.endswith("/chat/completions"):
                chat_errors.append("Base URL 被错误拼接了接口路径，请修复。")
            else:
                chat_ready = True
                chat_model = model
                chat_provider = provider

        # Embedding 状态（不影响 core status）
        emb_profile = conn.execute(
            """SELECT 1 FROM model_profile mp
               JOIN api_credential ac ON ac.id = mp.api_credential_id AND ac.user_id = mp.user_id
               WHERE mp.user_id=? AND mp.type='embedding' AND mp.is_active=1
                 AND mp.health_status='active' AND ac.status='active'
               LIMIT 1""",
            (user_id,),
        ).fetchone()
        embedding_ready = emb_profile is not None

        # Credential 数量
        cred_count = conn.execute(
            "SELECT COUNT(*) FROM api_credential WHERE user_id=? AND status='active'",
            (user_id,),
        ).fetchone()[0]

    return {
        "chatReady": chat_ready,
        "embeddingReady": embedding_ready,
        "chatModel": chat_model,
        "chatProvider": chat_provider,
        "chatErrors": chat_errors,
        "activeCredentials": cred_count,
        "coreReady": chat_ready,
        "message": "文本生成可用" if chat_ready else ("配置异常" if chat_errors else "未完成配置"),
    }


# ── 清空当前模型配置 ──

@router.post("/api/user/model-settings/reset")
def reset_model_settings(request: Request):
    """清空当前用户所有模型配置（ApiCredential + ModelProfile），但保留项目和数据。"""
    user_id = get_current_user(request)
    now = datetime.datetime.now().isoformat()

    with get_db() as conn:
        # 1. 清空 ProjectModelAssignment 中该用户所有 profileId 字段
        conn.execute(
            """UPDATE project_model_assignment SET
               architecture_profile_id=NULL, worldbuilding_profile_id=NULL,
               character_profile_id=NULL, outline_profile_id=NULL,
               draft_profile_id=NULL, polish_profile_id=NULL,
               review_profile_id=NULL, summary_profile_id=NULL,
               feedback_profile_id=NULL, embedding_profile_id=NULL,
               rerank_profile_id=NULL, updated_at=?
               WHERE user_id=?""",
            (now, user_id),
        )

        # 2. 删除该用户所有 ModelProfile
        deleted_profiles = conn.execute(
            "DELETE FROM model_profile WHERE user_id=?", (user_id,)
        ).rowcount

        # 3. 删除该用户所有 ApiCredential
        deleted_creds = conn.execute(
            "DELETE FROM api_credential WHERE user_id=?", (user_id,)
        ).rowcount

    return {
        "success": True,
        "message": "模型配置已清空，可以重新配置。",
        "details": {
            "deletedProfiles": deleted_profiles,
            "deletedCredentials": deleted_creds,
        },
    }


# ── 修复旧配置 ──

@router.post("/api/user/model-settings/repair")
def repair_model_settings(request: Request):
    """修复当前用户的脏数据：provider、baseUrl、model URL、孤儿 ModelProfile。"""
    user_id = get_current_user(request)
    fixes = []
    now = datetime.datetime.now().isoformat()

    with get_db() as conn:
        # 1. provider=custom 且 baseUrl 包含已知服务商域名 → 修正 provider
        domain_provider_map = [
            ("siliconflow.cn", "siliconflow"),
            ("openai.com", "openai"),
            ("deepseek.com", "deepseek"),
            ("dashscope.aliyuncs.com", "qwen"),
            ("anthropic.com", "anthropic"),
        ]
        custom_rows = conn.execute(
            "SELECT * FROM api_credential WHERE user_id=? AND provider='custom'",
            (user_id,),
        ).fetchall()

        for row in custom_rows:
            cred = dict(row)
            old_base = cred["base_url"] or ""
            for domain, correct_provider in domain_provider_map:
                if domain in old_base.lower():
                    conn.execute(
                        "UPDATE api_credential SET provider=?, updated_at=? WHERE id=? AND user_id=?",
                        (correct_provider, now, cred["id"], user_id),
                    )
                    fixes.append(f"修正 provider: custom→{correct_provider} (ID: {cred['id'][:8]}...)")
                    break

        # 2. 修复 baseUrl 里的错误路径
        all_creds = conn.execute(
            "SELECT * FROM api_credential WHERE user_id=?", (user_id,)
        ).fetchall()

        for row in all_creds:
            cred = dict(row)
            old_url = cred["base_url"] or ""
            new_url = old_url.rstrip("/")
            changed = False

            for suffix in ["/embeddings", "/chat/completions", "/v1/v1"]:
                if new_url.endswith(suffix):
                    new_url = new_url[: -len(suffix)]
                    changed = True

            # 确保非空 URL 以 /v1 结尾（除了 Anthropic）
            if new_url and not new_url.endswith("/v1") and "anthropic.com" not in new_url:
                if "/v1" not in new_url:
                    new_url = new_url.rstrip("/") + "/v1"
                    changed = True

            if changed:
                conn.execute(
                    "UPDATE api_credential SET base_url=?, updated_at=? WHERE id=? AND user_id=?",
                    (new_url, now, cred["id"], user_id),
                )
                fixes.append(f"修正 baseUrl: {old_url}→{new_url}")

        # 3. ModelProfile.model 是 URL → 标记 invalid
        url_models = conn.execute(
            """SELECT * FROM model_profile
               WHERE user_id=? AND (model LIKE 'http://%' OR model LIKE 'https://%')""",
            (user_id,),
        ).fetchall()

        for mp_row in url_models:
            mp = dict(mp_row)
            conn.execute(
                "UPDATE model_profile SET health_status='invalid', last_error='模型名是 URL，请修正。', updated_at=? WHERE id=? AND user_id=?",
                (now, mp["id"], user_id),
            )
            fixes.append(f"标记无效模型: {mp['name']} (模型名是 URL)")

        # 4. 删除孤儿 ModelProfile（绑定的 ApiCredential 不存在）
        orphans = conn.execute(
            """SELECT mp.id, mp.name FROM model_profile mp
               WHERE mp.user_id=? AND mp.api_credential_id IS NOT NULL
               AND mp.api_credential_id != ''
               AND NOT EXISTS (
                   SELECT 1 FROM api_credential ac
                   WHERE ac.id = mp.api_credential_id AND ac.user_id = mp.user_id
               )""",
            (user_id,),
        ).fetchall()

        for orphan in orphans:
            conn.execute("DELETE FROM model_profile WHERE id=? AND user_id=?", (orphan[0], user_id))
            fixes.append(f"删除孤儿模型配置: {orphan[1]} (凭证已不存在)")

    return {
        "success": True,
        "message": f"修复完成，共处理 {len(fixes)} 项。",
        "details": fixes,
    }


# ── 兼容旧接口（转发到 repair）──

@router.post("/api/user/fix-legacy-credentials")
def fix_legacy_credentials(request: Request):
    """已废弃，请使用 /api/user/model-settings/repair。"""
    return repair_model_settings(request)
