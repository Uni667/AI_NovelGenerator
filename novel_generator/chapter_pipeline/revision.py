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
        word_number=params.word_number,
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


def stream_chapter_ask_ai(
    ctx,
    chapter_number: int,
    chapter_meta: dict,
    chapter_content: str,
    question: str,
    selected_text: str | None = None,
    emitter=None,
    task_id: str | None = None,
    project_config: dict | None = None,
) -> str:
    """
    流式解答用户关于本章节的询问分析
    """
    llm = create_specialized_chat_adapter(ctx, "quality_rewrite", temperature=0.2)

    def _check_cancel():
        if task_id:
            raise_if_cancelled(task_id)
        return False

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

    chapter_role = chapter_meta.get("chapter_role") or "无"
    chapter_purpose = chapter_meta.get("chapter_purpose") or "无"
    suspense_level = chapter_meta.get("suspense_level") or "无"
    foreshadowing = chapter_meta.get("foreshadowing") or "无"
    plot_twist_level = chapter_meta.get("plot_twist_level") or "无"
    chapter_summary = chapter_meta.get("chapter_summary") or "无"

    selected_text_section = ""
    if selected_text and selected_text.strip():
        selected_text_section = f"【作者划线选中的正文段落】\n\"\"\"\n{selected_text.strip()}\n\"\"\"\n"

    prompt = f"""你是一名顶尖的网络小说总编辑和写作指导教练。作者正在创作当前章节，并就本章的写作逻辑、情节设计或特定文本段落向你发起咨询。

【项目背景与配置】
- 题材：{genre}
- 主题/金手指：{topic}
- 文风要求：{style_requirement}
- 避雷限制：{forbidden}
- 平台偏好：{platform_label}

【当前章节大纲设计】
- 章节号：第{chapter_number}章
- 章节定位：{chapter_role}
- 核心作用：{chapter_purpose}
- 悬念密度：{suspense_level}
- 伏笔操作：{foreshadowing}
- 认知颠覆：{plot_twist_level}
- 本章简述：{chapter_summary}

【本章正文内容】
{chapter_content}

{selected_text_section}

【作者提问】
{question}

请根据项目背景、大纲设计、上下文逻辑以及读者的期待，为作者提供深刻、专业且有建设性的解答。
1. 直接回答作者的问题（例如：为什么要这么写，合理吗？）。
2. 分析当前写法的优缺点（从节奏、代入感、悬念、人物塑造等角度）。
3. 如果不够合理或有提升空间，提供具体的修改建议或剧情微调方向。
回答要专业、言之有物，避免空洞和套话。

请直接给出解答，不需要前导问候语或解释。
"""

    if emitter and hasattr(emitter, "emit"):
        emitter.emit("progress", {"step": "ask_ai", "status": "running", "message": "AI 正在分析本章写作合理性..."})

    def _on_chunk(text: str):
        if emitter and hasattr(emitter, "emit"):
            emitter.emit("partial", {"step": "ask_ai", "content": text})

    result = invoke_with_cleaning(
        llm,
        prompt,
        cancel_check=_check_cancel,
        operation_name="询问AI写作合理性",
        step="ask_ai",
        stream_callback=_on_chunk,
    )
    
    if emitter and hasattr(emitter, "emit"):
        emitter.emit("progress", {"step": "ask_ai", "status": "done", "message": "分析完成"})
        
    return result
