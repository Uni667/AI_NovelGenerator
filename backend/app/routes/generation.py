import os
import asyncio
import json
import threading
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from backend.app.services import project_service, chapter_service
from backend.app.utils.sse import sse_emitter, sse_event_generator
from backend.app.dependencies import get_config as get_global_config, get_llm_config, get_embedding_config

router = APIRouter(tags=["AI 生成"])


def _run_in_thread(func, *args, **kwargs):
    """在后台线程运行生成任务，完成后向队列发送 sentinel"""
    try:
        func(*args, **kwargs)
    finally:
        sse_emitter.emit("done", {"message": "完成"})


@router.post("/api/v1/projects/{project_id}/generate/architecture")
@router.get("/api/v1/projects/{project_id}/generate/architecture")
async def generate_architecture(project_id: str, request: Request):
    project = project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    pconfig = project_service.get_project_config(project_id)
    if not pconfig:
        raise HTTPException(status_code=404, detail="项目配置不存在")

    queue = asyncio.Queue()
    loop = asyncio.get_event_loop()
    sse_emitter.set_queue(queue, loop)

    async def event_gen():
        loop.run_in_executor(None, _run_architecture, project, pconfig)
        async for sse_data in sse_event_generator(queue):
            if await request.is_disconnected():
                break
            yield sse_data
        sse_emitter.clear()

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


def _run_architecture(project: dict, pconfig: dict):
    global_config = get_global_config()
    arch_llm_name = pconfig.get("architecture_llm", "") or global_config.get("last_interface_format", "OpenAI")
    llm_conf = get_llm_config(arch_llm_name)
    if not llm_conf:
        sse_emitter.emit("error", {"message": f"LLM 配置 '{arch_llm_name}' 不存在"})
        return

    # 尝试获取 embedding 配置用于知识库检索
    emb_config_name = pconfig.get("embedding_config", "") or global_config.get("last_embedding_interface_format", "")
    emb_conf = get_embedding_config(emb_config_name) if emb_config_name else {}

    from llm_adapters import create_llm_adapter
    from embedding_adapters import create_embedding_adapter
    from novel_generator.vectorstore_utils import load_vector_store
    import prompt_definitions
    from novel_generator.common import invoke_with_cleaning

    llm = create_llm_adapter(
        interface_format=llm_conf.get("interface_format", "OpenAI"),
        base_url=llm_conf.get("base_url", ""),
        model_name=llm_conf.get("model_name", ""),
        api_key=llm_conf.get("api_key", ""),
        temperature=llm_conf.get("temperature", 0.7),
        max_tokens=llm_conf.get("max_tokens", 8192),
        timeout=llm_conf.get("timeout", 600)
    )

    filepath = project["filepath"]
    topic = pconfig.get("topic", "")
    genre = pconfig.get("genre", "")
    num_chapters = pconfig.get("num_chapters", 0)
    word_number = pconfig.get("word_number", 3000)
    user_guidance = pconfig.get("user_guidance", "")

    # 检索知识库
    knowledge_context = ""
    if emb_conf:
        try:
            emb_adapter = create_embedding_adapter(
                interface_format=emb_conf.get("interface_format", "OpenAI"),
                api_key=emb_conf.get("api_key", ""),
                base_url=emb_conf.get("base_url", ""),
                model_name=emb_conf.get("model_name", "")
            )
            store = load_vector_store(emb_adapter, filepath)
            if store:
                query = f"{topic} {genre} {user_guidance}"
                docs = store.similarity_search(query, k=5)
                if docs:
                    knowledge_context = "\n".join([d.page_content for d in docs])[:3000]
        except Exception:
            pass

    sse_emitter.emit("progress", {"step": "init", "status": "running", "message": "正在准备生成架构..."})

    # Step 1: 核心种子
    sse_emitter.emit("progress", {"step": "core_seed", "status": "running", "message": "正在生成核心种子..."})
    try:
        prompt_core = prompt_definitions.core_seed_prompt.format(
            topic=topic,
            genre=genre,
            number_of_chapters=num_chapters,
            word_number=word_number,
            user_guidance=user_guidance,
            knowledge_context=knowledge_context or "（无相关知识库内容）"
        )
        core_seed = invoke_with_cleaning(llm, prompt_core)
        sse_emitter.emit("progress", {"step": "core_seed", "status": "done", "message": "核心种子生成完成"})
        sse_emitter.emit("partial", {"step": "core_seed", "content": core_seed[:500] + "..."})
    except Exception as e:
        sse_emitter.emit("error", {"step": "core_seed", "message": str(e)})
        return

    # Step 2: 角色动力学
    sse_emitter.emit("progress", {"step": "character", "status": "running", "message": "正在生成角色动力学..."})
    try:
        prompt_char = prompt_definitions.character_dynamics_prompt.format(
            core_seed=core_seed,
            user_guidance=user_guidance
        )
        char_dynamics = invoke_with_cleaning(llm, prompt_char)
        sse_emitter.emit("progress", {"step": "character", "status": "done", "message": "角色动力学生成完成"})
    except Exception as e:
        sse_emitter.emit("error", {"step": "character", "message": str(e)})
        return

    # 生成初始角色状态
    sse_emitter.emit("progress", {"step": "character_state", "status": "running", "message": "正在生成初始角色状态..."})
    try:
        from utils import clear_file_content, save_string_to_txt
        prompt_cs = prompt_definitions.create_character_state_prompt.format(character_dynamics=char_dynamics)
        char_state = invoke_with_cleaning(llm, prompt_cs)
        cs_file = os.path.join(filepath, "character_state.txt")
        clear_file_content(cs_file)
        save_string_to_txt(char_state, cs_file)
        sse_emitter.emit("progress", {"step": "character_state", "status": "done", "message": "角色状态表已生成"})
    except Exception as e:
        sse_emitter.emit("error", {"step": "character_state", "message": str(e)})
        return

    # Step 3: 世界观
    sse_emitter.emit("progress", {"step": "world", "status": "running", "message": "正在生成世界观..."})
    try:
        prompt_world = prompt_definitions.world_building_prompt.format(
            core_seed=core_seed,
            user_guidance=user_guidance
        )
        world_building = invoke_with_cleaning(llm, prompt_world)
        sse_emitter.emit("progress", {"step": "world", "status": "done", "message": "世界观生成完成"})
    except Exception as e:
        sse_emitter.emit("error", {"step": "world", "message": str(e)})
        return

    # Step 4: 三幕式情节
    sse_emitter.emit("progress", {"step": "plot", "status": "running", "message": "正在生成三幕式情节架构..."})
    try:
        prompt_plot = prompt_definitions.plot_architecture_prompt.format(
            core_seed=core_seed,
            character_dynamics=char_dynamics,
            world_building=world_building,
            user_guidance=user_guidance
        )
        plot_arch = invoke_with_cleaning(llm, prompt_plot)
        sse_emitter.emit("progress", {"step": "plot", "status": "done", "message": "情节架构生成完成"})
    except Exception as e:
        sse_emitter.emit("error", {"step": "plot", "message": str(e)})
        return

    # 拼接并保存
    final_content = (
        f"#=== 0) 小说设定 ===\n"
        f"主题：{topic}, 类型：{genre}, 篇幅：约{num_chapters}章（每章{word_number}字）\n\n"
        f"#=== 1) 核心种子 ===\n{core_seed}\n\n"
        f"#=== 2) 角色动力学 ===\n{char_dynamics}\n\n"
        f"#=== 3) 世界观 ===\n{world_building}\n\n"
        f"#=== 4) 三幕式情节架构 ===\n{plot_arch}\n"
    )
    arch_file = os.path.join(filepath, "Novel_architecture.txt")
    from utils import clear_file_content, save_string_to_txt
    clear_file_content(arch_file)
    save_string_to_txt(final_content, arch_file)

    # 更新项目状态
    project_service.update_project(project["id"], {"status": "ready"})

    sse_emitter.emit("progress", {"step": "all", "status": "done", "message": "小说架构生成完毕！"})
    sse_emitter.emit("partial", {"step": "result", "content": final_content[:1000] + "\n\n...(完整内容请查看小说架构页面)"})


@router.post("/api/v1/projects/{project_id}/generate/blueprint")
@router.get("/api/v1/projects/{project_id}/generate/blueprint")
async def generate_blueprint(project_id: str, request: Request):
    project = project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    pconfig = project_service.get_project_config(project_id)
    if not pconfig:
        raise HTTPException(status_code=404, detail="项目配置不存在")

    queue = asyncio.Queue()
    loop = asyncio.get_event_loop()
    sse_emitter.set_queue(queue, loop)

    async def event_gen():
        loop.run_in_executor(None, _run_blueprint, project, pconfig)
        async for sse_data in sse_event_generator(queue):
            if await request.is_disconnected():
                break
            yield sse_data
        sse_emitter.clear()

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


def _run_blueprint(project: dict, pconfig: dict):
    global_config = get_global_config()
    outline_llm = pconfig.get("chapter_outline_llm", "") or next(iter(global_config.get("llm_configs", {}).keys()), "")
    llm_conf = get_llm_config(outline_llm)
    if not llm_conf:
        sse_emitter.emit("error", {"message": f"LLM 配置不存在"})
        return

    from llm_adapters import create_llm_adapter
    from novel_generator.blueprint import Chapter_blueprint_generate

    llm = create_llm_adapter(
        interface_format=llm_conf.get("interface_format", "OpenAI"),
        base_url=llm_conf.get("base_url", ""),
        model_name=llm_conf.get("model_name", ""),
        api_key=llm_conf.get("api_key", ""),
        temperature=llm_conf.get("temperature", 0.7),
        max_tokens=llm_conf.get("max_tokens", 8192),
        timeout=llm_conf.get("timeout", 600)
    )

    sse_emitter.emit("progress", {"step": "blueprint", "status": "running", "message": "正在生成章节目录..."})

    try:
        Chapter_blueprint_generate(
            interface_format=llm_conf.get("interface_format", "OpenAI"),
            api_key=llm_conf.get("api_key", ""),
            base_url=llm_conf.get("base_url", ""),
            llm_model=llm_conf.get("model_name", ""),
            number_of_chapters=pconfig.get("num_chapters", 10),
            filepath=project["filepath"],
            temperature=llm_conf.get("temperature", 0.7),
            max_tokens=llm_conf.get("max_tokens", 8192),
            timeout=llm_conf.get("timeout", 600),
            user_guidance=pconfig.get("user_guidance", "")
        )
        # 同步章节到数据库
        chapter_service.sync_chapters_from_directory(project["id"], project["filepath"])
        sse_emitter.emit("progress", {"step": "blueprint", "status": "done", "message": "章节目录生成完成"})
    except Exception as e:
        sse_emitter.emit("error", {"step": "blueprint", "message": str(e)})


@router.post("/api/v1/projects/{project_id}/generate/chapter/{chapter_number}")
@router.get("/api/v1/projects/{project_id}/generate/chapter/{chapter_number}")
async def generate_chapter(project_id: str, chapter_number: int, request: Request):
    project = project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    pconfig = project_service.get_project_config(project_id)
    if not pconfig:
        raise HTTPException(status_code=404, detail="项目配置不存在")

    queue = asyncio.Queue()
    loop = asyncio.get_event_loop()
    sse_emitter.set_queue(queue, loop)

    async def event_gen():
        loop.run_in_executor(None, _run_chapter_generation, project, pconfig, chapter_number)
        async for sse_data in sse_event_generator(queue):
            if await request.is_disconnected():
                break
            yield sse_data
        sse_emitter.clear()

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


def _run_chapter_generation(project: dict, pconfig: dict, chapter_number: int):
    global_config = get_global_config()
    draft_llm = pconfig.get("prompt_draft_llm", "") or next(iter(global_config.get("llm_configs", {}).keys()), "")
    llm_conf = get_llm_config(draft_llm)
    if not llm_conf:
        sse_emitter.emit("error", {"message": "LLM 配置不存在"})
        return

    emb_config_name = pconfig.get("embedding_config", "") or global_config.get("last_embedding_interface_format", "")
    emb_conf = get_embedding_config(emb_config_name) if emb_config_name else {}

    sse_emitter.emit("progress", {"step": "build_prompt", "status": "running", "message": f"正在构建第{chapter_number}章提示词..."})

    try:
        from novel_generator.chapter import build_chapter_prompt, generate_chapter_draft

        prompt_text = build_chapter_prompt(
            api_key=llm_conf.get("api_key", ""),
            base_url=llm_conf.get("base_url", ""),
            model_name=llm_conf.get("model_name", ""),
            filepath=project["filepath"],
            novel_number=chapter_number,
            word_number=pconfig.get("word_number", 3000),
            temperature=llm_conf.get("temperature", 0.7),
            user_guidance=pconfig.get("user_guidance", ""),
            characters_involved="",
            key_items="",
            scene_location="",
            time_constraint="",
            embedding_api_key=emb_conf.get("api_key", ""),
            embedding_url=emb_conf.get("base_url", ""),
            embedding_interface_format=emb_conf.get("interface_format", "OpenAI"),
            embedding_model_name=emb_conf.get("model_name", ""),
            embedding_retrieval_k=emb_conf.get("retrieval_k", 4),
            interface_format=llm_conf.get("interface_format", "OpenAI"),
            max_tokens=llm_conf.get("max_tokens", 8192),
            timeout=llm_conf.get("timeout", 600)
        )

        sse_emitter.emit("progress", {"step": "build_prompt", "status": "done", "message": "提示词构建完成"})
        sse_emitter.emit("progress", {"step": "draft", "status": "running", "message": f"正在生成第{chapter_number}章草稿..."})

        draft_text = generate_chapter_draft(
            api_key=llm_conf.get("api_key", ""),
            base_url=llm_conf.get("base_url", ""),
            model_name=llm_conf.get("model_name", ""),
            filepath=project["filepath"],
            novel_number=chapter_number,
            word_number=pconfig.get("word_number", 3000),
            temperature=llm_conf.get("temperature", 0.7),
            user_guidance=pconfig.get("user_guidance", ""),
            characters_involved="",
            key_items="",
            scene_location="",
            time_constraint="",
            embedding_api_key=emb_conf.get("api_key", ""),
            embedding_url=emb_conf.get("base_url", ""),
            embedding_interface_format=emb_conf.get("interface_format", "OpenAI"),
            embedding_model_name=emb_conf.get("model_name", ""),
            embedding_retrieval_k=emb_conf.get("retrieval_k", 4),
            interface_format=llm_conf.get("interface_format", "OpenAI"),
            max_tokens=llm_conf.get("max_tokens", 8192),
            timeout=llm_conf.get("timeout", 600),
            custom_prompt_text=prompt_text
        )

        if draft_text:
            sse_emitter.emit("progress", {"step": "draft", "status": "done", "message": f"第{chapter_number}章草稿生成完成"})
            sse_emitter.emit("partial", {"step": "draft", "content": draft_text[:500] + "..."})
            from utils import get_word_count
            wc = get_word_count(draft_text)
            chapter_service.mark_chapter_final(project["id"], chapter_number, wc)
        else:
            sse_emitter.emit("error", {"step": "draft", "message": "草稿生成返回空内容"})

    except Exception as e:
        sse_emitter.emit("error", {"step": "chapter", "message": str(e)})


@router.post("/api/v1/projects/{project_id}/generate/finalize/{chapter_number}")
@router.get("/api/v1/projects/{project_id}/generate/finalize/{chapter_number}")
async def finalize_chapter_route(project_id: str, chapter_number: int, request: Request):
    project = project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    pconfig = project_service.get_project_config(project_id)
    if not pconfig:
        raise HTTPException(status_code=404, detail="项目配置不存在")

    queue = asyncio.Queue()
    loop = asyncio.get_event_loop()
    sse_emitter.set_queue(queue, loop)

    async def event_gen():
        loop.run_in_executor(None, _run_finalize, project, pconfig, chapter_number)
        async for sse_data in sse_event_generator(queue):
            if await request.is_disconnected():
                break
            yield sse_data
        sse_emitter.clear()

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


def _run_finalize(project: dict, pconfig: dict, chapter_number: int):
    global_config = get_global_config()
    final_llm = pconfig.get("final_chapter_llm", "") or next(iter(global_config.get("llm_configs", {}).keys()), "")
    llm_conf = get_llm_config(final_llm)
    if not llm_conf:
        sse_emitter.emit("error", {"message": "LLM 配置不存在"})
        return

    emb_config_name = pconfig.get("embedding_config", "") or global_config.get("last_embedding_interface_format", "")
    emb_conf = get_embedding_config(emb_config_name) if emb_config_name else {}

    sse_emitter.emit("progress", {"step": "finalize", "status": "running", "message": f"正在定稿第{chapter_number}章..."})

    try:
        from novel_generator.finalization import finalize_chapter

        finalize_chapter(
            novel_number=chapter_number,
            word_number=pconfig.get("word_number", 3000),
            api_key=llm_conf.get("api_key", ""),
            base_url=llm_conf.get("base_url", ""),
            model_name=llm_conf.get("model_name", ""),
            temperature=llm_conf.get("temperature", 0.7),
            filepath=project["filepath"],
            embedding_api_key=emb_conf.get("api_key", ""),
            embedding_url=emb_conf.get("base_url", ""),
            embedding_interface_format=emb_conf.get("interface_format", "OpenAI"),
            embedding_model_name=emb_conf.get("model_name", ""),
            interface_format=llm_conf.get("interface_format", "OpenAI"),
            max_tokens=llm_conf.get("max_tokens", 8192),
            timeout=llm_conf.get("timeout", 600)
        )

        # 更新章节字数
        from utils import read_file, get_word_count
        chapter_text = read_file(os.path.join(project["filepath"], "chapters", f"chapter_{chapter_number}.txt"))
        wc = get_word_count(chapter_text)
        chapter_service.mark_chapter_final(project["id"], chapter_number, wc)

        sse_emitter.emit("progress", {"step": "finalize", "status": "done", "message": f"第{chapter_number}章定稿完成"})
    except Exception as e:
        sse_emitter.emit("error", {"step": "finalize", "message": str(e)})
