import asyncio
import json
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

HEARTBEAT = object()
MAX_EVENT_HISTORY = 500


@dataclass
class TaskStream:
    task_id: str
    lock: threading.RLock = field(default_factory=threading.RLock)
    listeners: set[tuple[asyncio.Queue, asyncio.AbstractEventLoop]] = field(default_factory=set)
    history: deque[dict] = field(default_factory=lambda: deque(maxlen=MAX_EVENT_HISTORY))
    terminal: bool = False
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


_STREAMS: dict[str, TaskStream] = {}
_STREAMS_LOCK = threading.RLock()


def _get_or_create_stream(task_id: str) -> TaskStream:
    with _STREAMS_LOCK:
        stream = _STREAMS.get(task_id)
        if stream is None:
            stream = TaskStream(task_id=task_id)
            _STREAMS[task_id] = stream
        return stream


def _is_terminal_event(event: str) -> bool:
    return event in {"done", "cancelled"}


def _dispatch_event(stream: TaskStream, payload: dict) -> None:
    dead_listeners: list[tuple[asyncio.Queue, asyncio.AbstractEventLoop]] = []
    for queue, loop in list(stream.listeners):
        try:
            async def _put():
                await queue.put(payload)
                if payload.get("event") in {"done", "cancelled"}:
                    await queue.put(None)

            asyncio.run_coroutine_threadsafe(_put(), loop)
        except Exception:
            dead_listeners.append((queue, loop))

    if dead_listeners:
        with stream.lock:
            for listener in dead_listeners:
                stream.listeners.discard(listener)


class SSEEmitter:
    """Task-scoped broadcaster that supports reconnect and event replay."""

    def __init__(self, task_id: str):
        self.task_id = task_id

    def emit(self, event: str, data: dict):
        stream = _get_or_create_stream(self.task_id)
        payload = {"event": event, "data": data}
        with stream.lock:
            if stream.terminal:
                return
            stream.history.append(payload)
            stream.updated_at = time.time()
            if _is_terminal_event(event):
                stream.terminal = True
        _dispatch_event(stream, payload)

    def clear(self):
        # Kept for compatibility with the existing call sites.
        return None


def attach_task_stream(task_id: str, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop) -> TaskStream:
    stream = _get_or_create_stream(task_id)
    listener = (queue, loop)
    with stream.lock:
        stream.listeners.add(listener)
        history = list(stream.history)
        terminal = stream.terminal

    for payload in history:
        loop.call_soon_threadsafe(queue.put_nowait, payload)
    if terminal:
        loop.call_soon_threadsafe(queue.put_nowait, None)
    return stream


def detach_task_stream(task_id: str, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop) -> None:
    with _STREAMS_LOCK:
        stream = _STREAMS.get(task_id)
    if stream is None:
        return
    with stream.lock:
        stream.listeners.discard((queue, loop))
        if stream.terminal and not stream.listeners:
            # Keep terminal streams around for task history/status APIs.
            stream.updated_at = time.time()


def reset_task_stream(task_id: str) -> None:
    with _STREAMS_LOCK:
        stream = _STREAMS.pop(task_id, None)
    if stream is None:
        return
    with stream.lock:
        listeners = list(stream.listeners)
        stream.listeners.clear()
    for queue, loop in listeners:
        try:
            loop.call_soon_threadsafe(queue.put_nowait, None)
        except Exception:
            pass


async def sse_event_generator(queue: asyncio.Queue, disconnect_check=None):
    """Read events from a queue and format them as SSE output."""
    while True:
        if disconnect_check and await disconnect_check():
            break
        msg = await queue.get()
        if msg is None:
            break
        if msg is HEARTBEAT:
            yield ": heartbeat\n\n"
            continue
        event = "generation_error" if msg["event"] == "error" else msg["event"]
        data = json.dumps(msg["data"], ensure_ascii=False)
        yield f"event: {event}\ndata: {data}\n\n"
