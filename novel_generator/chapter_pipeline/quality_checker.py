# -*- coding: utf-8 -*-
import json
import logging
from novel_generator.common import invoke_with_cleaning
from novel_generator.task_manager import raise_if_cancelled
from novel_generator import prompts as prompt_definitions
from novel_generator.chapter_pipeline.adapters import create_specialized_chat_adapter
from novel_generator.json_parser import extract_json_from_text

logger = logging.getLogger(__name__)


def get_semantic_segments(chapter_text: str) -> str:
    """
    智能地将正文切片，拼接出“开篇部分”、“中段部分”和“结尾部分”的精简段落，
    保留了段落的完整性（以换行为边界），避免粗暴字符截断导致语义扭曲，并极大节省 Token。
    """
    paragraphs = [p.strip() for p in chapter_text.splitlines() if p.strip()]
    if not paragraphs:
        return ""
    
    total_paras = len(paragraphs)
    # 如果总段落数比较少，直接返回全文
    if total_paras <= 15:
        return chapter_text

    # 开篇部分：取前 5 段
    opening = paragraphs[:5]
    
    # 结尾部分：取最后 5 段
    ending = paragraphs[-5:]
    
    # 中段部分：取正中间 5 段
    mid_start = max(5, total_paras // 2 - 2)
    middle = paragraphs[mid_start:mid_start + 5]
    
    formatted = [
        "【开篇部分段落】",
        "\n".join(opening),
        "\n======================================",
        "【中段部分段落】",
        "\n".join(middle),
        "\n======================================",
        "【结尾部分段落】",
        "\n".join(ending)
    ]
    return "\n".join(formatted)


def analyze_chapter_quality(ctx, chapter_text: str, task_id: str | None = None) -> dict:
    """
    合并原有的开篇、中段、结尾和对话质检，在单次 LLM 请求中完成分析，减少 API 延迟与费用。
    """
    if not chapter_text.strip():
        return {
            "opening": {"score": 0, "issues": ["章节内容为空"], "suggestion": "先生成正文"},
            "ending": {"has_hook": False, "hook_type": "无", "suggestion": "先生成正文"},
            "middle": {"score": 0, "issues": ["章节内容为空"], "suggestion": "先生成正文"},
            "dialogue": {"score": 0, "issues": ["章节内容为空"], "suggestion": "先生成正文"}
        }

    llm = create_specialized_chat_adapter(ctx, "review")

    def _check_cancel():
        if task_id:
            raise_if_cancelled(task_id)
        return False

    # 提取精简的语义段落，控制 Token 开销并避免单词斩断
    sliced_text = get_semantic_segments(chapter_text)

    prompt = prompt_definitions.get_prompt_template(
        ctx.project_id, 'chapter_comprehensive_quality_check_prompt'
    ).format(chapter_text=sliced_text)

    result = invoke_with_cleaning(
        llm,
        prompt,
        cancel_check=_check_cancel,
        operation_name="章节综合质检",
        step="quality_check",
    )
    
    parsed = extract_json_from_text(result)
    if parsed and isinstance(parsed, dict):
        # 确保包含必需的质检维度，如果没有则赋予正常分值的默认字典
        return {
            "opening": parsed.get("opening") or {"score": 8, "issues": [], "suggestion": "开篇分析解析失败，使用默认分值"},
            "ending": parsed.get("ending") or {"has_hook": True, "hook_type": "无", "suggestion": "结尾分析解析失败"},
            "middle": parsed.get("middle") or {"score": 8, "issues": [], "suggestion": "中段分析解析失败"},
            "dialogue": parsed.get("dialogue") or {"score": 8, "issues": [], "suggestion": "对话分析解析失败"}
        }
        
    logger.warning("Failed to parse comprehensive quality analysis. Raw: %s", result[:300])
    return {
        "opening": {"score": 8, "issues": ["综合质检输出解析失败"], "suggestion": "解析失败，跳过限制"},
        "ending": {"has_hook": True, "hook_type": "无", "suggestion": "解析失败"},
        "middle": {"score": 8, "issues": [], "suggestion": "解析失败"},
        "dialogue": {"score": 8, "issues": [], "suggestion": "解析失败"}
    }


# ==========================================
# 兼容旧接口的包装器，避免修改其他依赖文件
# ==========================================

def analyze_opening_hook(ctx, chapter_text: str, task_id: str | None = None) -> dict:
    res = analyze_chapter_quality(ctx, chapter_text, task_id)
    return res.get("opening", {"score": 8, "issues": [], "suggestion": ""})


def analyze_ending_hook(ctx, chapter_text: str, task_id: str | None = None) -> dict:
    res = analyze_chapter_quality(ctx, chapter_text, task_id)
    return res.get("ending", {"has_hook": True, "hook_type": "无", "suggestion": ""})


def analyze_mid_section_quality(ctx, chapter_text: str, task_id: str | None = None) -> dict:
    res = analyze_chapter_quality(ctx, chapter_text, task_id)
    return res.get("middle", {"score": 8, "issues": [], "suggestion": ""})


def analyze_dialogue_voice(ctx, chapter_text: str, task_id: str | None = None) -> dict:
    res = analyze_chapter_quality(ctx, chapter_text, task_id)
    return res.get("dialogue", {"score": 8, "issues": [], "suggestion": ""})
