# -*- coding: utf-8 -*-
"""
章节草稿生成及历史章节文本获取、知识库检索等。

重构要点：
- build_chapter_prompt / generate_chapter_draft 接受 GenerationContext + ChapterParams
- 移除 config_manager.IS_ENGLISH 依赖
"""
import os
import json
import logging
import re
from llm_adapters import create_llm_adapter
import prompt_definitions
from chapter_directory_parser import get_chapter_info_from_blueprint
from novel_generator.common import invoke_with_cleaning
from novel_generator.task_manager import TaskCancelledError, raise_if_cancelled
from utils import read_file, clear_file_content, save_string_to_txt
from novel_generator.vectorstore_utils import (
    get_relevant_context_from_vector_store,
    load_vector_store,
)

logger = logging.getLogger(__name__)


# ── 历史章节文本 ──

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


# ── 章节摘要生成 ──

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


# ── 解析 & 规则 ──

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


# ── 知识过滤 ──

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


# ── 构建章节提示词 ──

def build_chapter_prompt(
    ctx,      # GenerationContext
    params,   # ChapterParams
    task_id: str | None = None,
) -> str:
    """
    构造当前章节的请求提示词。
    ctx   : GenerationContext (llm + embedding + filepath)
    params: ChapterParams (章节号、标题、角色、道具、场景等)
    """
    def _check_cancel():
        if task_id:
            raise_if_cancelled(task_id)
        return False

    filepath = ctx.filepath
    novel_number = params.chapter_number

    # 读取基础文件
    _check_cancel()
    arch_text = read_file(os.path.join(filepath, "Novel_architecture.txt")).strip() or "（尚未生成小说架构）"
    blueprint_text = read_file(os.path.join(filepath, "Novel_directory.txt")).strip() or "（尚未生成章节目录）"
    global_summary_text = read_file(os.path.join(filepath, "global_summary.txt")).strip() or "（尚未生成全局摘要）"
    character_state_text = read_file(os.path.join(filepath, "character_state.txt")).strip() or "（尚未生成角色状态）"
    plot_arcs_text = read_file(os.path.join(filepath, "plot_arcs.txt")).strip() or "（尚未生成伏笔暗线台账）"

    # 从蓝图解析章节信息
    chapter_info = get_chapter_info_from_blueprint(blueprint_text, novel_number)
    next_chapter_info = get_chapter_info_from_blueprint(blueprint_text, novel_number + 1)

    chapters_dir = os.path.join(filepath, "chapters")
    os.makedirs(chapters_dir, exist_ok=True)

    # 第一章特殊处理
    if novel_number == 1:
        _check_cancel()
        return prompt_definitions.first_chapter_draft_prompt.format(
            novel_number=novel_number,
            word_number=params.word_number,
            chapter_title=chapter_info["chapter_title"],
            chapter_role=chapter_info["chapter_role"],
            chapter_purpose=chapter_info["chapter_purpose"],
            suspense_level=chapter_info["suspense_level"],
            foreshadowing=chapter_info["foreshadowing"],
            plot_twist_level=chapter_info["plot_twist_level"],
            chapter_summary=chapter_info["chapter_summary"],
            characters_involved=params.characters_involved,
            key_items=params.key_items,
            scene_location=params.scene_location,
            time_constraint=params.time_constraint,
            user_guidance=params.user_guidance,
            novel_setting=arch_text,
            plot_arcs=plot_arcs_text or "（尚未生成伏笔暗线台账，请优先遵守章节目录中的伏笔操作）",
        )

    # 获取前文摘要
    recent_texts = get_last_n_chapters_text(chapters_dir, novel_number, n=3)
    try:
        short_summary = summarize_recent_chapters(
            ctx, recent_texts, chapter_info, next_chapter_info, task_id=task_id
        )
    except Exception:
        logger.error("Error in summarize_recent_chapters", exc_info=True)
        short_summary = "（摘要生成失败）"

    # 前一章结尾
    previous_excerpt = ""
    for text in reversed(recent_texts):
        if text.strip():
            previous_excerpt = text[-800:] if len(text) > 800 else text
            break

    # ── 知识库检索 ──
    try:
        _check_cancel()
        llm = create_llm_adapter(
            interface_format=ctx.llm.interface_format,
            base_url=ctx.llm.base_url,
            model_name=ctx.llm.model_name,
            api_key=ctx.llm.api_key,
            temperature=0.3, max_tokens=ctx.llm.max_tokens, timeout=ctx.llm.timeout,
        )

        search_prompt = prompt_definitions.knowledge_search_prompt.format(
            chapter_number=novel_number,
            chapter_title=chapter_info["chapter_title"],
            characters_involved=params.characters_involved,
            key_items=params.key_items,
            scene_location=params.scene_location,
            chapter_role=chapter_info["chapter_role"],
            chapter_purpose=chapter_info["chapter_purpose"],
            foreshadowing=chapter_info["foreshadowing"],
            short_summary=short_summary,
            user_guidance=params.user_guidance,
            time_constraint=params.time_constraint,
        )
        search_response = invoke_with_cleaning(llm, search_prompt, cancel_check=_check_cancel)
        keyword_groups = parse_search_keywords(search_response)

        filtered_context = "（知识库处理失败）"
        if ctx.embedding.api_key:
            from embedding_adapters import create_embedding_adapter
            emb = create_embedding_adapter(
                ctx.embedding.interface_format,
                ctx.embedding.api_key,
                ctx.embedding.base_url,
                ctx.embedding.model_name,
            )
            store = load_vector_store(emb, filepath)
            if store:
                collection_size = store._collection.count()
                actual_k = min(ctx.embedding.retrieval_k, max(1, collection_size))
                all_contexts = []
                for group in keyword_groups:
                    _check_cancel()
                    context = get_relevant_context_from_vector_store(emb, group, filepath, k=actual_k)
                    if context:
                        if any(kw in group.lower() for kw in ["技法", "手法", "模板"]):
                            all_contexts.append(f"[TECHNIQUE] {context}")
                        elif any(kw in group.lower() for kw in ["设定", "技术", "世界观"]):
                            all_contexts.append(f"[SETTING] {context}")
                        else:
                            all_contexts.append(f"[GENERAL] {context}")

                processed = apply_content_rules(all_contexts, novel_number)
                chapter_info_for_filter = {
                    "chapter_number": novel_number,
                    "chapter_title": chapter_info["chapter_title"],
                    "chapter_role": chapter_info["chapter_role"],
                    "chapter_purpose": chapter_info["chapter_purpose"],
                    "characters_involved": params.characters_involved,
                    "key_items": params.key_items,
                    "scene_location": params.scene_location,
                    "foreshadowing": chapter_info["foreshadowing"],
                    "suspense_level": chapter_info["suspense_level"],
                    "plot_twist_level": chapter_info["plot_twist_level"],
                    "chapter_summary": chapter_info["chapter_summary"],
                    "time_constraint": params.time_constraint,
                }
                filtered_context = get_filtered_knowledge_context(ctx, chapter_info_for_filter, processed, task_id=task_id)
    except TaskCancelledError:
        raise
    except Exception:
        logger.error("知识处理流程异常", exc_info=True)
        filtered_context = "（知识库处理失败）"

    _check_cancel()
    return prompt_definitions.next_chapter_draft_prompt.format(
        user_guidance=params.user_guidance or "无特殊指导",
        global_summary=global_summary_text,
        previous_chapter_excerpt=previous_excerpt,
        character_state=character_state_text,
        plot_arcs=plot_arcs_text or "（尚未生成伏笔暗线台账，请优先遵守章节目录中的伏笔操作）",
        short_summary=short_summary,
        novel_number=novel_number,
        chapter_title=chapter_info["chapter_title"],
        chapter_role=chapter_info["chapter_role"],
        chapter_purpose=chapter_info["chapter_purpose"],
        suspense_level=chapter_info["suspense_level"],
        foreshadowing=chapter_info["foreshadowing"],
        plot_twist_level=chapter_info["plot_twist_level"],
        chapter_summary=chapter_info["chapter_summary"],
        word_number=params.word_number,
        characters_involved=params.characters_involved,
        key_items=params.key_items,
        scene_location=params.scene_location,
        time_constraint=params.time_constraint,
        next_chapter_number=novel_number + 1,
        next_chapter_title=next_chapter_info.get("chapter_title", "（未命名）"),
        next_chapter_role=next_chapter_info.get("chapter_role", "过渡章节"),
        next_chapter_purpose=next_chapter_info.get("chapter_purpose", "承上启下"),
        next_chapter_suspense_level=next_chapter_info.get("suspense_level", "中等"),
        next_chapter_foreshadowing=next_chapter_info.get("foreshadowing", "无特殊伏笔"),
        next_chapter_plot_twist_level=next_chapter_info.get("plot_twist_level", "★☆☆☆☆"),
        next_chapter_summary=next_chapter_info.get("chapter_summary", "衔接过渡内容"),
        filtered_context=filtered_context,
    )


# ── 生成章节草稿 ──

def generate_chapter_draft(
    ctx,                  # GenerationContext
    params,               # ChapterParams
    custom_prompt_text: str = None,
    task_id: str | None = None,
) -> str:
    """
    生成章节草稿，支持自定义提示词。

    ctx    : GenerationContext (llm + embedding + filepath)
    params : ChapterParams (章节参数)
    """
    if custom_prompt_text is None:
        prompt_text = build_chapter_prompt(ctx, params, task_id=task_id)
    else:
        prompt_text = custom_prompt_text

    if task_id:
        raise_if_cancelled(task_id)
    chapters_dir = os.path.join(ctx.filepath, "chapters")
    os.makedirs(chapters_dir, exist_ok=True)

    llm = create_llm_adapter(
        interface_format=ctx.llm.interface_format,
        base_url=ctx.llm.base_url,
        model_name=ctx.llm.model_name,
        api_key=ctx.llm.api_key,
        temperature=ctx.llm.temperature,
        max_tokens=ctx.llm.max_tokens,
        timeout=ctx.llm.timeout,
    )

    def _check_cancel():
        if task_id:
            raise_if_cancelled(task_id)
        return False

    chapter_content = invoke_with_cleaning(llm, prompt_text, cancel_check=_check_cancel)
    if task_id:
        raise_if_cancelled(task_id)
    if not chapter_content.strip():
        logger.warning("Generated chapter draft is empty.")
        raise RuntimeError("章节草稿生成为空")

    chapter_file = os.path.join(chapters_dir, f"chapter_{params.chapter_number}.txt")
    clear_file_content(chapter_file)
    save_string_to_txt(chapter_content, chapter_file)
    logger.info(f"[Draft] Chapter {params.chapter_number} generated as a draft.")
    return chapter_content
