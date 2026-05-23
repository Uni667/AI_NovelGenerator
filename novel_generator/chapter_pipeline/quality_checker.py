# -*- coding: utf-8 -*-
import json
import logging
from novel_generator.common import invoke_with_cleaning
from novel_generator.task_manager import raise_if_cancelled
from novel_generator import prompts as prompt_definitions
from novel_generator.chapter_pipeline.adapters import create_specialized_chat_adapter
from novel_generator.json_parser import extract_json_from_text

logger = logging.getLogger(__name__)


def analyze_opening_hook(ctx, chapter_text: str, task_id: str | None = None) -> dict:
    if not chapter_text.strip():
        return {"score": 0, "issues": ["章节内容为空"], "suggestion": "先生成正文"}

    llm = create_specialized_chat_adapter(ctx, "review")

    def _check_cancel():
        if task_id:
            raise_if_cancelled(task_id)
        return False

    prompt = (
        "你是一位网络小说编辑。请严格按 JSON 输出以下开篇分析结果。\n\n"
        "评估标准：\n"
        "1. 前200字是否快速进入冲突、危机、异样、欲望或强悬念。\n"
        "2. 是否避免了空泛铺垫、背景说明和模板化解释。\n"
        "3. 是否让读者自然产生继续读下去的冲动。\n\n"
        f"待分析文本：\n{chapter_text[:2000]}\n\n"
        "输出格式：\n"
        "{\n"
        '  "score": 1-10,\n'
        '  "issues": ["问题1", "问题2"],\n'
        '  "suggestion": "50字以内建议",\n'
        '  "rewritten_opening": "可选，改写后的开头片段"\n'
        "}\n"
        "只输出 JSON。"
    )

    result = invoke_with_cleaning(
        llm,
        prompt,
        cancel_check=_check_cancel,
        operation_name="章节开篇质检",
        step="opening_check",
    )
    parsed = extract_json_from_text(result)
    if parsed:
        return parsed
    logger.warning("Failed to parse opening analysis. Raw: %s", result[:200])
    return {"score": 0, "issues": ["无法解析开篇质检结果"], "suggestion": result[:120]}


def analyze_ending_hook(ctx, chapter_text: str, task_id: str | None = None) -> dict:
    if not chapter_text.strip():
        return {"has_hook": False, "suggestion": "先生成正文"}

    llm = create_specialized_chat_adapter(ctx, "review")

    def _check_cancel():
        if task_id:
            raise_if_cancelled(task_id)
        return False

    ending = chapter_text[-500:] if len(chapter_text) > 500 else chapter_text
    prompt = (
        "你是一位网络小说编辑。请严格按 JSON 输出以下章节结尾钩子分析结果。\n\n"
        "检查重点：\n"
        "1. 结尾是否留下危机、揭秘、欲望、反转中的至少一种钩子。\n"
        "2. 读者是否会自然想点下一章。\n"
        "3. 结尾是否过于平、收得太死、解释过多。\n\n"
        f"待分析结尾：\n{ending}\n\n"
        "输出格式：\n"
        "{\n"
        '  "has_hook": true/false,\n'
        '  "hook_type": "危机型/揭秘型/欲望型/反转型/无",\n'
        '  "suggestion": "50字以内建议"\n'
        "}\n"
        "只输出 JSON。"
    )

    result = invoke_with_cleaning(
        llm,
        prompt,
        cancel_check=_check_cancel,
        operation_name="章节结尾质检",
        step="ending_check",
    )
    parsed = extract_json_from_text(result)
    if parsed:
        return parsed
    logger.warning("Failed to parse ending analysis. Raw: %s", result[:200])
    return {"has_hook": False, "hook_type": "无", "suggestion": result[:120]}


def analyze_mid_section_quality(ctx, chapter_text: str, task_id: str | None = None) -> dict:
    if not chapter_text.strip():
        return {"score": 0, "issues": ["章节内容为空"], "suggestion": "先生成正文"}

    llm = create_specialized_chat_adapter(ctx, "review")

    def _check_cancel():
        if task_id:
            raise_if_cancelled(task_id)
        return False

    middle_text = chapter_text
    if len(chapter_text) > 1800:
        start = min(600, len(chapter_text) // 4)
        end = max(start + 600, len(chapter_text) - 600)
        middle_text = chapter_text[start:end]

    result = invoke_with_cleaning(
        llm,
        prompt_definitions.mid_section_quality_prompt.format(chapter_text=middle_text[:2500]),
        cancel_check=_check_cancel,
        operation_name="章节中段质检",
        step="mid_check",
    )
    parsed = extract_json_from_text(result)
    if parsed:
        return parsed
    logger.warning("Failed to parse mid-section analysis. Raw: %s", result[:200])
    return {"score": 0, "issues": ["无法解析中段质检结果"], "suggestion": result[:120]}


def analyze_dialogue_voice(ctx, chapter_text: str, task_id: str | None = None) -> dict:
    if not chapter_text.strip():
        return {"score": 0, "issues": ["章节内容为空"], "suggestion": "先生成正文"}

    llm = create_specialized_chat_adapter(ctx, "review")

    def _check_cancel():
        if task_id:
            raise_if_cancelled(task_id)
        return False

    result = invoke_with_cleaning(
        llm,
        prompt_definitions.dialogue_voice_check_prompt.format(chapter_text=chapter_text[:3000]),
        cancel_check=_check_cancel,
        operation_name="人物话语质检",
        step="dialogue_check",
    )
    parsed = extract_json_from_text(result)
    if parsed:
        return parsed
    logger.warning("Failed to parse dialogue analysis. Raw: %s", result[:200])
    return {"score": 0, "issues": ["无法解析人物话语质检结果"], "suggestion": result[:120]}


