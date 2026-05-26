# -*- coding: utf-8 -*-
import logging
from novel_generator import prompts as prompt_definitions
from novel_generator.common import invoke_with_cleaning
from backend.app.services.model_runtime import create_chat_adapter_from_config as create_llm_adapter

logger = logging.getLogger(__name__)

def run_multi_agent_brainstorming(
    ctx,             # GenerationContext
    global_summary: str,
    chapter_info: dict,
    task_id: str | None = None,
    emitter = None,
    cancel_check = None
) -> str:
    """
    运行多智能体头脑风暴，按顺序调用：毒舌读者 -> 反派首脑 -> 总导演。
    返回总导演的高燃突发事件指南。
    """
    def _emit(event_type: str, data: dict):
        if emitter and hasattr(emitter, "emit"):
            emitter.emit(event_type, data)

    def _check_cancel():
        if cancel_check:
            cancel_check()

    llm = create_llm_adapter(
        interface_format=ctx.llm.interface_format,
        base_url=ctx.llm.base_url,
        model_name=ctx.llm.model_name,
        api_key=ctx.llm.api_key,
        temperature=0.8, # 稍微提高温度以增加创意
        max_tokens=ctx.llm.max_tokens,
        timeout=ctx.llm.timeout,
        cancel_token=ctx.cancel_token,
    )

    formatted_chapter_info = (
        f"第{chapter_info.get('chapter_number', '?')}章《{chapter_info.get('chapter_title', '未命名')}》\n"
        f"定位：{chapter_info.get('chapter_role', '')}\n"
        f"核心目标：{chapter_info.get('chapter_purpose', '')}\n"
        f"本章简述：{chapter_info.get('chapter_summary', '')}\n"
    )

    # 加载角色状态与伏笔暗线上下文
    import os
    character_state = ""
    plot_arcs = ""
    if ctx.filepath:
        char_state_path = os.path.join(ctx.filepath, "character_state.txt")
        if os.path.exists(char_state_path):
            try:
                with open(char_state_path, "r", encoding="utf-8") as f:
                    character_state = f.read().strip()
            except Exception as e:
                logger.warning(f"Failed to read character_state.txt: {e}")
        
        plot_arcs_path = os.path.join(ctx.filepath, "plot_arcs.txt")
        if os.path.exists(plot_arcs_path):
            try:
                with open(plot_arcs_path, "r", encoding="utf-8") as f:
                    plot_arcs = f.read().strip()
            except Exception as e:
                logger.warning(f"Failed to read plot_arcs.txt: {e}")
                
    if not character_state:
        character_state = "（暂无角色状态数据，请先生成或导入角色状态）"
    if not plot_arcs:
        plot_arcs = "（暂无伏笔与剧情线数据，请先生成或导入伏笔台账）"

    # 1. 读者 Agent
    _check_cancel()
    _emit("progress", {"step": "brainstorm_reader", "status": "running", "message": "毒舌读者 Agent 正在无情吐槽大纲..."})
    reader_prompt = prompt_definitions.get_prompt_template(ctx.project_id, 'reader_agent_prompt').format(
        global_summary=global_summary,
        chapter_info=formatted_chapter_info,
        character_state=character_state,
        plot_arcs=plot_arcs
    )
    reader_critique = invoke_with_cleaning(llm, reader_prompt, cancel_check=_check_cancel)
    _emit("progress", {"step": "brainstorm_reader", "status": "done", "message": "读者 Agent 吐槽完毕"})

    # 2. 反派 Agent
    _check_cancel()
    _emit("progress", {"step": "brainstorm_villain", "status": "running", "message": "反派首脑 Agent 正在密谋突袭计划..."})
    villain_prompt = prompt_definitions.get_prompt_template(ctx.project_id, 'villain_agent_prompt').format(
        chapter_info=formatted_chapter_info,
        reader_critique=reader_critique,
        character_state=character_state,
        plot_arcs=plot_arcs
    )
    villain_plan = invoke_with_cleaning(llm, villain_prompt, cancel_check=_check_cancel)
    _emit("progress", {"step": "brainstorm_villain", "status": "done", "message": "反派 Agent 密谋完毕"})

    # 3. 导演 Agent
    _check_cancel()
    _emit("progress", {"step": "brainstorm_director", "status": "running", "message": "总导演 Agent 正在敲定反转剧本..."})
    director_prompt = prompt_definitions.get_prompt_template(ctx.project_id, 'director_agent_prompt').format(
        chapter_info=formatted_chapter_info,
        reader_critique=reader_critique,
        villain_plan=villain_plan,
        character_state=character_state,
        plot_arcs=plot_arcs
    )
    director_guidance = invoke_with_cleaning(llm, director_prompt, cancel_check=_check_cancel)
    _emit("progress", {"step": "brainstorm_director", "status": "done", "message": "总导演敲定【高燃突发事件指南】"})

    # 返回给主笔的指导
    brainstorm_result = f"\n\n【多智能体头脑风暴-高燃突发事件指南】\n（主笔注意：必须将以下意外事件自然地融合进本章中！）\n{director_guidance}\n\n"
    return brainstorm_result
