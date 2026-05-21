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
from backend.app.services.model_runtime import create_chat_adapter_from_config as create_llm_adapter, _provider_to_interface
import prompt_definitions
from novel_generator.commercial_prompts import build_generation_context_block
from novel_generator.platform_guidance import get_platform_chapter_guidance
from chapter_directory_parser import get_chapter_info_from_blueprint
from novel_generator.common import invoke_with_cleaning
from backend.app.services.model_runtime import get_runtime_config
from novel_generator.task_manager import TaskCancelledError, raise_if_cancelled
from utils import read_file, clear_file_content, save_string_to_txt
from novel_generator.vectorstore_utils import (
    get_relevant_context_from_vector_store,
    load_vector_store,
)

logger = logging.getLogger(__name__)


def create_specialized_chat_adapter(ctx, purpose: str):
    if not ctx.project_id or not ctx.user_id:
        return create_llm_adapter(
            interface_format=ctx.llm.interface_format,
            base_url=ctx.llm.base_url,
            model_name=ctx.llm.model_name,
            api_key=ctx.llm.api_key,
            temperature=ctx.llm.temperature,
            max_tokens=ctx.llm.max_tokens,
            timeout=ctx.llm.timeout,
            cancel_token=ctx.cancel_token,
        )

    try:
        runtime = get_runtime_config(ctx.user_id, purpose, ctx.project_id)
    except Exception:
        runtime = None

    if runtime is None:
        return create_llm_adapter(
            interface_format=ctx.llm.interface_format,
            base_url=ctx.llm.base_url,
            model_name=ctx.llm.model_name,
            api_key=ctx.llm.api_key,
            temperature=ctx.llm.temperature,
            max_tokens=ctx.llm.max_tokens,
            timeout=ctx.llm.timeout,
            cancel_token=ctx.cancel_token,
        )

    return create_llm_adapter(
        interface_format=_provider_to_interface(runtime.provider),
        base_url=runtime.base_url,
        model_name=runtime.model,
        api_key=runtime.api_key,
        temperature=runtime.temperature or ctx.llm.temperature,
        max_tokens=runtime.max_tokens or ctx.llm.max_tokens,
        timeout=runtime.timeout or ctx.llm.timeout,
        cancel_token=ctx.cancel_token,
    )


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
    try:
        json_start = result.find("{")
        json_end = result.rfind("}") + 1
        if json_start != -1 and json_end > json_start:
            return json.loads(result[json_start:json_end])
    except Exception:
        logger.warning("Failed to parse opening analysis", exc_info=True)
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
    try:
        json_start = result.find("{")
        json_end = result.rfind("}") + 1
        if json_start != -1 and json_end > json_start:
            return json.loads(result[json_start:json_end])
    except Exception:
        logger.warning("Failed to parse ending analysis", exc_info=True)
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
    try:
        json_start = result.find("{")
        json_end = result.rfind("}") + 1
        if json_start != -1 and json_end > json_start:
            return json.loads(result[json_start:json_end])
    except Exception:
        logger.warning("Failed to parse mid-section analysis", exc_info=True)
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
    try:
        json_start = result.find("{")
        json_end = result.rfind("}") + 1
        if json_start != -1 and json_end > json_start:
            return json.loads(result[json_start:json_end])
    except Exception:
        logger.warning("Failed to parse dialogue analysis", exc_info=True)
    return {"score": 0, "issues": ["无法解析人物话语质检结果"], "suggestion": result[:120]}


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

    prompt = prompt_definitions.chapter_quality_rewrite_prompt.format(
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

    prompt = prompt_definitions.de_ai_style_revision_prompt.format(
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
    platform_label, platform_rules = get_platform_chapter_guidance(getattr(params, "platform", "tomato"))
    platform_guidance = prompt_definitions.platform_chapter_guidance_prompt.format(
        platform_label=platform_label,
        platform_rules=platform_rules,
    )
    commercial_guidance = build_generation_context_block(
        platform=getattr(params, "platform", "tomato"),
        trend_key=getattr(params, "trend_key", ""),
        custom_trend=getattr(params, "custom_trend", ""),
        forbidden=getattr(params, "forbidden", ""),
        reader_direction=getattr(params, "reader_direction", ""),
    )
    if getattr(params, "trend_translation", ""):
        commercial_guidance += "\n用户指定热点转译方式：" + getattr(params, "trend_translation", "")
    if getattr(params, "style_requirement", ""):
        commercial_guidance += "\n文风要求：" + getattr(params, "style_requirement", "")
    if getattr(params, "target_reader", ""):
        commercial_guidance += "\n目标读者：" + getattr(params, "target_reader", "")
    platform_guidance = f"{commercial_guidance}\n\n{platform_guidance}"

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
            platform_guidance=platform_guidance,
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
            from backend.app.services.model_runtime import create_embedding_adapter_from_config
            emb = create_embedding_adapter_from_config(
                interface_format=ctx.embedding.interface_format,
                api_key=ctx.embedding.api_key,
                base_url=ctx.embedding.base_url,
                model_name=ctx.embedding.model_name,
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
        platform_guidance=platform_guidance,
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
    emitter = None,
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
        cancel_token=ctx.cancel_token,
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

    blueprint_text = read_file(os.path.join(ctx.filepath, "Novel_directory.txt")).strip() or ""
    chapter_info = get_chapter_info_from_blueprint(blueprint_text, params.chapter_number)

    if emitter is not None:
        emitter.emit("progress", {"step": "voice_polish", "status": "running", "message": f"正在优化第 {params.chapter_number} 章文风..."})
    chapter_content = revise_chapter_voice(ctx, params, chapter_info, chapter_content, task_id=task_id)
    if emitter is not None:
        emitter.emit("progress", {"step": "voice_polish", "status": "done", "message": "文风优化完成"})

    if emitter is not None:
        emitter.emit("progress", {"step": "quality_check", "status": "running", "message": "正在执行平台质检..."})
    opening_feedback = analyze_opening_hook(ctx, chapter_content, task_id=task_id)
    ending_feedback = analyze_ending_hook(ctx, chapter_content, task_id=task_id)
    mid_feedback = analyze_mid_section_quality(ctx, chapter_content, task_id=task_id)
    dialogue_feedback = analyze_dialogue_voice(ctx, chapter_content, task_id=task_id)

    opening_score = int(opening_feedback.get("score", 0) or 0)
    mid_score = int(mid_feedback.get("score", 0) or 0)
    dialogue_score = int(dialogue_feedback.get("score", 0) or 0)
    has_hook = bool(ending_feedback.get("has_hook", False))

    if opening_score < 8 or mid_score < 7 or dialogue_score < 7 or not has_hook:
        if emitter is not None:
            emitter.emit("progress", {"step": "quality_rewrite", "status": "running", "message": "平台质检未达标，正在自动返修..."})
        chapter_content = rewrite_chapter_by_quality_feedback(
            ctx,
            params,
            chapter_info,
            chapter_content,
            opening_feedback,
            ending_feedback,
            mid_feedback,
            dialogue_feedback,
            task_id=task_id,
        )
        if emitter is not None:
            emitter.emit("progress", {"step": "quality_rewrite", "status": "done", "message": "自动返修完成"})

    if emitter is not None:
        emitter.emit("progress", {"step": "quality_check", "status": "done", "message": "平台质检完成"})

    chapter_file = os.path.join(chapters_dir, f"chapter_{params.chapter_number}.txt")
    clear_file_content(chapter_file)
    save_string_to_txt(chapter_content, chapter_file)
    logger.info(f"[Draft] Chapter {params.chapter_number} generated as a draft.")
    return chapter_content
