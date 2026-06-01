# -*- coding: utf-8 -*-
import os
import logging
from novel_generator import prompts as prompt_definitions
from novel_generator.commercial_prompts import build_generation_context_block
from novel_generator.platform_guidance import get_platform_chapter_guidance
from chapter_directory_parser import get_chapter_info_from_blueprint
from novel_generator.task_manager import raise_if_cancelled, TaskCancelledError
from utils import read_file, save_string_to_txt
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
from novel_generator.knowledge_graph import KnowledgeGraphManager
import re

logger = logging.getLogger(__name__)


def get_or_generate_chapter_summary(ctx, chapter_num: int, task_id: str | None = None) -> str:
    """
    获取指定章节的微型摘要。
    如果存在 chapter_X_summary.txt 则直接读取，否则读取章节全文并调用 LLM 生成摘要并持久化。
    """
    def _check_cancel():
        if task_id:
            raise_if_cancelled(task_id)
        if ctx.cancel_token is not None:
            ctx.cancel_token.raise_if_set()
        return False

    chapters_dir = os.path.join(ctx.filepath, "chapters")
    summary_file = os.path.join(chapters_dir, f"chapter_{chapter_num}_summary.txt")
    if os.path.exists(summary_file):
        summary = read_file(summary_file).strip()
        if summary:
            return summary

    # 如果摘要不存在，尝试读取章节正文
    chapter_file = os.path.join(chapters_dir, f"chapter_{chapter_num}.txt")
    if not os.path.exists(chapter_file):
        return ""

    chapter_text = read_file(chapter_file).strip()
    if not chapter_text:
        return ""

    # 调用 LLM 生成单章微型摘要
    try:
        _check_cancel()
        llm = create_llm_adapter(
            interface_format=ctx.llm.interface_format,
            base_url=ctx.llm.base_url,
            model_name=ctx.llm.model_name,
            api_key=ctx.llm.api_key,
            temperature=0.3,
            max_tokens=ctx.llm.max_tokens,
            timeout=ctx.llm.timeout,
        )
        prompt_single_summary = prompt_definitions.get_prompt_template(ctx.project_id, 'single_chapter_summary_prompt').format(
            chapter_text=chapter_text
        )
        summary = invoke_with_cleaning(llm, prompt_single_summary, cancel_check=_check_cancel)
        if not summary.strip():
            summary = chapter_text[:250]
        else:
            summary = summary.strip()
        save_string_to_txt(summary, summary_file)
        return summary
    except Exception as e:
        logger.error(f"Error generating single chapter summary for chapter {chapter_num}: {e}", exc_info=True)
        return chapter_text[:250]



def build_chapter_prompt(
    ctx,      # GenerationContext
    params,   # ChapterParams
    task_id: str | None = None,
    gen_ctx_data: dict = None,
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
    core_summary_text = read_file(os.path.join(filepath, "core_summary.txt")).strip()
    global_summary_text = read_file(os.path.join(filepath, "global_summary.txt")).strip() or "（尚未生成全局摘要）"
    if core_summary_text:
        global_summary_text = core_summary_text + "\n\n---\n\n【近期剧情摘要】\n" + global_summary_text
    character_state_text = read_file(os.path.join(filepath, "character_state.txt")).strip() or "（尚未生成角色状态）"
    plot_arcs_text = read_file(os.path.join(filepath, "plot_arcs.txt")).strip() or "（尚未生成伏笔暗线台账）"

    # 从蓝图解析章节信息
    chapter_info = get_chapter_info_from_blueprint(blueprint_text, novel_number)
    next_chapter_info = get_chapter_info_from_blueprint(blueprint_text, novel_number + 1)

    chapters_dir = os.path.join(filepath, "chapters")
    os.makedirs(chapters_dir, exist_ok=True)

    # 从大纲中抽取即将出场的实体 (简单的分词)
    graph_manager = KnowledgeGraphManager(filepath)
    # 将角色、道具和简述作为潜在实体去匹配图谱
    potential_entities_text = (
        getattr(params, "characters_involved", "") + " " + 
        getattr(params, "key_items", "") + " " + 
        chapter_info.get("chapter_summary", "")
    )
    # 提取所有可能的实体词汇（连续中文字符）
    words = set(re.findall(r'[\u4e00-\u9fa5]+', potential_entities_text))
    # 过滤出存在于图谱中的实体
    matched_entities = [w for w in words if graph_manager.graph.has_node(w)]
    graph_context = graph_manager.get_subgraph_context(matched_entities, max_depth=1) if matched_entities else "（未匹配到相关图谱记忆）"

    # 第一章特殊处理
    if novel_number == 1:
        _check_cancel()
        if gen_ctx_data and gen_ctx_data.get("has_memory_state"):
            gctx = gen_ctx_data.get("context", {})
            return prompt_definitions.get_prompt_template(ctx.project_id, 'first_chapter_draft_prompt_memory_aware').format(
                novel_number=novel_number,
                word_number=params.word_number,
                chapter_title=chapter_info["chapter_title"],
                chapter_role=chapter_info["chapter_role"],
                chapter_purpose=chapter_info["chapter_purpose"],
                suspense_level=chapter_info["suspense_level"],
                foreshadowing=chapter_info["foreshadowing"],
                plot_twist_level=chapter_info["plot_twist_level"],
                chapter_summary=chapter_info["chapter_summary"],
                user_guidance=params.user_guidance,
                forbidden_violations="\n".join(gctx.get("forbidden_violations", [])),
                locked_previous_facts="\n".join(gctx.get("locked_previous_facts", [])),
                character_state_brief=gctx.get("character_state_brief", ""),
                name_usage_rules_brief=gctx.get("name_usage_rules_brief", ""),
                plot_threads_brief=gctx.get("plot_threads_brief", ""),
                global_summary=gctx.get("global_summary", "")
            )
        else:
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
                graph_context=graph_context,
                platform_guidance=platform_guidance,
            )

    # ── 组装滑动前文摘要 ──
    # 获取前文微摘要列表：第 N-3, N-2, N-1 章的摘要
    summaries = []
    start_chap = max(1, novel_number - 3)
    for c in range(start_chap, novel_number):
        c_summary = get_or_generate_chapter_summary(ctx, c, task_id=task_id)
        if c_summary:
            summaries.append(f"第 {c} 章剧情摘要：\n{c_summary}")
    
    if summaries:
        short_summary = "\n\n".join(summaries)
    else:
        short_summary = "（无前文剧情摘要）"

    # 前一章全文正文部分（保留最近一章正文最后 3000 字作为前文承接）
    previous_excerpt = ""
    if novel_number > 1:
        prev_file = os.path.join(chapters_dir, f"chapter_{novel_number-1}.txt")
        if os.path.exists(prev_file):
            prev_text = read_file(prev_file).strip()
            if prev_text:
                previous_excerpt = prev_text[-3000:] if len(prev_text) > 3000 else prev_text


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
                    context = get_relevant_context_from_vector_store(emb, group, filepath, k=actual_k, current_chapter_number=novel_number)
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
    if gen_ctx_data and gen_ctx_data.get("has_memory_state"):
        gctx = gen_ctx_data.get("context", {})
        return prompt_definitions.get_prompt_template(ctx.project_id, 'next_chapter_draft_prompt_memory_aware').format(
            novel_number=novel_number,
            word_number=params.word_number,
            chapter_title=chapter_info["chapter_title"],
            chapter_role=chapter_info["chapter_role"],
            chapter_purpose=chapter_info["chapter_purpose"],
            suspense_level=chapter_info["suspense_level"],
            foreshadowing=chapter_info["foreshadowing"],
            plot_twist_level=chapter_info["plot_twist_level"],
            chapter_summary=chapter_info["chapter_summary"],
            user_guidance=params.user_guidance or "无特殊指导",
            forbidden_violations="\n".join(gctx.get("forbidden_violations", [])),
            locked_previous_facts="\n".join(gctx.get("locked_previous_facts", [])),
            character_state_brief=gctx.get("character_state_brief", ""),
            name_usage_rules_brief=gctx.get("name_usage_rules_brief", ""),
            plot_threads_brief=gctx.get("plot_threads_brief", ""),
            global_summary=gctx.get("global_summary", ""),
            previous_chapter_excerpt=previous_excerpt,
        )
    else:
        return prompt_definitions.get_prompt_template(ctx.project_id, 'next_chapter_draft_prompt').format(
            user_guidance=params.user_guidance or "无特殊指导",
            global_summary=global_summary_text,
            previous_chapter_excerpt=previous_excerpt,
            character_state=character_state_text,
            plot_arcs=plot_arcs_text or "（尚未生成伏笔暗线台账，请优先遵守章节目录中的伏笔操作）",
            graph_context=graph_context,
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


