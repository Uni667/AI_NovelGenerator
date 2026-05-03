"""角色关系图 API — 关系 CRUD + 图谱数据"""

from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from backend.app.database import get_db
from backend.app.services import project_service
from backend.app.auth import get_current_user
from backend.app.models.chapter import (
    CharacterRelationshipCreate,
    CharacterRelationshipUpdate,
    CharacterRelationshipResponse,
)

router = APIRouter(tags=["角色关系图"])

REL_TYPES = [
    {"value": "family", "label": "亲属"},
    {"value": "ally", "label": "盟友"},
    {"value": "enemy", "label": "敌对"},
    {"value": "mentor", "label": "师徒"},
    {"value": "lover", "label": "爱慕/情感"},
    {"value": "interest", "label": "利益绑定"},
    {"value": "hidden", "label": "隐性关系"},
    {"value": "evolving", "label": "阶段性变化"},
    {"value": "rival", "label": "竞争/对手"},
    {"value": "other", "label": "其他"},
]

STATUSES = ["active", "strained", "broken", "evolving", "resolved"]


def _check_project(project_id: str, request: Request):
    user_id = get_current_user(request)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return user_id


@router.get("/api/v1/projects/{project_id}/character-relationships")
def list_relationships(project_id: str, request: Request):
    _check_project(project_id, request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT cr.*, ca.name AS name_a, cb.name AS name_b
               FROM character_relationship cr
               LEFT JOIN character_profile ca ON ca.id = cr.character_id_a
               LEFT JOIN character_profile cb ON cb.id = cr.character_id_b
               WHERE cr.project_id = ?
               ORDER BY cr.updated_at DESC""",
            (project_id,)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["name_a"] = d.pop("name_a", "") or ""
            d["name_b"] = d.pop("name_b", "") or ""
            result.append(d)
        return result


@router.post("/api/v1/projects/{project_id}/character-relationships")
def create_relationship(project_id: str, data: CharacterRelationshipCreate, request: Request):
    _check_project(project_id, request)
    if data.character_id_a == data.character_id_b:
        raise HTTPException(status_code=400, detail="不能创建与自身的关系")
    now = datetime.now().isoformat()
    with get_db() as conn:
        # dedup: check existing
        existing = conn.execute(
            """SELECT id FROM character_relationship
               WHERE project_id=? AND (
                 (character_id_a=? AND character_id_b=?) OR
                 (character_id_a=? AND character_id_b=?)
               )""",
            (project_id, data.character_id_a, data.character_id_b,
             data.character_id_b, data.character_id_a)
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="这两个角色之间已存在关系记录，请使用更新接口")
        cur = conn.execute(
            """INSERT INTO character_relationship
               (project_id, character_id_a, character_id_b, rel_type, description,
                strength, direction, start_chapter, status, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (project_id, data.character_id_a, data.character_id_b,
             data.rel_type, data.description, data.strength, data.direction,
             data.start_chapter, data.status, now)
        )
        return {"id": cur.lastrowid, "message": "关系创建成功"}


@router.put("/api/v1/projects/{project_id}/character-relationships/{rel_id}")
def update_relationship(project_id: str, rel_id: int, data: CharacterRelationshipUpdate, request: Request):
    _check_project(project_id, request)
    updates = data.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="没有提供更新字段")
    updates["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [rel_id, project_id]
    with get_db() as conn:
        cur = conn.execute(
            f"UPDATE character_relationship SET {set_clause} WHERE id=? AND project_id=?",
            values
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="关系记录不存在")
    return {"message": "关系已更新"}


@router.delete("/api/v1/projects/{project_id}/character-relationships/{rel_id}")
def delete_relationship(project_id: str, rel_id: int, request: Request):
    _check_project(project_id, request)
    with get_db() as conn:
        cur = conn.execute(
            "DELETE FROM character_relationship WHERE id=? AND project_id=?",
            (rel_id, project_id)
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="关系记录不存在")
    return {"message": "关系已删除"}


@router.get("/api/v1/projects/{project_id}/character-relationships/graph")
def get_relationship_graph(project_id: str, request: Request):
    """返回适合前端可视化的关系图谱数据 (nodes + edges)"""
    _check_project(project_id, request)
    with get_db() as conn:
        chars = conn.execute(
            "SELECT id, name, status FROM character_profile WHERE project_id=?",
            (project_id,)
        ).fetchall()
        rels = conn.execute(
            """SELECT cr.*, ca.name AS name_a, cb.name AS name_b
               FROM character_relationship cr
               LEFT JOIN character_profile ca ON ca.id = cr.character_id_a
               LEFT JOIN character_profile cb ON cb.id = cr.character_id_b
               WHERE cr.project_id=?""",
            (project_id,)
        ).fetchall()

    nodes = [{"id": c["id"], "name": c["name"], "status": c["status"]} for c in chars]
    edges = []
    for r in rels:
        d = dict(r)
        edges.append({
            "id": d["id"],
            "source": d["character_id_a"],
            "target": d["character_id_b"],
            "sourceName": d.get("name_a", ""),
            "targetName": d.get("name_b", ""),
            "type": d["rel_type"],
            "strength": d["strength"],
            "direction": d["direction"],
            "status": d["status"],
        })
    return {"nodes": nodes, "edges": edges}


@router.get("/api/v1/character-relationship-types")
def get_relationship_types():
    return {"types": REL_TYPES, "statuses": STATUSES}
