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

    prompt = prompt_definitions.chapter_quality_rewrite_prompt.format(
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

    prompt = prompt_definitions.de_ai_style_revision_prompt.format(
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


