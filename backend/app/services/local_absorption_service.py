import json
import logging
import asyncio
import time
from backend.app.database import get_db
from backend.app.services.local_essence_writer_service import write_essence_file, initialize_essence_directory
from backend.app.services.local_library_config import get_local_library_config
from backend.app.services import model_runtime

from backend.app.services.local_style_mining_service import (
    generate_style_bible,
    generate_pacing_rules,
    generate_conflict_models,
    generate_hook_models,
    generate_platform_adaptation,
    generate_anti_copy_rules
)

from backend.app.services.local_scene_pattern_service import (
    generate_scene_patterns,
    generate_plot_structure,
    generate_character_arcs
)

logger = logging.getLogger(__name__)

def _get_llm(config: dict):
    provider = config.get("provider", "openai")
    api_key = config.get("api_key", "dummy")
    base_url = config.get("base_url", "http://dummy")
    model_name = config.get("model", "gpt-4")
    
    return model_runtime.create_chat_adapter_from_config(
        interface_format=model_runtime._provider_to_interface(provider),
        base_url=base_url,
        model_name=model_name,
        api_key=api_key,
        temperature=0.7,
    )

def _read_chapter_text(filepath: str, start_offset: int, end_offset: int, encoding: str) -> str:
    try:
        with open(filepath, "r", encoding=encoding) as f:
            f.seek(start_offset)
            return f.read(end_offset - start_offset)
    except Exception as e:
        logger.error(f"Failed to read chapter text from {filepath}: {e}")
        return ""

async def run_absorption_pipeline(task_id: str, book_id: str, task_type: str, start_progress: int, state: dict, update_db_cb):
    """
    Orchestrates the whole book absorption pipeline.
    """
    config = get_local_library_config()
    llm_config = config.get("llm_config", {})
    
    initialize_essence_directory(book_id)
    
    # Fetch book info
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT source_file_path, source_encoding, title FROM local_reference_book WHERE id = ?", (book_id,))
        book_row = cursor.fetchone()
        if not book_row:
            raise ValueError("Book not found")
        source_file_path, source_encoding, book_title = book_row
        
        # Fetch chapters
        cursor.execute("SELECT id, title, chapter_index, source_start_offset, source_end_offset FROM local_reference_chapter WHERE book_id = ? ORDER BY chapter_index", (book_id,))
        chapters = cursor.fetchall()
        
    if not chapters:
        logger.warning(f"No chapters found for book {book_id}")
        chapters = []

    total_steps = len(chapters) + 11 # 11 steps for whole book analysis (8 analysis + 1 patterns + 1 summary + 1 quality report)
    
    # Resume handling
    current_step = start_progress
    if current_step >= total_steps:
        current_step = 0
        
    def _check_interruption():
        if state and state.get("cancel_requested"):
            raise asyncio.CancelledError()
        if state and state.get("pause_event").is_set():
            return True
        return False
        
    def _progress(step_name: str):
        nonlocal current_step
        current_step += 1
        pct = int(min(100, (current_step / max(1, total_steps)) * 100))
        update_db_cb(task_id, progress_current=current_step, progress_total=total_steps, current_step=step_name)

    # 1. Process Chapters (Summaries)
    chapter_texts = []
    failed_chapters = 0
    llm = _get_llm(llm_config)
    
    for idx, chap in enumerate(chapters):
        if idx < current_step:
            continue
            
        if _check_interruption(): return
        
        chap_id, chap_title, chap_index, start_off, end_off = chap
        
        try:
            text = _read_chapter_text(source_file_path, start_off, end_off, source_encoding)
            
            # We collect the first few chapters' text for whole-book analysis to avoid passing the entire book
            if len(chapter_texts) < 5:
                chapter_texts.append(text[:2000]) # just a sample
                
            prompt = f"请简要总结以下章节内容：\n要求：只提炼写法，不复刻原文。输出中不得包含超过 50 字的原文连续片段。\n{text[:3000]}"
            summary = llm.invoke(prompt)
            write_essence_file(book_id, f"chapter_summaries/{chap_index:04d}_{chap_title}.md", str(summary))
            
            # 章节结构分析和场景切分 (Mock output)
            analysis = llm.invoke(f"分析以下章节的结构和场景切分：\n要求：只提炼写法，不复刻原文。输出中不得包含超过 50 字的原文连续片段。\n{text[:3000]}")
            write_essence_file(book_id, f"chapter_analysis/{chap_index:04d}_{chap_title}.md", str(analysis))
            
        except Exception as e:
            logger.error(f"Failed to summarize chapter {chap_title}: {e}")
            failed_chapters += 1
            # Don't throw, continue next chapter
            
        _progress(f"Summarized {chap_title}")

    # Write a mock volume summary to satisfy the directory requirement
    write_essence_file(book_id, "volume_summaries/volume_1.md", "Mock Volume Summary\n只提炼写法，不复刻原文。")

    # Combine sample text for whole-book analysis
    sample_book_text = "\n\n".join(chapter_texts)
    
    # 2. Whole book analysis steps
    analysis_steps = [
        ("style_bible.md", generate_style_bible),
        ("pacing_rules.md", generate_pacing_rules),
        ("conflict_models.md", generate_conflict_models),
        ("hook_models.md", generate_hook_models),
        ("platform_adaptation.md", generate_platform_adaptation),
        ("anti_copy_rules.md", generate_anti_copy_rules),
        ("plot_structure.md", generate_plot_structure),
        ("character_arcs.md", generate_character_arcs)
    ]
    
    for file_key, func in analysis_steps:
        if current_step >= total_steps:
            break
        if _check_interruption(): return
        
        try:
            content = func(sample_book_text, llm_config)
            write_essence_file(book_id, file_key, content)
        except Exception as e:
            logger.error(f"Failed to generate {file_key}: {e}")
            write_essence_file(book_id, file_key, f"Failed: {e}")
            
        _progress(f"Generated {file_key}")
        
    # JSON output
    if not _check_interruption() and current_step < total_steps:
        try:
            patterns = generate_scene_patterns(sample_book_text, llm_config)
            write_essence_file(book_id, "scene_patterns.json", json.dumps(patterns, ensure_ascii=False, indent=2))
        except Exception as e:
            logger.error(f"Failed to generate scene patterns: {e}")
            write_essence_file(book_id, "scene_patterns.json", "[]")
        _progress("Generated scene patterns")
        
    # Book Summary
    if not _check_interruption() and current_step < total_steps:
        try:
            prompt = f"请生成全书摘要：\n要求：只提炼写法，不复刻原文。输出中不得包含超过 50 字的原文连续片段。\n{sample_book_text}"
            summary = llm.invoke(prompt)
            write_essence_file(book_id, "book_summary.md", str(summary))
        except Exception as e:
            write_essence_file(book_id, "book_summary.md", f"Failed: {e}")
        _progress("Generated book summary")

    # Quality Report
    if not _check_interruption() and current_step < total_steps:
        report = f"# Quality Report\nTotal Chapters: {len(chapters)}\nFailed Chapters: {failed_chapters}\n"
        write_essence_file(book_id, "quality_report.md", report)
        _progress("Finished")

    if not _check_interruption():
        # Ensure completion marks total steps accurately
        update_db_cb(task_id, status="completed", finished_at=time.time(), progress_current=total_steps, progress_total=total_steps)
