import os
import datetime
from backend.app.database import get_db
from utils import read_file
from chapter_directory_parser import parse_chapter_blueprint


def list_chapters(project_id: str) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM chapter WHERE project_id=? ORDER BY chapter_number ASC",
            (project_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_chapter(project_id: str, chapter_number: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM chapter WHERE project_id=? AND chapter_number=?",
            (project_id, chapter_number)
        ).fetchone()
        if not row:
            return None
        return dict(row)


def sync_chapters_from_directory(project_id: str, filepath: str):
    """从 Novel_directory.txt 解析章节元信息并同步到数据库"""
    directory_file = os.path.join(filepath, "Novel_directory.txt")
    if not os.path.exists(directory_file):
        return
    content = read_file(directory_file)
    if not content.strip():
        return
    chapters = parse_chapter_blueprint(content)
    now = datetime.datetime.now().isoformat()
    with get_db() as conn:
        for ch in chapters:
            existing = conn.execute(
                "SELECT id FROM chapter WHERE project_id=? AND chapter_number=?",
                (project_id, ch["chapter_number"])
            ).fetchone()
            if existing:
                conn.execute(
                    """UPDATE chapter SET chapter_title=?, chapter_role=?, chapter_purpose=?,
                       suspense_level=?, foreshadowing=?, plot_twist_level=?, chapter_summary=?, updated_at=?
                       WHERE project_id=? AND chapter_number=?""",
                    (ch.get("chapter_title", ""), ch.get("chapter_role", ""), ch.get("chapter_purpose", ""),
                     ch.get("suspense_level", ""), ch.get("foreshadowing", ""), ch.get("plot_twist_level", ""),
                     ch.get("chapter_summary", ""), now, project_id, ch["chapter_number"])
                )
            else:
                conn.execute(
                    """INSERT INTO chapter (project_id, chapter_number, chapter_title, chapter_role, chapter_purpose,
                       suspense_level, foreshadowing, plot_twist_level, chapter_summary, status, created_at, updated_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (project_id, ch["chapter_number"],
                     ch.get("chapter_title", ""), ch.get("chapter_role", ""), ch.get("chapter_purpose", ""),
                     ch.get("suspense_level", ""), ch.get("foreshadowing", ""), ch.get("plot_twist_level", ""),
                     ch.get("chapter_summary", ""), "pending", now, now)
                )


def get_chapter_content(project_id: str, chapter_number: int, filepath: str) -> str:
    chapter_file = os.path.join(filepath, "chapters", f"chapter_{chapter_number}.txt")
    if os.path.exists(chapter_file):
        return read_file(chapter_file)
    return ""


def update_chapter_content(project_id: str, chapter_number: int, filepath: str, content: str) -> dict | None:
    from utils import save_string_to_txt, clear_file_content, get_word_count
    chapter_file = os.path.join(filepath, "chapters", f"chapter_{chapter_number}.txt")
    os.makedirs(os.path.dirname(chapter_file), exist_ok=True)
    clear_file_content(chapter_file)
    save_string_to_txt(content, chapter_file)
    word_count = get_word_count(content)
    now = datetime.datetime.now().isoformat()
    with get_db() as conn:
        conn.execute(
            "UPDATE chapter SET word_count=?, status='draft', updated_at=? WHERE project_id=? AND chapter_number=?",
            (word_count, now, project_id, chapter_number)
        )
    return get_chapter(project_id, chapter_number)


def mark_chapter_draft(project_id: str, chapter_number: int, word_count: int = 0):
    now = datetime.datetime.now().isoformat()
    with get_db() as conn:
        conn.execute(
            "UPDATE chapter SET status='draft', word_count=?, updated_at=? WHERE project_id=? AND chapter_number=?",
            (word_count, now, project_id, chapter_number)
        )


def mark_chapter_final(project_id: str, chapter_number: int, word_count: int = 0):
    now = datetime.datetime.now().isoformat()
    with get_db() as conn:
        conn.execute(
            "UPDATE chapter SET status='final', word_count=?, updated_at=? WHERE project_id=? AND chapter_number=?",
            (word_count, now, project_id, chapter_number)
        )
