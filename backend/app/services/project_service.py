import os
import uuid
import datetime
from backend.app.database import get_db

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_PROJECTS_DIR = os.path.join(ROOT_DIR, "projects")


def create_project(data: dict, user_id: str) -> dict:
    project_id = str(uuid.uuid4())
    now = datetime.datetime.now().isoformat()
    filepath = os.path.join(DEFAULT_PROJECTS_DIR, project_id)
    os.makedirs(filepath, exist_ok=True)
    os.makedirs(os.path.join(filepath, "chapters"), exist_ok=True)
    os.makedirs(os.path.join(filepath, "knowledge"), exist_ok=True)

    with get_db() as conn:
        conn.execute(
            "INSERT INTO project (id, user_id, name, description, filepath, status, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)",
            (project_id, user_id, data.get("name", ""), data.get("description", ""), filepath, "draft", now, now)
        )
        conn.execute(
            "INSERT INTO project_config (project_id, topic, genre, num_chapters, word_number, user_guidance, language, platform, category) VALUES (?,?,?,?,?,?,?,?,?)",
            (project_id,
             data.get("topic", ""),
             data.get("genre", ""),
             data.get("num_chapters", 0),
             data.get("word_number", 3000),
             data.get("user_guidance", ""),
             data.get("language", "zh"),
             data.get("platform", "tomato"),
             data.get("category", ""))
        )

    return get_project(project_id, user_id)


def get_project(project_id: str, user_id: str = "") -> dict | None:
    with get_db() as conn:
        if user_id:
            row = conn.execute("SELECT * FROM project WHERE id = ? AND user_id = ?", (project_id, user_id)).fetchone()
        else:
            row = conn.execute("SELECT * FROM project WHERE id = ?", (project_id,)).fetchone()
        if not row:
            return None
        return dict(row)


def list_projects(user_id: str) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM project WHERE user_id = ? ORDER BY updated_at DESC", (user_id,)).fetchall()
        return [dict(r) for r in rows]


def update_project(project_id: str, data: dict, user_id: str) -> dict | None:
    project = get_project(project_id, user_id)
    if not project:
        return None
    now = datetime.datetime.now().isoformat()
    sets = []
    params = []
    for field in ["name", "description", "status"]:
        if field in data and data[field] is not None:
            sets.append(f"{field}=?")
            params.append(data[field])
    if not sets:
        return project
    sets.append("updated_at=?")
    params.append(now)
    params.extend([project_id, user_id])
    with get_db() as conn:
        conn.execute(f"UPDATE project SET {', '.join(sets)} WHERE id = ? AND user_id = ?", params)
    return get_project(project_id, user_id)


def delete_project(project_id: str, user_id: str) -> bool:
    import shutil
    project = get_project(project_id, user_id)
    if not project:
        return False
    filepath = project.get("filepath", "")
    with get_db() as conn:
        conn.execute("DELETE FROM project WHERE id = ? AND user_id = ?", (project_id, user_id))
    if filepath and os.path.exists(filepath):
        try:
            shutil.rmtree(filepath)
        except Exception:
            pass
    return True


def get_project_config(project_id: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM project_config WHERE project_id = ?", (project_id,)).fetchone()
        if not row:
            return None
        return dict(row)


def update_project_config(project_id: str, data: dict) -> dict:
    config = get_project_config(project_id)
    if not config:
        raise ValueError(f"项目配置不存在: {project_id}")
    allowed_fields = ["topic", "genre", "num_chapters", "word_number", "user_guidance",
                      "language", "platform", "category",
                      "architecture_llm", "chapter_outline_llm", "prompt_draft_llm",
                      "final_chapter_llm", "consistency_review_llm", "embedding_config"]
    sets = []
    params = []
    for field in allowed_fields:
        if field in data and data[field] is not None:
            sets.append(f"{field}=?")
            params.append(data[field])
    if not sets:
        return config
    params.append(project_id)
    with get_db() as conn:
        conn.execute(f"UPDATE project_config SET {', '.join(sets)} WHERE project_id = ?", params)
    return get_project_config(project_id)
