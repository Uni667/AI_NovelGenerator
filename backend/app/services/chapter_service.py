import os
import datetime
from backend.app.database import get_db
from utils import read_file
from chapter_directory_parser import parse_chapter_blueprint


def list_chapters(project_id: str, user_id: str | None = None) -> list[dict]:
    with get_db() as conn:
        if user_id:
            rows = conn.execute(
                "SELECT * FROM chapter WHERE project_id=? AND user_id=? ORDER BY chapter_number ASC",
                (project_id, user_id)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM chapter WHERE project_id=? ORDER BY chapter_number ASC",
                (project_id,)
            ).fetchall()
        return [dict(r) for r in rows]


def clear_chapter_directory(project_id: str):
    """清空章节目录同步出来的章节元数据，不删除章节正文文件。"""
    with get_db() as conn:
        conn.execute("DELETE FROM chapter WHERE project_id=?", (project_id,))


def get_chapter(project_id: str, chapter_number: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM chapter WHERE project_id=? AND chapter_number=?",
            (project_id, chapter_number)
        ).fetchone()
        if not row:
            return None
        return dict(row)


def sync_chapters_from_directory(project_id: str, filepath: str, user_id: str | None = None):
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
                    """INSERT INTO chapter (user_id, project_id, chapter_number, chapter_title, chapter_role, chapter_purpose,
                       suspense_level, foreshadowing, plot_twist_level, chapter_summary, status, created_at, updated_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (user_id, project_id, ch["chapter_number"],
                     ch.get("chapter_title", ""), ch.get("chapter_role", ""), ch.get("chapter_purpose", ""),
                     ch.get("suspense_level", ""), ch.get("foreshadowing", ""), ch.get("plot_twist_level", ""),
                     ch.get("chapter_summary", ""), "pending", now, now)
                )


def get_chapter_content(project_id: str, chapter_number: int, filepath: str) -> str:
    with get_db() as conn:
        row = conn.execute("SELECT user_id FROM project WHERE id=?", (project_id,)).fetchone()
    user_id = row["user_id"] if row else None
    if user_id:
        from backend.app.services import file_service
        file_service.sync_project_files_to_disk(project_id, filepath, user_id)

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
        row = conn.execute("SELECT user_id FROM project WHERE id=?", (project_id,)).fetchone()
        user_id = row["user_id"] if row else "unknown"
        conn.execute(
            "UPDATE chapter SET word_count=?, status='draft', updated_at=? WHERE project_id=? AND chapter_number=?",
            (word_count, now, project_id, chapter_number)
        )
    from backend.app.services import file_service
    file_service.create_project_file(
        project_id=project_id,
        user_id=user_id,
        type="chapter",
        title=f"第{chapter_number}章",
        filename=f"chapters/chapter_{chapter_number}.txt",
        content=content,
        source="user_edited",
        is_current=True
    )
    return get_chapter(project_id, chapter_number)


def mark_chapter_draft(project_id: str, chapter_number: int, word_count: int = 0):
    now = datetime.datetime.now().isoformat()
    with get_db() as conn:
        row = conn.execute("SELECT filepath, user_id FROM project WHERE id=?", (project_id,)).fetchone()
        if row:
            filepath = row["filepath"]
            user_id = row["user_id"]
            from backend.app.services import file_service
            file_service.sync_project_files_to_disk(project_id, filepath, user_id)
            chapter_file = os.path.join(filepath, "chapters", f"chapter_{chapter_number}.txt")
            if not os.path.exists(chapter_file) or os.path.getsize(chapter_file) == 0:
                raise FileNotFoundError(f"章节物理文件未生成或内容为空，无法标记为草稿: {chapter_file}")
            content = read_file(chapter_file)
            file_service.create_project_file(
                project_id=project_id,
                user_id=user_id,
                type="chapter",
                title=f"第{chapter_number}章",
                filename=f"chapters/chapter_{chapter_number}.txt",
                content=content,
                source="ai_generated",
                is_current=True
            )
        conn.execute(
            "UPDATE chapter SET status='draft', word_count=?, updated_at=? WHERE project_id=? AND chapter_number=?",
            (word_count, now, project_id, chapter_number)
        )


def batch_upsert_from_upload(project_id: str, filepath: str, chapters_data: list[dict], user_id: str | None = None):
    """批量从上传写入章节文件并更新数据库。
    chapters_data: [{"chapter_number": int, "content": str}, ...]
    """
    from utils import save_string_to_txt, clear_file_content, get_word_count
    now = datetime.datetime.now().isoformat()
    chapters_dir = os.path.join(filepath, "chapters")
    os.makedirs(chapters_dir, exist_ok=True)
    results = []

    if not user_id:
        with get_db() as conn:
            row = conn.execute("SELECT user_id FROM project WHERE id=?", (project_id,)).fetchone()
            user_id = row["user_id"] if row else "unknown"

    with get_db() as conn:
        for ch in chapters_data:
            cn = ch["chapter_number"]
            content = ch["content"]
            chapter_file = os.path.join(chapters_dir, f"chapter_{cn}.txt")
            clear_file_content(chapter_file)
            save_string_to_txt(content, chapter_file)
            wc = get_word_count(content)

            existing = conn.execute(
                "SELECT id FROM chapter WHERE project_id=? AND chapter_number=?",
                (project_id, cn)
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE chapter SET word_count=?, status='draft', updated_at=? WHERE project_id=? AND chapter_number=?",
                    (wc, now, project_id, cn)
                )
            else:
                conn.execute(
                    """INSERT INTO chapter (user_id, project_id, chapter_number, status, word_count, created_at, updated_at)
                       VALUES (?,?,?,'draft',?,?,?)""",
                    (user_id, project_id, cn, wc, now, now)
                )
            from backend.app.services import file_service
            file_service.create_project_file(
                project_id=project_id,
                user_id=user_id,
                type="chapter",
                title=f"第{cn}章",
                filename=f"chapters/chapter_{cn}.txt",
                content=content,
                source="user_imported",
                is_current=True
            )
            results.append({"chapter_number": cn, "word_count": wc, "status": "ok"})
    return results


def delete_chapter(project_id: str, chapter_number: int, filepath: str) -> bool:
    """删除章节数据库记录和文件。返回是否成功。"""
    import os as _os
    deleted = False
    chapter_file = _os.path.join(filepath, "chapters", f"chapter_{chapter_number}.txt")
    if _os.path.exists(chapter_file):
        _os.remove(chapter_file)
        deleted = True
    with get_db() as conn:
        conn.execute(
            "DELETE FROM chapter WHERE project_id=? AND chapter_number=?",
            (project_id, chapter_number)
        )
        deleted = deleted or conn.total_changes > 0
    try:
        with get_db() as conn:
            conn.execute(
                "DELETE FROM project_file WHERE project_id=? AND type='chapter' AND filename LIKE ?",
                (project_id, f"%chapter_{chapter_number}.txt")
            )
    except Exception:
        pass
    return deleted


def mark_chapter_final(project_id: str, chapter_number: int, word_count: int = 0):
    now = datetime.datetime.now().isoformat()
    with get_db() as conn:
        row = conn.execute("SELECT filepath, user_id FROM project WHERE id=?", (project_id,)).fetchone()
        if row:
            filepath = row["filepath"]
            user_id = row["user_id"]
            from backend.app.services import file_service
            file_service.sync_project_files_to_disk(project_id, filepath, user_id)
            chapter_file = os.path.join(filepath, "chapters", f"chapter_{chapter_number}.txt")
            if not os.path.exists(chapter_file) or os.path.getsize(chapter_file) == 0:
                raise FileNotFoundError(f"章节物理文件未生成或内容为空，无法标记为定稿: {chapter_file}")
            content = read_file(chapter_file)
            file_service.create_project_file(
                project_id=project_id,
                user_id=user_id,
                type="chapter",
                title=f"第{chapter_number}章",
                filename=f"chapters/chapter_{chapter_number}.txt",
                content=content,
                source="ai_generated",
                is_current=True
            )
        conn.execute(
            "UPDATE chapter SET status='final', word_count=?, updated_at=? WHERE project_id=? AND chapter_number=?",
            (word_count, now, project_id, chapter_number)
        )


def update_chapter_meta(project_id: str, chapter_number: int, data) -> dict | None:
    now = datetime.datetime.now().isoformat()
    fields = []
    params = []
    
    meta_fields = ["chapter_title", "chapter_role", "chapter_purpose", "suspense_level", "foreshadowing", "plot_twist_level", "chapter_summary"]
    for field in meta_fields:
        val = getattr(data, field)
        if val is not None:
            fields.append(f"{field}=?")
            params.append(val)
            
    if not fields:
        return get_chapter(project_id, chapter_number)
        
    params.append(now)
    params.append(project_id)
    params.append(chapter_number)
    
    query = f"UPDATE chapter SET {', '.join(fields)}, updated_at=? WHERE project_id=? AND chapter_number=?"
    
    with get_db() as conn:
        conn.execute(query, tuple(params))
        
    return get_chapter(project_id, chapter_number)


def copy_chapter(project_id: str, chapter_number: int, filepath: str) -> dict | None:
    now = datetime.datetime.now().isoformat()
    with get_db() as conn:
        max_row = conn.execute("SELECT MAX(chapter_number) as max_num FROM chapter WHERE project_id=?", (project_id,)).fetchone()
        next_number = (max_row["max_num"] or 0) + 1
        
        src = conn.execute("SELECT * FROM chapter WHERE project_id=? AND chapter_number=?", (project_id, chapter_number)).fetchone()
        if not src:
            return None
            
        conn.execute(
            """INSERT INTO chapter (user_id, project_id, chapter_number, chapter_title, chapter_role, chapter_purpose,
               suspense_level, foreshadowing, plot_twist_level, chapter_summary, word_count, status, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (src["user_id"], project_id, next_number, f"{src['chapter_title'] or '未命名'} - 副本", src["chapter_role"], src["chapter_purpose"],
             src["suspense_level"], src["foreshadowing"], src["plot_twist_level"], src["chapter_summary"], src["word_count"], "draft", now, now)
        )
        user_id = src["user_id"]
        
    src_file = os.path.join(filepath, "chapters", f"chapter_{chapter_number}.txt")
    dst_file = os.path.join(filepath, "chapters", f"chapter_{next_number}.txt")
    content = ""
    if os.path.exists(src_file):
        with open(src_file, "r", encoding="utf-8") as f:
            content = f.read()
        os.makedirs(os.path.dirname(dst_file), exist_ok=True)
        with open(dst_file, "w", encoding="utf-8") as f:
            f.write(content)
            
    if content:
        from backend.app.services import file_service
        file_service.create_project_file(
            project_id=project_id,
            user_id=user_id,
            type="chapter",
            title=f"第{next_number}章",
            filename=f"chapters/chapter_{next_number}.txt",
            content=content,
            source="user_edited",
            is_current=True
        )
        
    return get_chapter(project_id, next_number)

