# -*- coding: utf-8 -*-
"""
章节草稿生成模块 (Orchestrator)
现在作为一个协调器，按顺序调用 chapter_pipeline 中的各个步骤。
"""
import os
import logging
from chapter_directory_parser import get_chapter_info_from_blueprint
from novel_generator.common import invoke_with_cleaning
from backend.app.services.model_runtime import create_chat_adapter_from_config as create_llm_adapter
from novel_generator.task_manager import raise_if_cancelled
from utils import read_file, clear_file_content, save_string_to_txt, get_word_count

# 导入管道模块
from novel_generator.chapter_pipeline import build_chapter_prompt
from novel_generator.chapter_pipeline.context_retriever import (
    get_last_n_chapters_text,
    summarize_recent_chapters,
    get_filtered_knowledge_context,
)
from novel_generator.chapter_pipeline.revision import revise_chapter_voice, rewrite_chapter_by_quality_feedback
from novel_generator.chapter_pipeline.quality_checker import analyze_chapter_quality

logger = logging.getLogger(__name__)

def generate_chapter_draft(
    ctx,                  # GenerationContext
    params,               # ChapterParams
    custom_prompt_text: str = None,
    emitter = None,
    task_id: str | None = None,
    start_step: str | None = None,
    enable_brainstorming: bool = False,
) -> str:
    """
    生成章节草稿，支持自定义提示词。
    """
    if task_id:
        raise_if_cancelled(task_id)

    # --- 1. 构建提示词 ---
    if custom_prompt_text is None:
        if enable_brainstorming and (not start_step or start_step == "drafting"):
            from novel_generator.chapter_pipeline.brainstorm import run_multi_agent_brainstorming

            core_summary_text = read_file(os.path.join(ctx.filepath, "core_summary.txt")).strip()
            global_summary_text = read_file(os.path.join(ctx.filepath, "global_summary.txt")).strip() or "（尚未生成全局摘要）"
            if core_summary_text:
                global_summary_text = core_summary_text + "\n\n---\n\n【近期剧情摘要】\n" + global_summary_text
            blueprint_text = read_file(os.path.join(ctx.filepath, "Novel_directory.txt")).strip() or "（尚未生成章节目录）"
            chapter_info = get_chapter_info_from_blueprint(blueprint_text, params.chapter_number)

            def _cancel_check():
                if task_id:
                    raise_if_cancelled(task_id)

            director_guidance = run_multi_agent_brainstorming(
                ctx,
                global_summary=global_summary_text,
                chapter_info=chapter_info,
                task_id=task_id,
                emitter=emitter,
                cancel_check=_cancel_check
            )
            original_guidance = getattr(params, "user_guidance", "") or ""
            params.user_guidance = original_guidance + director_guidance

        prompt_text = build_chapter_prompt(ctx, params, task_id=task_id)
    else:
        prompt_text = custom_prompt_text

    if task_id:
        raise_if_cancelled(task_id)
        
    chapters_dir = os.path.join(ctx.filepath, "chapters")
    os.makedirs(chapters_dir, exist_ok=True)

    # 按目标字数估算 token 上限（中文约 1 token ≈ 1.5 字），留 2 倍余量防止漫无边际地写
    suggested_max_tokens = max(int(params.word_number * 2), 2048)
    chapter_max_tokens = min(ctx.llm.max_tokens, suggested_max_tokens)

    llm = create_llm_adapter(
        interface_format=ctx.llm.interface_format,
        base_url=ctx.llm.base_url,
        model_name=ctx.llm.model_name,
        api_key=ctx.llm.api_key,
        temperature=ctx.llm.temperature,
        max_tokens=chapter_max_tokens,
        timeout=ctx.llm.timeout,
        cancel_token=ctx.cancel_token,
    )
    llm._log_ctx = ctx.make_log_ctx(task_id) if hasattr(ctx, "make_log_ctx") else None

    def _check_cancel():
        if task_id:
            raise_if_cancelled(task_id)
        return False

    partial_file = os.path.join(chapters_dir, f"chapter_{params.chapter_number}_partial.txt")
    chapter_content = ""

    if start_step and start_step != "drafting":
        if os.path.exists(partial_file):
            chapter_content = read_file(partial_file)
        if not chapter_content.strip():
            logger.warning(f"Resume step {start_step} requested, but partial file is empty. Restarting from drafting.")
            start_step = "drafting"
    else:
        start_step = "drafting"

    # --- 2. 生成初稿 ---
    if start_step == "drafting":
        if emitter is not None:
            emitter.emit("progress", {"step": "drafting", "status": "running", "message": f"正在生成第 {params.chapter_number} 章初稿..."})
            
        chapter_content = invoke_with_cleaning(llm, prompt_text, cancel_check=_check_cancel)
        
        if task_id:
            raise_if_cancelled(task_id)
        if not chapter_content.strip():
            logger.warning("Generated chapter draft is empty.")
            raise RuntimeError("章节草稿生成为空")
            
        save_string_to_txt(chapter_content, partial_file)
        if task_id:
            from novel_generator.task_manager import update_task
            update_task(task_id, current_step="voice_polish")

    blueprint_text = read_file(os.path.join(ctx.filepath, "Novel_directory.txt")).strip() or ""
    chapter_info = get_chapter_info_from_blueprint(blueprint_text, params.chapter_number)

    # --- 3. 优化文风 ---
    if start_step in ("drafting", "voice_polish"):
        if emitter is not None:
            emitter.emit("progress", {"step": "voice_polish", "status": "running", "message": f"正在优化第 {params.chapter_number} 章文风..."})
        chapter_content = revise_chapter_voice(ctx, params, chapter_info, chapter_content, task_id=task_id)
        if emitter is not None:
            emitter.emit("progress", {"step": "voice_polish", "status": "done", "message": "文风优化完成"})
        save_string_to_txt(chapter_content, partial_file)
        if task_id:
            from novel_generator.task_manager import update_task
            update_task(task_id, current_step="quality_check")

    # --- 4. 平台质检 ---
    if start_step in ("drafting", "voice_polish", "quality_check", "quality_rewrite"):
        if emitter is not None:
            emitter.emit("progress", {"step": "quality_check", "status": "running", "message": "正在执行平台质检..."})
        
        # 仅调用一次大模型进行综合审查，降低成本和等待时间
        quality_feedback = analyze_chapter_quality(ctx, chapter_content, task_id=task_id)
        opening_feedback = quality_feedback.get("opening", {})
        ending_feedback = quality_feedback.get("ending", {})
        mid_feedback = quality_feedback.get("middle", {})
        dialogue_feedback = quality_feedback.get("dialogue", {})

        opening_score = int(opening_feedback.get("score", 0) or 0)
        mid_score = int(mid_feedback.get("score", 0) or 0)
        dialogue_score = int(dialogue_feedback.get("score", 0) or 0)
        has_hook = bool(ending_feedback.get("has_hook", False))

        # --- 5. 定向返修 ---
        if opening_score < 8 or mid_score < 7 or dialogue_score < 7 or not has_hook:
            if task_id:
                from novel_generator.task_manager import update_task
                update_task(task_id, current_step="quality_rewrite")
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
            save_string_to_txt(chapter_content, partial_file)

        if emitter is not None:
            emitter.emit("progress", {"step": "quality_check", "status": "done", "message": "平台质检完成"})

        # --- 5.1 防照抄检测 (Similarity Guard) ---
        try:
            from backend.app.services.local_reference_context_service import get_bindings
            bindings = get_bindings(ctx.project_id)
            guard_bindings = [b for b in bindings if b.get("enabled") and b.get("use_anti_copy_guard")]
            if guard_bindings:
                if emitter is not None:
                    emitter.emit("progress", {"step": "similarity_check", "status": "running", "message": "正在进行相似度查重..."})
                    
                from backend.app.services.local_similarity_guard_service import analyze_similarity, save_similarity_report
                from backend.app.services.local_reference_context_service import build_reference_context
                ref_context = build_reference_context(ctx.project_id)
                
                reference_texts = []
                for book_id, data in ref_context.items():
                    if book_id == "style_bible_excerpt": continue
                    for _, content in data.get("data", {}).items():
                        reference_texts.append(str(content))
                
                # Check similarity
                report = analyze_similarity(chapter_content, reference_texts, ctx.project_id)
                save_similarity_report(ctx.filepath, report, params.chapter_number)
                
                # Auto rewrite loop (max 2 times)
                max_retries = 2
                retry_count = 0
                while report["needs_rewrite"] and retry_count < max_retries:
                    if emitter is not None:
                        emitter.emit("progress", {"step": "similarity_rewrite", "status": "running", "message": f"查重未通过，正在进行自动重写 ({retry_count+1}/{max_retries})..."})
                    
                    if task_id:
                        update_task(task_id, current_step="similarity_rewrite")
                        
                    rewrite_prompt = (
                        f"以下是你生成的正文草稿，系统检测出它与参考书原文存在高度雷同！\n\n{report['rewrite_instruction']}\n\n"
                        f"【原草稿内容】：\n{chapter_content}\n\n"
                        f"请重新输出一份完全原创的正文，保持情节不变但必须打碎原句式。"
                        f"字数要求：{params.word_number}字左右，与原稿篇幅相近，不要显著缩水或膨胀。只输出正文："
                    )
                    
                    chapter_content = invoke_with_cleaning(llm, rewrite_prompt, cancel_check=_check_cancel)
                    save_string_to_txt(chapter_content, partial_file)
                    
                    # Re-check
                    report = analyze_similarity(chapter_content, reference_texts, ctx.project_id)
                    save_similarity_report(ctx.filepath, report, params.chapter_number)
                    retry_count += 1

                if emitter is not None:
                    emitter.emit("progress", {"step": "similarity_check", "status": "done", "message": "相似度查重完成"})
        except Exception as e:
            logger.error(f"相似度查重流程异常: {e}", exc_info=True)
            if emitter is not None:
                emitter.emit("progress", {"step": "similarity_check", "status": "done", "message": "查重异常，按安全策略跳过"})

    # --- 5.2 字数校验回环 (Word Count Guard) ---
    target_wc = params.word_number
    low_threshold = int(target_wc * 0.8)
    high_threshold = int(target_wc * 1.3)
    current_wc = get_word_count(chapter_content)
    logger.info(f"[WordCount] Chapter {params.chapter_number}: current={current_wc}, target={target_wc}")

    if current_wc < low_threshold:
        if emitter is not None:
            emitter.emit("progress", {"step": "word_count_adjust", "status": "running", "message": f"字数不足（{current_wc}/{target_wc}），正在扩写补足..."})
        try:
            from novel_generator.finalization import enrich_chapter_text
            enriched = enrich_chapter_text(ctx, chapter_content, target_wc, task_id=task_id)
            if enriched and enriched.strip() and get_word_count(enriched) > current_wc:
                chapter_content = enriched.strip()
            save_string_to_txt(chapter_content, partial_file)
        except Exception as e:
            logger.warning(f"Enrich failed for chapter {params.chapter_number}, keeping original: {e}")
        if emitter is not None:
            emitter.emit("progress", {"step": "word_count_adjust", "status": "done", "message": f"扩写完成（{get_word_count(chapter_content)}字）"})

    elif current_wc > high_threshold:
        if emitter is not None:
            emitter.emit("progress", {"step": "word_count_adjust", "status": "running", "message": f"字数超标（{current_wc}/{target_wc}），正在压缩..."})
        try:
            compress_prompt = (
                f"以下是 {current_wc} 字的章节正文，目标字数为 {target_wc} 字。"
                f"请在完全保留情节、人物、伏笔、钩子的前提下，删除冗余描写、合并重复信息、压缩空泛段落，"
                f"使总字数接近 {target_wc} 字。只输出压缩后的正文，不要解释。\n\n{chapter_content}"
            )
            compressed = invoke_with_cleaning(llm, compress_prompt, cancel_check=_check_cancel)
            if compressed and compressed.strip() and get_word_count(compressed) < current_wc:
                chapter_content = compressed.strip()
            save_string_to_txt(chapter_content, partial_file)
        except Exception as e:
            logger.warning(f"Compress failed for chapter {params.chapter_number}, keeping original: {e}")
        if emitter is not None:
            emitter.emit("progress", {"step": "word_count_adjust", "status": "done", "message": f"压缩完成（{get_word_count(chapter_content)}字）"})

    # --- 6. 存储结果 ---
    chapter_file = os.path.join(chapters_dir, f"chapter_{params.chapter_number}.txt")
    clear_file_content(chapter_file)
    save_string_to_txt(chapter_content, chapter_file)
    
    # 清理 partial 文件
    if os.path.exists(partial_file):
        os.remove(partial_file)
        
    if task_id:
        from novel_generator.task_manager import update_task
        update_task(task_id, current_step="completed")
        
    logger.info(f"[Draft] Chapter {params.chapter_number} generated as a draft.")
    return chapter_content
