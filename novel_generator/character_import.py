"""Character import parsing, scoring, and merge helpers."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Iterable, Optional


CHARACTER_SECTION_HINTS = (
    "人物",
    "角色",
    "已出现",
    "计划登场",
    "补充人物",
    "角色档案",
    "角色总览",
    "核心人物",
)

PERSON_FIELD_HINTS = (
    "身份",
    "目标",
    "关系",
    "秘密",
    "外貌",
    "性格",
    "能力",
    "状态",
    "心理",
    "阵营",
    "首次登场",
    "预计登场",
    "登场章节",
    "出场章节",
    "备注",
)

POSITIVE_HINTS = (
    "身份",
    "目标",
    "关系",
    "秘密",
    "外貌",
    "性格",
    "能力",
    "出场",
    "登场",
    "阵营",
    "立场",
    "心理",
    "动机",
    "经历",
)

LOCATION_HINTS = (
    "城",
    "镇",
    "村",
    "市",
    "县",
    "省",
    "国",
    "区",
    "街",
    "路",
    "山",
    "河",
    "湖",
    "港",
    "岛",
    "宫",
    "府",
    "院",
    "馆",
    "塔",
    "门",
    "派",
    "帮",
    "寨",
    "营",
    "谷",
    "谷地",
    "基地",
    "学园",
)

ORGANIZATION_HINTS = (
    "公司",
    "集团",
    "学院",
    "学校",
    "医院",
    "研究所",
    "研究院",
    "协会",
    "组织",
    "部门",
    "委员会",
    "局",
    "署",
    "社",
    "会",
    "军",
    "队",
    "宗",
    "教会",
    "门派",
)

TITLE_HINTS = (
    "先生",
    "女士",
    "老师",
    "老板",
    "教授",
    "主任",
    "队长",
    "长老",
    "少爷",
    "小姐",
    "大人",
    "阁下",
    "医生",
    "律师",
    "警官",
    "经理",
    "师傅",
    "秘书",
)

EVENT_HINTS = (
    "事件",
    "事故",
    "灾难",
    "战争",
    "叛乱",
    "袭击",
    "审判",
    "会议",
    "庆典",
    "任务",
    "计划",
    "标签",
    "规则",
    "设定",
    "伏笔",
    "暗线",
)

ABSTRACT_HINTS = (
    "主题",
    "情绪",
    "概念",
    "标签",
    "设定",
    "规则",
    "象征",
    "隐喻",
    "模型",
    "机制",
)


@dataclass
class CharacterImportCandidate:
    candidate_id: str
    name: str
    normalized_name: str
    description: str
    section: str
    raw_text: str
    entity_type: str
    confidence: float
    decision: str
    reasons: list[str] = field(default_factory=list)
    status: str = "planned"
    source: str = "ai"
    first_appearance_chapter: Optional[int] = None
    existing_character_id: Optional[int] = None
    matched_existing_name: str = ""
    aliases: list[str] = field(default_factory=list)
    selected: bool = False

    def to_dict(self) -> dict:
        return {
            "candidate_id": self.candidate_id,
            "name": self.name,
            "normalized_name": self.normalized_name,
            "description": self.description,
            "section": self.section,
            "raw_text": self.raw_text,
            "entity_type": self.entity_type,
            "confidence": round(self.confidence, 3),
            "decision": self.decision,
            "reasons": self.reasons,
            "status": self.status,
            "source": self.source,
            "first_appearance_chapter": self.first_appearance_chapter,
            "existing_character_id": self.existing_character_id,
            "matched_existing_name": self.matched_existing_name,
            "aliases": self.aliases,
            "selected": self.selected,
        }


def normalize_character_name(name: str) -> str:
    text = re.sub(r"[\s\u3000]+", "", name or "")
    text = text.strip(" -_*#|:：[]（）()【】<>《》\"'“”‘’，,。.!?;；·")
    text = re.sub(r"[（(][^)）]*?[暂待]?定[)）]$", "", text)
    text = re.sub(r"[（(][^)）]*?[建议|候选|AI|测试][)）]$", "", text)
    return text


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def _is_heading(line: str) -> tuple[int, str] | None:
    match = re.match(r"^(#{1,6})\s*(.+?)\s*$", line.strip())
    if not match:
        return None
    return len(match.group(1)), match.group(2).strip()


def _is_character_section(section: str) -> bool:
    return any(hint in section for hint in CHARACTER_SECTION_HINTS)


def _clean_heading_title(title: str) -> str:
    cleaned = normalize_character_name(title)
    cleaned = re.sub(r"^\d+[.、)\s-]*", "", cleaned)
    cleaned = cleaned.strip()
    return cleaned or title.strip()


def _parse_first_appearance(text: str) -> Optional[int]:
    patterns = (
        r"(?:首次登场|首次出现|预计登场|登场章节|出场章节|第)\s*(\d+)\s*章",
        r"第\s*(\d+)\s*章",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                continue
    return None


def _looks_like_candidate_name(name: str) -> bool:
    if not name:
        return False
    normalized = normalize_character_name(name)
    if len(normalized) < 2 or len(normalized) > 18:
        return False
    if re.search(r"[0-9`~!@#$%^&*+=<>?/\\]", normalized):
        return False
    if " " in normalized:
        return False
    return True


def _split_candidate_blocks(text: str) -> list[dict]:
    lines = (text or "").splitlines()
    candidates: list[dict] = []
    current_section = ""
    current_candidate: dict | None = None
    current_candidate_level = 99

    def flush_candidate():
        nonlocal current_candidate
        if not current_candidate:
            return
        current_candidate["raw_lines"] = [line for line in current_candidate["raw_lines"] if line is not None]
        current_candidate["raw_text"] = "\n".join(current_candidate["raw_lines"]).strip()
        candidates.append(current_candidate)
        current_candidate = None

    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            if current_candidate:
                current_candidate["raw_lines"].append("")
            continue

        heading = _is_heading(stripped)
        if heading:
            level, title = heading
            clean_title = _clean_heading_title(title)
            if level == 1:
                flush_candidate()
                current_section = clean_title
                current_candidate_level = 99
                continue

            if current_candidate and level <= current_candidate_level:
                flush_candidate()

            if _is_character_section(current_section) and level >= 2 and _looks_like_candidate_name(clean_title):
                current_candidate = {
                    "name": clean_title,
                    "section": current_section,
                    "heading_level": level,
                    "start_line": index,
                    "raw_lines": [stripped],
                }
                current_candidate_level = level
                continue

            if current_candidate:
                current_candidate["raw_lines"].append(stripped)
            continue

        if current_candidate:
            current_candidate["raw_lines"].append(stripped)
            continue

        if _is_character_section(current_section):
            bullet_match = re.match(r"^[\-*•]\s*(.+)$", stripped)
            if bullet_match:
                payload = bullet_match.group(1).strip()
                if not payload:
                    continue
                if any(payload.startswith(field + "：") or payload.startswith(field + ":") for field in PERSON_FIELD_HINTS):
                    continue
                name_part = re.split(r"[：:]", payload, maxsplit=1)[0].strip()
                name_part = _clean_heading_title(name_part)
                if _looks_like_candidate_name(name_part):
                    current_candidate = {
                        "name": name_part,
                        "section": current_section,
                        "heading_level": 2,
                        "start_line": index,
                        "raw_lines": [stripped],
                    }
                    current_candidate_level = 2
                    continue

    flush_candidate()
    return candidates


def _infer_entity_type(name: str, body_text: str) -> str:
    combined = f"{name}\n{body_text}"
    location_score = sum(1 for hint in LOCATION_HINTS if hint in combined)
    organization_score = sum(1 for hint in ORGANIZATION_HINTS if hint in combined)
    title_score = sum(1 for hint in TITLE_HINTS if hint in combined)
    event_score = sum(1 for hint in EVENT_HINTS if hint in combined)
    abstract_score = sum(1 for hint in ABSTRACT_HINTS if hint in combined)

    scores = {
        "place": location_score,
        "organization": organization_score,
        "title": title_score,
        "event": event_score,
        "abstract": abstract_score,
    }
    best_type = max(scores, key=scores.get)
    if scores[best_type] == 0:
        return "character"
    if best_type == "title" and len(normalize_character_name(name)) > 4:
        return "character"
    if best_type == "place" and any(ch in name for ch in ("人", "者", "君", "娘", "哥", "姐")):
        return "character"
    return best_type


def _score_candidate(
    name: str,
    section: str,
    body_text: str,
    entity_type: str,
    existing_names: set[str],
) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 0.15

    if _is_character_section(section):
        score += 0.25
        reasons.append("位于人物相关分区")

    if len(name) in {2, 3, 4} and re.search(r"[\u4e00-\u9fff]", name):
        score += 0.18
        reasons.append("名称长度和形态接近人物名")

    field_hits = sum(1 for hint in PERSON_FIELD_HINTS if hint in body_text)
    if field_hits:
        bonus = min(0.25, field_hits * 0.06)
        score += bonus
        reasons.append("包含人物属性字段")

    if re.search(r"[：:]\s*[^：:\n]{2,40}", body_text):
        score += 0.05

    lower_body = body_text.lower()
    if any(hint in body_text for hint in TITLE_HINTS):
        score -= 0.18
        reasons.append("包含称谓/头衔噪声")

    if any(hint in body_text for hint in LOCATION_HINTS):
        score -= 0.28
        reasons.append("存在地名特征")

    if any(hint in body_text for hint in ORGANIZATION_HINTS):
        score -= 0.32
        reasons.append("存在组织名特征")

    if any(hint in body_text for hint in EVENT_HINTS):
        score -= 0.22
        reasons.append("存在事件或标签噪声")

    if any(hint in body_text for hint in ABSTRACT_HINTS):
        score -= 0.15
        reasons.append("存在抽象概念噪声")

    if entity_type != "character":
        penalty_map = {
            "place": 0.35,
            "organization": 0.32,
            "title": 0.18,
            "event": 0.3,
            "abstract": 0.22,
        }
        score -= penalty_map.get(entity_type, 0.2)
        reasons.append(f"判定为{entity_type}")

    normalized_name = normalize_character_name(name)
    if normalized_name in existing_names:
        score -= 0.12
        reasons.append("与已有角色同名")

    if len(normalized_name) <= 1:
        score -= 0.3

    if re.search(r"\d", normalized_name):
        score -= 0.15

    if "角色" in normalized_name and len(normalized_name) <= 3:
        score -= 0.15

    if any(token in lower_body for token in ("地点", "位置", "城市", "村庄", "势力", "组织")):
        score -= 0.05

    score = max(0.0, min(1.0, score))
    if not reasons:
        reasons.append("基础人物结构匹配")
    return score, reasons


def _decision_for_candidate(entity_type: str, confidence: float, duplicate: bool) -> str:
    if entity_type != "character" and confidence < 0.7:
        return "reject"
    if confidence >= 0.72 and not duplicate:
        return "keep"
    if confidence >= 0.45 or duplicate:
        return "review"
    return "reject"


def _derive_status(section: str, confidence: float) -> str:
    if any(hint in section for hint in ("已出现", "出场", "现有")):
        return "appeared"
    if any(hint in section for hint in ("计划", "预备", "准备", "后续")):
        return "planned"
    if any(hint in section for hint in ("建议", "推荐", "补充")):
        return "suggested"
    return "appeared" if confidence >= 0.75 else "planned"


def _normalize_existing_names(existing_names: Iterable[str]) -> set[str]:
    return {normalize_character_name(name) for name in existing_names if normalize_character_name(name)}


def build_character_import_preview(
    state_text: str,
    existing_characters: Iterable[dict] | None = None,
) -> list[CharacterImportCandidate]:
    existing_characters = list(existing_characters or [])
    existing_name_map = {
        normalize_character_name(item.get("name", "")): item
        for item in existing_characters
        if normalize_character_name(item.get("name", ""))
    }

    preview: list[CharacterImportCandidate] = []
    blocks = _split_candidate_blocks(state_text)
    for block in blocks:
        name = _clean_heading_title(block.get("name", ""))
        normalized_name = normalize_character_name(name)
        if not normalized_name:
            continue
        body_text = _clean_text(block.get("raw_text", ""))
        section = _clean_text(block.get("section", ""))
        entity_type = _infer_entity_type(name, body_text)
        duplicate_row = existing_name_map.get(normalized_name)
        confidence, reasons = _score_candidate(
            name=name,
            section=section,
            body_text=body_text,
            entity_type=entity_type,
            existing_names=set(existing_name_map.keys()),
        )
        duplicate = duplicate_row is not None
        decision = _decision_for_candidate(entity_type, confidence, duplicate)
        candidate = CharacterImportCandidate(
            candidate_id=_candidate_id(name, section, body_text, block.get("start_line", 0)),
            name=name,
            normalized_name=normalized_name,
            description=_summarize_candidate_description(body_text),
            section=section,
            raw_text=body_text,
            entity_type=entity_type,
            confidence=confidence,
            decision=decision,
            reasons=reasons,
            status=_derive_status(section, confidence),
            source="ai",
            first_appearance_chapter=_parse_first_appearance(body_text),
            existing_character_id=duplicate_row.get("id") if duplicate_row else None,
            matched_existing_name=duplicate_row.get("name", "") if duplicate_row else "",
            aliases=_extract_aliases(body_text, name),
            selected=decision != "reject",
        )
        preview.append(candidate)

    merged = _merge_duplicate_candidates(preview)
    merged.sort(key=lambda item: (-item.confidence, item.decision, item.name))
    return merged


def _candidate_id(name: str, section: str, raw_text: str, start_line: int) -> str:
    payload = f"{normalize_character_name(name)}|{section}|{start_line}|{raw_text[:300]}"
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]


def _summarize_candidate_description(raw_text: str) -> str:
    lines = []
    for line in raw_text.splitlines():
        cleaned = line.strip().lstrip("-*•")
        if cleaned:
            lines.append(cleaned)
    summary = " ".join(lines)
    return summary[:800]


def _extract_aliases(raw_text: str, name: str) -> list[str]:
    aliases = []
    for pattern in (r"别名[:：]\s*([^\n，,;；]+)", r"昵称[:：]\s*([^\n，,;；]+)", r"外号[:：]\s*([^\n，,;；]+)"):
        for match in re.findall(pattern, raw_text):
            alias = normalize_character_name(match)
            if alias and alias != normalize_character_name(name) and alias not in aliases:
                aliases.append(alias)
    return aliases[:5]


def _merge_duplicate_candidates(candidates: list[CharacterImportCandidate]) -> list[CharacterImportCandidate]:
    merged: dict[str, CharacterImportCandidate] = {}
    for candidate in candidates:
        key = candidate.normalized_name
        if key not in merged:
            merged[key] = candidate
            continue
        existing = merged[key]
        if candidate.confidence > existing.confidence:
            existing.reasons = list(dict.fromkeys(existing.reasons + candidate.reasons))
            existing.raw_text = _merge_text(existing.raw_text, candidate.raw_text)
            existing.description = _merge_text(existing.description, candidate.description)
            existing.confidence = candidate.confidence
            existing.decision = candidate.decision
            existing.entity_type = candidate.entity_type
            existing.status = candidate.status
            existing.first_appearance_chapter = (
                candidate.first_appearance_chapter or existing.first_appearance_chapter
            )
            existing.existing_character_id = candidate.existing_character_id or existing.existing_character_id
            existing.matched_existing_name = candidate.matched_existing_name or existing.matched_existing_name
        else:
            existing.reasons = list(dict.fromkeys(existing.reasons + candidate.reasons))
            existing.raw_text = _merge_text(existing.raw_text, candidate.raw_text)
            existing.description = _merge_text(existing.description, candidate.description)
        for alias in candidate.aliases:
            if alias not in existing.aliases and alias != existing.name:
                existing.aliases.append(alias)
    return list(merged.values())


def _merge_text(left: str, right: str) -> str:
    pieces = []
    for text in (left, right):
        if text and text not in pieces:
            pieces.append(text)
    return "\n".join(pieces)[:1000]


def merge_character_description(existing_description: str, candidate_description: str) -> str:
    return _merge_text(existing_description.strip(), candidate_description.strip())


def preferred_character_status(existing_status: str, candidate_status: str) -> str:
    order = {"appeared": 3, "planned": 2, "suggested": 1, "draft": 0}
    if order.get(candidate_status, 0) > order.get(existing_status, 0):
        return candidate_status
    return existing_status or candidate_status

