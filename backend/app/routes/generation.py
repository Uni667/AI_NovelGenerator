import os
import asyncio
import logging
import uuid
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from backend.app.services import project_service, chapter_service
from backend.app.utils.sse import SSEEmitter, sse_event_generator, HEARTBEAT
from backend.app.dependencies import get_user_llm_config, get_user_embedding_config
from backend.app.auth import get_current_user
from novel_generator.task_manager import (
    TaskCancelledError,
    finish_task,
    get_active_task,
    get_task,
    register_task,
    request_cancel,
    raise_if_cancelled,
    task_payload,
)

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


def _make_ctx(llm_conf: dict, emb_conf: dict, filepath: str, project_id: str = "") -> GenerationContext:
    return GenerationContext.from_dicts(
        llm_dict=llm_conf,
        emb_dict=emb_conf,
        filepath=filepath,
        project_id=project_id,
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


def _task_label(kind: str) -> str:
    return {
        "architecture": "架构生成",
        "blueprint": "章节目录生成",
        "chapter": "章节草稿生成",
        "chapter_batch": "批量章节生成",
        "finalize": "章节定稿",
    }.get(kind, kind)


def _prepare_generation_task(project_id: str, kind: str, task_id: str | None, metadata: dict[str, object]) -> str:
    resolved_task_id = task_id or uuid.uuid4().hex
    existing_task = get_task(resolved_task_id)
    if existing_task and existing_task.status not in {"done", "failed", "cancelled"}:
        raise HTTPException(status_code=409, detail="该任务标识已经在运行，请先取消当前任务后再开始新的生成")

    active_task = get_active_task(project_id)
    if active_task and active_task.task_id != resolved_task_id:
        raise HTTPException(
            status_code=409,
            detail=f"项目正在执行{_task_label(active_task.kind)}，请先中断后再开始新的生成",
        )

    register_task(resolved_task_id, project_id, kind, metadata)
    return resolved_task_id


def _run_in_thread(emitter: SSEEmitter, task_id: str, func, *args, **kwargs):
    try:
        func(emitter, *args, task_id=task_id, **kwargs)
    except TaskCancelledError as exc:
        finish_task(task_id, "cancelled", str(exc))
        emitter.emit("cancelled", {"message": str(exc), "status": "cancelled", "task_id": task_id})
    except HTTPException as exc:
        message = str(exc.detail)
        finish_task(task_id, "failed", message)
        emitter.emit("error", {"step": "request", "message": message, "task_id": task_id})
        emitter.emit("done", {"message": message, "status": "failed", "task_id": task_id})
    except Exception as exc:
        logger.exception("Generation task failed")
        message = f"{func.__name__} 执行失败: {exc}"
        finish_task(task_id, "failed", message)
        emitter.emit("error", {"step": "server", "message": message, "task_id": task_id})
        emitter.emit("done", {"message": message, "status": "failed", "task_id": task_id})
    else:
        finish_task(task_id, "done", "完成")
        emitter.emit("done", {"message": "完成", "status": "done", "task_id": task_id})


def _require_project_file(filepath: str, filename: str, purpose: str) -> str:
    full_path = os.path.join(filepath, filename)
    if not os.path.exists(full_path):
        raise RuntimeError(f"缺少{purpose}文件: {filename}。请先生成对应内容。")
    content = read_file(full_path).strip()
    if not content:
        raise RuntimeError(f"{purpose}文件为空: {filename}。请重新生成对应内容。")
    return content


async def _heartbeat(queue: asyncio.Queue, interval: float = 3.0):
    """每 interval 秒发送 SSE 注释 ping，防止中间代理空闲超时断开连接"""
    while True:
        await asyncio.sleep(interval)
        await queue.put(HEARTBEAT)


def _make_streaming_response(
    request: Request,
    queue: asyncio.Queue,
    emitter: SSEEmitter,
    task_id: str,
    target_func,
    *args,
) -> StreamingResponse:
    loop = asyncio.get_event_loop()
    emitter.set_queue(queue, loop)

    async def event_gen():
        loop.run_in_executor(None, _run_in_thread, emitter, task_id, target_func, *args)
        hb = asyncio.create_task(_heartbeat(queue))
        try:
            async for sse_data in sse_event_generator(queue):
                if await request.is_disconnected():
                    request_cancel(task_id)
                    break
                yield sse_data
        finally:
            hb.cancel()
            emitter.clear()

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "X-Task-ID": task_id},
    )


@router.get("/api/v1/projects/{project_id}/generate/tasks/{task_id}")
def get_generation_task(project_id: str, task_id: str, request: Request):
    _check_project(project_id, request)
    task = get_task(task_id)
    if not task or task.project_id != project_id:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task_payload(task_id)


@router.post("/api/v1/projects/{project_id}/generate/tasks/{task_id}/cancel")
def cancel_generation_task(project_id: str, task_id: str, request: Request):
    _check_project(project_id, request)
    task = get_task(task_id)
    if not task or task.project_id != project_id:
        raise HTTPException(status_code=404, detail="任务不存在")
    result = request_cancel(task_id)
    if not result:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task_payload(task_id)


# ── 架构生成 ──

@router.post("/api/v1/projects/{project_id}/generate/architecture")
@router.get("/api/v1/projects/{project_id}/generate/architecture")
async def generate_architecture(project_id: str, request: Request, task_id: str | None = None):
    project, pconfig, user_id = _check_project(project_id, request)
    resolved_task_id = _prepare_generation_task(
        project_id,
        "architecture",
        task_id,
        {"project_name": project.get("name", ""), "chapter_count": pconfig.get("num_chapters", 0)},
    )
    return _make_streaming_response(
        request, asyncio.Queue(), SSEEmitter(), resolved_task_id,
        _run_architecture, project, pconfig, user_id,
    )


def _run_architecture(emitter: SSEEmitter, project: dict, pconfig: dict, user_id: str, task_id: str | None = None):
    """复用 novel_generator.Novel_architecture_generate，消除重复逻辑"""
    from novel_generator.architecture import Novel_architecture_generate

    llm_conf = _resolve_llm(user_id, pconfig.get("architecture_llm", ""))
    emb_conf = _resolve_emb(user_id, pconfig.get("embedding_config", ""))

    ctx = _make_ctx(llm_conf, emb_conf, project["filepath"], project_id=project["id"])
    proj_cfg = _make_project_cfg(pconfig)

    Novel_architecture_generate(ctx, proj_cfg, emitter=emitter, task_id=task_id)
    project_service.update_project(project["id"], {"status": "ready"}, user_id)


# ── 蓝本章节目录生成 ──

@router.post("/api/v1/projects/{project_id}/generate/blueprint")
@router.get("/api/v1/projects/{project_id}/generate/blueprint")
async def generate_blueprint(project_id: str, request: Request, task_id: str | None = None):
    project, pconfig, user_id = _check_project(project_id, request)
    resolved_task_id = _prepare_generation_task(
        project_id,
        "blueprint",
        task_id,
        {"project_name": project.get("name", ""), "chapter_count": pconfig.get("num_chapters", 0)},
    )
    return _make_streaming_response(
        request, asyncio.Queue(), SSEEmitter(), resolved_task_id,
        _run_blueprint, project, pconfig, user_id,
    )


def _run_blueprint(emitter: SSEEmitter, project: dict, pconfig: dict, user_id: str, task_id: str | None = None):
    """复用 novel_generator.Chapter_blueprint_generate"""
    from novel_generator.blueprint import Chapter_blueprint_generate

    _require_project_file(project["filepath"], "Novel_architecture.txt", "小说架构")
    llm_conf = _resolve_llm(user_id, pconfig.get("chapter_outline_llm", ""))
    ctx = _make_ctx(llm_conf, {}, project["filepath"], project_id=project["id"])
    proj_cfg = _make_project_cfg(pconfig)

    Chapter_blueprint_generate(ctx, proj_cfg, emitter=emitter, task_id=task_id)
    if task_id:
        raise_if_cancelled(task_id)
    chapter_service.sync_chapters_from_directory(project["id"], project["filepath"])


# ── 章节草稿生成 ──

@router.post("/api/v1/projects/{project_id}/generate/chapter/{chapter_number}")
@router.get("/api/v1/projects/{project_id}/generate/chapter/{chapter_number}")
async def generate_chapter(project_id: str, chapter_number: int, request: Request, task_id: str | None = None):
    project, pconfig, user_id = _check_project(project_id, request)
    resolved_task_id = _prepare_generation_task(
        project_id,
        "chapter",
        task_id,
        {"project_name": project.get("name", ""), "chapter_number": chapter_number},
    )
    return _make_streaming_response(
        request, asyncio.Queue(), SSEEmitter(), resolved_task_id,
        _run_chapter_generation, project, pconfig, chapter_number, user_id,
    )


@router.post("/api/v1/projects/{project_id}/generate/chapters")
@router.get("/api/v1/projects/{project_id}/generate/chapters")
async def generate_chapter_batch(project_id: str, request: Request, start_chapter: int = 1, count: int = 1, task_id: str | None = None):
    if start_chapter < 1:
        raise HTTPException(status_code=400, detail="起始章节必须大于 0")
    if count < 1 or count > 20:
        raise HTTPException(status_code=400, detail="本轮生成章数必须在 1 到 20 之间")
    project, pconfig, user_id = _check_project(project_id, request)
    resolved_task_id = _prepare_generation_task(
        project_id,
        "chapter_batch",
        task_id,
        {"project_name": project.get("name", ""), "start_chapter": start_chapter, "count": count},
    )
    return _make_streaming_response(
        request, asyncio.Queue(), SSEEmitter(), resolved_task_id,
        _run_chapter_batch_generation, project, pconfig, start_chapter, count, user_id,
    )


def _run_chapter_batch_generation(
    emitter: SSEEmitter,
    project: dict,
    pconfig: dict,
    start_chapter: int,
    count: int,
    user_id: str,
    task_id: str | None = None,
):
    for offset in range(count):
        chapter_number = start_chapter + offset
        emitter.emit("progress", {
            "step": "batch",
            "status": "running",
            "message": f"开始生成第{chapter_number}章（{offset + 1}/{count}）",
        })
        _run_chapter_generation(emitter, project, pconfig, chapter_number, user_id, task_id=task_id)


def _run_chapter_generation(emitter: SSEEmitter, project: dict, pconfig: dict, chapter_number: int, user_id: str, task_id: str | None = None):
    """复用 novel_generator.build_chapter_prompt + generate_chapter_draft"""
    from novel_generator.chapter import build_chapter_prompt, generate_chapter_draft

    _require_project_file(project["filepath"], "Novel_architecture.txt", "小说架构")
    _require_project_file(project["filepath"], "Novel_directory.txt", "章节目录")
    llm_conf = _resolve_llm(user_id, pconfig.get("prompt_draft_llm", ""))
    emb_conf = _resolve_emb(user_id, pconfig.get("embedding_config", ""))

    ctx = _make_ctx(llm_conf, emb_conf, project["filepath"], project_id=project["id"])
    params = _make_chapter_params(pconfig, chapter_number)

    emitter.emit("progress", {"step": "build_prompt", "status": "running",
                               "message": f"正在构建第{chapter_number}章提示词..."})

    prompt_text = build_chapter_prompt(ctx, params, task_id=task_id)
    emitter.emit("progress", {"step": "build_prompt", "status": "done", "message": "提示词构建完成"})

    emitter.emit("progress", {"step": "draft", "status": "running",
                               "message": f"正在生成第{chapter_number}章草稿..."})

    draft_text = generate_chapter_draft(ctx, params, custom_prompt_text=prompt_text, task_id=task_id)

    if draft_text:
        if task_id:
            raise_if_cancelled(task_id)
        from utils import get_word_count
        wc = get_word_count(draft_text)
        chapter_service.mark_chapter_draft(project["id"], chapter_number, wc)
        emitter.emit("progress", {"step": "draft", "status": "done",
                                   "message": f"第{chapter_number}章草稿生成完成"})
        emitter.emit("partial", {"step": "draft", "content": draft_text[:500] + "..."})
    else:
        emitter.emit("error", {"step": "draft", "message": "草稿生成返回空内容"})


# ── 定稿 ──

@router.post("/api/v1/projects/{project_id}/generate/finalize/{chapter_number}")
@router.get("/api/v1/projects/{project_id}/generate/finalize/{chapter_number}")
async def finalize_chapter_route(project_id: str, chapter_number: int, request: Request, task_id: str | None = None):
    project, pconfig, user_id = _check_project(project_id, request)
    resolved_task_id = _prepare_generation_task(
        project_id,
        "finalize",
        task_id,
        {"project_name": project.get("name", ""), "chapter_number": chapter_number},
    )
    return _make_streaming_response(
        request, asyncio.Queue(), SSEEmitter(), resolved_task_id,
        _run_finalize, project, pconfig, chapter_number, user_id,
    )


def _run_finalize(emitter: SSEEmitter, project: dict, pconfig: dict, chapter_number: int, user_id: str, task_id: str | None = None):
    """复用 novel_generator.finalize_chapter"""
    from novel_generator.finalization import finalize_chapter

    chapter_filename = os.path.join("chapters", f"chapter_{chapter_number}.txt")
    _require_project_file(project["filepath"], chapter_filename, f"第{chapter_number}章草稿")
    llm_conf = _resolve_llm(user_id, pconfig.get("final_chapter_llm", ""))
    emb_conf = _resolve_emb(user_id, pconfig.get("embedding_config", ""))

    ctx = _make_ctx(llm_conf, emb_conf, project["filepath"], project_id=project["id"])
    params = _make_chapter_params(pconfig, chapter_number)

    emitter.emit("progress", {"step": "finalize", "status": "running",
                               "message": f"正在定稿第{chapter_number}章..."})

    finalize_chapter(ctx, params, emitter=emitter, task_id=task_id)
    if task_id:
        raise_if_cancelled(task_id)

    from utils import get_word_count
    chapter_text = read_file(os.path.join(project["filepath"], "chapters", f"chapter_{chapter_number}.txt"))
    wc = get_word_count(chapter_text)
    chapter_service.mark_chapter_final(project["id"], chapter_number, wc)

    emitter.emit("progress", {"step": "finalize", "status": "done",
                               "message": f"第{chapter_number}章定稿完成"})
