# -*- coding: utf-8 -*-
"""Prompt builder for platform-aware commercial web-novel assistance."""

from __future__ import annotations

from dataclasses import dataclass

from novel_generator.commercial_profiles import format_profile_for_prompt, format_trend_for_prompt, get_platform_profile


SUPPORTED_MODES = {
    "generate_chapter": "章节生成",
    "rewrite_chapter": "章节改写",
    "outline": "生成章节大纲",
    "volume_outline": "生成卷纲",
    "character_bio": "生成角色小传",
    "platform_opening": "生成平台化开篇",
    "selling_points": "生成爽点设计",
    "ending_hook": "生成结尾钩子",
    "set_piece": "生成名场面",
    "short_drama": "生成短剧化分镜",
    "diagnose": "诊断章节问题",
    "platform_rewrite": "根据平台重写同一章",
}


@dataclass
class CommercialPromptInput:
    mode: str = "generate_chapter"
    novel_name: str = ""
    novel_type: str = ""
    platform: str = ""
    target_reader: str = ""
    reader_direction: str = ""
    current_chapter: str = ""
    previous_summary: str = ""
    world_setting: str = ""
    character_setting: str = ""
    protagonist_goal: str = ""
    main_conflict: str = ""
    chapter_task: str = ""
    chapter_selling_point: str = ""
    chapter_emotion: str = ""
    chapter_hook: str = ""
    trend_key: str = ""
    custom_trend: str = ""
    trend_translation: str = ""
    forbidden: str = ""
    style_requirement: str = ""
    word_range: str = ""
    chapter_text: str = ""
    output_revision_notes: bool = True


def safety_prompt() -> str:
    return "\n".join([
        "安全与作者控制边界：",
        "1. 不写真实人物谣言，不消费灾难，不硬蹭敏感事件。",
        "2. 不生成仇恨、色情、违法擦边、极端暴力内容。",
        "3. 不直接照搬现实新闻，只抽象为小说世界内部矛盾。",
        "4. 不强制覆盖作者原设定；世界观、人物关系、主线立意、感情走向以用户输入为准。",
        "5. 对不确定处只给诊断、建议或备选方案，必须标明可选，不替作者做最终决定。",
    ])


def system_prompt() -> str:
    return "\n".join([
        "你不是普通小说续写助手，而是“网文平台主编 + 商业化编辑 + 读者画像分析师 + 热点转译策划 + 连载节奏医生 + 改稿编辑”。",
        "你的任务是根据用户提供的小说设定、目标平台、当前章节任务、前文摘要和读者偏好，生成适合连载平台发布的内容、诊断或改稿建议。",
        "必须让理念通过冲突、选择、代价、反击和阶段性胜利体现，不要只写文艺句子、抽象设定或空泛哲理。",
    ])


def story_context_prompt(data: CommercialPromptInput) -> str:
    fields = [
        ("小说名称", data.novel_name),
        ("小说类型", data.novel_type),
        ("目标读者", data.target_reader),
        ("读者方向", data.reader_direction),
        ("当前章节", data.current_chapter),
        ("前文摘要", data.previous_summary),
        ("世界观设定", data.world_setting),
        ("人物设定", data.character_setting),
        ("主角目标", data.protagonist_goal),
        ("主要矛盾", data.main_conflict),
        ("当前章节任务", data.chapter_task),
        ("本章爽点", data.chapter_selling_point),
        ("本章情绪点", data.chapter_emotion),
        ("本章结尾钩子", data.chapter_hook),
        ("禁止改动设定/禁止事项", data.forbidden),
        ("文风要求", data.style_requirement),
        ("字数范围", data.word_range),
    ]
    lines = ["故事上下文与用户可控参数："]
    for label, value in fields:
        lines.append(f"- {label}：{value.strip() if isinstance(value, str) and value.strip() else '未指定'}")
    return "\n".join(lines)


def output_format_prompt(mode: str) -> str:
    normalized = mode if mode in SUPPORTED_MODES else "generate_chapter"
    if normalized == "diagnose":
        return "\n".join([
            "输出格式：",
            "【总体评分】1-100分，并说明扣分原因",
            "【平台适配】",
            "【本章最大问题】",
            "【最该保留的亮点】",
            "【需要压缩的内容】",
            "【需要新增的冲突】",
            "【建议强化的爽点】",
            "【结尾钩子建议】",
            "【改写示范】",
        ])
    if normalized == "platform_rewrite":
        return "\n".join([
            "输出格式：",
            "【原章节问题】",
            "【目标平台读者偏好】",
            "【改写方向】",
            "【改写后正文】",
            "【改写说明】",
        ])
    if normalized == "short_drama":
        return "\n".join([
            "输出格式：",
            "【可视化冲突】",
            "【角色名场面】",
            "【反转点】",
            "【分镜式大纲】",
            "【爆点台词】",
        ])
    return "\n".join([
        "输出格式：",
        "【本章标题】",
        "【本章核心冲突】",
        "【本章爽点】",
        "【本章情绪点】",
        "【本章正文或方案】",
        "【本章结尾钩子】",
        "【下一章引子】",
    ])


def chapter_diagnosis_dimensions(platform: str | None = None) -> str:
    profile = get_platform_profile(platform)
    platform_focus = "、".join(profile.get("diagnosisFocus", []))
    return "\n".join([
        "章节诊断维度：",
        "1. 平台适配度",
        "2. 开篇钩子",
        "3. 本章核心冲突",
        "4. 本章爽点",
        "5. 本章情绪点",
        "6. 人物高光",
        "7. 女主主体性",
        "8. 反派压迫感",
        "9. 设定是否过密",
        "10. 信息释放是否合理",
        "11. 是否有阶段性推进",
        "12. 结尾是否有追读钩子",
        "13. 是否存在空泛哲理",
        "14. 是否存在节奏拖慢",
        "15. 是否适合目标平台连载",
        f"平台额外关注：{platform_focus or '无'}",
    ])


def build_commercial_prompt(data: CommercialPromptInput) -> str:
    mode_label = SUPPORTED_MODES.get(data.mode, SUPPORTED_MODES["generate_chapter"])
    trend_prompt = format_trend_for_prompt(data.trend_key, data.custom_trend)
    if data.trend_translation.strip():
        trend_prompt += "\n用户指定热点转译方式：" + data.trend_translation.strip()
    parts = [
        system_prompt(),
        format_profile_for_prompt(data.platform),
        trend_prompt,
        story_context_prompt(data),
        chapter_diagnosis_dimensions(data.platform) if data.mode in {"diagnose", "platform_rewrite"} else "",
        "当前创作模式：" + mode_label,
        "章节原文/待处理文本：\n" + (data.chapter_text.strip() or "未提供"),
        output_format_prompt(data.mode),
        safety_prompt(),
    ]
    return "\n\n".join(part for part in parts if part.strip())


def build_generation_context_block(
    *,
    platform: str,
    trend_key: str = "",
    custom_trend: str = "",
    forbidden: str = "",
    reader_direction: str = "",
) -> str:
    return "\n\n".join([
        "【平台化网文创作约束】",
        format_profile_for_prompt(platform),
        format_trend_for_prompt(trend_key, custom_trend),
        f"读者方向：{reader_direction or '未指定，按目标平台默认读者画像处理'}",
        f"禁止改动设定：{forbidden or '未指定。仍必须保留用户已给出的世界观、人物关系、主线立意和感情走向。'}",
        safety_prompt(),
    ])
