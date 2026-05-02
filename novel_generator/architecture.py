# -*- coding: utf-8 -*-
"""
小说总体架构生成（Novel_architecture_generate 及相关辅助函数）

重构要点：
- 接受 GenerationContext + ProjectConfig 替代散落参数
- 可选 emitter 回调（用于 Web SSE 进度推送）
- 保留 partial_architecture.json 断点续传机制
"""
import os
import json
import logging
import traceback
from novel_generator.common import invoke_with_cleaning
from llm_adapters import create_llm_adapter
import prompt_definitions
from utils import clear_file_content, save_string_to_txt

logger = logging.getLogger(__name__)


def load_partial_architecture_data(filepath: str) -> dict:
    partial_file = os.path.join(filepath, "partial_architecture.json")
    if not os.path.exists(partial_file):
        return {}
    try:
        with open(partial_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        logger.warning("Failed to load partial_architecture.json")
        return {}


def save_partial_architecture_data(filepath: str, data: dict):
    partial_file = os.path.join(filepath, "partial_architecture.json")
    try:
        with open(partial_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        logger.warning("Failed to save partial_architecture.json")


def Novel_architecture_generate(
    # ---- 新接口：统一上下文 ----
    ctx,         # GenerationContext
    project,     # ProjectConfig
    # ---- 可选 emitter 回调 ----
    emitter=None,
) -> None:
    """
    依次调用:
      1. core_seed_prompt
      2. character_dynamics_prompt
      3. world_building_prompt
      4. plot_architecture_prompt

    若中间任何一步失败且重试多次失败，则将已生成内容写入 partial_architecture.json 并退出；
    下次调用时可从该步骤继续。

    emitter (可选): 具有 .emit(event_type, data) 方法的对象，用于 SSE 进度推送。
    """

    def _emit(event_type: str, data: dict):
        if emitter and hasattr(emitter, "emit"):
            emitter.emit(event_type, data)

    def _failure_message(step_label: str) -> str:
        last_error = getattr(llm, "last_error", "").strip()
        if last_error:
            return f"{step_label}失败：LLM 调用没有返回有效内容。模型错误：{last_error}"
        return f"{step_label}失败：LLM 调用没有返回有效内容。请检查模型、API Key、Base URL、max_tokens 和超时设置。"

    def _fail(step: str, message: str):
        _emit("error", {"step": step, "message": message})
        save_partial_architecture_data(filepath, partial_data)
        raise RuntimeError(message)

    filepath = ctx.filepath
    os.makedirs(filepath, exist_ok=True)

    partial_data = load_partial_architecture_data(filepath)

    llm = create_llm_adapter(
        interface_format=ctx.llm.interface_format,
        base_url=ctx.llm.base_url,
        model_name=ctx.llm.model_name,
        api_key=ctx.llm.api_key,
        temperature=ctx.llm.temperature,
        max_tokens=ctx.llm.max_tokens,
        timeout=ctx.llm.timeout,
    )

    topic = project.topic
    genre = project.genre
    category = project.category
    num_chapters = project.num_chapters
    word_number = project.word_number
    user_guidance = project.user_guidance
    knowledge_context = getattr(project, "knowledge_context", "")

    # ── Step 1: 核心种子 ──
    if "core_seed_result" not in partial_data:
        logger.info("Step1: Generating core_seed_prompt (核心种子) ...")
        _emit("progress", {"step": "core_seed", "status": "running", "message": "正在生成核心种子..."})

        prompt_core = prompt_definitions.core_seed_prompt.format(
            topic=topic, genre=genre, category=category,
            number_of_chapters=num_chapters, word_number=word_number,
            user_guidance=user_guidance,
            knowledge_context=knowledge_context,
        )
        core_seed_result = invoke_with_cleaning(llm, prompt_core)
        if not core_seed_result.strip():
            logger.warning("core_seed_prompt generation failed and returned empty.")
            _fail("core_seed", _failure_message("核心种子生成"))
        partial_data["core_seed_result"] = core_seed_result
        save_partial_architecture_data(filepath, partial_data)
        _emit("progress", {"step": "core_seed", "status": "done", "message": "核心种子生成完成"})
        _emit("partial", {"step": "core_seed", "content": core_seed_result[:500] + "..."})
    else:
        logger.info("Step1 already done. Skipping...")

    # ── Step 2: 角色动力学 ──
    if "character_dynamics_result" not in partial_data:
        logger.info("Step2: Generating character_dynamics_prompt ...")
        _emit("progress", {"step": "character", "status": "running", "message": "正在生成角色动力学..."})

        prompt_character = prompt_definitions.character_dynamics_prompt.format(
            core_seed=partial_data["core_seed_result"].strip(),
            user_guidance=user_guidance
        )
        character_dynamics_result = invoke_with_cleaning(llm, prompt_character)
        if not character_dynamics_result.strip():
            logger.warning("character_dynamics_prompt generation failed.")
            _fail("character", _failure_message("角色动力学生成"))
        partial_data["character_dynamics_result"] = character_dynamics_result
        save_partial_architecture_data(filepath, partial_data)
        _emit("progress", {"step": "character", "status": "done", "message": "角色动力学生成完成"})
    else:
        logger.info("Step2 already done. Skipping...")

    # ── 生成初始角色状态 ──
    if "character_dynamics_result" in partial_data and "character_state_result" not in partial_data:
        logger.info("Generating initial character state from character dynamics ...")
        _emit("progress", {"step": "character_state", "status": "running", "message": "正在生成初始角色状态..."})

        prompt_char_state_init = prompt_definitions.create_character_state_prompt.format(
            character_dynamics=partial_data["character_dynamics_result"].strip()
        )
        character_state_init = invoke_with_cleaning(llm, prompt_char_state_init)
        if not character_state_init.strip():
            logger.warning("create_character_state_prompt generation failed.")
            _fail("character_state", _failure_message("角色状态生成"))
        partial_data["character_state_result"] = character_state_init
        character_state_file = os.path.join(filepath, "character_state.txt")
        clear_file_content(character_state_file)
        save_string_to_txt(character_state_init, character_state_file)
        save_partial_architecture_data(filepath, partial_data)
        _emit("progress", {"step": "character_state", "status": "done", "message": "角色状态表已生成"})
        logger.info("Initial character state created and saved.")

    # ── Step 3: 世界观 ──
    if "world_building_result" not in partial_data:
        logger.info("Step3: Generating world_building_prompt ...")
        _emit("progress", {"step": "world", "status": "running", "message": "正在生成世界观..."})

        prompt_world = prompt_definitions.world_building_prompt.format(
            core_seed=partial_data["core_seed_result"].strip(),
            user_guidance=user_guidance
        )
        world_building_result = invoke_with_cleaning(llm, prompt_world)
        if not world_building_result.strip():
            logger.warning("world_building_prompt generation failed.")
            _fail("world", _failure_message("世界观生成"))
        partial_data["world_building_result"] = world_building_result
        save_partial_architecture_data(filepath, partial_data)
        _emit("progress", {"step": "world", "status": "done", "message": "世界观生成完成"})
    else:
        logger.info("Step3 already done. Skipping...")

    # ── Step 4: 三幕式情节 ──
    if "plot_arch_result" not in partial_data:
        logger.info("Step4: Generating plot_architecture_prompt ...")
        _emit("progress", {"step": "plot", "status": "running", "message": "正在生成三幕式情节架构..."})

        prompt_plot = prompt_definitions.plot_architecture_prompt.format(
            core_seed=partial_data["core_seed_result"].strip(),
            character_dynamics=partial_data["character_dynamics_result"].strip(),
            world_building=partial_data["world_building_result"].strip(),
            user_guidance=user_guidance
        )
        plot_arch_result = invoke_with_cleaning(llm, prompt_plot)
        if not plot_arch_result.strip():
            logger.warning("plot_architecture_prompt generation failed.")
            _fail("plot", _failure_message("三幕式情节架构生成"))
        partial_data["plot_arch_result"] = plot_arch_result
        save_partial_architecture_data(filepath, partial_data)
        _emit("progress", {"step": "plot", "status": "done", "message": "情节架构生成完成"})
    else:
        logger.info("Step4 already done. Skipping...")

    core_seed_result = partial_data["core_seed_result"]
    character_dynamics_result = partial_data["character_dynamics_result"]
    world_building_result = partial_data["world_building_result"]
    plot_arch_result = partial_data["plot_arch_result"]

    final_content = (
        "#=== 0) 小说设定 ===\n"
        f"主题：{topic}, 类型：{category}, 风格流派：{genre}, 篇幅：约{num_chapters}章（每章{word_number}字）\n\n"
        "#=== 1) 核心种子 ===\n"
        f"{core_seed_result}\n\n"
        "#=== 2) 角色动力学 ===\n"
        f"{character_dynamics_result}\n\n"
        "#=== 3) 世界观 ===\n"
        f"{world_building_result}\n\n"
        "#=== 4) 三幕式情节架构 ===\n"
        f"{plot_arch_result}\n"
    )

    arch_file = os.path.join(filepath, "Novel_architecture.txt")
    clear_file_content(arch_file)
    save_string_to_txt(final_content, arch_file)
    logger.info("Novel_architecture.txt has been generated successfully.")

    partial_arch_file = os.path.join(filepath, "partial_architecture.json")
    if os.path.exists(partial_arch_file):
        os.remove(partial_arch_file)
        logger.info("partial_architecture.json removed (all steps completed).")

    _emit("progress", {"step": "all", "status": "done", "message": "小说架构生成完毕！"})
    _emit("partial", {"step": "result", "content": final_content[:1000] + "\n\n...(完整内容请查看小说架构页面)"})
