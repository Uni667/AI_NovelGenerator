# emotion_analyzer.py
# -*- coding: utf-8 -*-
"""
中文文本情感分析模块
支持三种分析方法：
  1. 词典法（SnowNLP）        - 轻量，无需训练
  2. 关键词法（自定义词典）    - 针对文学文本优化
  3. 大模型零样本法（LLM）    - 理解文学暗喻，最准确

用于 AI 小说生成器的章节情感质量监控与情感弧线生成。
"""

from __future__ import annotations

import logging
import re
import json
from typing import Optional

logger = logging.getLogger(__name__)


# ============================================================
# 情感标签常量
# ============================================================
LABEL_POSITIVE = "积极"
LABEL_NEGATIVE = "消极"
LABEL_NEUTRAL = "中性"
LABEL_TENSE = "紧张"
LABEL_SAD = "悲伤"
LABEL_JOYFUL = "喜悦"
LABEL_ANGRY = "愤怒"


# ============================================================
# 方法一：词典法（SnowNLP）
# ============================================================
def analyze_by_snownlp(text: str) -> dict:
    """
    使用 SnowNLP 进行中文情感分析（词典+朴素贝叶斯）。
    返回 0~1 之间的情感分数：越接近1越积极，越接近0越消极。

    适用场景：快速批量分析，对直白表达效果较好。
    局限性：对文学暗喻、环境描写的情感识别准确率较低。
    """
    try:
        from snownlp import SnowNLP
    except ImportError:
        logger.warning("SnowNLP 未安装，请运行: pip install snownlp")
        return {"score": 0.5, "label": LABEL_NEUTRAL, "method": "snownlp", "error": "未安装SnowNLP"}

    # 分句处理（增强准确性）
    sentences = _split_sentences(text)
    if not sentences:
        return {"score": 0.5, "label": LABEL_NEUTRAL, "method": "snownlp"}

    scores = []
    for sent in sentences:
        sent = sent.strip()
        if len(sent) < 3:
            continue
        try:
            s = SnowNLP(sent)
            scores.append(s.sentiments)
        except Exception:
            pass

    if not scores:
        return {"score": 0.5, "label": LABEL_NEUTRAL, "method": "snownlp"}

    avg_score = sum(scores) / len(scores)
    label = _score_to_label(avg_score)

    return {
        "score": round(avg_score, 4),
        "label": label,
        "method": "snownlp",
        "sentence_count": len(scores),
        "sentence_scores": [round(s, 3) for s in scores[:20]],  # 最多返回前20句
    }


# ============================================================
# 方法二：自定义文学情感词典法
# ============================================================

# 积极情感词库（文学文本高频）
_POSITIVE_WORDS = {
    # 明确积极
    "欢喜", "喜悦", "高兴", "快乐", "幸福", "幸运", "希望", "期待", "温暖", "光明",
    "胜利", "成功", "荣耀", "自由", "救赎", "坚强", "勇敢", "爱", "爱意", "柔情",
    "笑", "微笑", "欢笑", "感激", "感谢", "美好", "美丽", "安宁", "平静", "满足",
    "感动", "动容", "振奋", "激昂", "豪情", "壮志", "热情", "活力", "生机", "曙光",
    # 文学暗喻（正向）
    "朝阳", "春风", "花开", "破晓", "重生", "新生", "彩虹", "星光", "月华", "清晨",
}

# 消极情感词库（文学文本高频）
_NEGATIVE_WORDS = {
    # 明确消极
    "悲伤", "痛苦", "绝望", "恐惧", "愤怒", "仇恨", "孤独", "寂寞", "迷茫", "黑暗",
    "失败", "死亡", "毁灭", "崩溃", "绝境", "悔恨", "内疚", "羞耻", "憎恨", "嫉妒",
    "哭", "泪", "哭泣", "泣不成声", "哀嚎", "哀伤", "沉重", "压抑", "窒息", "痛",
    "杀", "血", "尸", "鲜血", "冷漠", "残忍", "凶狠", "阴暗", "腐朽", "枯萎",
    # 文学暗喻（负向）
    "黄昏", "残阳", "枯叶", "寒风", "深渊", "泥潭", "囚笼", "锁链", "荒芜", "废墟",
}

# 程度副词（强化系数）
_INTENSIFIERS = {"非常", "极度", "十分", "万分", "无比", "彻底", "完全", "极其", "愈发", "越来越"}
_NEGATORS = {"不", "没有", "无", "未", "别", "毫无", "丝毫", "并非", "并不"}


def analyze_by_keyword(text: str) -> dict:
    """
    基于自定义文学情感词典进行分析。
    相比 SnowNLP 更适合文学语境，但召回率依赖词典覆盖度。
    """
    pos_count = 0
    neg_count = 0
    matched_pos = []
    matched_neg = []

    sentences = _split_sentences(text)

    for sent in sentences:
        # 检测否定词（简单窗口：否定词前后3字内的情感词翻转）
        negated = any(neg in sent for neg in _NEGATORS)

        for word in _POSITIVE_WORDS:
            if word in sent:
                if negated:
                    neg_count += 1
                    matched_neg.append(f"[否定]{word}")
                else:
                    pos_count += 1
                    matched_pos.append(word)

        for word in _NEGATIVE_WORDS:
            if word in sent:
                if negated:
                    pos_count += 1
                    matched_pos.append(f"[否定]{word}")
                else:
                    neg_count += 1
                    matched_neg.append(word)

    total = pos_count + neg_count
    if total == 0:
        score = 0.5
    else:
        score = pos_count / total

    label = _score_to_label(score)

    return {
        "score": round(score, 4),
        "label": label,
        "method": "keyword",
        "pos_count": pos_count,
        "neg_count": neg_count,
        "matched_positive": list(set(matched_pos))[:10],
        "matched_negative": list(set(matched_neg))[:10],
    }


# ============================================================
# 方法三：大模型零样本法（LLM）
# ============================================================

_LLM_EMOTION_PROMPT = """\
你是一位专业的文学情感分析师。请分析以下中文小说文本段落的情感基调。

要求：
1. 从整体情感基调、张力强度、情绪类型三个维度进行判断
2. 情感得分范围 0.0~1.0（0=极度消极/悲伤, 0.5=中性/平淡, 1.0=极度积极/喜悦）
3. 注意：文学文本常用环境描写、动作细节暗示情感，请深度理解
4. 严格按JSON格式返回，不要有多余解释

待分析文本（前800字）：
{text}

请返回如下JSON（无需markdown代码块）：
{{
  "score": <0.0~1.0的浮点数>,
  "label": "<积极/消极/中性/紧张/悲伤/喜悦/愤怒>",
  "tension": <0.0~1.0，剧情张力强度>,
  "reasoning": "<一句话说明判断依据，不超过50字>",
  "key_emotions": ["<情绪词1>", "<情绪词2>"]
}}
"""


def analyze_by_llm(
    text: str,
    api_key: str,
    base_url: str,
    model_name: str,
    interface_format: str = "openai",
    temperature: float = 0.1,
    max_tokens: int = 512,
    timeout: int = 60,
) -> dict:
    """
    使用大语言模型进行零样本情感分析。
    最能理解文学暗喻和复杂语境，但需要LLM API调用。
    """
    try:
        from llm_adapters import create_llm_adapter
    except ImportError:
        logger.error("llm_adapters 模块未找到")
        return {"score": 0.5, "label": LABEL_NEUTRAL, "method": "llm", "error": "llm_adapters未找到"}

    # 截取前800字（避免超出token限制）
    truncated = text[:800] if len(text) > 800 else text
    prompt = _LLM_EMOTION_PROMPT.format(text=truncated)

    try:
        adapter = create_llm_adapter(
            interface_format=interface_format,
            base_url=base_url,
            model_name=model_name,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
        response = adapter.invoke(prompt)
        if not response:
            return {"score": 0.5, "label": LABEL_NEUTRAL, "method": "llm", "error": "LLM无回复"}

        # 解析JSON
        result = _parse_llm_json(response)
        result["method"] = "llm"
        return result

    except Exception as e:
        logger.warning(f"[EmotionAnalyzer] LLM分析失败: {e}")
        return {"score": 0.5, "label": LABEL_NEUTRAL, "method": "llm", "error": str(e)}


def _parse_llm_json(response: str) -> dict:
    """从LLM回复中提取JSON内容"""
    # 去除markdown代码块
    text = re.sub(r"```(?:json)?\s*", "", response).strip()
    text = text.rstrip("```").strip()

    # 找到第一个{...}结构
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return {"score": 0.5, "label": LABEL_NEUTRAL, "raw": response}

    try:
        data = json.loads(match.group())
        # 确保 score 在范围内
        score = float(data.get("score", 0.5))
        score = max(0.0, min(1.0, score))
        data["score"] = round(score, 4)
        return data
    except (json.JSONDecodeError, ValueError):
        return {"score": 0.5, "label": LABEL_NEUTRAL, "raw": response}


# ============================================================
# 综合分析入口
# ============================================================

def analyze_chapter_emotion(
    text: str,
    method: str = "snownlp",
    llm_config: Optional[dict] = None,
) -> dict:
    """
    对单个章节文本进行情感分析。

    Args:
        text: 章节文本内容
        method: 分析方法，"snownlp" | "keyword" | "llm" | "all"
        llm_config: LLM配置字典（method="llm"时必填）
            {"api_key": ..., "base_url": ..., "model_name": ..., "interface_format": ...}

    Returns:
        情感分析结果字典
    """
    if not text or not text.strip():
        return {"score": 0.5, "label": LABEL_NEUTRAL, "method": method, "error": "文本为空"}

    if method == "snownlp":
        return analyze_by_snownlp(text)

    elif method == "keyword":
        return analyze_by_keyword(text)

    elif method == "llm":
        if not llm_config:
            return {"score": 0.5, "label": LABEL_NEUTRAL, "method": "llm", "error": "未提供LLM配置"}
        return analyze_by_llm(text, **llm_config)

    elif method == "all":
        # 三种方法全部运行，返回综合结果
        result_snow = analyze_by_snownlp(text)
        result_kw = analyze_by_keyword(text)

        results = {"snownlp": result_snow, "keyword": result_kw}

        # LLM分析（可选）
        if llm_config:
            result_llm = analyze_by_llm(text, **llm_config)
            results["llm"] = result_llm
            # 加权融合：LLM权重0.5，其余各0.25
            avg = (result_snow["score"] * 0.25 +
                   result_kw["score"] * 0.25 +
                   result_llm["score"] * 0.5)
        else:
            avg = (result_snow["score"] + result_kw["score"]) / 2

        avg = round(avg, 4)
        results["combined_score"] = avg
        results["combined_label"] = _score_to_label(avg)
        results["method"] = "all"
        return results

    else:
        return {"score": 0.5, "label": LABEL_NEUTRAL, "error": f"未知方法: {method}"}


def analyze_novel_arc(
    chapters: list[dict],
    method: str = "snownlp",
    llm_config: Optional[dict] = None,
) -> list[dict]:
    """
    对整本小说的章节列表进行情感弧线分析。

    Args:
        chapters: 章节列表，每项需包含 {"chapter_number": int, "content": str, "title": str}
        method: 分析方法
        llm_config: LLM配置（method="llm"时使用）

    Returns:
        情感弧线数据列表，按章节排序
    """
    arc = []
    for ch in chapters:
        chapter_number = ch.get("chapter_number", 0)
        content = ch.get("content", "")
        title = ch.get("title", f"第{chapter_number}章")

        result = analyze_chapter_emotion(content, method=method, llm_config=llm_config)
        arc.append({
            "chapter_number": chapter_number,
            "title": title,
            "score": result.get("score", 0.5),
            "label": result.get("label", LABEL_NEUTRAL),
            "detail": result,
        })

    # 按章节号排序
    arc.sort(key=lambda x: x["chapter_number"])
    return arc


# ============================================================
# 工具函数
# ============================================================

def _split_sentences(text: str) -> list[str]:
    """将文本按句子分割"""
    # 按中文标点分句
    sentences = re.split(r'[。！？…\n]+', text)
    return [s.strip() for s in sentences if s.strip()]


def _score_to_label(score: float) -> str:
    """将0~1的分数转换为情感标签"""
    if score >= 0.7:
        return LABEL_POSITIVE
    elif score >= 0.55:
        return LABEL_NEUTRAL
    elif score >= 0.4:
        return LABEL_TENSE
    elif score >= 0.25:
        return LABEL_SAD
    else:
        return LABEL_NEGATIVE
