import os
import asyncio
import logging
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from backend.app.services import project_service, chapter_service
from backend.app.utils.sse import SSEEmitter, sse_event_generator
from backend.app.dependencies import get_user_llm_config, get_user_embedding_config
from backend.app.auth import get_current_user

from novel_generator.context import GenerationContext, ChapterParams, ProjectConfig
from utils import read_file

router = APIRouter(tags=["AI 生成"])
logger = logging.getLogger(__name__)


# ── helpers ──

def _check_project(project_id: str, request: Request) -> tuple:
    user_id = get_current_user(request)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    pconfig = project_service.get_project_config(project_id)
    if not pconfig:
        raise HTTPException(status_code=404, detail="项目配置不存在")
    return project, pconfig, user_id


def _resolve_llm(user_id: str, preferred: str) -> dict:
    if preferred:
        conf = get_user_llm_config(user_id, preferred)
        if conf:
            return conf
    from backend.app.services.user_service import list_user_llm_configs
    configs = list_user_llm_configs(user_id)
    if not configs:
        raise HTTPException(status_code=400, detail="请先在设置中添加 LLM 配置")
    first_name = next(iter(configs.keys()))
    return get_user_llm_config(user_id, first_name)


def _resolve_emb(user_id: str, preferred: str) -> dict:
    if not preferred:
        return {}
    conf = get_user_embedding_config(user_id, preferred)
    return conf or {}


def _make_ctx(llm_conf: dict, emb_conf: dict, filepath: str) -> GenerationContext:
    return GenerationContext.from_dicts(
        llm_dict=llm_conf,
        emb_dict=emb_conf,
        filepath=filepath,
    )


def _make_project_cfg(pconfig: dict) -> ProjectConfig:
    return ProjectConfig(
        topic=pconfig.get("topic", ""),
        genre=pconfig.get("genre", ""),
        category=pconfig.get("category", ""),
        platform=pconfig.get("platform", "tomato"),
        num_chapters=pconfig.get("num_chapters", 0),
        word_number=pconfig.get("word_number", 3000),
        language=pconfig.get("language", "zh"),
        user_guidance=pconfig.get("user_guidance", ""),
    )


def _make_chapter_params(pconfig: dict, chapter_number: int) -> ChapterParams:
    return ChapterParams(
        chapter_number=chapter_number,
        word_number=pconfig.get("word_number", 3000),
        user_guidance=pconfig.get("user_guidance", ""),
    )


def _run_in_thread(emitter: SSEEmitter, func, *args, **kwargs):
    failed = False
    try:
        func(emitter, *args, **kwargs)
    except HTTPException as e:
        failed = True
        emitter.emit("error", {"step": "request", "message": str(e.detail)})
    except Exception as e:
        failed = True
        logger.exception("Generation task failed")
        emitter.emit("error", {"step": "server", "message": f"{func.__name__} 执行失败: {e}"})
    finally:
        emitter.emit("done", {"message": "已结束" if failed else "完成", "status": "error" if failed else "done"})


def _require_project_file(filepath: str, filename: str, purpose: str) -> str:
    full_path = os.path.join(filepath, filename)
    if not os.path.exists(full_path):
        raise RuntimeError(f"缺少{purpose}文件: {filename}。请先生成对应内容。")
    content = read_file(full_path).strip()
    if not content:
        raise RuntimeError(f"{purpose}文件为空: {filename}。请重新生成对应内容。")
    return content


def _make_streaming_response(
    request: Request,
    queue: asyncio.Queue,
    emitter: SSEEmitter,
    target_func,
    *args,
) -> StreamingResponse:
    loop = asyncio.get_event_loop()
    emitter.set_queue(queue, loop)

    async def event_gen():
        loop.run_in_executor(None, target_func, emitter, *args)
        async for sse_data in sse_event_generator(queue):
            if await request.is_disconnected():
                break
            yield sse_data
        emitter.clear()

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── 架构生成 ──

@router.post("/api/v1/projects/{project_id}/generate/architecture")
@router.get("/api/v1/projects/{project_id}/generate/architecture")
async def generate_architecture(project_id: str, request: Request):
    project, pconfig, user_id = _check_project(project_id, request)
    return _make_streaming_response(
        request, asyncio.Queue(), SSEEmitter(),
        _run_architecture, project, pconfig, user_id,
    )


def _run_architecture(emitter: SSEEmitter, project: dict, pconfig: dict, user_id: str):
    """复用 novel_generator.Novel_architecture_generate，消除重复逻辑"""
    from novel_generator.architecture import Novel_architecture_generate

    llm_conf = _resolve_llm(user_id, pconfig.get("architecture_llm", ""))
    emb_conf = _resolve_emb(user_id, pconfig.get("embedding_config", ""))

    ctx = _make_ctx(llm_conf, emb_conf, project["filepath"])
    proj_cfg = _make_project_cfg(pconfig)

    Novel_architecture_generate(ctx, proj_cfg, emitter=emitter)
    project_service.update_project(project["id"], {"status": "ready"}, user_id)


# ── 蓝本章节目录生成 ──

@router.post("/api/v1/projects/{project_id}/generate/blueprint")
@router.get("/api/v1/projects/{project_id}/generate/blueprint")
async def generate_blueprint(project_id: str, request: Request):
    project, pconfig, user_id = _check_project(project_id, request)
    return _make_streaming_response(
        request, asyncio.Queue(), SSEEmitter(),
        _run_blueprint, project, pconfig, user_id,
    )


def _run_blueprint(emitter: SSEEmitter, project: dict, pconfig: dict, user_id: str):
    """复用 novel_generator.Chapter_blueprint_generate"""
    from novel_generator.blueprint import Chapter_blueprint_generate

    _require_project_file(project["filepath"], "Novel_architecture.txt", "小说架构")
    llm_conf = _resolve_llm(user_id, pconfig.get("chapter_outline_llm", ""))
    ctx = _make_ctx(llm_conf, {}, project["filepath"])
    proj_cfg = _make_project_cfg(pconfig)

    Chapter_blueprint_generate(ctx, proj_cfg, emitter=emitter)
    chapter_service.sync_chapters_from_directory(project["id"], project["filepath"])


# ── 章节草稿生成 ──

@router.post("/api/v1/projects/{project_id}/generate/chapter/{chapter_number}")
@router.get("/api/v1/projects/{project_id}/generate/chapter/{chapter_number}")
async def generate_chapter(project_id: str, chapter_number: int, request: Request):
    project, pconfig, user_id = _check_project(project_id, request)
    return _make_streaming_response(
        request, asyncio.Queue(), SSEEmitter(),
        _run_chapter_generation, project, pconfig, chapter_number, user_id,
    )


def _run_chapter_generation(emitter: SSEEmitter, project: dict, pconfig: dict, chapter_number: int, user_id: str):
    """复用 novel_generator.build_chapter_prompt + generate_chapter_draft"""
    from novel_generator.chapter import build_chapter_prompt, generate_chapter_draft

    _require_project_file(project["filepath"], "Novel_architecture.txt", "小说架构")
    _require_project_file(project["filepath"], "Novel_directory.txt", "章节目录")
    llm_conf = _resolve_llm(user_id, pconfig.get("prompt_draft_llm", ""))
    emb_conf = _resolve_emb(user_id, pconfig.get("embedding_config", ""))

    ctx = _make_ctx(llm_conf, emb_conf, project["filepath"])
    params = _make_chapter_params(pconfig, chapter_number)

    emitter.emit("progress", {"step": "build_prompt", "status": "running",
                               "message": f"正在构建第{chapter_number}章提示词..."})

    prompt_text = build_chapter_prompt(ctx, params)
    emitter.emit("progress", {"step": "build_prompt", "status": "done", "message": "提示词构建完成"})

    emitter.emit("progress", {"step": "draft", "status": "running",
                               "message": f"正在生成第{chapter_number}章草稿..."})

    draft_text = generate_chapter_draft(ctx, params, custom_prompt_text=prompt_text)

    if draft_text:
        from utils import get_word_count
        wc = get_word_count(draft_text)
        chapter_service.mark_chapter_final(project["id"], chapter_number, wc)
        emitter.emit("progress", {"step": "draft", "status": "done",
                                   "message": f"第{chapter_number}章草稿生成完成"})
        emitter.emit("partial", {"step": "draft", "content": draft_text[:500] + "..."})
    else:
        emitter.emit("error", {"step": "draft", "message": "草稿生成返回空内容"})


# ── 定稿 ──

@router.post("/api/v1/projects/{project_id}/generate/finalize/{chapter_number}")
@router.get("/api/v1/projects/{project_id}/generate/finalize/{chapter_number}")
async def finalize_chapter_route(project_id: str, chapter_number: int, request: Request):
    project, pconfig, user_id = _check_project(project_id, request)
    return _make_streaming_response(
        request, asyncio.Queue(), SSEEmitter(),
        _run_finalize, project, pconfig, chapter_number, user_id,
    )


def _run_finalize(emitter: SSEEmitter, project: dict, pconfig: dict, chapter_number: int, user_id: str):
    """复用 novel_generator.finalize_chapter"""
    from novel_generator.finalization import finalize_chapter

    chapter_filename = os.path.join("chapters", f"chapter_{chapter_number}.txt")
    _require_project_file(project["filepath"], chapter_filename, f"第{chapter_number}章草稿")
    llm_conf = _resolve_llm(user_id, pconfig.get("final_chapter_llm", ""))
    emb_conf = _resolve_emb(user_id, pconfig.get("embedding_config", ""))

    ctx = _make_ctx(llm_conf, emb_conf, project["filepath"])
    params = _make_chapter_params(pconfig, chapter_number)

    emitter.emit("progress", {"step": "finalize", "status": "running",
                               "message": f"正在定稿第{chapter_number}章..."})

    finalize_chapter(ctx, params)

    from utils import get_word_count
    chapter_text = read_file(os.path.join(project["filepath"], "chapters", f"chapter_{chapter_number}.txt"))
    wc = get_word_count(chapter_text)
    chapter_service.mark_chapter_final(project["id"], chapter_number, wc)

    emitter.emit("progress", {"step": "finalize", "status": "done",
                               "message": f"第{chapter_number}章定稿完成"})
