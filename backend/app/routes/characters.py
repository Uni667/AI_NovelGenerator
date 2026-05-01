import os
from datetime import datetime
from fastapi import APIRouter, HTTPException
from backend.app.database import get_db
from backend.app.services import project_service
from backend.app.models.chapter import CharacterProfileCreate, CharacterProfileUpdate

router = APIRouter(tags=["角色管理"])


@router.get("/api/v1/projects/{project_id}/characters")
def list_characters(project_id: str):
    project = project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM character_profile WHERE project_id = ? ORDER BY updated_at DESC",
            (project_id,)
        ).fetchall()
        return [dict(r) for r in rows]


@router.post("/api/v1/projects/{project_id}/characters")
def create_character(project_id: str, data: CharacterProfileCreate):
    project = project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    now = datetime.now().isoformat()
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO character_profile (project_id, name, description, updated_at) VALUES (?, ?, ?, ?)",
            (project_id, data.name, data.description, now)
        )
        return {"id": cursor.lastrowid, "name": data.name, "description": data.description, "updated_at": now}


@router.put("/api/v1/projects/{project_id}/characters/{character_id}")
def update_character(project_id: str, character_id: int, data: CharacterProfileUpdate):
    project = project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
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
def delete_character(project_id: str, character_id: int):
    project = project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM character_profile WHERE id = ? AND project_id = ?",
            (character_id, project_id)
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="角色不存在")
        return {"message": "角色已删除"}


@router.post("/api/v1/projects/{project_id}/characters/import-from-state")
def import_characters_from_state(project_id: str):
    """从 character_state.txt 解析角色并导入数据库"""
    project = project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    state_file = os.path.join(project["filepath"], "character_state.txt")
    if not os.path.exists(state_file):
        raise HTTPException(status_code=404, detail="character_state.txt 不存在，请先生成架构")

    with open(state_file, "r", encoding="utf-8") as f:
        content = f.read()

    # 简单解析：按行分割，查找角色名
    imported = []
    now = datetime.now().isoformat()
    with get_db() as conn:
        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # 尝试提取角色名（格式：角色名：描述 / 角色名 - 描述 / **角色名** 等）
            name = line.split("：")[0].split(":")[0].split(" - ")[0].split("–")[0].strip().lstrip("- *>#|")
            if len(name) < 2 or len(name) > 30:
                continue
            description = line[len(name):].lstrip("：:-– ")
            if not description:
                description = line
            # 检查是否已存在
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
