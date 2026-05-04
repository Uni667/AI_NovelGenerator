import os
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from backend.app.database import get_db
from backend.app.services import project_service
from backend.app.auth import get_current_user
from backend.app.models.chapter import (
    CharacterImportSelection,
    CharacterProfileCreate,
    CharacterProfileUpdate,
    CharacterProfileResponse,
)
from novel_generator.character_import import (
    build_character_import_preview,
    merge_character_description,
    normalize_character_name,
    preferred_character_status,
)

router = APIRouter(tags=["角色管理"])


CHARACTER_SUGGESTION_PROMPT = """你是网文小说人物策划编辑。请根据项目设定和已有人物，补全适合后续剧情的人物建议。

## 项目设定
- 主题：{topic}
- 类型：{genre}
- 分类：{category}
- 平台：{platform}
- 章节数：{num_chapters}
- 用户指导：{user_guidance}

## 小说架构
{architecture}

## 已有人物
{existing_characters}

## 输出要求
生成 5 个可用于后续剧情的人物，避免和已有人物重名。人物要服务主线冲突、爽点或反转。
只输出 JSON 数组，不要 Markdown，不要解释：
[
  {{
    "name": "人物名",
    "description": "人物定位、和主角关系、潜在冲突或爽点，80字以内",
    "first_appearance_chapter": 预计首次登场章节数字
  }}
]"""


def _check_project(project_id: str, request: Request) -> dict:
    user_id = get_current_user(request)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


def _load_existing_characters(project_id: str) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM character_profile WHERE project_id = ? ORDER BY updated_at DESC",
            (project_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def _load_character_state_text(project: dict) -> str:
    state_file = os.path.join(project["filepath"], "character_state.txt")
    if not os.path.exists(state_file):
        raise HTTPException(status_code=404, detail="character_state.txt 不存在，请先生成架构")
    with open(state_file, "r", encoding="utf-8") as file:
        return file.read()


def _upsert_character_from_candidate(
    conn,
    project_id: str,
    candidate: dict,
    now: str,
) -> dict:
    candidate_name = candidate.get("name", "").strip()
    normalized_name = normalize_character_name(candidate_name)
    rows = conn.execute(
        "SELECT * FROM character_profile WHERE project_id = ?",
        (project_id,),
    ).fetchall()
    existing_row = None
    for row in rows:
        if normalize_character_name(row["name"]) == normalized_name:
            existing_row = dict(row)
            break

    description = candidate.get("description", "").strip() or candidate.get("raw_text", "").strip()
    if existing_row:
        merged_description = merge_character_description(existing_row.get("description", ""), description)
        merged_status = preferred_character_status(existing_row.get("status", ""), candidate.get("status", "planned"))
        first_appearance = existing_row.get("first_appearance_chapter")
        candidate_chapter = candidate.get("first_appearance_chapter")
        if candidate_chapter and (not first_appearance or candidate_chapter < first_appearance):
            first_appearance = candidate_chapter
        merged_source = existing_row.get("source") or candidate.get("source", "ai")
        conn.execute(
            """UPDATE character_profile
               SET description = ?, status = ?, source = ?, first_appearance_chapter = ?, updated_at = ?
               WHERE id = ? AND project_id = ?""",
            (
                merged_description[:1000],
                merged_status,
                merged_source,
                first_appearance,
                now,
                existing_row["id"],
                project_id,
            ),
        )
        return {
            "id": existing_row["id"],
            "name": existing_row["name"],
            "description": merged_description[:1000],
            "status": merged_status,
            "source": merged_source,
            "first_appearance_chapter": first_appearance,
            "updated_at": now,
            "merged": True,
        }

    cursor = conn.execute(
        """INSERT INTO character_profile
           (project_id, name, description, status, source, first_appearance_chapter, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            project_id,
            candidate_name,
            description[:1000],
            candidate.get("status", "planned"),
            candidate.get("source", "ai"),
            candidate.get("first_appearance_chapter"),
            now,
        ),
    )
    return {
        "id": cursor.lastrowid,
        "name": candidate_name,
        "description": description[:1000],
        "status": candidate.get("status", "planned"),
        "source": candidate.get("source", "ai"),
        "first_appearance_chapter": candidate.get("first_appearance_chapter"),
        "updated_at": now,
        "merged": False,
    }


@router.get("/api/v1/projects/{project_id}/characters")
def list_characters(project_id: str, request: Request):
    _check_project(project_id, request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT * FROM character_profile
               WHERE project_id = ?
               ORDER BY
                 CASE status WHEN 'appeared' THEN 0 WHEN 'planned' THEN 1 WHEN 'suggested' THEN 2 ELSE 3 END,
                 COALESCE(first_appearance_chapter, 999999),
                 updated_at DESC""",
            (project_id,)
        ).fetchall()
        return [dict(r) for r in rows]


@router.post("/api/v1/projects/{project_id}/characters")
def create_character(project_id: str, data: CharacterProfileCreate, request: Request):
    _check_project(project_id, request)
    now = datetime.now().isoformat()
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO character_profile
               (project_id, name, description, status, source, first_appearance_chapter, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (project_id, data.name, data.description, data.status, data.source, data.first_appearance_chapter, now)
        )
        return {
            "id": cursor.lastrowid,
            "name": data.name,
            "description": data.description,
            "status": data.status,
            "source": data.source,
            "first_appearance_chapter": data.first_appearance_chapter,
            "updated_at": now,
        }


@router.put("/api/v1/projects/{project_id}/characters/{character_id}")
def update_character(project_id: str, character_id: int, data: CharacterProfileUpdate, request: Request):
    _check_project(project_id, request)
    updates = data.model_dump(exclude_unset=True)
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


@router.post("/api/v1/projects/{project_id}/characters/import-from-state/preview")
def preview_characters_from_state(project_id: str, request: Request):
    project = _check_project(project_id, request)
    content = _load_character_state_text(project)
    existing = _load_existing_characters(project_id)
    candidates = build_character_import_preview(content, existing)
    summary = {
        "total": len(candidates),
        "keep": sum(1 for item in candidates if item.decision == "keep"),
        "review": sum(1 for item in candidates if item.decision == "review"),
        "reject": sum(1 for item in candidates if item.decision == "reject"),
        "duplicates": sum(1 for item in candidates if item.existing_character_id),
    }
    return {
        "summary": summary,
        "candidates": [candidate.to_dict() for candidate in candidates],
    }


@router.post("/api/v1/projects/{project_id}/characters/import-from-state")
def import_characters_from_state(
    project_id: str,
    request: Request,
    data: CharacterImportSelection | None = None,
):
    """从 character_state.txt 解析角色，支持预览后的定向导入。"""
    project = _check_project(project_id, request)
    content = _load_character_state_text(project)
    existing = _load_existing_characters(project_id)
    candidates = build_character_import_preview(content, existing)
    candidate_map = {candidate.candidate_id: candidate for candidate in candidates}

    if data and data.selected_candidate_ids:
        selected_ids = {candidate_id for candidate_id in data.selected_candidate_ids if candidate_id in candidate_map}
    else:
        selected_ids = {candidate.candidate_id for candidate in candidates if candidate.decision == "keep"}

    if not selected_ids:
        return {
            "message": "没有可导入的角色候选",
            "characters": [],
            "summary": {
                "total": len(candidates),
                "selected": 0,
                "imported": 0,
                "merged": 0,
            },
        }

    now = datetime.now().isoformat()
    imported: list[dict] = []
    skipped: list[dict] = []
    with get_db() as conn:
        for candidate in candidates:
            if candidate.candidate_id not in selected_ids:
                skipped.append(
                    {
                        "candidate_id": candidate.candidate_id,
                        "name": candidate.name,
                        "decision": candidate.decision,
                        "reason": "未勾选",
                    }
                )
                continue

            result = _upsert_character_from_candidate(conn, project_id, candidate.to_dict(), now)
            imported.append(result)

    merged_count = sum(1 for item in imported if item.get("merged"))
    return {
        "message": f"已导入/更新 {len(imported)} 个角色",
        "characters": imported,
        "skipped": skipped,
        "summary": {
            "total": len(candidates),
            "selected": len(selected_ids),
            "imported": len(imported) - merged_count,
            "merged": merged_count,
        },
    }


@router.post("/api/v1/projects/{project_id}/characters/suggest")
def suggest_characters(project_id: str, request: Request):
    """让 AI 根据当前设定给出后续人物建议，但不直接写入数据库。"""
    user_id = get_current_user(request)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    pconfig = project_service.get_project_config(project_id)
    if not pconfig:
        raise HTTPException(status_code=404, detail="项目配置不存在")

    with get_db() as conn:
        rows = conn.execute(
            "SELECT name, description, status, first_appearance_chapter FROM character_profile WHERE project_id = ?",
            (project_id,)
        ).fetchall()
        existing = [dict(r) for r in rows]

    from backend.app.services.model_runtime import get_runtime_config, ConfigError

    try:
        runtime_cfg = get_runtime_config(user_id, "character", project_id)
    except ConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))

    architecture_file = os.path.join(project["filepath"], "Novel_architecture.txt")
    architecture = ""
    if os.path.exists(architecture_file):
        with open(architecture_file, "r", encoding="utf-8") as f:
            architecture = f.read()[:5000]

    from llm_adapters import create_llm_adapter

    # Map provider to interface format (same mapping as model_runtime._provider_to_interface)
    _provider_iface_map = {
        "openai": "OpenAI", "deepseek": "OpenAI", "qwen": "OpenAI",
        "anthropic": "OpenAI", "custom": "OpenAI", "local": "Ollama",
    }
    interface_format = _provider_iface_map.get(runtime_cfg.provider, "OpenAI")

    llm = create_llm_adapter(
        interface_format=interface_format,
        base_url=runtime_cfg.base_url,
        model_name=runtime_cfg.model,
        api_key=runtime_cfg.api_key,
        temperature=runtime_cfg.temperature,
        max_tokens=runtime_cfg.max_tokens,
        timeout=600,
    )

    prompt = CHARACTER_SUGGESTION_PROMPT.format(
        topic=pconfig.get("topic", ""),
        genre=pconfig.get("genre", ""),
        category=pconfig.get("category", ""),
        platform=pconfig.get("platform", ""),
        num_chapters=pconfig.get("num_chapters", 0),
        user_guidance=pconfig.get("user_guidance", ""),
        architecture=architecture or "暂无架构文件",
        existing_characters=json.dumps(existing, ensure_ascii=False),
    )

    try:
        result = llm.invoke(prompt)
        json_start = result.find("[")
        json_end = result.rfind("]") + 1
        if json_start == -1 or json_end <= json_start:
            raise ValueError("AI 返回内容不是 JSON 数组")
        raw_items = json.loads(result[json_start:json_end])
        suggestions = []
        existing_names = {item.get("name") for item in existing}
        for item in raw_items:
            name = str(item.get("name", "")).strip()
            if not name or name in existing_names:
                continue
            suggestions.append({
                "name": name[:30],
                "description": str(item.get("description", "")).strip()[:500],
                "status": "suggested",
                "source": "ai",
                "first_appearance_chapter": item.get("first_appearance_chapter"),
            })
        return {"characters": suggestions[:8]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"人物建议生成失败: {str(e)}")


# ── 角色库全景视图 ──

@router.get("/api/v1/projects/{project_id}/characters/dashboard")
def character_dashboard(project_id: str, request: Request):
    """角色库统一入口：返回角色 + 关系 + 冲突 + 登场时间线的完整快照"""
    _check_project(project_id, request)
    with get_db() as conn:
        characters = [
            dict(r) for r in conn.execute(
                """SELECT * FROM character_profile WHERE project_id=?
                   ORDER BY COALESCE(first_appearance_chapter, 999999), updated_at DESC""",
                (project_id,)
            ).fetchall()
        ]

        relationships = [
            dict(r) for r in conn.execute(
                """SELECT cr.*, ca.name AS name_a, cb.name AS name_b
                   FROM character_relationship cr
                   LEFT JOIN character_profile ca ON ca.id=cr.character_id_a
                   LEFT JOIN character_profile cb ON cb.id=cr.character_id_b
                   WHERE cr.project_id=?
                   ORDER BY cr.strength DESC""",
                (project_id,)
            ).fetchall()
        ]

        conflicts = [
            dict(r) for r in conn.execute(
                "SELECT * FROM character_conflict WHERE project_id=? ORDER BY intensity DESC",
                (project_id,)
            ).fetchall()
        ]
        for c in conflicts:
            c["participants"] = [
                dict(p) for p in conn.execute(
                    """SELECT cp.*, ch.name, ch.status AS char_status
                       FROM character_conflict_participant cp
                       JOIN character_profile ch ON ch.id=cp.character_id
                       WHERE cp.conflict_id=?""",
                    (c["id"],)
                ).fetchall()
            ]

        appearances = [
            dict(r) for r in conn.execute(
                """SELECT ca.*, ch.name AS character_name, ch.status AS character_status
                   FROM character_appearance ca
                   JOIN character_profile ch ON ch.id=ca.character_id
                   WHERE ca.project_id=?
                   ORDER BY ca.chapter_number""",
                (project_id,)
            ).fetchall()
        ]

        # timeline aggregation
        chapters_map: dict[int, list] = {}
        for a in appearances:
            ch_num = a["chapter_number"]
            chapters_map.setdefault(ch_num, []).append(dict(a))
        timeline = [
            {
                "chapter_number": ch,
                "character_count": len(entries),
                "entries": entries,
            }
            for ch, entries in sorted(chapters_map.items())
        ]

    return {
        "characters": characters,
        "relationships": relationships,
        "conflicts": conflicts,
        "appearances": appearances,
        "timeline": timeline,
        "summary": {
            "total_characters": len(characters),
            "appeared": sum(1 for c in characters if c.get("status") == "appeared"),
            "planned": sum(1 for c in characters if c.get("status") == "planned"),
            "suggested": sum(1 for c in characters if c.get("status") == "suggested"),
            "total_relationships": len(relationships),
            "active_relationships": sum(1 for r in relationships if r.get("status") == "active"),
            "total_conflicts": len(conflicts),
            "active_conflicts": sum(1 for c in conflicts if c.get("status") in ("active", "escalating", "brewing")),
            "total_appearances": len(appearances),
            "chapters_with_data": len(timeline),
        },
    }
