import datetime
import logging
import uuid

from backend.app.database import get_db

logger = logging.getLogger(__name__)

SOURCE_LABELS = {
    "ai_generated": "AI 生成",
    "user_imported": "用户导入",
    "user_edited": "用户编辑",
}


def create_project_file(
    project_id: str,
    type: str,
    title: str,
    filename: str,
    content: str,
    source: str = "ai_generated",
    is_current: bool = False,
) -> dict:
    file_id = uuid.uuid4().hex
    now = datetime.datetime.now().isoformat()
    file_size = len(content.encode("utf-8"))

    if is_current:
        _clear_current_for_type(project_id, type, now)

    with get_db() as conn:
        conn.execute(
            """INSERT INTO project_file (id, project_id, type, title, filename,
               content, source, is_current, file_size, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (file_id, project_id, type, title, filename, content, source,
             1 if is_current else 0, file_size, now, now),
        )
    logger.info("Created project_file %s type=%s project=%s current=%s", file_id, type, project_id, is_current)
    return _get_project_file(file_id)


def _get_project_file(file_id: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM project_file WHERE id=?", (file_id,)).fetchone()
        if not row:
            return None
        return _row_to_dict(row)


def list_project_files(project_id: str, file_type: str | None = None) -> list[dict]:
    with get_db() as conn:
        if file_type:
            rows = conn.execute(
                "SELECT * FROM project_file WHERE project_id=? AND type=? ORDER BY updated_at DESC",
                (project_id, file_type),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM project_file WHERE project_id=? ORDER BY updated_at DESC",
                (project_id,),
            ).fetchall()
        return [_row_to_dict(r) for r in rows]


def get_current_file(project_id: str, file_type: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM project_file WHERE project_id=? AND type=? AND is_current=1 LIMIT 1",
            (project_id, file_type),
        ).fetchone()
        if not row:
            return None
        return _row_to_dict(row)


def set_current_file(file_id: str) -> dict | None:
    record = _get_project_file(file_id)
    if not record:
        return None
    now = datetime.datetime.now().isoformat()
    _clear_current_for_type(record["project_id"], record["type"], now)
    with get_db() as conn:
        conn.execute(
            "UPDATE project_file SET is_current=1, updated_at=? WHERE id=?",
            (now, file_id),
        )
    return _get_project_file(file_id)


def delete_project_file(file_id: str) -> bool:
    record = _get_project_file(file_id)
    if not record:
        return False
    with get_db() as conn:
        conn.execute("DELETE FROM project_file WHERE id=?", (file_id,))
    logger.info("Deleted project_file %s", file_id)
    return True


def _clear_current_for_type(project_id: str, file_type: str, now: str) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE project_file SET is_current=0, updated_at=? WHERE project_id=? AND type=? AND is_current=1",
            (now, project_id, file_type),
        )


def _row_to_dict(row) -> dict:
    d = dict(row)
    d["is_current"] = bool(d.get("is_current", False))
    return d
