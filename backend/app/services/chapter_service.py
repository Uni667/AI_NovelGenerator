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


def update_chapter_content(project_id: str, chapter_number: int, filepath: str, content: str, status: str | None = None) -> dict | None:
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
        
        if status is not None:
            new_status = status
        else:
            existing = conn.execute("SELECT status FROM chapter WHERE project_id=? AND chapter_number=?", (project_id, chapter_number)).fetchone()
            new_status = existing["status"] if (existing and existing["status"] == "final") else "draft"

        conn.execute(
            "UPDATE chapter SET word_count=?, status=?, updated_at=? WHERE project_id=? AND chapter_number=?",
            (word_count, new_status, now, project_id, chapter_number)
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
    
    meta_fields = [
        "chapter_title", "chapter_role", "chapter_purpose", 
        "suspense_level", "foreshadowing", "plot_twist_level", 
        "chapter_summary", "target_emotion"
    ]
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


def serialize_chapter_blueprint(chapters: list[dict]) -> str:
    lines = []
    for ch in chapters:
        lines.append(f"第{ch['chapter_number']}章 - {ch.get('chapter_title') or '未命名'}")
        lines.append(f"本章定位：{ch.get('chapter_role') or ''}")
        lines.append(f"核心作用：{ch.get('chapter_purpose') or ''}")
        lines.append(f"悬念密度：{ch.get('suspense_level') or ''}")
        lines.append(f"伏笔操作：{ch.get('foreshadowing') or ''}")
        lines.append(f"认知颠覆：{ch.get('plot_twist_level') or ''}")
        lines.append(f"本章简述：{ch.get('chapter_summary') or ''}")
        lines.append("")
    return "\n".join(lines).strip()


def sync_subsequent_chapters(project_id: str, chapter_number: int, user_id: str) -> list[dict]:
    """
    Deprecated/high-risk:
    This method rewrites the full Novel_directory.txt using LLM output.
    It should not be triggered automatically.
    Future implementation should use outline_state.json and JSON Patch to update only unlocked future chapters.
    """
    import os
    import datetime
    from backend.app.database import get_db
    from backend.app.services import project_service, file_service
    from backend.app.services.model_runtime import create_chat_adapter_from_config as create_llm_adapter
    from novel_generator.common import invoke_with_cleaning
    from chapter_directory_parser import parse_chapter_blueprint
    
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise ValueError("项目不存在")
        
    pconfig = project_service.get_project_config(project_id)
    if not pconfig:
        raise ValueError("项目配置不存在")
        
    # Get all chapters
    all_chapters = list_chapters(project_id, user_id)
    subsequent_ch = [ch for ch in all_chapters if ch["chapter_number"] > chapter_number]
    
    if not subsequent_ch:
        return all_chapters # No chapters to sync
        
    # 1. Build prompt context
    filepath = project["filepath"]
    arch_file = os.path.join(filepath, "Novel_architecture.txt")
    architecture_text = read_file(arch_file).strip() if os.path.exists(arch_file) else "无"
    
    preceding_text = ""
    for ch in all_chapters:
        if ch["chapter_number"] < chapter_number:
            preceding_text += f"第{ch['chapter_number']}章 - {ch['chapter_title'] or '未命名'}\n本章简述：{ch['chapter_summary'] or '无'}\n\n"
        elif ch["chapter_number"] == chapter_number:
            preceding_text += f"第{ch['chapter_number']}章 - {ch['chapter_title'] or '未命名'}\n本章简述：{ch['chapter_summary'] or '无'}\n"
            # Read actual content
            ch_file = os.path.join(filepath, "chapters", f"chapter_{chapter_number}.txt")
            if os.path.exists(ch_file):
                content_snippet = read_file(ch_file)[:2000]
                preceding_text += f"实际正文（截取前2000字）：\n{content_snippet}\n\n"
                
    subsequent_text = ""
    for ch in subsequent_ch:
        subsequent_text += f"第{ch['chapter_number']}章 - {ch['chapter_title'] or '未命名'}\n"
        subsequent_text += f"本章定位：{ch['chapter_role'] or '无'}\n"
        subsequent_text += f"核心作用：{ch['chapter_purpose'] or '无'}\n"
        subsequent_text += f"悬念密度：{ch['suspense_level'] or '无'}\n"
        subsequent_text += f"伏笔操作：{ch['foreshadowing'] or '无'}\n"
        subsequent_text += f"认知颠覆：{ch['plot_twist_level'] or '无'}\n"
        subsequent_text += f"本章简述：{ch['chapter_summary'] or '无'}\n\n"

    # Load runtime profile for LLM using builder context (fallback to general)
    try:
        from backend.app.services.generation_context_builder import build_full_context
        # Create dummy cancel token
        from novel_generator.cancel_token import CancelToken
        ctx, _, rt = build_full_context(user_id, project, pconfig, "blueprint_polish", CancelToken())
        llm = create_llm_adapter(
            interface_format=ctx.llm.interface_format,
            base_url=ctx.llm.base_url,
            model_name=ctx.llm.model_name,
            api_key=ctx.llm.api_key,
            temperature=ctx.llm.temperature,
            max_tokens=ctx.llm.max_tokens,
            timeout=ctx.llm.timeout,
            cancel_token=ctx.cancel_token,
        )
    except Exception:
        # Fallback to direct resolution
        raise RuntimeError("无法加载模型配置以连接大模型。")
        
    prompt = f"""你是一名资深的网络小说策划总编辑。
因为前面的章节（第{chapter_number}章）已经完成了定稿和修改，你需要同步调整后续所有章节的大纲设计，以确保整个故事的发展逻辑、伏笔连贯性及节奏的一致性。

【小说整体架构】
{architecture_text}

【前面已完成章节（包含最新定稿的第{chapter_number}章）】
{preceding_text}

【原本规划的后续章节大纲（从第{chapter_number+1}章开始）】
{subsequent_text}

请结合第{chapter_number}章的新变化，重新规划并优化后续章节的大纲。
要求：
1. 确保情节过渡、角色动机、伏笔以及节奏与前面的内容完全契合，无逻辑硬伤。
2. 必须保留原有的后续章节列表，章节号递增顺序不能遗漏或打乱。
3. 必须输出每一章的完整字段（本章定位、核心作用、悬念密度、伏笔操作、认知颠覆、本章简述）。
4. 输出的文本必须可以直接由系统解析。请严格按照如下示例格式输出：

第n章 - [标题]
本章定位：[角色/事件/主题]
核心作用：[推进/转折/揭示]
悬念密度：[紧凑/渐进/爆发]
伏笔操作：[描述具体的埋设、强化或回收操作]
认知颠覆：[★☆☆☆☆]
本章简述：[具体发生的事件及核心刺激点]

请直接给出重新设计后的后续章节大纲，不需要任何前导语、问候语或后续解释。
"""

    result_text = invoke_with_cleaning(llm, prompt)
    if not result_text.strip():
        raise RuntimeError("大模型返回了空的大纲内容")
        
    parsed = parse_chapter_blueprint(result_text)
    if not parsed:
        raise RuntimeError("大模型返回的内容无法被系统解析，请重试")
        
    # Update SQLite database
    now = datetime.datetime.now().isoformat()
    with get_db() as conn:
        for ch in parsed:
            # Only update if it is a subsequent chapter number
            cn = ch["chapter_number"]
            if cn > chapter_number:
                conn.execute(
                    """UPDATE chapter 
                       SET chapter_title=?, chapter_role=?, chapter_purpose=?, suspense_level=?,
                           foreshadowing=?, plot_twist_level=?, chapter_summary=?, updated_at=?
                       WHERE project_id=? AND chapter_number=?""",
                    (ch.get("chapter_title", ""), ch.get("chapter_role", ""), ch.get("chapter_purpose", ""),
                     ch.get("suspense_level", ""), ch.get("foreshadowing", ""), ch.get("plot_twist_level", ""),
                     ch.get("chapter_summary", ""), now, project_id, cn)
                )

    # Rebuild Novel_directory.txt
    updated_all = list_chapters(project_id, user_id)
    blueprint_content = serialize_chapter_blueprint(updated_all)
    dir_file = os.path.join(filepath, "Novel_directory.txt")
    if os.path.exists(dir_file):
        os.remove(dir_file)
    with open(dir_file, "w", encoding="utf-8") as f:
        f.write(blueprint_content)
        
    # Update project file history in DB
    file_service.create_project_file(
        project_id=project_id,
        user_id=user_id,
        type="outline",
        title="同步后章节目录",
        filename="Novel_directory.txt",
        content=blueprint_content,
        source="ai_generated",
        is_current=True
    )
    
    return updated_all

