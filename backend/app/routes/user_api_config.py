"""API 凭证管理 + 模型配置管理 + 项目模型分配 + 迁移 + 调用日志。"""

import datetime
import logging
import uuid

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from backend.app.auth import get_current_user
from backend.app.database import get_db
from backend.app.services.api_credential_service import (
    create_credential,
    delete_credential,
    get_credential,
    list_credentials,
    set_status,
    test_credential,
    update_credential,
)
from backend.app.services.user_api_config_service import (
    get_user_api_config_response,
    save_user_api_config,
    update_user_api_config,
)
from backend.app.utils.crypto import decrypt

router = APIRouter(tags=["API 配置"])
logger = logging.getLogger(__name__)


# ── Pydantic models ──

class SaveConfigReq(BaseModel):
    provider: str = "openai"
    api_key: str = Field(..., min_length=1)
    base_url: str | None = None
    default_chat_model: str | None = None
    default_embedding_model: str | None = None
    default_model: str | None = None


class UpdateConfigReq(BaseModel):
    default_chat_model: str | None = None
    default_embedding_model: str | None = None
    base_url: str | None = None
    provider: str | None = None


class CredentialReq(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
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
    name: str = Field(..., min_length=1)
    type: str = "chat"
    purpose: str = "general"
    provider: str = "openai"
    base_url: str = ""
    model: str = Field(..., min_length=1)
    api_credential_id: str = ""
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
    base_url: str | None = None
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


# ── 旧版兼容：单 API 配置 ──

@router.get("/api/user/api-config")
def get_config(request: Request):
    return get_user_api_config_response(get_current_user(request))


@router.post("/api/user/api-config")
def save_config(data: SaveConfigReq, request: Request):
    user_id = get_current_user(request)
    try:
        return save_user_api_config(
            user_id=user_id, provider=data.provider, api_key=data.api_key,
            base_url=data.base_url, default_chat_model=data.default_chat_model or data.default_model,
            default_embedding_model=data.default_embedding_model,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/api/user/api-config")
def update_config(data: UpdateConfigReq, request: Request):
    user_id = get_current_user(request)
    try:
        return update_user_api_config(user_id, data.model_dump(exclude_none=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/user/api-config/test")
def test_config(request: Request):
    user_id = get_current_user(request)
    from backend.app.services.user_api_config_service import test_user_api_config
    return test_user_api_config(user_id)


@router.delete("/api/user/api-config")
def delete_config(request: Request):
    user_id = get_current_user(request)
    from backend.app.services.user_api_config_service import delete_user_api_config
    if not delete_user_api_config(user_id):
        raise HTTPException(status_code=404, detail="没有已保存的配置")
    return {"message": "已删除"}


# ── 新版：API 凭证 CRUD ──

@router.get("/api/user/api-credentials")
def list_api_credentials(request: Request):
    return list_credentials(get_current_user(request))


@router.get("/api/user/api-credentials/{cred_id}")
def get_api_credential(cred_id: str, request: Request):
    user_id = get_current_user(request)
    cred = get_credential(cred_id, user_id)
    if not cred:
        raise HTTPException(status_code=404, detail="凭证不存在")
    return cred


@router.post("/api/user/api-credentials")
def create_api_credential(data: CredentialReq, request: Request):
    try:
        return create_credential(get_current_user(request), data.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/api/user/api-credentials/{cred_id}")
def update_api_credential(cred_id: str, data: CredentialUpdateReq, request: Request):
    try:
        return update_credential(cred_id, get_current_user(request), data.model_dump(exclude_none=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/api/user/api-credentials/{cred_id}")
def delete_api_credential(cred_id: str, request: Request):
    try:
        delete_credential(cred_id, get_current_user(request))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"message": "已删除"}


@router.post("/api/user/api-credentials/{cred_id}/test")
def test_api_credential(cred_id: str, request: Request):
    result = test_credential(cred_id, get_current_user(request))
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.post("/api/user/api-credentials/{cred_id}/enable")
def enable_credential(cred_id: str, request: Request):
    return set_status(cred_id, get_current_user(request), "active")


@router.post("/api/user/api-credentials/{cred_id}/disable")
def disable_credential(cred_id: str, request: Request):
    return set_status(cred_id, get_current_user(request), "disabled")


# ── 新版：ModelProfile CRUD ──

@router.get("/api/user/model-profiles")
def list_model_profiles(request: Request):
    user_id = get_current_user(request)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM model_profile WHERE user_id=? ORDER BY created_at", (user_id,)
        ).fetchall()
    return [_profile_row(r) for r in rows]


@router.get("/api/user/model-profiles/{profile_id}")
def get_model_profile(profile_id: str, request: Request):
    user_id = get_current_user(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM model_profile WHERE id=? AND user_id=?", (profile_id, user_id)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="模型配置不存在")
    return _profile_row(row)


def _profile_row(row) -> dict:
    r = dict(row)
    for bf in ["is_default", "is_active", "supports_streaming", "supports_json"]:
        r[bf] = bool(r.get(bf, False))
    return r


@router.post("/api/user/model-profiles")
def create_model_profile(data: ModelProfileReq, request: Request):
    user_id = get_current_user(request)
    profile_id = uuid.uuid4().hex
    now = datetime.datetime.now().isoformat()

    if data.is_default:
        with get_db() as conn:
            conn.execute(
                "UPDATE model_profile SET is_default=0 WHERE user_id=? AND purpose=?", (user_id, data.purpose)
            )

    with get_db() as conn:
        conn.execute(
            """INSERT INTO model_profile
               (id, user_id, name, type, purpose, provider, base_url, model,
                temperature, max_tokens, top_p,
                api_credential_id, is_default, is_active, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (profile_id, user_id, data.name, data.type, data.purpose,
             data.provider, data.base_url, data.model,
             data.temperature, data.max_tokens, data.top_p,
             data.api_credential_id or None,
             1 if data.is_default else 0, 1, now, now),
        )
    return {"id": profile_id, "message": "模型配置已创建"}


@router.put("/api/user/model-profiles/{profile_id}")
def update_model_profile(profile_id: str, data: ModelProfileUpdateReq, request: Request):
    user_id = get_current_user(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM model_profile WHERE id=? AND user_id=?", (profile_id, user_id)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="模型配置不存在")

    now = datetime.datetime.now().isoformat()
    sets = []
    params = []
    for field in ["name", "type", "purpose", "provider", "base_url", "model",
                  "api_credential_id", "temperature", "max_tokens", "top_p",
                  "is_default", "is_active"]:
        val = getattr(data, field, None)
        if val is not None:
            sets.append(f"{field}=?")
            params.append(val)

    if data.is_default:
        with get_db() as conn:
            latest = conn.execute("SELECT purpose FROM model_profile WHERE id=?", (profile_id,)).fetchone()
            if latest:
                conn.execute(
                    "UPDATE model_profile SET is_default=0 WHERE user_id=? AND purpose=?",
                    (user_id, latest[0]),
                )

    sets.append("updated_at=?")
    params.append(now)
    params.extend([profile_id, user_id])

    with get_db() as conn:
        conn.execute(f"UPDATE model_profile SET {', '.join(sets)} WHERE id=? AND user_id=?", params)
    return {"message": "已更新"}


@router.delete("/api/user/model-profiles/{profile_id}")
def delete_model_profile(profile_id: str, request: Request):
    user_id = get_current_user(request)
    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM model_profile WHERE id=? AND user_id=?", (profile_id, user_id)
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="模型配置不存在")
    return {"message": "已删除"}


@router.post("/api/user/model-profiles/{profile_id}/test")
def test_model_profile(profile_id: str, request: Request):
    user_id = get_current_user(request)
    from backend.app.services.model_runtime import _build_runtime, _invoke_chat, _invoke_embedding, ConfigError

    try:
        cfg = _build_runtime(profile_id, "general")
    except ConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))

    now = datetime.datetime.now().isoformat()
    if cfg.type == "embedding":
        result = _invoke_embedding(cfg, "test vectorization")
        if result:
            return {"success": True, "message": f"测试成功，向量维度: {len(result)}"}
        return {"success": False, "message": "Embedding 返回空向量"}
    else:
        adapter = _build_chat(cfg)
        response = adapter.invoke("Reply exactly: OK")
        if response:
            return {"success": True, "message": f"测试成功: {response[:200]}"}
        err = getattr(adapter, "last_error", "") or "无响应"
        _update_model_health(profile_id, "invalid", err, now)
        return {"success": False, "message": f"测试失败: {err}"}


def _build_chat(cfg):
    from llm_adapters import create_llm_adapter
    return create_llm_adapter(
        interface_format="OpenAI", base_url=cfg.base_url, model_name=cfg.model,
        api_key=cfg.api_key, temperature=cfg.temperature or 0.7,
        max_tokens=cfg.max_tokens or 8192, timeout=600,
    )


def _update_model_health(profile_id: str, status: str, error: str, now: str) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE model_profile SET health_status=?, last_error=?, last_tested_at=?, updated_at=? WHERE id=?",
            (status, error[:500], now, now, profile_id),
        )


@router.post("/api/user/model-profiles/{profile_id}/set-default")
def set_default_profile(profile_id: str, request: Request):
    user_id = get_current_user(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT purpose FROM model_profile WHERE id=? AND user_id=?", (profile_id, user_id)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="模型配置不存在")
        purpose = row[0]
        conn.execute(
            "UPDATE model_profile SET is_default=0 WHERE user_id=? AND purpose=?", (user_id, purpose)
        )
        conn.execute(
            "UPDATE model_profile SET is_default=1, updated_at=? WHERE id=? AND user_id=?",
            (datetime.datetime.now().isoformat(), profile_id, user_id),
        )
    return {"message": "已设为默认"}


# ── 项目模型分配 ──

@router.get("/api/projects/{project_id}/model-assignment")
def get_project_assignment(project_id: str, request: Request):
    user_id = get_current_user(request)
    from backend.app.services.project_service import get_project
    if not get_project(project_id, user_id):
        raise HTTPException(status_code=404, detail="项目不存在")
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM project_model_assignment WHERE project_id=?", (project_id,)
        ).fetchone()
    return dict(row) if row else {}


@router.put("/api/projects/{project_id}/model-assignment")
def save_project_assignment(project_id: str, data: ProjectAssignmentReq, request: Request):
    user_id = get_current_user(request)
    from backend.app.services.project_service import get_project
    if not get_project(project_id, user_id):
        raise HTTPException(status_code=404, detail="项目不存在")

    now = datetime.datetime.now().isoformat()
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM project_model_assignment WHERE project_id=?", (project_id,)
        ).fetchone()

        if existing:
            sets = []
            params = []
            for field in ["architecture_profile_id", "worldbuilding_profile_id", "character_profile_id",
                          "outline_profile_id", "draft_profile_id", "polish_profile_id",
                          "review_profile_id", "summary_profile_id", "feedback_profile_id",
                          "embedding_profile_id", "rerank_profile_id"]:
                val = getattr(data, field, None)
                if val is not None:
                    sets.append(f"{field}=?")
                    params.append(val)
            if sets:
                sets.append("updated_at=?")
                params.append(now)
                params.append(project_id)
                conn.execute(
                    f"UPDATE project_model_assignment SET {', '.join(sets)} WHERE project_id=?", params
                )
        else:
            conn.execute(
                """INSERT INTO project_model_assignment
                   (id, project_id, architecture_profile_id, worldbuilding_profile_id,
                    character_profile_id, outline_profile_id, draft_profile_id,
                    polish_profile_id, review_profile_id, summary_profile_id,
                    feedback_profile_id, embedding_profile_id, rerank_profile_id,
                    created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (uuid.uuid4().hex, project_id,
                 data.architecture_profile_id, data.worldbuilding_profile_id,
                 data.character_profile_id, data.outline_profile_id,
                 data.draft_profile_id, data.polish_profile_id,
                 data.review_profile_id, data.summary_profile_id,
                 data.feedback_profile_id, data.embedding_profile_id,
                 data.rerank_profile_id, now, now),
            )
    return get_project_assignment(project_id, request)


# ── 迁移旧配置 ──

@router.post("/api/user/migrate-legacy-llm-configs")
def migrate_legacy(request: Request):
    user_id = get_current_user(request)
    migrated = _migrate_legacy(user_id)
    return {"migrated": migrated, "message": f"已迁移 {migrated} 个旧配置"}


@router.get("/api/user/legacy-llm-configs/status")
def legacy_status(request: Request):
    user_id = get_current_user(request)
    with get_db() as conn:
        llm_count = conn.execute(
            "SELECT COUNT(*) FROM user_llm_config WHERE user_id=?", (user_id,)
        ).fetchone()[0]
        emb_count = conn.execute(
            "SELECT COUNT(*) FROM user_embedding_config WHERE user_id=?", (user_id,)
        ).fetchone()[0]
    return {"total": llm_count + emb_count, "llm": llm_count, "embedding": emb_count}


def _migrate_legacy(user_id: str) -> int:
    count = 0
    with get_db() as conn:
        llms = conn.execute("SELECT * FROM user_llm_config WHERE user_id=?", (user_id,)).fetchall()
        embs = conn.execute("SELECT * FROM user_embedding_config WHERE user_id=?", (user_id,)).fetchall()

    # 为每个旧 LLM 创建 ApiCredential（如果同名不存在）
    for row in llms:
        r = dict(row)
        try:
            api_key = decrypt(r["api_key"])
        except Exception:
            continue
        cred_id = _ensure_cred(user_id, r["name"], r["interface_format"], api_key, r["base_url"])
        _ensure_profile(user_id, r["name"], "chat", r["interface_format"], r["base_url"],
                        r["model_name"], cred_id)
        count += 1

    for row in embs:
        r = dict(row)
        try:
            api_key = decrypt(r["api_key"])
        except Exception:
            continue
        cred_id = _ensure_cred(user_id, r["name"], r["interface_format"], api_key, r["base_url"])
        _ensure_profile(user_id, r["name"], "embedding", r["interface_format"], r["base_url"],
                        r["model_name"], cred_id)
        count += 1

    return count


def _ensure_cred(user_id: str, name: str, provider: str, api_key: str, base_url: str) -> str:
    kh = __import__("backend.app.utils.crypto", fromlist=["hash_api_key"]).hash_api_key(api_key)
    now = datetime.datetime.now().isoformat()
    with get_db() as conn:
        exist = conn.execute(
            "SELECT id FROM api_credential WHERE user_id=? AND api_key_hash=?", (user_id, kh)
        ).fetchone()
        if exist:
            return exist[0]
        cred_id = uuid.uuid4().hex
        conn.execute(
            """INSERT INTO api_credential
               (id, user_id, name, provider, api_key_encrypted, api_key_last4, api_key_hash,
                base_url, status, is_default, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (cred_id, user_id, f"{name}-migrated", provider.lower(),
             __import__("backend.app.utils.crypto", fromlist=["encrypt_api_key"]).encrypt_api_key(api_key),
             api_key[-4:] if len(api_key) > 4 else api_key, kh,
             base_url, "untested", 0, now, now),
        )
        return cred_id


def _ensure_profile(user_id: str, name: str, ptype: str, provider: str, base_url: str,
                    model: str, cred_id: str) -> None:
    now = datetime.datetime.now().isoformat()
    with get_db() as conn:
        exist = conn.execute(
            "SELECT id FROM model_profile WHERE user_id=? AND name=? AND type=?",
            (user_id, name, ptype),
        ).fetchone()
        if exist:
            conn.execute(
                "UPDATE model_profile SET api_credential_id=?, updated_at=? WHERE id=?",
                (cred_id, now, exist[0]),
            )
            return
        conn.execute(
            """INSERT INTO model_profile
               (id, user_id, name, type, purpose, provider, base_url, model,
                api_credential_id, is_default, is_active, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (uuid.uuid4().hex, user_id, f"{name}-migrated", ptype,
             "embedding" if ptype == "embedding" else "general",
             provider.lower(), base_url, model,
             cred_id, 0, 1, now, now),
        )


# ── 调用日志 ──

@router.get("/api/user/model-invocation-logs")
def list_invocation_logs(request: Request, limit: int = 50):
    user_id = get_current_user(request)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM model_invocation_log WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (user_id, min(limit, 200)),
        ).fetchall()
    result = []
    for row in rows:
        r = dict(row)
        r["success"] = bool(r["success"])
        result.append(r)
    return result


@router.get("/api/projects/{project_id}/model-invocation-logs")
def list_project_invocation_logs(project_id: str, request: Request, limit: int = 30):
    user_id = get_current_user(request)
    from backend.app.services.project_service import get_project
    if not get_project(project_id, user_id):
        raise HTTPException(status_code=404, detail="项目不存在")
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM model_invocation_log WHERE project_id=? ORDER BY created_at DESC LIMIT ?",
            (project_id, min(limit, 100)),
        ).fetchall()
    result = []
    for row in rows:
        r = dict(row)
        r["success"] = bool(r["success"])
        result.append(r)
    return result
