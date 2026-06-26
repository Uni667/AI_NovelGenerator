import datetime
import logging
import re
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
from backend.app.services.config_resolver import PROVIDER_DEFAULT_CHAT_MODELS
from backend.app.errors import (
    API_CREDENTIAL_IN_USE,
    API_KEY_INVALID,
    MODEL_CONFIG_INVALID,
    api_error,
)

logger = logging.getLogger(__name__)
from backend.app.services.model_runtime import (
    get_chat_model_status,
    normalize_base_url,
    repair_user_model_settings,
    reset_user_model_settings,
    test_chat_connection,
)
from backend.app.utils.crypto import decrypt_api_key, encrypt_api_key, hash_api_key, last4

router = APIRouter(tags=["model-settings"])

CHAT_PURPOSES = {
    "general", "architecture", "worldbuilding", "character", "outline",
    "draft", "polish", "review", "summary", "feedback",
    "voice_polish", "quality_rewrite", "blueprint_polish", "architecture_polish",
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


class PlatformPresetReq(BaseModel):
    platform: str = Field(default="tomato", min_length=1)


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


FAST_KEYWORDS = {
    "mini": 5, "flash": 6, "lite": 5, "haiku": 5, "small": 3, "turbo": 3,
    "instant": 4, "nano": 4, "8b": 2, "7b": 2, "1.5b": 2,
}
STRONG_KEYWORDS = {
    "gpt-5": 8, "gpt5": 8, "gpt-4.1": 7, "gpt-4o": 6, "sonnet": 7, "opus": 8,
    "max": 6, "pro": 5, "v4": 5, "qwen-plus": 5, "qwen-max": 7,
    "32b": 3, "70b": 5, "72b": 5, "110b": 6,
}
REASONING_KEYWORDS = {
    "reasoner": 8, "r1": 7, "reason": 4, "thinking": 5, "o1": 7, "o3": 8, "o4": 6,
}
CREATIVE_KEYWORDS = {
    "gpt-4o": 5, "sonnet": 6, "qwen-plus": 5, "qwen-max": 6, "v4": 5, "pro": 3,
}


def _profile_text(profile: dict) -> str:
    return " ".join(str(profile.get(key, "") or "").lower() for key in ("name", "model", "provider", "purpose"))


def _keyword_score(text: str, keywords: dict[str, int]) -> int:
    score = 0
    for keyword, weight in keywords.items():
        if keyword in text:
            score += weight
    return score


def _platform_slot_weights(platform: str, slot: str) -> dict[str, int]:
    platform = (platform or "tomato").lower()
    if slot in {"architecture_profile_id", "worldbuilding_profile_id", "character_profile_id"}:
        return {"strong": 3, "reasoning": 2, "creative": 1, "fast": 0}
    if slot == "outline_profile_id":
        if platform == "tomato":
            return {"fast": 3, "creative": 2, "strong": 1, "reasoning": 0}
        return {"strong": 2, "creative": 1, "reasoning": 1, "fast": 1}
    if slot == "draft_profile_id":
        if platform == "tomato":
            return {"creative": 3, "fast": 2, "strong": 2, "reasoning": 0}
        if platform == "qidian":
            return {"strong": 3, "reasoning": 2, "creative": 1, "fast": 0}
        if platform == "zongheng":
            return {"strong": 2, "creative": 2, "reasoning": 2, "fast": 0}
    if slot == "polish_profile_id":
        return {"strong": 3, "creative": 2, "reasoning": 1, "fast": 0}
    if slot == "review_profile_id":
        return {"strong": 3, "reasoning": 3, "creative": 0, "fast": 0}
    if slot in {"summary_profile_id", "feedback_profile_id"}:
        return {"strong": 2, "reasoning": 1, "creative": 0, "fast": 2}
    return {"strong": 1, "reasoning": 1, "creative": 1, "fast": 1}


def _slot_to_expected_purpose(slot: str) -> str:
    mapping = {
        "architecture_profile_id": "architecture",
        "worldbuilding_profile_id": "worldbuilding",
        "character_profile_id": "character",
        "outline_profile_id": "outline",
        "draft_profile_id": "draft",
        "polish_profile_id": "polish",
        "review_profile_id": "review",
        "summary_profile_id": "summary",
        "feedback_profile_id": "feedback",
    }
    return mapping.get(slot, "general")


def _score_chat_profile_for_slot(profile: dict, slot: str, platform: str) -> int:
    text = _profile_text(profile)
    weights = _platform_slot_weights(platform, slot)
    score = 0

    health = (profile.get("health_status") or "").lower()
    if health == "active":
        score += 30
    elif health == "untested":
        score += 5
    elif health in {"invalid", "disabled"}:
        return -10**9

    if profile.get("is_default"):
        score += 6
    if profile.get("last_tested_at"):
        score += 4

    purpose = (profile.get("purpose") or "").lower()
    expected_purpose = _slot_to_expected_purpose(slot)
    if purpose == expected_purpose:
        score += 35
    elif purpose == "general":
        score += 8
    elif expected_purpose in {"review", "polish"} and purpose in {"review", "polish"}:
        score += 18

    score += _keyword_score(text, FAST_KEYWORDS) * weights.get("fast", 0)
    score += _keyword_score(text, STRONG_KEYWORDS) * weights.get("strong", 0)
    score += _keyword_score(text, REASONING_KEYWORDS) * weights.get("reasoning", 0)
    score += _keyword_score(text, CREATIVE_KEYWORDS) * weights.get("creative", 0)

    max_tokens = int(profile.get("max_tokens") or 0)
    if max_tokens >= 32000:
        score += 6 * (weights.get("strong", 0) + weights.get("reasoning", 0))
    elif max_tokens >= 16000:
        score += 3 * (weights.get("strong", 0) + weights.get("reasoning", 0))

    model = str(profile.get("model", "") or "").lower()
    if platform == "tomato" and any(k in model for k in ["flash", "mini", "gpt-4o", "sonnet", "deepseek-chat"]):
        score += 8
    if platform == "qidian" and any(k in model for k in ["reasoner", "r1", "max", "pro", "sonnet", "gpt-5", "gpt-4.1"]):
        score += 8
    if platform == "zongheng" and any(k in model for k in ["sonnet", "qwen-plus", "qwen-max", "gpt-4.1", "gpt-5"]):
        score += 6

    return score


def _pick_best_chat_profile(profiles: list[dict], slot: str, platform: str) -> str | None:
    best_id = None
    best_score = -10**9
    for profile in profiles:
        score = _score_chat_profile_for_slot(profile, slot, platform)
        if score > best_score:
            best_score = score
            best_id = profile.get("id")
    return best_id


@router.get("/api/v1/user/api-credentials")
def list_api_credentials(request: Request):
    return list_credentials(get_current_user(request))


@router.get("/api/v1/user/api-credentials/{cred_id}")
def get_api_credential(cred_id: str, request: Request):
    cred = get_credential(cred_id, get_current_user(request))
    if not cred:
        raise HTTPException(status_code=404, detail="API 凭证不存在。")
    return cred


@router.post("/api/v1/user/api-credentials")
def create_api_credential(data: CredentialReq, request: Request):
    try:
        return create_credential(get_current_user(request), data.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/api/v1/user/api-credentials/{cred_id}")
def update_api_credential(cred_id: str, data: CredentialUpdateReq, request: Request):
    try:
        return update_credential(cred_id, get_current_user(request), data.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/api/v1/user/api-credentials/{cred_id}")
def delete_api_credential(cred_id: str, request: Request, cascade: bool = False):
    """删除 API 凭证。cascade=true 时同时删除关联的 ModelProfile。"""
    user_id = get_current_user(request)
    try:
        delete_credential(cred_id, user_id, cascade=cascade)
        return {"success": True, "message": "模型服务账号已删除。"}
    except ValueError as exc:
        text = str(exc)
        if text.startswith("API_CREDENTIAL_IN_USE:"):
            count = int(text.split(":", 1)[1] or "0")
            raise api_error(
                400,
                API_CREDENTIAL_IN_USE,
                "该模型服务账号正在被模型配置使用。你可以选择同时删除关联模型配置。",
                {"count": count},
            )
        if "不存在" in text:
            raise HTTPException(status_code=404, detail="API 凭证不存在。")
        raise HTTPException(status_code=400, detail="删除失败，请稍后重试。")


@router.post("/api/v1/user/api-credentials/{cred_id}/test")
def test_api_credential(cred_id: str, request: Request):
    result = test_credential(cred_id, get_current_user(request))
    if not result.get("success"):
        raise api_error(400, result.get("code") or API_KEY_INVALID, result.get("message") or "测试失败，请检查 API Key 和服务商是否匹配。")
    return result


@router.post("/api/v1/user/api-credentials/{cred_id}/enable")
def enable_credential(cred_id: str, request: Request):
    return set_status(cred_id, get_current_user(request), "active")


@router.post("/api/v1/user/api-credentials/{cred_id}/disable")
def disable_credential(cred_id: str, request: Request):
    return set_status(cred_id, get_current_user(request), "disabled")


@router.get("/api/v1/user/model-profiles")
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
    return [_bools(row) for row in rows]


@router.post("/api/v1/user/model-profiles")
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


@router.put("/api/v1/user/model-profiles/{profile_id}")
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


@router.delete("/api/v1/user/model-profiles/{profile_id}")
def delete_model_profile(profile_id: str, request: Request):
    user_id = get_current_user(request)
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM model_profile WHERE id=? AND user_id=?", (profile_id, user_id))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="模型配置不存在。")
    return {"message": "已删除"}


@router.post("/api/v1/user/model-profiles/{profile_id}/test")
def test_model_profile(profile_id: str, request: Request):
    user_id = get_current_user(request)
    from backend.app.services.config_resolver import ConfigError, _build_runtime, _invoke_chat, _invoke_embedding

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
                    now = datetime.datetime.now().isoformat()
                    conn.execute("UPDATE model_profile SET health_status='active', last_error='', last_tested_at=?, updated_at=? WHERE id=? AND user_id=?", (now, now, profile_id, user_id))
                    conn.execute("UPDATE api_credential SET status='active', last_error='', last_tested_at=?, updated_at=? WHERE id=? AND user_id=?", (now, now, cfg.api_credential_id, user_id))
            if ok:
                return {"success": True, "message": "测试成功"}
            return {"success": ok, "message": f"测试成功，向量维度 {len(vector)}" if ok else "Embedding 返回空向量"}
        if cfg.type == "rerank":
            raise HTTPException(status_code=400, detail="Rerank 测试接口尚未实现。")
        text = _invoke_chat(user_id, cfg, "Reply exactly: OK", None, 32)
        ok = bool(text)
        if ok:
            with get_db() as conn:
                now = datetime.datetime.now().isoformat()
                conn.execute("UPDATE model_profile SET health_status='active', last_error='', last_tested_at=?, updated_at=? WHERE id=? AND user_id=?", (now, now, profile_id, user_id))
                conn.execute("UPDATE api_credential SET status='active', last_error='', last_tested_at=?, updated_at=? WHERE id=? AND user_id=?", (now, now, cfg.api_credential_id, user_id))
            if ok:
                return {"success": True, "message": "测试成功"}
        return {"success": ok, "message": f"测试成功: {text[:200]}" if ok else "模型返回空内容"}
    except ConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/api/v1/user/model-profiles/{profile_id}/set-default")
def set_default_profile(profile_id: str, request: Request):
    user_id = get_current_user(request)
    now = datetime.datetime.now().isoformat()
    with get_db() as conn:
        profile = _get_profile(conn, user_id, profile_id)
        conn.execute("UPDATE model_profile SET is_default=0 WHERE user_id=? AND purpose=?", (user_id, profile["purpose"]))
        conn.execute("UPDATE model_profile SET is_default=1, updated_at=? WHERE id=? AND user_id=?", (now, profile_id, user_id))
    return {"message": "已设为默认"}


@router.get("/api/v1/projects/{project_id}/model-assignment")
def get_project_assignment(project_id: str, request: Request):
    user_id = get_current_user(request)
    _require_project(user_id, project_id)
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM project_model_assignment WHERE project_id=? AND user_id=?",
            (project_id, user_id),
        ).fetchone()
    return dict(row) if row else {}


@router.put("/api/v1/projects/{project_id}/model-assignment")
def save_project_assignment(project_id: str, data: ProjectAssignmentReq, request: Request):
    user_id = get_current_user(request)
    _require_project(user_id, project_id)
    payload = data.model_dump(exclude_unset=True)
    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM project_model_assignment WHERE project_id=? AND user_id=?",
            (project_id, user_id),
        ).fetchone()
        current = dict(existing) if existing else {}
        for field, expected_type in ASSIGNMENT_FIELDS.items():
            profile_id = payload.get(field, current.get(field))
            if not profile_id:
                continue
            profile = _get_profile(conn, user_id, profile_id)
            if profile["type"] != expected_type:
                raise HTTPException(status_code=400, detail=f"{field} 需要 {expected_type} 模型。")
        now = datetime.datetime.now().isoformat()
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


@router.post("/api/v1/projects/{project_id}/model-assignment/apply-platform-preset")
def apply_platform_assignment_preset(project_id: str, data: PlatformPresetReq, request: Request):
    user_id = get_current_user(request)
    _require_project(user_id, project_id)
    platform = (data.platform or "tomato").strip().lower()

    with get_db() as conn:
        profiles = [
            dict(row)
            for row in conn.execute(
                """SELECT * FROM model_profile
                   WHERE user_id=? AND type='chat' AND is_active=1
                   ORDER BY is_default DESC, last_tested_at DESC, updated_at DESC""",
                (user_id,),
            ).fetchall()
        ]
        if not profiles:
            raise HTTPException(status_code=400, detail="还没有可用的文本模型，请先完成模型设置。")

        current = conn.execute(
            "SELECT * FROM project_model_assignment WHERE project_id=? AND user_id=?",
            (project_id, user_id),
        ).fetchone()
        current_data = dict(current) if current else {}

        payload = {
            "architecture_profile_id": _pick_best_chat_profile(profiles, "architecture_profile_id", platform),
            "worldbuilding_profile_id": _pick_best_chat_profile(profiles, "worldbuilding_profile_id", platform),
            "character_profile_id": _pick_best_chat_profile(profiles, "character_profile_id", platform),
            "outline_profile_id": _pick_best_chat_profile(profiles, "outline_profile_id", platform),
            "draft_profile_id": _pick_best_chat_profile(profiles, "draft_profile_id", platform),
            "polish_profile_id": _pick_best_chat_profile(profiles, "polish_profile_id", platform),
            "review_profile_id": _pick_best_chat_profile(profiles, "review_profile_id", platform),
            "summary_profile_id": _pick_best_chat_profile(profiles, "summary_profile_id", platform),
            "feedback_profile_id": _pick_best_chat_profile(profiles, "feedback_profile_id", platform),
            "embedding_profile_id": current_data.get("embedding_profile_id"),
            "rerank_profile_id": current_data.get("rerank_profile_id"),
        }

    return save_project_assignment(project_id, ProjectAssignmentReq(**payload), request)


@router.get("/api/v1/user/model-invocation-logs")
def list_invocation_logs(request: Request, limit: int = 50):
    user_id = get_current_user(request)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM model_invocation_log WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (user_id, min(limit, 200)),
        ).fetchall()
    return [_bools(row) for row in rows]


@router.get("/api/v1/projects/{project_id}/model-invocation-logs")
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


@router.get("/api/v1/user/api-credentials/{cred_id}/models")
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
        raise api_error(400, API_KEY_INVALID, "测试失败，请检查 API Key 和服务商是否匹配。")

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
        logger.warning("Model list fetch failed: %s", e)
        raise HTTPException(status_code=400, detail="请求模型列表失败，请检查网络连接和服务地址")

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

ASSIGNMENT_CHAT_FIELDS = [
    "architecture_profile_id", "worldbuilding_profile_id", "character_profile_id",
    "outline_profile_id", "draft_profile_id", "polish_profile_id",
    "review_profile_id", "summary_profile_id",
]


class QuickSetupReq(BaseModel):
    provider: str = Field(..., min_length=1)
    api_key: str = Field(..., min_length=1)
    project_id: str | None = None


@router.post("/api/v1/user/model-quick-setup")
def model_quick_setup(data: QuickSetupReq, request: Request):
    """一键配置文本生成模型：选择服务商 + 填 Key → 测试 → 保存。不自动创建 Embedding。"""
    user_id = get_current_user(request)
    provider = data.provider.strip()
    api_key = data.api_key.strip()
    project_id = (data.project_id or "").strip()

    if provider not in PROVIDER_DEFAULTS:
        raise api_error(400, MODEL_CONFIG_INVALID, "当前模型配置不完整，建议清空后重新配置。")
    if not PROVIDER_DEFAULT_CHAT_MODELS.get(provider):
        raise api_error(400, MODEL_CONFIG_INVALID, "当前模型配置不完整，建议清空后重新配置。")
    if not api_key:
        raise api_error(400, API_KEY_INVALID, "测试失败，请检查 API Key 和服务商是否匹配。")

    base_url = normalize_base_url(provider, PROVIDER_DEFAULTS[provider])
    default_model = PROVIDER_DEFAULT_CHAT_MODELS[provider]

    # 1. 先测试 API Key（不写入数据库）
    test_result = test_chat_connection(
        provider=provider,
        base_url=base_url,
        model_name=default_model,
        api_key=api_key,
        timeout=25,
    )
    if not test_result.get("success"):
        raise api_error(
            400,
            test_result.get("code") or API_KEY_INVALID,
            test_result.get("message") or "测试失败，请检查 API Key 和服务商是否匹配。",
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
                   base_url=?, status='active', is_default=1, last_tested_at=?, last_error='', updated_at=?
                   WHERE id=? AND user_id=?""",
                (encrypted_key, last4(api_key), hash_api_key(api_key),
                 base_url, now, now, cred_id, user_id),
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
                """UPDATE model_profile SET provider=?, base_url=?, model=?, api_credential_id=?, health_status='active',
                   is_default=1, is_active=1, last_tested_at=?, last_error='', updated_at=?
                   WHERE id=? AND user_id=?""",
                (provider, base_url, default_model, cred_id, now, now, chat_profile_id, user_id),
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
                   (id, user_id, name, type, purpose, provider, base_url, model, api_credential_id,
                    temperature, max_tokens, is_default, is_active, health_status, last_tested_at, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (chat_profile_id, user_id, f"{display_name} 文本模型",
                 "chat", "general", provider, base_url, default_model, cred_id,
                 0.7, 8192, 1, 1, "active", now, now, now),
            )

    # 4. 如果有项目，只绑定 Chat 相关阶段（不处理 embeddingProfileId）
    if project_id:
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

@router.get("/api/v1/user/model-settings/status")
def get_model_system_status(request: Request):
    """返回当前用户模型系统的真实可用状态。"""
    user_id = get_current_user(request)
    return get_chat_model_status(user_id)


# ── 清空当前模型配置 ──

@router.post("/api/v1/user/model-settings/reset")
def reset_model_settings(request: Request):
    """清空当前用户所有模型配置（ApiCredential + ModelProfile），但保留项目和数据。"""
    user_id = get_current_user(request)
    return reset_user_model_settings(user_id)


# ── 修复旧配置 ──

@router.post("/api/v1/user/model-settings/repair")
def repair_model_settings(request: Request):
    """修复当前用户的脏数据：provider、baseUrl、model URL、孤儿 ModelProfile。"""
    user_id = get_current_user(request)
    return repair_user_model_settings(user_id)


# ── 兼容旧接口（转发到 repair）──

@router.post("/api/v1/user/fix-legacy-credentials")
def fix_legacy_credentials(request: Request):
    """已废弃，请使用 /api/user/model-settings/repair。"""
    return repair_model_settings(request)
