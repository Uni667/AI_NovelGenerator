"""角色登场时间线 API — 章节维度登场/退场记录"""

from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from backend.app.database import get_db
from backend.app.services import project_service
from backend.app.auth import get_current_user
from backend.app.models.chapter import (
    CharacterAppearanceCreate,
    CharacterAppearanceUpdate,
)

router = APIRouter(tags=["角色登场时间线"])

APPEARANCE_TYPES = [
    {"value": "present", "label": "登场"},
    {"value": "mentioned", "label": "被提及"},
    {"value": "flashback", "label": "闪回"},
    {"value": "implied", "label": "暗示/伏笔"},
    {"value": "exit", "label": "退场"},
    {"value": "return", "label": "回归"},
    {"value": "transformation", "label": "重大转变"},
]

ROLE_TYPES = [
    {"value": "pov", "label": "主视角"},
    {"value": "major", "label": "主要配角"},
    {"value": "minor", "label": "次要配角"},
    {"value": "background", "label": "背景/提及"},
]


def _check_project(project_id: str, request: Request):
    user_id = get_current_user(request)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return user_id


@router.get("/api/v1/projects/{project_id}/character-appearances")
def list_appearances(project_id: str, request: Request, character_id: int | None = None,
                     chapter_number: int | None = None):
    _check_project(project_id, request)
    with get_db() as conn:
        query = """SELECT ca.*, ch.name AS character_name, ch.status AS character_status
                   FROM character_appearance ca
                   JOIN character_profile ch ON ch.id = ca.character_id
                   WHERE ca.project_id = ?"""
        params: list = [project_id]
        if character_id is not None:
            query += " AND ca.character_id = ?"
            params.append(character_id)
        if chapter_number is not None:
            query += " AND ca.chapter_number = ?"
            params.append(chapter_number)
        query += " ORDER BY ca.chapter_number, ca.character_id"

        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


@router.post("/api/v1/projects/{project_id}/character-appearances")
def create_appearance(project_id: str, data: CharacterAppearanceCreate, request: Request):
    _check_project(project_id, request)
    now = datetime.now().isoformat()
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM character_appearance WHERE character_id=? AND chapter_number=?",
            (data.character_id, data.chapter_number)
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="该角色在此章节已有登场记录，请使用更新接口")

        cur = conn.execute(
            """INSERT INTO character_appearance
               (project_id, character_id, chapter_number, appearance_type,
                role_in_chapter, summary, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (project_id, data.character_id, data.chapter_number,
             data.appearance_type, data.role_in_chapter, data.summary, now)
        )
        # 更新角色首次登场章节（如果是首次登场记录）
        conn.execute(
            """UPDATE character_profile
               SET first_appearance_chapter = COALESCE(first_appearance_chapter, ?)
               WHERE id=? AND project_id=?""",
            (data.chapter_number, data.character_id, project_id)
        )
    return {"id": cur.lastrowid, "message": "登场记录创建成功"}


@router.put("/api/v1/projects/{project_id}/character-appearances/{appearance_id}")
def update_appearance(project_id: str, appearance_id: int, data: CharacterAppearanceUpdate, request: Request):
    _check_project(project_id, request)
    updates = data.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="没有提供更新字段")
    updates["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [appearance_id, project_id]
    with get_db() as conn:
        cur = conn.execute(
            f"UPDATE character_appearance SET {set_clause} WHERE id=? AND project_id=?",
            values
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="登场记录不存在")
    return {"message": "登场记录已更新"}


@router.delete("/api/v1/projects/{project_id}/character-appearances/{appearance_id}")
def delete_appearance(project_id: str, appearance_id: int, request: Request):
    _check_project(project_id, request)
    with get_db() as conn:
        cur = conn.execute(
            "DELETE FROM character_appearance WHERE id=? AND project_id=?",
            (appearance_id, project_id)
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="登场记录不存在")
    return {"message": "登场记录已删除"}


@router.get("/api/v1/projects/{project_id}/character-appearances/timeline")
def get_timeline(project_id: str, request: Request):
    """返回按章节聚合的角色登场时间线，便于全局规划"""
    _check_project(project_id, request)
    with get_db() as conn:
        appearances = conn.execute(
            """SELECT ca.*, ch.name AS character_name, ch.status AS character_status
               FROM character_appearance ca
               JOIN character_profile ch ON ch.id = ca.character_id
               WHERE ca.project_id=?
               ORDER BY ca.chapter_number, ca.appearance_type""",
            (project_id,)
        ).fetchall()

        chapters_map: dict[int, list] = {}
        for a in appearances:
            d = dict(a)
            ch_num = d["chapter_number"]
            if ch_num not in chapters_map:
                chapters_map[ch_num] = []
            chapters_map[ch_num].append(d)

        result = []
        for ch_num in sorted(chapters_map):
            entries = chapters_map[ch_num]
            chars_in_chapter = [e["character_name"] for e in entries]
            result.append({
                "chapter_number": ch_num,
                "character_count": len(chars_in_chapter),
                "characters": chars_in_chapter,
                "entries": entries,
            })
        return result


@router.get("/api/v1/character-appearance-types")
def get_appearance_types():
    return {"types": APPEARANCE_TYPES, "roles": ROLE_TYPES}


@router.post("/api/v1/projects/{project_id}/character-appearances/batch")
def create_appearances_batch(project_id: str, data: list[CharacterAppearanceCreate], request: Request):
    """批量创建登场记录"""
    _check_project(project_id, request)
    if not data:
        raise HTTPException(status_code=400, detail="请提供至少一条登场记录")
    now = datetime.now().isoformat()
    created = []
    with get_db() as conn:
        for item in data:
            existing = conn.execute(
                "SELECT id FROM character_appearance WHERE character_id=? AND chapter_number=?",
                (item.character_id, item.chapter_number)
            ).fetchone()
            if existing:
                continue
            cur = conn.execute(
                """INSERT INTO character_appearance
                   (project_id, character_id, chapter_number, appearance_type,
                    role_in_chapter, summary, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (project_id, item.character_id, item.chapter_number,
                 item.appearance_type, item.role_in_chapter, item.summary, now)
            )
            conn.execute(
                """UPDATE character_profile
                   SET first_appearance_chapter=COALESCE(first_appearance_chapter, ?)
                   WHERE id=? AND project_id=?""",
                (item.chapter_number, item.character_id, project_id)
            )
            created.append(cur.lastrowid)
    return {"created": len(created), "ids": created}
