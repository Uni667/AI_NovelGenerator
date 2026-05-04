import asyncio
import logging
import os
import uuid

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from backend.app.auth import get_current_user
from backend.app.services import chapter_service, file_service, project_service
from backend.app.services.model_runtime import ConfigError, RuntimeConfig, call_chat, call_embedding, create_chat_adapter, create_embedding_adapter, get_runtime_config, mark_used
from backend.app.utils.sse import HEARTBEAT, SSEEmitter, sse_event_generator
from llm_errors import LLMInvocationError, coerce_error_info
from novel_generator.cancel_token import CancelToken
from novel_generator.context import ChapterParams, GenerationContext, ProjectConfig
from novel_generator.task_manager import (
    TaskCancelledError,
    bind_cancel_token,
    finish_task,
    get_active_task,
    get_task,
    raise_if_cancelled,
    register_task,
    request_cancel,
    task_payload,
    unbind_cancel_token,
)
from utils import read_file

router = APIRouter(tags=["AI 生成"])
logger = logging.getLogger(__name__)


def _check_project(project_id: str, request: Request) -> tuple[dict, dict, str]:
    user_id = get_current_user(request)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    pconfig = project_service.get_project_config(project_id)
    if not pconfig:
        raise HTTPException(status_code=404, detail="项目配置不存在")
    return project, pconfig, user_id


def _get_runtime_config(user_id: str, purpose: str, project_id: str) -> RuntimeConfig:
    """获取指定用途的运行时配置。所有模型调用的唯一入口。"""
    try:
        return get_runtime_config(user_id, purpose, project_id)
    except ConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))


def _runtime_to_llm_conf(rt: RuntimeConfig) -> dict:
    return {
        "api_key": rt.api_key,
        "base_url": rt.base_url,
        "model_name": rt.model,
        "interface_format": "OpenAI",
        "temperature": rt.temperature or 0.7,
        "max_tokens": rt.max_tokens or 8192,
        "timeout": 600,
    }


def _runtime_to_emb_conf(rt: RuntimeConfig) -> dict:
    return {
        "api_key": rt.api_key,
        "base_url": rt.base_url,
        "model_name": rt.model,
        "interface_format": "OpenAI",
    }


def _make_ctx(
    llm_conf: dict,
    emb_conf: dict,
    filepath: str,
    project_id: str = "",
    cancel_token: CancelToken | None = None,
) -> GenerationContext:
    return GenerationContext.from_dicts(
        llm_dict=llm_conf,
        emb_dict=emb_conf,
        filepath=filepath,
        project_id=project_id,
        cancel_token=cancel_token,
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
        raise HTTPException(status_code=409, detail="该任务标识已在运行，请先取消当前任务后再开始新的生成")

    active_task = get_active_task(project_id)
    if active_task and active_task.task_id != resolved_task_id:
        raise HTTPException(
            status_code=409,
            detail=f"项目正在执行{_task_label(active_task.kind)}，请先中断后再开始新的生成",
        )

    register_task(resolved_task_id, project_id, kind, metadata)
    return resolved_task_id


def _mask_api_key(api_key: str) -> str:
    api_key = (api_key or "").strip()
    if not api_key:
        return ""
    if len(api_key) <= 8:
        return "*" * len(api_key)
    return f"{api_key[:4]}***{api_key[-4:]}"


def _sanitize_base_url(base_url: str) -> str:
    return (base_url or "").strip().rstrip("/")


def _log_llm_selection(task_id: str, project: dict, llm_conf: dict, kind: str) -> None:
    logger.info(
        "Generation preflight [task_id=%s kind=%s project_id=%s project_name=%s provider=%s model=%s base_url=%s api_key=%s timeout=%s max_tokens=%s]",
        task_id,
        kind,
        project.get("id"),
        project.get("name"),
        llm_conf.get("interface_format", ""),
        llm_conf.get("model_name", ""),
        _sanitize_base_url(llm_conf.get("base_url", "")),
        _mask_api_key(llm_conf.get("api_key", "")),
        llm_conf.get("timeout"),
        llm_conf.get("max_tokens"),
    )


def _build_terminal_error_payload(task_id: str, step: str, message: str, **extra) -> dict[str, object]:
    payload: dict[str, object] = {
        "step": step,
        "message": message,
        "task_id": task_id,
        "status": "failed",
        "terminal": True,
    }
    payload.update({key: value for key, value in extra.items() if value is not None})
    return payload


def _run_in_thread(emitter: SSEEmitter, task_id: str, func, *args, **kwargs):
    try:
        func(emitter, *args, task_id=task_id, **kwargs)
    except TaskCancelledError as exc:
        finish_task(task_id, "cancelled", str(exc))
        emitter.emit("cancelled", {"message": str(exc), "status": "cancelled", "task_id": task_id})
    except LLMInvocationError as exc:
        payload = exc.to_payload()
        info = coerce_error_info(payload)
        logger.warning(
            "Generation task provider failure [task_id=%s func=%s category=%s code=%s status=%s provider=%s model=%s base_url=%s]: %s",
            task_id,
            func.__name__,
            info.category if info else payload.get("category"),
            info.code if info else payload.get("code"),
            info.status_code if info else payload.get("status_code"),
            info.provider if info else payload.get("provider"),
            info.model_name if info else payload.get("model_name"),
            info.base_url if info else payload.get("base_url"),
            info.detail if info else payload.get("detail"),
        )
        message = str(exc)
        finish_task(task_id, "failed", message)
        emitter.emit(
            "error",
            _build_terminal_error_payload(
                task_id,
                payload.get("step") or "llm",
                message,
                error_code=payload.get("code"),
                error_category=payload.get("category"),
                detail=payload.get("detail"),
                retryable=payload.get("retryable"),
                provider=payload.get("provider"),
                model_name=payload.get("model_name"),
                base_url=payload.get("base_url"),
                status_code=payload.get("status_code"),
                operation=payload.get("operation"),
            ),
        )
        emitter.emit(
            "done",
            _build_terminal_error_payload(
                task_id,
                payload.get("step") or "llm",
                message,
                error_code=payload.get("code"),
                error_category=payload.get("category"),
            ),
        )
    except HTTPException as exc:
        message = str(exc.detail)
        finish_task(task_id, "failed", message)
        emitter.emit("error", _build_terminal_error_payload(task_id, "request", message))
        emitter.emit("done", _build_terminal_error_payload(task_id, "request", message))
    except Exception as exc:
        logger.exception("Generation task failed")
        message = f"{func.__name__} 执行失败: {exc}"
        finish_task(task_id, "failed", message)
        emitter.emit("error", _build_terminal_error_payload(task_id, "server", message))
        emitter.emit("done", _build_terminal_error_payload(task_id, "server", message))
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
        request,
        asyncio.Queue(),
        SSEEmitter(),
        resolved_task_id,
        _run_architecture,
        project,
        pconfig,
        user_id,
    )


def _run_architecture(emitter: SSEEmitter, project: dict, pconfig: dict, user_id: str, task_id: str | None = None):
    from novel_generator.architecture import Novel_architecture_generate

    cancel_token = CancelToken()
    previous_status = project.get("status", "draft")
    if task_id:
        bind_cancel_token(task_id, cancel_token)

    rt = _get_runtime_config(user_id, "architecture", project["id"])
    llm_conf = _runtime_to_llm_conf(rt)
    emb_conf = _runtime_to_emb_conf(rt)
    if task_id:
        _log_llm_selection(task_id, project, llm_conf, "architecture")

    ctx = _make_ctx(llm_conf, emb_conf, project["filepath"], project_id=project["id"], cancel_token=cancel_token)
    proj_cfg = _make_project_cfg(pconfig)

    try:
        project_service.update_project(project["id"], {"status": "generating"}, user_id)
        Novel_architecture_generate(ctx, proj_cfg, emitter=emitter, task_id=task_id)

        arch_path = os.path.join(project["filepath"], "Novel_architecture.txt")
        arch_content = read_file(arch_path) if os.path.exists(arch_path) else ""
        if arch_content.strip():
            file_service.create_project_file(
                project_id=project["id"],
                type="architecture",
                title=f"{project.get('name', '')} 架构",
                filename="Novel_architecture.txt",
                content=arch_content,
                source="ai_generated",
                is_current=True,
            )

        project_service.update_project(project["id"], {"status": "ready"}, user_id)
        mark_used(user_id, rt.api_credential_id, rt.model_profile_id)
    except Exception:
        project_service.update_project(project["id"], {"status": previous_status}, user_id)
        raise
    finally:
        if task_id:
            unbind_cancel_token(task_id)


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
        request,
        asyncio.Queue(),
        SSEEmitter(),
        resolved_task_id,
        _run_blueprint,
        project,
        pconfig,
        user_id,
    )


def _run_blueprint(emitter: SSEEmitter, project: dict, pconfig: dict, user_id: str, task_id: str | None = None):
    from novel_generator.blueprint import Chapter_blueprint_generate

    cancel_token = CancelToken()
    if task_id:
        bind_cancel_token(task_id, cancel_token)

    _require_project_file(project["filepath"], "Novel_architecture.txt", "小说架构")
    rt = _get_runtime_config(user_id, "outline", project["id"])
    llm_conf = _runtime_to_llm_conf(rt)
    if task_id:
        _log_llm_selection(task_id, project, llm_conf, "blueprint")
    ctx = _make_ctx(llm_conf, {}, project["filepath"], project_id=project["id"], cancel_token=cancel_token)
    proj_cfg = _make_project_cfg(pconfig)

    try:
        Chapter_blueprint_generate(ctx, proj_cfg, emitter=emitter, task_id=task_id)
        if task_id:
            raise_if_cancelled(task_id)

        dir_path = os.path.join(project["filepath"], "Novel_directory.txt")
        dir_content = read_file(dir_path) if os.path.exists(dir_path) else ""
        if dir_content.strip():
            file_service.create_project_file(
                project_id=project["id"],
                type="outline",
                title=f"{project.get('name', '')} 章节目录",
                filename="Novel_directory.txt",
                content=dir_content,
                source="ai_generated",
                is_current=True,
            )

        chapter_service.sync_chapters_from_directory(project["id"], project["filepath"])
    finally:
        if task_id:
            unbind_cancel_token(task_id)


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
        request,
        asyncio.Queue(),
        SSEEmitter(),
        resolved_task_id,
        _run_chapter_generation,
        project,
        pconfig,
        chapter_number,
        user_id,
    )


@router.post("/api/v1/projects/{project_id}/generate/chapters")
@router.get("/api/v1/projects/{project_id}/generate/chapters")
async def generate_chapter_batch(
    project_id: str,
    request: Request,
    start_chapter: int = 1,
    count: int = 1,
    task_id: str | None = None,
):
    if start_chapter < 1:
        raise HTTPException(status_code=400, detail="起始章节必须大于 0")
    if count < 1 or count > 20:
        raise HTTPException(status_code=400, detail="本轮生成章节数必须在 1 到 20 之间")
    project, pconfig, user_id = _check_project(project_id, request)
    resolved_task_id = _prepare_generation_task(
        project_id,
        "chapter_batch",
        task_id,
        {"project_name": project.get("name", ""), "start_chapter": start_chapter, "count": count},
    )
    return _make_streaming_response(
        request,
        asyncio.Queue(),
        SSEEmitter(),
        resolved_task_id,
        _run_chapter_batch_generation,
        project,
        pconfig,
        start_chapter,
        count,
        user_id,
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
    cancel_token = CancelToken()
    if task_id:
        bind_cancel_token(task_id, cancel_token)
    try:
        for offset in range(count):
            chapter_number = start_chapter + offset
            emitter.emit(
                "progress",
                {
                    "step": "batch",
                    "status": "running",
                    "message": f"开始生成第 {chapter_number} 章（{offset + 1}/{count}）",
                },
            )
            _run_chapter_generation(
                emitter,
                project,
                pconfig,
                chapter_number,
                user_id,
                task_id=task_id,
                cancel_token=cancel_token,
            )
    finally:
        if task_id:
            unbind_cancel_token(task_id)


def _run_chapter_generation(
    emitter: SSEEmitter,
    project: dict,
    pconfig: dict,
    chapter_number: int,
    user_id: str,
    task_id: str | None = None,
    cancel_token: CancelToken | None = None,
):
    from novel_generator.chapter import build_chapter_prompt, generate_chapter_draft

    if cancel_token is None:
        cancel_token = CancelToken()
        if task_id:
            bind_cancel_token(task_id, cancel_token)
        own_token = True
    else:
        own_token = False

    try:
        _require_project_file(project["filepath"], "Novel_architecture.txt", "小说架构")
        _require_project_file(project["filepath"], "Novel_directory.txt", "章节目录")
        rt = _get_runtime_config(user_id, "draft", project["id"])
        llm_conf = _runtime_to_llm_conf(rt)
        emb_conf = _runtime_to_emb_conf(rt)
        if task_id:
            _log_llm_selection(task_id, project, llm_conf, "chapter")

        ctx = _make_ctx(llm_conf, emb_conf, project["filepath"], project_id=project["id"], cancel_token=cancel_token)
        params = _make_chapter_params(pconfig, chapter_number)

        emitter.emit(
            "progress",
            {"step": "build_prompt", "status": "running", "message": f"正在构建第 {chapter_number} 章提示词..."},
        )
        prompt_text = build_chapter_prompt(ctx, params, task_id=task_id)
        emitter.emit("progress", {"step": "build_prompt", "status": "done", "message": "提示词构建完成"})

        emitter.emit("progress", {"step": "draft", "status": "running", "message": f"正在生成第 {chapter_number} 章草稿..."})
        draft_text = generate_chapter_draft(ctx, params, custom_prompt_text=prompt_text, task_id=task_id)

        if draft_text:
            if task_id:
                raise_if_cancelled(task_id)
            from utils import get_word_count

            wc = get_word_count(draft_text)
            chapter_service.mark_chapter_draft(project["id"], chapter_number, wc)
            emitter.emit("progress", {"step": "draft", "status": "done", "message": f"第 {chapter_number} 章草稿生成完成"})
            emitter.emit("partial", {"step": "draft", "content": draft_text[:500] + "..."})
        else:
            emitter.emit(
                "error",
                _build_terminal_error_payload(task_id or "", "draft", "草稿生成返回空内容"),
            )
    finally:
        if own_token and task_id:
            unbind_cancel_token(task_id)


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
        request,
        asyncio.Queue(),
        SSEEmitter(),
        resolved_task_id,
        _run_finalize,
        project,
        pconfig,
        chapter_number,
        user_id,
    )


def _run_finalize(
    emitter: SSEEmitter,
    project: dict,
    pconfig: dict,
    chapter_number: int,
    user_id: str,
    task_id: str | None = None,
):
    from novel_generator.finalization import finalize_chapter

    cancel_token = CancelToken()
    if task_id:
        bind_cancel_token(task_id, cancel_token)

    try:
        chapter_filename = os.path.join("chapters", f"chapter_{chapter_number}.txt")
        _require_project_file(project["filepath"], chapter_filename, f"第 {chapter_number} 章草稿")
        rt = _get_runtime_config(user_id, "polish", project["id"])
        llm_conf = _runtime_to_llm_conf(rt)
        emb_conf = _runtime_to_emb_conf(rt)
        if task_id:
            _log_llm_selection(task_id, project, llm_conf, "finalize")

        ctx = _make_ctx(llm_conf, emb_conf, project["filepath"], project_id=project["id"], cancel_token=cancel_token)
        params = _make_chapter_params(pconfig, chapter_number)

        emitter.emit("progress", {"step": "finalize", "status": "running", "message": f"正在定稿第 {chapter_number} 章..."})
        finalize_chapter(ctx, params, emitter=emitter, task_id=task_id)
        if task_id:
            raise_if_cancelled(task_id)

        from utils import get_word_count

        chapter_text = read_file(os.path.join(project["filepath"], "chapters", f"chapter_{chapter_number}.txt"))
        wc = get_word_count(chapter_text)
        chapter_service.mark_chapter_final(project["id"], chapter_number, wc)
        emitter.emit("progress", {"step": "finalize", "status": "done", "message": f"第 {chapter_number} 章定稿完成"})
    finally:
        if task_id:
            unbind_cancel_token(task_id)


# ── 新增：任务列表、任务重试 ──

@router.get("/api/v1/projects/{project_id}/generate/tasks")
def list_generation_tasks(project_id: str, request: Request):
    _check_project(project_id, request)
    from novel_generator.task_manager import list_tasks, task_payload

    tasks = list_tasks(project_id)
    results = [task_payload(t.task_id) for t in tasks]
    results.sort(key=lambda p: p.get("created_at", 0), reverse=True)
    return results


@router.post("/api/v1/projects/{project_id}/generate/tasks/{task_id}/retry")
async def retry_generation_task(project_id: str, task_id: str, request: Request):
    project, pconfig, user_id = _check_project(project_id, request)
    from novel_generator.task_manager import get_task

    task = get_task(task_id)
    if not task or task.project_id != project_id:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.status not in ("failed", "cancelled"):
        raise HTTPException(status_code=400, detail="只能重试失败或已取消的任务")

    kind = task.kind
    metadata = task.metadata or {}
    if kind == "architecture":
        return await generate_architecture(project_id, request, task_id=task_id)
    elif kind == "blueprint":
        return await generate_blueprint(project_id, request, task_id=task_id)
    elif kind == "finalize":
        chapter_num = metadata.get("chapter_number", 1)
        return await finalize_chapter_route(project_id, chapter_num, request, task_id=task_id)
    elif kind == "chapter":
        chapter_num = metadata.get("chapter_number", 1)
        return await generate_chapter(project_id, chapter_num, request, task_id=task_id)
    elif kind == "chapter_batch":
        start = metadata.get("start_chapter", 1)
        count = metadata.get("count", 1)
        return await generate_chapter_batch(project_id, request, start_chapter=start, count=count, task_id=task_id)
    else:
        raise HTTPException(status_code=400, detail=f"不支持重试该任务类型: {kind}")
