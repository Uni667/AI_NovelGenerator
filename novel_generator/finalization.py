# -*- coding: utf-8 -*-
"""
定稿章节和扩写章节（finalize_chapter、enrich_chapter_text）

重构要点：
- 接受 GenerationContext 替代散落参数
"""
import os
import logging
from llm_adapters import create_llm_adapter
from embedding_adapters import create_embedding_adapter
import prompt_definitions
from novel_generator.common import invoke_with_cleaning
from novel_generator.task_manager import raise_if_cancelled
from utils import read_file, clear_file_content, save_string_to_txt
from novel_generator.vectorstore_utils import update_vector_store

logger = logging.getLogger(__name__)


def finalize_chapter(
    ctx,             # GenerationContext
    params,          # ChapterParams (使用 chapter_number 和 word_number)
    emitter=None,
    task_id: str | None = None,
):
    """
    对指定章节做最终处理：更新前文摘要、更新角色状态、插入向量库等。
    """
    def _emit(event_type: str, data: dict):
        if emitter and hasattr(emitter, "emit"):
            emitter.emit(event_type, data)

    def _check_cancel():
        if task_id:
            raise_if_cancelled(task_id)
        return False

    filepath = ctx.filepath
    novel_number = params.chapter_number

    chapters_dir = os.path.join(filepath, "chapters")
    chapter_file = os.path.join(chapters_dir, f"chapter_{novel_number}.txt")
    chapter_text = read_file(chapter_file).strip()
    if not chapter_text:
        logger.warning(f"Chapter {novel_number} is empty, cannot finalize.")
        return
    _check_cancel()

    global_summary_file = os.path.join(filepath, "global_summary.txt")
    old_global_summary = read_file(global_summary_file)
    character_state_file = os.path.join(filepath, "character_state.txt")
    old_character_state = read_file(character_state_file)
    plot_arcs_file = os.path.join(filepath, "plot_arcs.txt")
    old_plot_arcs = read_file(plot_arcs_file)

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

    _emit("progress", {"step": "summary_update", "status": "running", "message": "正在更新全局摘要..."})
    prompt_summary = prompt_definitions.summary_prompt.format(
        chapter_text=chapter_text, global_summary=old_global_summary
    )
    new_global_summary = invoke_with_cleaning(llm, prompt_summary, cancel_check=_check_cancel)
    if not new_global_summary.strip():
        new_global_summary = old_global_summary
    _emit("progress", {"step": "summary_update", "status": "done", "message": "全局摘要已更新"})

    _check_cancel()
    _emit("progress", {"step": "character_state_update", "status": "running", "message": "正在更新角色状态..."})
    prompt_char_state = prompt_definitions.update_character_state_prompt.format(
        chapter_text=chapter_text, old_state=old_character_state
    )
    new_char_state = invoke_with_cleaning(llm, prompt_char_state, cancel_check=_check_cancel)
    if not new_char_state.strip():
        new_char_state = old_character_state
    _emit("progress", {"step": "character_state_update", "status": "done", "message": "角色状态已更新"})

    _check_cancel()
    _emit("progress", {"step": "plot_arcs_update", "status": "running", "message": "正在更新伏笔暗线台账..."})
    prompt_plot_arcs = prompt_definitions.update_plot_arcs_prompt.format(
        chapter_number=novel_number,
        chapter_text=chapter_text,
        global_summary=new_global_summary,
        character_state=new_char_state,
        old_plot_arcs=old_plot_arcs,
    )
    new_plot_arcs = invoke_with_cleaning(llm, prompt_plot_arcs, cancel_check=_check_cancel)
    if not new_plot_arcs.strip():
        new_plot_arcs = old_plot_arcs
    _emit("progress", {"step": "plot_arcs_update", "status": "done", "message": "伏笔暗线台账已更新"})

    _check_cancel()
    clear_file_content(global_summary_file)
    save_string_to_txt(new_global_summary, global_summary_file)
    clear_file_content(character_state_file)
    save_string_to_txt(new_char_state, character_state_file)
    clear_file_content(plot_arcs_file)
    save_string_to_txt(new_plot_arcs, plot_arcs_file)

    _check_cancel()
    if ctx.embedding.api_key:
        emb = create_embedding_adapter(
            ctx.embedding.interface_format,
            ctx.embedding.api_key,
            ctx.embedding.base_url,
            ctx.embedding.model_name,
        )
        update_vector_store(emb, chapter_text, filepath)

    logger.info(f"Chapter {novel_number} has been finalized.")


def enrich_chapter_text(
    ctx,              # GenerationContext
    chapter_text: str,
    word_number: int,
    task_id: str | None = None,
) -> str:
    def _check_cancel():
        if task_id:
            raise_if_cancelled(task_id)
        return False

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
    prompt = prompt_definitions.enrich_prompt.format(word_number=word_number, chapter_text=chapter_text)
    enriched_text = invoke_with_cleaning(llm, prompt, cancel_check=_check_cancel)
    return enriched_text if enriched_text else chapter_text
