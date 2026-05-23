# -*- coding: utf-8 -*-
import os
import logging
from novel_generator import prompts as prompt_definitions
from novel_generator.commercial_prompts import build_generation_context_block
from novel_generator.platform_guidance import get_platform_chapter_guidance
from chapter_directory_parser import get_chapter_info_from_blueprint
from novel_generator.task_manager import raise_if_cancelled, TaskCancelledError
from utils import read_file
from novel_generator.vectorstore_utils import (
    get_relevant_context_from_vector_store,
    load_vector_store,
)
from novel_generator.chapter_pipeline.context_retriever import (
    get_last_n_chapters_text,
    summarize_recent_chapters,
    parse_search_keywords,
    apply_content_rules,
    get_filtered_knowledge_context
)
from novel_generator.common import invoke_with_cleaning
from backend.app.services.model_runtime import create_chat_adapter_from_config as create_llm_adapter

logger = logging.getLogger(__name__)


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
    platform_guidance = prompt_definitions.get_prompt_template(ctx.project_id, 'platform_chapter_guidance_prompt').format(
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
        return prompt_definitions.get_prompt_template(ctx.project_id, 'first_chapter_draft_prompt').format(
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

        search_prompt = prompt_definitions.get_prompt_template(ctx.project_id, 'knowledge_search_prompt').format(
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
    return prompt_definitions.get_prompt_template(ctx.project_id, 'next_chapter_draft_prompt').format(
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


