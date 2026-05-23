# -*- coding: utf-8 -*-
import os
import re
import logging
from backend.app.services.model_runtime import create_chat_adapter_from_config as create_llm_adapter
from novel_generator import prompts as prompt_definitions
from novel_generator.common import invoke_with_cleaning
from novel_generator.task_manager import raise_if_cancelled, TaskCancelledError
from utils import read_file

logger = logging.getLogger(__name__)


def get_last_n_chapters_text(chapters_dir: str, current_chapter_num: int, n: int = 3) -> list:
    texts = []
    start_chap = max(1, current_chapter_num - n)
    for c in range(start_chap, current_chapter_num):
        chap_file = os.path.join(chapters_dir, f"chapter_{c}.txt")
        if os.path.exists(chap_file):
            texts.append(read_file(chap_file).strip())
        else:
            texts.append("")
    return texts


def extract_summary_from_response(response_text: str) -> str:
    if not response_text:
        return ""
    markers = [
        "Current Chapter Summary:", "Summary:",
        "当前章节摘要:", "章节摘要:", "摘要:", "本章摘要:"
    ]
    for marker in markers:
        if marker in response_text:
            parts = response_text.split(marker, 1)
            if len(parts) > 1:
                return parts[1].strip()
    return response_text.strip()


def summarize_recent_chapters(
    ctx,              # GenerationContext
    chapters_text_list: list,
    chapter_info: dict,
    next_chapter_info: dict,
    task_id: str | None = None,
) -> str:
    try:
        def _check_cancel():
            if task_id:
                raise_if_cancelled(task_id)
            if ctx.cancel_token is not None:
                ctx.cancel_token.raise_if_set()
            return False

        _check_cancel()
        combined_text = "\n".join(chapters_text_list).strip()
        if not combined_text:
            return ""

        max_combined_length = 4000
        if len(combined_text) > max_combined_length:
            combined_text = combined_text[-max_combined_length:]

        llm = create_llm_adapter(
            interface_format=ctx.llm.interface_format,
            base_url=ctx.llm.base_url,
            model_name=ctx.llm.model_name,
            api_key=ctx.llm.api_key,
            temperature=ctx.llm.temperature,
            max_tokens=ctx.llm.max_tokens,
            timeout=ctx.llm.timeout,
            cancel_token=ctx.cancel_token,
        )

        chapter_info = chapter_info or {}
        next_chapter_info = next_chapter_info or {}

        prompt = prompt_definitions.summarize_recent_chapters_prompt.format(
            combined_text=combined_text,
            novel_number=chapter_info.get("chapter_number", 0),
            chapter_title=chapter_info.get("chapter_title", "未命名"),
            chapter_role=chapter_info.get("chapter_role", "常规章节"),
            chapter_purpose=chapter_info.get("chapter_purpose", "内容推进"),
            suspense_level=chapter_info.get("suspense_level", "中等"),
            foreshadowing=chapter_info.get("foreshadowing", "无"),
            plot_twist_level=chapter_info.get("plot_twist_level", "★☆☆☆☆"),
            chapter_summary=chapter_info.get("chapter_summary", ""),
            next_chapter_number=chapter_info.get("chapter_number", 0) + 1,
            next_chapter_title=next_chapter_info.get("chapter_title", "（未命名）"),
            next_chapter_role=next_chapter_info.get("chapter_role", "过渡章节"),
            next_chapter_purpose=next_chapter_info.get("chapter_purpose", "承上启下"),
            next_chapter_summary=next_chapter_info.get("chapter_summary", "衔接过渡内容"),
            next_chapter_suspense_level=next_chapter_info.get("suspense_level", "中等"),
            next_chapter_foreshadowing=next_chapter_info.get("foreshadowing", "无特殊伏笔"),
            next_chapter_plot_twist_level=next_chapter_info.get("plot_twist_level", "★☆☆☆☆"),
        )

        response_text = invoke_with_cleaning(llm, prompt, cancel_check=_check_cancel)
        summary = extract_summary_from_response(response_text)
        if not summary:
            logger.warning("Failed to extract summary, using full response")
            return response_text[:2000]
        return summary[:2000]
    except TaskCancelledError:
        raise
    except Exception:
        logger.error("Error in summarize_recent_chapters", exc_info=True)
        return ""


def parse_search_keywords(response_text: str) -> list:
    return [
        line.strip().replace('·', ' ')
        for line in response_text.strip().split('\n')
        if '·' in line
    ][:5]


def apply_content_rules(texts: list, novel_number: int) -> list:
    processed = []
    for text in texts:
        if re.search(r'第[\d]+章', text) or re.search(r'chapter_[\d]+', text):
            chap_nums = list(map(int, re.findall(r'\d+', text)))
            recent_chap = max(chap_nums) if chap_nums else 0
            time_distance = novel_number - recent_chap
            if time_distance <= 2:
                processed.append(f"[SKIP] 跳过近章内容：{text[:120]}...")
            elif 3 <= time_distance <= 5:
                processed.append(f"[MOD40%] {text}（需修改≥40%）")
            else:
                processed.append(f"[OK] {text}（可引用核心）")
        else:
            processed.append(f"[PRIOR] {text}（优先使用）")
    return processed


def apply_knowledge_rules(contexts: list, chapter_num: int) -> list:
    processed = []
    for text in contexts:
        if "第" in text and "章" in text:
            chap_nums = [int(s) for s in text.split() if s.isdigit()]
            recent_chap = max(chap_nums) if chap_nums else 0
            time_distance = chapter_num - recent_chap
            if time_distance <= 3:
                processed.append(f"[历史章节限制] 跳过近期内容: {text[:50]}...")
                continue
            processed.append(f"[历史参考] {text} (需进行30%以上改写)")
        else:
            processed.append(f"[外部知识] {text}")
    return processed


def get_filtered_knowledge_context(
    ctx,                # GenerationContext
    chapter_info: dict,
    retrieved_texts: list,
    task_id: str | None = None,
) -> str:
    if not retrieved_texts:
        return "（无相关知识库内容）"

    try:
        def _check_cancel():
            if task_id:
                raise_if_cancelled(task_id)
            if ctx.cancel_token is not None:
                ctx.cancel_token.raise_if_set()
            return False

        _check_cancel()
        processed_texts = apply_knowledge_rules(retrieved_texts, chapter_info.get('chapter_number', 0))

        llm = create_llm_adapter(
            interface_format=ctx.llm.interface_format,
            base_url=ctx.llm.base_url,
            model_name=ctx.llm.model_name,
            api_key=ctx.llm.api_key,
            temperature=0.3,
            max_tokens=ctx.llm.max_tokens,
            timeout=ctx.llm.timeout,
        )

        formatted_texts = []
        max_text_length = 600
        for i, text in enumerate(processed_texts, 1):
            if len(text) > max_text_length:
                text = text[:max_text_length] + "..."
            formatted_texts.append(f"[预处理结果{i}]\n{text}")

        formatted_chapter_info = (
            f"当前章节定位：{chapter_info.get('chapter_role', '')}\n"
            f"核心目标：{chapter_info.get('chapter_purpose', '')}\n"
            f"关键要素：{chapter_info.get('characters_involved', '')} | "
            f"{chapter_info.get('key_items', '')} | "
            f"{chapter_info.get('scene_location', '')}"
        )

        prompt = prompt_definitions.knowledge_filter_prompt.format(
            chapter_info=formatted_chapter_info,
            retrieved_texts="\n\n".join(formatted_texts) if formatted_texts else "（无检索结果）"
        )

        filtered_content = invoke_with_cleaning(llm, prompt, cancel_check=_check_cancel)
        return filtered_content if filtered_content else "（知识内容过滤失败）"
    except TaskCancelledError:
        raise
    except Exception:
        logger.error("Error in knowledge filtering", exc_info=True)
        return "（内容过滤过程出错）"


