"""API 凭证管理 + 模型配置管理 + 项目模型分配 + 调用日志。旧版 LLM/Embedding 配置已移除。"""

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

router = APIRouter(tags=["API 配置"])
logger = logging.getLogger(__name__)


# ── Pydantic models ──

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


# ── 工具函数 ──

def _profile_row(row) -> dict:
    r = dict(row)
    for bf in ["is_default", "is_active", "supports_streaming", "supports_json"]:
        r[bf] = bool(r.get(bf, False))
    return r


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


def _check_project_owner(project_id: str, user_id: str) -> None:
    from backend.app.services.project_service import get_project
    if not get_project(project_id, user_id):
        raise HTTPException(status_code=404, detail="项目不存在或你没有权限访问。")


def _check_model_ownership(conn, profile_id: str, user_id: str) -> None:
    row = conn.execute(
        "SELECT id, user_id FROM model_profile WHERE id=? AND user_id=?", (profile_id, user_id)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=400, detail=f"模型配置 {profile_id} 不存在或不属于你")

def _check_credential_ownership(conn, cred_id: str, user_id: str) -> None:
    row = conn.execute(
        "SELECT id FROM api_credential WHERE id=? AND user_id=?", (cred_id, user_id)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=400, detail=f"API 凭证 {cred_id} 不存在或不属于你")


# ── API 凭证 CRUD ──

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


# ── ModelProfile CRUD ──

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


@router.post("/api/user/model-profiles")
def create_model_profile(data: ModelProfileReq, request: Request):
    user_id = get_current_user(request)
    profile_id = uuid.uuid4().hex
    now = datetime.datetime.now().isoformat()

    # 校验凭证归属
    if data.api_credential_id:
        with get_db() as conn:
            _check_credential_ownership(conn, data.api_credential_id, user_id)

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
        current = dict(row)

    # 校验新凭证归属
    if data.api_credential_id:
        with get_db() as conn:
            _check_credential_ownership(conn, data.api_credential_id, user_id)

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
        purpose = current.get("purpose", "general")
        with get_db() as conn:
            conn.execute(
                "UPDATE model_profile SET is_default=0 WHERE user_id=? AND purpose=?",
                (user_id, purpose),
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

    with get_db() as conn:
        _check_model_ownership(conn, profile_id, user_id)

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
    _check_project_owner(project_id, user_id)
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM project_model_assignment WHERE project_id=?", (project_id,)
        ).fetchone()
    return dict(row) if row else {}


@router.put("/api/projects/{project_id}/model-assignment")
def save_project_assignment(project_id: str, data: ProjectAssignmentReq, request: Request):
    user_id = get_current_user(request)
    _check_project_owner(project_id, user_id)

    # 校验所有指定的 model_profile 都属于当前用户
    with get_db() as conn:
        for field_name in ["architecture_profile_id", "worldbuilding_profile_id", "character_profile_id",
                          "outline_profile_id", "draft_profile_id", "polish_profile_id",
                          "review_profile_id", "summary_profile_id", "feedback_profile_id",
                          "embedding_profile_id", "rerank_profile_id"]:
            val = getattr(data, field_name, None)
            if val:
                _check_model_ownership(conn, val, user_id)

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
    _check_project_owner(project_id, user_id)
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
