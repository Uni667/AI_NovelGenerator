"""角色冲突网 API — 冲突 CRUD + 参与方管理"""

from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from backend.app.database import get_db
from backend.app.services import project_service
from backend.app.auth import get_current_user
from backend.app.models.chapter import (
    CharacterConflictCreate,
    CharacterConflictUpdate,
)

router = APIRouter(tags=["角色冲突网"])

CONFLICT_TYPES = [
    {"value": "position", "label": "立场冲突"},
    {"value": "interest", "label": "利益冲突"},
    {"value": "emotion", "label": "情感冲突"},
    {"value": "power", "label": "权力冲突"},
    {"value": "misunderstanding", "label": "误会"},
    {"value": "life_death", "label": "生死冲突"},
    {"value": "ideology", "label": "理念冲突"},
    {"value": "class", "label": "阶层冲突"},
    {"value": "betrayal", "label": "背叛"},
    {"value": "other", "label": "其他"},
]

CONFLICT_STATUSES = ["brewing", "active", "escalating", "climax", "subsiding", "resolved"]

PARTICIPANT_ROLES = ["protagonist", "antagonist", "mediator", "bystander", "instigator", "victim"]


def _check_project(project_id: str, request: Request):
    user_id = get_current_user(request)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return user_id


@router.get("/api/v1/projects/{project_id}/character-conflicts")
def list_conflicts(project_id: str, request: Request):
    _check_project(project_id, request)
    with get_db() as conn:
        conflicts = conn.execute(
            "SELECT * FROM character_conflict WHERE project_id=? ORDER BY intensity DESC, updated_at DESC",
            (project_id,)
        ).fetchall()

        result = []
        for c in conflicts:
            d = dict(c)
            participants = conn.execute(
                """SELECT cp.id AS pid, cp.character_id, cp.role,
                          ch.name, ch.status AS char_status
                   FROM character_conflict_participant cp
                   JOIN character_profile ch ON ch.id = cp.character_id
                   WHERE cp.conflict_id=?""",
                (d["id"],)
            ).fetchall()
            d["participants"] = [dict(p) for p in participants]
            result.append(d)
        return result


@router.post("/api/v1/projects/{project_id}/character-conflicts")
def create_conflict(project_id: str, data: CharacterConflictCreate, request: Request):
    _check_project(project_id, request)
    now = datetime.now().isoformat()
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO character_conflict
               (project_id, title, description, conflict_type, intensity,
                start_chapter, resolved_chapter, resolution, status, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (project_id, data.title, data.description, data.conflict_type,
             data.intensity, data.start_chapter, data.resolved_chapter,
             data.resolution, data.status, now)
        )
        conflict_id = cur.lastrowid

        # 批量插入参与方
        for char_id in data.participant_ids:
            conn.execute(
                "INSERT OR IGNORE INTO character_conflict_participant (conflict_id, character_id, role) VALUES (?, ?, ?)",
                (conflict_id, char_id, "participant")
            )

    return {"id": conflict_id, "message": "冲突创建成功"}


@router.put("/api/v1/projects/{project_id}/character-conflicts/{conflict_id}")
def update_conflict(project_id: str, conflict_id: int, data: CharacterConflictUpdate, request: Request):
    _check_project(project_id, request)
    participant_ids = data.participant_ids
    updates = {k: v for k, v in data.model_dump(exclude_unset=True).items() if k != "participant_ids"}
    if not updates and participant_ids is None:
        raise HTTPException(status_code=400, detail="没有提供更新字段")

    now = datetime.now().isoformat()
    with get_db() as conn:
        if updates:
            updates["updated_at"] = now
            set_clause = ", ".join(f"{k}=?" for k in updates)
            values = list(updates.values()) + [conflict_id, project_id]
            conn.execute(
                f"UPDATE character_conflict SET {set_clause} WHERE id=? AND project_id=?",
                values
            )

        if participant_ids is not None:
            conn.execute("DELETE FROM character_conflict_participant WHERE conflict_id=?", (conflict_id,))
            for char_id in participant_ids:
                conn.execute(
                    "INSERT OR IGNORE INTO character_conflict_participant (conflict_id, character_id, role) VALUES (?, ?, ?)",
                    (conflict_id, char_id, "participant")
                )

    return {"message": "冲突已更新"}


@router.delete("/api/v1/projects/{project_id}/character-conflicts/{conflict_id}")
def delete_conflict(project_id: str, conflict_id: int, request: Request):
    _check_project(project_id, request)
    with get_db() as conn:
        cur = conn.execute("DELETE FROM character_conflict WHERE id=? AND project_id=?", (conflict_id, project_id))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="冲突记录不存在")
    return {"message": "冲突已删除"}


@router.put("/api/v1/projects/{project_id}/character-conflicts/{conflict_id}/participants/{character_id}")
def update_participant_role(project_id: str, conflict_id: int, character_id: int,
                            role: str = "participant", request: Request = None):
    _check_project(project_id, request)
    with get_db() as conn:
        conn.execute(
            "UPDATE character_conflict_participant SET role=? WHERE conflict_id=? AND character_id=?",
            (role, conflict_id, character_id)
        )
    return {"message": "参与方角色已更新"}


@router.get("/api/v1/character-conflict-types")
def get_conflict_types():
    return {"types": CONFLICT_TYPES, "statuses": CONFLICT_STATUSES, "roles": PARTICIPANT_ROLES}
