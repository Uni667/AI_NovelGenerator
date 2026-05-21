from __future__ import annotations

from novel_generator.commercial_profiles import format_profile_for_prompt, get_platform_profile


def get_platform_chapter_guidance(platform: str) -> tuple[str, str]:
    """Return a human platform label and chapter-level commercial guidance."""
    profile = get_platform_profile(platform)
    rules = "\n".join([
        format_profile_for_prompt(platform),
        "章节执行要求：",
        "- 每章必须有核心冲突、情绪推进、阶段性变化和结尾追读钩子。",
        "- 设定必须通过事件、选择、代价和反击落地，不要一次性倾倒设定。",
        "- 不替作者改世界观、人物关系、主线立意和感情走向，只围绕既定设定增强表达。",
    ])
    return profile["name"], rules


def get_platform_story_rhythm_guidance(platform: str) -> tuple[str, str]:
    """Return a human platform label and full-story rhythm guidance."""
    profile = get_platform_profile(platform)
    rules = "\n".join([
        format_profile_for_prompt(platform),
        "全书节奏要求：",
        "- 前期尽快亮出卖点、主线压力和读者追读理由。",
        "- 中期持续升级冲突、关系、资源和规则压力，避免连续平章。",
        "- 每3到5章形成一个小单元推进：压迫、选择、反击、代价或新悬念。",
        "- 长线伏笔要稳定推进，但每章也要有当前章节的可感知收益。",
        "- 作者明确禁止改动的设定一律保留，只能给备选建议。",
    ])
    return profile["name"], rules
