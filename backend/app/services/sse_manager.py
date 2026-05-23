import asyncio
import logging
import threading
from typing import Any, Callable

from fastapi import Request
from fastapi.responses import StreamingResponse

from backend.app.utils.sse import HEARTBEAT, SSEEmitter, attach_task_stream, detach_task_stream, sse_event_generator

logger = logging.getLogger(__name__)


async def _heartbeat(queue: asyncio.Queue, interval: float = 3.0):
    while True:
        await asyncio.sleep(interval)
        await queue.put(HEARTBEAT)


def make_streaming_response(
    request: Request,
    task_id: str,
    target_func: Callable,
    *args: Any,
) -> StreamingResponse:
    """
    创建一个受控的 SSE 响应，并在后台线程启动具体的生成任务。
    分离了 HTTP 通信逻辑和具体的任务编排逻辑。
    """
    queue = asyncio.Queue()
    loop = asyncio.get_event_loop()
    attach_task_stream(task_id, queue, loop)

    t = threading.Thread(
        target=target_func,
        args=(SSEEmitter(task_id), task_id, *args),
        daemon=True,
    )
    t.start()

    async def event_gen():
        hb = asyncio.create_task(_heartbeat(queue))
        try:
            async for sse_data in sse_event_generator(queue):
                if await request.is_disconnected():
                    break
                yield sse_data
        finally:
            hb.cancel()
            detach_task_stream(task_id, queue, loop)

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "X-Task-ID": task_id},
    )
