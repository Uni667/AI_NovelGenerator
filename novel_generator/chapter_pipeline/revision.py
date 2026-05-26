# -*- coding: utf-8 -*-
import json
import logging
from novel_generator.common import invoke_with_cleaning
from novel_generator.task_manager import raise_if_cancelled
from novel_generator import prompts as prompt_definitions
from novel_generator.platform_guidance import get_platform_chapter_guidance
from novel_generator.chapter_pipeline.adapters import create_specialized_chat_adapter

logger = logging.getLogger(__name__)


def rewrite_chapter_by_quality_feedback(
    ctx,
    params,
    chapter_info: dict,
    chapter_text: str,
    opening_feedback: dict,
    ending_feedback: dict,
    mid_feedback: dict | None = None,
    dialogue_feedback: dict | None = None,
    task_id: str | None = None,
) -> str:
    platform_label, platform_rules = get_platform_chapter_guidance(getattr(params, "platform", "tomato"))

    llm = create_specialized_chat_adapter(ctx, "quality_rewrite")

    def _check_cancel():
        if task_id:
            raise_if_cancelled(task_id)
        return False

    prompt = prompt_definitions.get_prompt_template(ctx.project_id, 'chapter_quality_rewrite_prompt').format(
        platform_label=platform_label,
        platform_rules=platform_rules,
        novel_number=params.chapter_number,
        chapter_title=chapter_info.get("chapter_title", ""),
        chapter_role=chapter_info.get("chapter_role", ""),
        chapter_purpose=chapter_info.get("chapter_purpose", ""),
        suspense_level=chapter_info.get("suspense_level", ""),
        foreshadowing=chapter_info.get("foreshadowing", ""),
        plot_twist_level=chapter_info.get("plot_twist_level", ""),
        chapter_summary=chapter_info.get("chapter_summary", ""),
        opening_feedback=json.dumps({
            "opening": opening_feedback,
            "middle": mid_feedback or {},
            "dialogue": dialogue_feedback or {},
        }, ensure_ascii=False, indent=2),
        ending_feedback=json.dumps(ending_feedback, ensure_ascii=False, indent=2),
        chapter_text=chapter_text,
    )

    revised = invoke_with_cleaning(
        llm,
        prompt,
        cancel_check=_check_cancel,
        operation_name="章节平台质检返修",
        step="quality_rewrite",
    )
    return revised.strip() or chapter_text


def revise_chapter_voice(
    ctx,
    params,
    chapter_info: dict,
    chapter_text: str,
    task_id: str | None = None,
) -> str:
    if not chapter_text.strip():
        return chapter_text

    platform_label, platform_rules = get_platform_chapter_guidance(getattr(params, "platform", "tomato"))

    llm = create_specialized_chat_adapter(ctx, "voice_polish")

    def _check_cancel():
        if task_id:
            raise_if_cancelled(task_id)
        return False

    prompt = prompt_definitions.get_prompt_template(ctx.project_id, 'de_ai_style_revision_prompt').format(
        platform_label=platform_label,
        platform_rules=platform_rules,
        novel_number=params.chapter_number,
        chapter_title=chapter_info.get("chapter_title", ""),
        chapter_role=chapter_info.get("chapter_role", ""),
        chapter_purpose=chapter_info.get("chapter_purpose", ""),
        suspense_level=chapter_info.get("suspense_level", ""),
        foreshadowing=chapter_info.get("foreshadowing", ""),
        plot_twist_level=chapter_info.get("plot_twist_level", ""),
        chapter_summary=chapter_info.get("chapter_summary", ""),
        word_number=params.word_number,
        chapter_text=chapter_text,
    )

    revised = invoke_with_cleaning(
        llm,
        prompt,
        cancel_check=_check_cancel,
        operation_name="章节去AI味修订",
        step="voice_polish",
    )
    return revised.strip() or chapter_text


def stream_interactive_rewrite(
    ctx,
    context_before: str,
    selected_text: str,
    context_after: str,
    user_instruction: str,
    emitter=None,
    task_id: str | None = None,
    project_config: dict | None = None,
) -> str:
    """
    流式重写选中的文本段落
    """
    llm = create_specialized_chat_adapter(ctx, "quality_rewrite")

    def _check_cancel():
        if task_id:
            raise_if_cancelled(task_id)
        return False

    # Extract platform and configuration constraints to prevent style washouts and settings breaches
    platform_label = "自定义"
    platform_rules = "无"
    forbidden = "无"
    style_requirement = "无"
    genre = "无"
    topic = "无"

    if project_config:
        platform = project_config.get("platform", "tomato")
        platform_label, platform_rules = get_platform_chapter_guidance(platform)
        forbidden = project_config.get("forbidden") or "无"
        style_requirement = project_config.get("style_requirement") or "无"
        genre = project_config.get("genre") or "无"
        topic = project_config.get("topic") or "无"

    prompt = prompt_definitions.get_prompt_template(ctx.project_id, 'interactive_rewrite_prompt').format(
        context_before=context_before,
        selected_text=selected_text,
        context_after=context_after,
        user_instruction=user_instruction,
        platform_label=platform_label,
        platform_rules=platform_rules,
        forbidden=forbidden,
        style_requirement=style_requirement,
        genre=genre,
        topic=topic,
    )

    if emitter and hasattr(emitter, "emit"):
        emitter.emit("progress", {"step": "interactive_rewrite", "status": "running", "message": "正在局部重写..."})

    def _on_chunk(text: str):
        if emitter and hasattr(emitter, "emit"):
            emitter.emit("partial", {"step": "interactive_rewrite", "content": text})

    revised = invoke_with_cleaning(
        llm,
        prompt,
        cancel_check=_check_cancel,
        operation_name="划线局部重写",
        step="interactive_rewrite",
        stream_callback=_on_chunk,
    )
    
    if emitter and hasattr(emitter, "emit"):
        emitter.emit("progress", {"step": "interactive_rewrite", "status": "done", "message": "局部重写完成"})
        
    return revised.strip() or selected_text
