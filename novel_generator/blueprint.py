# -*- coding: utf-8 -*-
"""
章节蓝图生成（Chapter_blueprint_generate 及辅助函数）

重构要点：
- 接受 GenerationContext + ProjectConfig 替代散落参数
- 可选 emitter 回调用于 SSE 进度推送
"""
import os
import re
import logging
from novel_generator.common import invoke_with_cleaning
from novel_generator.task_manager import raise_if_cancelled, TaskCancelledError
from llm_adapters import create_llm_adapter
import prompt_definitions
from utils import read_file, clear_file_content, save_string_to_txt

logger = logging.getLogger(__name__)


def compute_chunk_size(number_of_chapters: int, max_tokens: int) -> int:
    tokens_per_chapter = 200.0
    ratio = max_tokens / tokens_per_chapter
    ratio_rounded_to_10 = int(ratio // 10) * 10
    chunk_size = ratio_rounded_to_10 - 10
    if chunk_size < 1:
        chunk_size = 1
    if chunk_size > number_of_chapters:
        chunk_size = number_of_chapters
    return chunk_size


def limit_chapter_blueprint(blueprint_text: str, limit_chapters: int = 100) -> str:
    pattern = r"(第\s*\d+\s*章.*?)(?=第\s*\d+\s*章|$)"
    chapters = re.findall(pattern, blueprint_text, flags=re.DOTALL)
    if not chapters:
        return blueprint_text
    if len(chapters) <= limit_chapters:
        return blueprint_text
    selected = chapters[-limit_chapters:]
    return "\n\n".join(selected).strip()


def Chapter_blueprint_generate(
    ctx,           # GenerationContext
    project,       # ProjectConfig
    emitter=None,  # 可选 SSE emitter
    task_id: str | None = None,
) -> None:
    """
    若 Novel_directory.txt 已存在且内容非空，则从下一个章节继续分块生成；
    否则从第 1 章开始生成。

    emitter: 具有 .emit(event_type, data) 的对象，用于 SSE 进度推送。
    """

    def _emit(event_type: str, data: dict):
        if emitter and hasattr(emitter, "emit"):
            emitter.emit(event_type, data)

    def _check_cancel():
        if task_id:
            raise_if_cancelled(task_id)
        if ctx.cancel_token is not None:
            ctx.cancel_token.raise_if_set()
        return False

    filepath = ctx.filepath
    number_of_chapters = project.num_chapters
    user_guidance = project.user_guidance

    _check_cancel()
    arch_file = os.path.join(filepath, "Novel_architecture.txt")
    if not os.path.exists(arch_file):
        logger.warning("Novel_architecture.txt not found. Please generate architecture first.")
        _emit("error", {"step": "blueprint", "message": "未找到小说架构文件，请先生成架构"})
        raise RuntimeError("未找到小说架构文件，请先生成架构")

    architecture_text = read_file(arch_file).strip()
    if not architecture_text:
        logger.warning("Novel_architecture.txt is empty.")
        _emit("error", {"step": "blueprint", "message": "小说架构文件为空"})
        raise RuntimeError("小说架构文件为空")

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

    filename_dir = os.path.join(filepath, "Novel_directory.txt")
    if not os.path.exists(filename_dir):
        open(filename_dir, "w", encoding="utf-8").close()

    existing_blueprint = read_file(filename_dir).strip()
    chunk_size = compute_chunk_size(number_of_chapters, ctx.llm.max_tokens)
    logger.info(f"Number of chapters = {number_of_chapters}, computed chunk_size = {chunk_size}.")

    _emit("progress", {"step": "blueprint", "status": "running", "message": "正在生成章节目录..."})

    if existing_blueprint:
        logger.info("Detected existing blueprint content. Will resume chunked generation from that point.")
        _check_cancel()
        pattern = r"第\s*(\d+)\s*章"
        existing_chapter_numbers = re.findall(pattern, existing_blueprint)
        existing_chapter_numbers = [int(x) for x in existing_chapter_numbers if x.isdigit()]
        max_existing_chap = max(existing_chapter_numbers) if existing_chapter_numbers else 0
        logger.info(f"Existing blueprint indicates up to chapter {max_existing_chap} has been generated.")
        final_blueprint = existing_blueprint
        current_start = max_existing_chap + 1
        while current_start <= number_of_chapters:
            current_end = min(current_start + chunk_size - 1, number_of_chapters)
            limited_blueprint = limit_chapter_blueprint(final_blueprint, 100)
            chunk_prompt = prompt_definitions.chunked_chapter_blueprint_prompt.format(
                novel_architecture=architecture_text,
                chapter_list=limited_blueprint,
                number_of_chapters=number_of_chapters,
                n=current_start, m=current_end,
                user_guidance=user_guidance
            )
            logger.info(f"Generating chapters [{current_start}..{current_end}] in a chunk...")
            _check_cancel()
            _emit("progress", {"step": "blueprint", "status": "running",
                               "message": f"正在生成第{current_start}-{current_end}章蓝图..."})
            chunk_result = invoke_with_cleaning(llm, chunk_prompt, cancel_check=_check_cancel)
            if not chunk_result.strip():
                logger.warning(f"Chunk generation for chapters [{current_start}..{current_end}] is empty.")
                clear_file_content(filename_dir)
                save_string_to_txt(final_blueprint.strip(), filename_dir)
                _emit("error", {"step": "blueprint", "message": f"第{current_start}-{current_end}章生成失败"})
                raise RuntimeError(f"第{current_start}-{current_end}章生成失败")
            final_blueprint += "\n\n" + chunk_result.strip()
            clear_file_content(filename_dir)
            save_string_to_txt(final_blueprint.strip(), filename_dir)
            current_start = current_end + 1

        _emit("progress", {"step": "blueprint", "status": "done", "message": "章节目录生成完成"})
        logger.info("All chapters blueprint have been generated (resumed chunked).")
        return

    if chunk_size >= number_of_chapters:
        prompt = prompt_definitions.chapter_blueprint_prompt.format(
            novel_architecture=architecture_text,
            number_of_chapters=number_of_chapters,
            user_guidance=user_guidance
        )
        _check_cancel()
        blueprint_text = invoke_with_cleaning(llm, prompt, cancel_check=_check_cancel)
        if not blueprint_text.strip():
            logger.warning("Chapter blueprint generation result is empty.")
            _emit("error", {"step": "blueprint", "message": "章节目录生成为空"})
            raise RuntimeError("章节目录生成为空")
        clear_file_content(filename_dir)
        save_string_to_txt(blueprint_text, filename_dir)
        _emit("progress", {"step": "blueprint", "status": "done", "message": "章节目录生成完成"})
        logger.info("Novel_directory.txt (chapter blueprint) has been generated successfully (single-shot).")
        return

    logger.info("Will generate chapter blueprint in chunked mode from scratch.")
    final_blueprint = ""
    current_start = 1
    while current_start <= number_of_chapters:
        current_end = min(current_start + chunk_size - 1, number_of_chapters)
        limited_blueprint = limit_chapter_blueprint(final_blueprint, 100)
        chunk_prompt = prompt_definitions.chunked_chapter_blueprint_prompt.format(
            novel_architecture=architecture_text,
            chapter_list=limited_blueprint,
            number_of_chapters=number_of_chapters,
            n=current_start, m=current_end,
            user_guidance=user_guidance
        )
        logger.info(f"Generating chapters [{current_start}..{current_end}] in a chunk...")
        _check_cancel()
        _emit("progress", {"step": "blueprint", "status": "running",
                           "message": f"正在生成第{current_start}-{current_end}章蓝图..."})
        chunk_result = invoke_with_cleaning(llm, chunk_prompt, cancel_check=_check_cancel)
        if not chunk_result.strip():
            logger.warning(f"Chunk generation for chapters [{current_start}..{current_end}] is empty.")
            clear_file_content(filename_dir)
            save_string_to_txt(final_blueprint.strip(), filename_dir)
            _emit("error", {"step": "blueprint", "message": f"第{current_start}-{current_end}章生成失败"})
            raise RuntimeError(f"第{current_start}-{current_end}章生成失败")
        if final_blueprint.strip():
            final_blueprint += "\n\n" + chunk_result.strip()
        else:
            final_blueprint = chunk_result.strip()
        clear_file_content(filename_dir)
        save_string_to_txt(final_blueprint.strip(), filename_dir)
        current_start = current_end + 1

    _emit("progress", {"step": "blueprint", "status": "done", "message": "章节目录生成完成"})
    logger.info("Novel_directory.txt (chapter blueprint) has been generated successfully (chunked).")
