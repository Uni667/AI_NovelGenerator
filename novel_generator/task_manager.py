"""Lightweight cooperative task registry and cancellation helpers with DB persistence."""

from __future__ import annotations

import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

TERMINAL_STATUSES = {"done", "failed", "cancelled"}
ACTIVE_STATUSES = {"running", "cancelling"}


class TaskCancelledError(RuntimeError):
    """Raised when a generation task is cancelled by the user."""


@dataclass
class TaskState:
    task_id: str
    project_id: str
    kind: str
    status: str = "running"
    message: str = ""
    cancel_requested: bool = False
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None
    metadata: dict[str, Any] = field(default_factory=dict)


_TASKS: dict[str, TaskState] = {}
_CANCEL_TOKENS: dict[str, object] = {}  # task_id → CancelToken
_LOCK = threading.RLock()


def _persist_task_to_db(state: TaskState) -> None:
    """将任务状态写入数据库（惰性导入避免循环依赖）。"""
    try:
        import datetime

        from backend.app.database import get_db

        now_str = datetime.datetime.now().isoformat()
        created_str = datetime.datetime.fromtimestamp(state.created_at).isoformat()
        finished_str = (
            datetime.datetime.fromtimestamp(state.finished_at).isoformat()
            if state.finished_at
            else None
        )
        error_message = state.message if state.status == "failed" else None
        error_code = state.metadata.get("error_code") if state.metadata else None
        error_category = state.metadata.get("error_category") if state.metadata else None
        retryable = 1 if (state.metadata or {}).get("retryable") else 0
        input_snapshot = (state.metadata or {}).get("input_snapshot", "")
        output_file_id = (state.metadata or {}).get("output_file_id")

        with get_db() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO generation_task
                   (id, project_id, type, status, input_snapshot, output_file_id,
                    error_message, error_code, error_category, retryable,
                    created_at, updated_at, finished_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    state.task_id,
                    state.project_id,
                    state.kind,
                    state.status,
                    input_snapshot,
                    output_file_id,
                    error_message,
                    error_code,
                    error_category,
                    retryable,
                    created_str,
                    now_str,
                    finished_str,
                ),
            )
    except Exception:
        pass  # 持久化失败不阻断内存操作


def load_tasks_from_db() -> None:
    """从数据库恢复任务状态到内存（服务器启动时调用）。"""
    try:
        from backend.app.database import get_db

        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM generation_task WHERE status IN ('running','pending')"
            ).fetchall()
        for row in rows:
            r = dict(row)
            created = time.mktime(
                time.strptime(r["created_at"], "%Y-%m-%dT%H:%M:%S.%f")
            ) if "." in r["created_at"] else time.mktime(
                time.strptime(r["created_at"], "%Y-%m-%dT%H:%M:%S")
            ) if "T" in r["created_at"] else time.time()
            state = TaskState(
                task_id=r["id"],
                project_id=r["project_id"],
                kind=r["type"],
                status="failed",
                message="服务器重启导致任务中断",
                created_at=created,
                metadata={
                    "output_file_id": r.get("output_file_id"),
                    "error_code": r.get("error_code"),
                    "error_category": r.get("error_category"),
                    "input_snapshot": r.get("input_snapshot", ""),
                },
            )
            _TASKS[state.task_id] = state
    except Exception:
        pass


def _cleanup_finished_tasks_locked(max_age_seconds: int = 86400) -> None:
    now = time.time()
    stale_ids = [
        task_id
        for task_id, state in _TASKS.items()
        if state.status in TERMINAL_STATUSES
        and state.finished_at is not None
        and now - state.finished_at > max_age_seconds
    ]
    for task_id in stale_ids:
        _TASKS.pop(task_id, None)


def register_task(
    task_id: str,
    project_id: str,
    kind: str,
    metadata: Optional[dict[str, Any]] = None,
) -> TaskState:
    now = time.time()
    with _LOCK:
        _cleanup_finished_tasks_locked()
        existing = _TASKS.get(task_id)
        if existing and existing.status in ACTIVE_STATUSES:
            return existing
        state = TaskState(
            task_id=task_id,
            project_id=project_id,
            kind=kind,
            metadata=dict(metadata or {}),
            created_at=now,
            updated_at=now,
        )
        _TASKS[task_id] = state
        _persist_task_to_db(state)
        return state


def get_task(task_id: str) -> Optional[TaskState]:
    with _LOCK:
        _cleanup_finished_tasks_locked()
        return _TASKS.get(task_id)


def get_active_task(project_id: str, kind: str | None = None) -> Optional[TaskState]:
    with _LOCK:
        _cleanup_finished_tasks_locked()
        for state in _TASKS.values():
            if state.project_id != project_id:
                continue
            if state.status not in ACTIVE_STATUSES:
                continue
            if kind and state.kind != kind:
                continue
            return state
        return None


def list_tasks(project_id: str | None = None) -> list[TaskState]:
    with _LOCK:
        _cleanup_finished_tasks_locked()
        tasks = list(_TASKS.values())
    if project_id:
        return [task for task in tasks if task.project_id == project_id]
    return tasks


def update_task(task_id: str, **changes: Any) -> Optional[TaskState]:
    with _LOCK:
        state = _TASKS.get(task_id)
        if not state:
            return None
        for key, value in changes.items():
            if hasattr(state, key) and value is not None:
                setattr(state, key, value)
        state.updated_at = time.time()
        _persist_task_to_db(state)
        return state


def bind_cancel_token(task_id: str, cancel_token) -> None:
    """Associate a CancelToken with a task for transport-level abort."""
    with _LOCK:
        _CANCEL_TOKENS[task_id] = cancel_token


def unbind_cancel_token(task_id: str) -> None:
    with _LOCK:
        _CANCEL_TOKENS.pop(task_id, None)


def request_cancel(task_id: str) -> Optional[TaskState]:
    with _LOCK:
        state = _TASKS.get(task_id)
        if not state:
            return None
        if state.status in TERMINAL_STATUSES:
            return state
        state.cancel_requested = True
        state.status = "cancelling"
        state.message = state.message or "用户请求中断"
        state.updated_at = time.time()

        # ── 触发 HTTP 传输层 abort ──
        token = _CANCEL_TOKENS.get(task_id)
        if token is not None:
            try:
                token.cancel()
            except Exception:
                pass

        _persist_task_to_db(state)
        return state


def is_cancel_requested(task_id: str) -> bool:
    with _LOCK:
        state = _TASKS.get(task_id)
        return bool(state and state.cancel_requested)


def raise_if_cancelled(task_id: Optional[str]) -> None:
    if task_id and is_cancel_requested(task_id):
        state = get_task(task_id)
        label = state.kind if state else "任务"
        raise TaskCancelledError(f"{label}已取消")


def finish_task(task_id: str, status: str, message: str) -> Optional[TaskState]:
    with _LOCK:
        state = _TASKS.get(task_id)
        if not state:
            return None
        state.status = status
        state.message = message
        state.updated_at = time.time()
        state.finished_at = state.updated_at
        _persist_task_to_db(state)
        return state


def task_payload(task_id: str) -> dict[str, Any]:
    state = get_task(task_id)
    if not state:
        return {}
    d = asdict(state)
    # 将 metadata 字段映射到外部期望的名称
    if state.metadata.get("output_file_id"):
        d["output_file_id"] = state.metadata["output_file_id"]
    if state.metadata.get("error_code"):
        d["error_code"] = state.metadata["error_code"]
    if state.metadata.get("error_category"):
        d["error_category"] = state.metadata["error_category"]
    return d
