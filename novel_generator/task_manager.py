"""Lightweight cooperative task registry and cancellation helpers."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field, asdict
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
_LOCK = threading.RLock()


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
        return state


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
        return state


def task_payload(task_id: str) -> dict[str, Any]:
    state = get_task(task_id)
    if not state:
        return {}
    return asdict(state)

