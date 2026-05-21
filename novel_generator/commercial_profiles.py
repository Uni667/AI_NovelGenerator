# -*- coding: utf-8 -*-
"""Commercial web-novel platform profiles and trend translators.

The data here is intentionally plain Python so editors can maintain it without
touching prompt assembly logic. These profiles guide suggestions; they must not
override an author's explicit worldbuilding, character relationships, theme, or
romance direction.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


DEFAULT_PLATFORM_KEY = "fanqie_free"

PLATFORM_ALIASES = {
    "tomato": "fanqie_free",
    "fanqie": "fanqie_free",
    "qimao": "fanqie_free",
    "qidian": "qidian_male",
    "qq": "qidian_male",
    "qq_reading": "qidian_male",
    "jjwxc": "jjwxc_xianxia",
    "jinjiang": "jjwxc_xianxia",
    "short": "short_drama",
    "short_drama_ip": "short_drama",
    "drama": "short_drama",
}

PLATFORM_PROFILES: dict[str, dict[str, Any]] = {
    "qidian_male": {
        "name": "起点 / QQ 阅读男频",
        "readerPreference": ["世界观清晰", "升级体系明确", "主角目标明确", "长线伏笔", "阶段性胜利", "智斗和秩序感"],
        "chapterRequirement": ["每章必须推进主线", "设定必须事件化", "概念必须转化为具体冲突", "阶段性胜利要定期兑现", "避免过度文艺化"],
        "avoid": ["长篇空谈哲理", "主角目标模糊", "设定一次性倾倒", "爽点兑现太慢", "概念只停留在解释层"],
        "hookStrategy": ["下一步行动目标", "更高阶资源或规则露出", "长线伏笔被局部触发", "阶段性胜利后出现新压迫"],
        "diagnosisFocus": ["主线推进", "升级路径", "设定事件化", "阶段性胜利", "长线伏笔"],
    },
    "fanqie_free": {
        "name": "番茄 / 七猫免费阅读",
        "readerPreference": ["强开局", "强冲突", "强反转", "短章爽点", "情绪刺激", "结尾钩子"],
        "chapterRequirement": ["前三章快速建立压迫和反击", "每章结尾必须有追读钩子", "减少抽象议论", "多写行动、冲突、选择、结果"],
        "avoid": ["慢热", "设定堆砌", "文艺化独白", "主角被动太久", "只铺垫不兑现"],
        "hookStrategy": ["危机压顶", "身份揭露", "反转未落地", "反击刚开始", "奖励或代价悬而未决"],
        "diagnosisFocus": ["开篇钩子", "反转密度", "情绪刺激", "短章爽点", "结尾追读"],
    },
    "jjwxc_xianxia": {
        "name": "晋江 / 女频仙侠",
        "readerPreference": ["人物关系", "情绪张力", "双强拉扯", "女主主体性", "宿命感", "感情递进"],
        "chapterRequirement": ["女主必须有独立目标", "感情线必须服务人物成长", "选择必须有代价", "关系变化要可感知"],
        "avoid": ["女主工具人", "感情线突兀", "男主单方面碾压", "只写设定不写情绪", "把女性角色写成奖励品"],
        "hookStrategy": ["关系选择的代价", "双强立场冲突", "宿命线索露出", "女主独立高光后的新压力"],
        "diagnosisFocus": ["人物关系", "情绪张力", "女主主体性", "感情递进", "选择代价"],
    },
    "short_drama": {
        "name": "短剧 / IP 改编向",
        "readerPreference": ["名场面", "视觉冲突", "强反转", "爆点台词", "人物标签", "节奏密集"],
        "chapterRequirement": ["每3到5章设计一个可剪辑爆点", "冲突必须可视化", "台词要有传播性", "人物行为要有辨识度"],
        "avoid": ["大段内心独白", "低画面感", "反转不足", "角色标签不清", "冲突只靠旁白解释"],
        "hookStrategy": ["画面级反转", "爆点台词后切断", "身份/关系骤变", "可剪辑动作冲突升级"],
        "diagnosisFocus": ["视觉化冲突", "名场面", "爆点台词", "反转强度", "分镜潜力"],
    },
}

TREND_TRANSLATORS: dict[str, dict[str, Any]] = {
    "resource_anxiety": {
        "name": "资源焦虑",
        "realEmotion": "学历、阶层、资源分配焦虑",
        "fictionalTranslation": ["学院名额被世家垄断", "宗门考核暗藏门第门槛", "灵脉资源按身份分配", "白籍没有上层修炼资格", "修炼资格被名册制度锁死"],
        "avoid": ["直接影射真实学校或现实个人", "把现实新闻原样搬进剧情"],
    },
    "rule_pressure": {
        "name": "规则压迫",
        "realEmotion": "算法、制度、平台规则带来的压迫感",
        "fictionalTranslation": ["天道刻度给所有人评分", "命牌限制修士选择", "司籍署审查身份流动", "官灯监察违规者", "宗门贡献点决定生路"],
        "avoid": ["直接照搬现实平台争议", "写成政策评论"],
    },
    "fairness_anxiety": {
        "name": "公平焦虑",
        "realEmotion": "年轻人对机会公平和暗箱规则的焦虑",
        "fictionalTranslation": ["寒门修士对抗世家弟子", "低阶修士挑战既定秩序", "资源分配不公", "榜单黑幕", "试炼名次被后台篡改"],
        "avoid": ["空喊口号", "让角色长篇讲道理"],
    },
    "labor_discipline": {
        "name": "打工人规训感",
        "realEmotion": "被制度安排、被绩效标价、被流程消耗的压迫感",
        "fictionalTranslation": ["白籍被标价", "修士被强制派役", "外门弟子被压榨", "神朝用制度安排命运", "贡献点低者被剥夺选择权"],
        "avoid": ["流水账式抱怨", "缺少具体反击事件"],
    },
    "ai_humanity": {
        "name": "AI / 技术 / 人性焦虑",
        "realEmotion": "技术替代、人性被算法重塑的焦虑",
        "fictionalTranslation": ["天机傀儡替代修士判断", "命算法预测并干预人生", "无情天规抹除例外", "人格改造术", "补天会以修补人性为名控制人"],
        "avoid": ["真实公司映射", "技术恐慌口号化"],
    },
    "female_agency": {
        "name": "女性主体性",
        "realEmotion": "女性希望拥有独立选择、边界和高光",
        "fictionalTranslation": ["女主有独立大道", "女主拥有独立高光", "女主不是奖励品", "女主能救人也能拒绝救人", "女主的温柔有边界"],
        "avoid": ["把女主写成主角奖励", "用牺牲证明价值"],
    },
    "anti_involution": {
        "name": "反内卷情绪",
        "realEmotion": "不愿被单一标准评价和耗尽",
        "fictionalTranslation": ["主角不只追求变强", "主角质疑谁制定强弱标准", "主角不接受被榜单定义", "主角建立自己的秩序", "修行体系被重新解释"],
        "avoid": ["消极躺平", "没有行动方案的说教"],
    },
}


def normalize_platform_key(platform: str | None) -> str:
    key = (platform or DEFAULT_PLATFORM_KEY).strip().lower()
    key = PLATFORM_ALIASES.get(key, key)
    return key if key in PLATFORM_PROFILES else DEFAULT_PLATFORM_KEY


def get_platform_profile(platform: str | None) -> dict[str, Any]:
    key = normalize_platform_key(platform)
    profile = deepcopy(PLATFORM_PROFILES[key])
    profile["key"] = key
    return profile


def get_trend_translation(trend_key: str | None) -> dict[str, Any] | None:
    if not trend_key:
        return None
    key = trend_key.strip().lower()
    if key not in TREND_TRANSLATORS:
        return None
    item = deepcopy(TREND_TRANSLATORS[key])
    item["key"] = key
    return item


def list_platform_profiles() -> dict[str, dict[str, Any]]:
    return deepcopy(PLATFORM_PROFILES)


def list_trend_translators() -> dict[str, dict[str, Any]]:
    return deepcopy(TREND_TRANSLATORS)


def format_profile_for_prompt(platform: str | None) -> str:
    profile = get_platform_profile(platform)
    return "\n".join([
        f"目标平台：{profile['name']}",
        "读者偏好：" + "、".join(profile["readerPreference"]),
        "章节要求：" + "；".join(profile["chapterRequirement"]),
        "需要避免：" + "；".join(profile["avoid"]),
        "追读钩子策略：" + "；".join(profile["hookStrategy"]),
    ])


def format_trend_for_prompt(trend_key: str | None, custom_trend: str = "") -> str:
    trend = get_trend_translation(trend_key)
    parts: list[str] = []
    if trend:
        parts.extend([
            f"热点情绪：{trend['name']}",
            f"现实情绪抽象：{trend['realEmotion']}",
            "小说化转译备选：" + "；".join(trend["fictionalTranslation"]),
            "禁止：" + "；".join(trend["avoid"]),
        ])
    if custom_trend.strip():
        parts.append(f"用户自定义热点情绪：{custom_trend.strip()}")
        parts.append("处理方式：只能抽象成世界内部矛盾，不得照搬真实新闻、真实人物或敏感事件。")
    return "\n".join(parts) if parts else "热点情绪：未指定。可按平台读者的普遍情绪需求处理，但不得硬蹭现实新闻。"
