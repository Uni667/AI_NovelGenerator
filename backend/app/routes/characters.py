import os
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from backend.app.database import get_db
from backend.app.services import project_service
from backend.app.auth import get_current_user
from backend.app.models.chapter import CharacterProfileCreate, CharacterProfileUpdate

router = APIRouter(tags=["角色管理"])


def _check_project(project_id: str, request: Request) -> dict:
    user_id = get_current_user(request)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


@router.get("/api/v1/projects/{project_id}/characters")
def list_characters(project_id: str, request: Request):
    _check_project(project_id, request)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM character_profile WHERE project_id = ? ORDER BY updated_at DESC",
            (project_id,)
        ).fetchall()
        return [dict(r) for r in rows]


@router.post("/api/v1/projects/{project_id}/characters")
def create_character(project_id: str, data: CharacterProfileCreate, request: Request):
    _check_project(project_id, request)
    now = datetime.now().isoformat()
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO character_profile (project_id, name, description, updated_at) VALUES (?, ?, ?, ?)",
            (project_id, data.name, data.description, now)
        )
        return {"id": cursor.lastrowid, "name": data.name, "description": data.description, "updated_at": now}


@router.put("/api/v1/projects/{project_id}/characters/{character_id}")
def update_character(project_id: str, character_id: int, data: CharacterProfileUpdate, request: Request):
    _check_project(project_id, request)
    updates = data.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="没有提供更新字段")
    updates["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [character_id, project_id]
    with get_db() as conn:
        cursor = conn.execute(
            f"UPDATE character_profile SET {set_clause} WHERE id = ? AND project_id = ?",
            values
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="角色不存在")
        row = conn.execute("SELECT * FROM character_profile WHERE id = ?", (character_id,)).fetchone()
        return dict(row) if row else {}


@router.delete("/api/v1/projects/{project_id}/characters/{character_id}")
def delete_character(project_id: str, character_id: int, request: Request):
    _check_project(project_id, request)
    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM character_profile WHERE id = ? AND project_id = ?",
            (character_id, project_id)
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="角色不存在")
        return {"message": "角色已删除"}


@router.post("/api/v1/projects/{project_id}/characters/import-from-state")
def import_characters_from_state(project_id: str, request: Request):
    """从 character_state.txt 解析角色并导入数据库"""
    project = _check_project(project_id, request)
    state_file = os.path.join(project["filepath"], "character_state.txt")
    if not os.path.exists(state_file):
        raise HTTPException(status_code=404, detail="character_state.txt 不存在，请先生成架构")

    with open(state_file, "r", encoding="utf-8") as f:
        content = f.read()

    imported = []
    now = datetime.now().isoformat()
    with get_db() as conn:
        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            name = line.split("：")[0].split(":")[0].split(" - ")[0].split("–")[0].strip().lstrip("- *>#|")
            if len(name) < 2 or len(name) > 30:
                continue
            description = line[len(name):].lstrip("：:-– ")
            if not description:
                description = line
            existing = conn.execute(
                "SELECT id FROM character_profile WHERE project_id = ? AND name = ?",
                (project_id, name)
            ).fetchone()
            if existing:
                continue
            conn.execute(
                "INSERT INTO character_profile (project_id, name, description, updated_at) VALUES (?, ?, ?, ?)",
                (project_id, name, description[:500], now)
            )
            imported.append(name)

    return {"message": f"已导入 {len(imported)} 个角色", "characters": imported}
