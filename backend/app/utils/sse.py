import asyncio
import json
from typing import Optional

HEARTBEAT = object()


class SSEEmitter:
    """每个连接独立实例，消除全局单例竞态条件"""

    def __init__(self):
        self._queue: Optional[asyncio.Queue] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_queue(self, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
        self._queue = queue
        self._loop = loop

    def emit(self, event: str, data: dict):
        if self._queue and self._loop:
            async def _put():
                await self._queue.put({"event": event, "data": data})
                if event in {"done", "cancelled"}:
                    await self._queue.put(None)

            asyncio.run_coroutine_threadsafe(_put(), self._loop)

    def clear(self):
        self._queue = None
        self._loop = None


async def sse_event_generator(queue: asyncio.Queue, disconnect_check=None):
    """从队列中读取事件并生成 SSE 格式字符串; HEARTBEAT 保持连接活跃"""
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
