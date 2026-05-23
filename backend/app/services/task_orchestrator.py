import logging
import time
import uuid
from typing import Callable, Optional

from fastapi import HTTPException

from backend.app.utils.sse import SSEEmitter
from llm_errors import LLMInvocationError, coerce_error_info
from novel_generator.task_manager import (
    TaskCancelledError,
    finish_task,
    get_active_task,
    get_task,
    register_task,
    update_task_status,
)

logger = logging.getLogger(__name__)


def _task_label(kind: str) -> str:
    return {
        "generate_architecture": "架构生成",
        "generate_outline": "章节目录生成",
        "generate_chapter": "章节草稿生成",
        "generate_chapter_batch": "批量章节生成",
        "finalize_chapter": "章节定稿",
    }.get(kind, kind)


def prepare_generation_task(
    project_id: str, user_id: str, kind: str, task_id: Optional[str], metadata: dict
) -> str:
    """注册和验证新的生成任务，确保没有冲突。"""
    resolved_task_id = task_id or uuid.uuid4().hex
    existing_task = get_task(resolved_task_id)
    if existing_task and existing_task.status not in {"done", "failed", "cancelled"}:
        if existing_task.project_id != project_id:
            raise HTTPException(status_code=409, detail="该任务标识已在运行，请先取消当前任务后再开始新的生成")
        return resolved_task_id

    state = register_task(resolved_task_id, project_id, kind, user_id=user_id, metadata=metadata)
    if state.task_id == resolved_task_id:
        active = get_active_task(project_id)
        if active and active.task_id != resolved_task_id:
            state.status = "cancelled"
            state.finished_at = time.time()
            raise HTTPException(
                status_code=409,
                detail=f"项目正在执行{_task_label(active.kind)}，请先中断后再开始新的生成",
            )
    return resolved_task_id


def build_terminal_error_payload(task_id: str, step: str, message: str, **extra) -> dict:
    payload = {
        "step": step,
        "message": message,
        "task_id": task_id,
        "status": "failed",
        "terminal": True,
    }
    payload.update({key: value for key, value in extra.items() if value is not None})
    return payload


def run_orchestrated_task(emitter: SSEEmitter, task_id: str, func: Callable, *args, **kwargs):
    """
    负责在后台执行具体的生成逻辑，并包装统一的错误拦截与状态回调。
    消灭静默异常。
    """
    update_task_status(task_id, "running")
    try:
        func(emitter, *args, task_id=task_id, **kwargs)
    except TaskCancelledError as exc:
        finish_task(task_id, "cancelled", str(exc))
        emitter.emit("cancelled", {"message": str(exc), "status": "cancelled", "task_id": task_id})
    except LLMInvocationError as exc:
        payload = exc.to_payload()
        info = coerce_error_info(payload)
        logger.warning(
            "Generation task provider failure [task_id=%s func=%s code=%s status=%s model=%s]: %s",
            task_id,
            func.__name__,
            info.code if info else payload.get("code"),
            info.status_code if info else payload.get("status_code"),
            info.model_name if info else payload.get("model_name"),
            info.detail if info else payload.get("detail"),
        )
        message = str(exc)
        finish_task(task_id, "failed", message)
        emitter.emit(
            "error",
            build_terminal_error_payload(
                task_id,
                payload.get("step") or "llm",
                message,
                error_code=payload.get("code"),
                error_category=payload.get("category"),
                detail=payload.get("detail"),
                retryable=payload.get("retryable"),
                provider=payload.get("provider"),
                model_name=payload.get("model_name"),
                status_code=payload.get("status_code"),
            ),
        )
        emitter.emit("done", build_terminal_error_payload(task_id, payload.get("step") or "llm", message))
    except HTTPException as exc:
        message = str(exc.detail)
        finish_task(task_id, "failed", message)
        emitter.emit("error", build_terminal_error_payload(task_id, "request", message))
        emitter.emit("done", build_terminal_error_payload(task_id, "request", message))
    except Exception as exc:
        # 这里记录完整的 traceback，前端不再只有模糊的 "任务失败"
        logger.exception("Generation task failed with unhandled exception")
        message = f"生成任务异常崩溃: {str(exc)}"
        finish_task(task_id, "failed", message)
        emitter.emit("error", build_terminal_error_payload(task_id, "server", message))
        emitter.emit("done", build_terminal_error_payload(task_id, "server", message))
    else:
        finish_task(task_id, "done", "完成")
        emitter.emit("done", {"message": "完成", "status": "done", "task_id": task_id})
