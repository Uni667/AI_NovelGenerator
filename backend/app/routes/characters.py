import os
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from backend.app.database import get_db
from backend.app.services import project_service
from backend.app.auth import get_current_user
from backend.app.models.chapter import CharacterProfileCreate, CharacterProfileUpdate

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
                """INSERT INTO character_profile
                   (project_id, name, description, status, source, first_appearance_chapter, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (project_id, name, description[:500], "appeared", "ai", None, now)
            )
            imported.append(name)

    return {"message": f"已导入 {len(imported)} 个角色", "characters": imported}


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

    from backend.app.services.user_service import list_user_llm_configs, get_user_llm_config_raw
    llm_name = pconfig.get("prompt_draft_llm", "") or pconfig.get("architecture_llm", "")
    if llm_name:
        llm_conf = get_user_llm_config_raw(user_id, llm_name)
    else:
        configs = list_user_llm_configs(user_id)
        if not configs:
            raise HTTPException(status_code=400, detail="没有可用的 LLM 配置，请先在设置中添加 LLM")
        llm_conf = get_user_llm_config_raw(user_id, next(iter(configs.keys())))
    if not llm_conf:
        raise HTTPException(status_code=400, detail="没有可用的 LLM 配置，请检查模型名称和 API Key")

    architecture_file = os.path.join(project["filepath"], "Novel_architecture.txt")
    architecture = ""
    if os.path.exists(architecture_file):
        with open(architecture_file, "r", encoding="utf-8") as f:
            architecture = f.read()[:5000]

    from llm_adapters import create_llm_adapter
    llm = create_llm_adapter(
        interface_format=llm_conf.get("interface_format", "OpenAI"),
        base_url=llm_conf.get("base_url", ""),
        model_name=llm_conf.get("model_name", ""),
        api_key=llm_conf.get("api_key", ""),
        temperature=0.8,
        max_tokens=llm_conf.get("max_tokens", 4096),
        timeout=llm_conf.get("timeout", 120),
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
