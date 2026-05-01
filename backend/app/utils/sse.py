import asyncio
import json
from typing import Optional


class SSEEmitter:
    """全局单例，允许同步代码向异步队列推送 SSE 事件"""

    def __init__(self):
        self._queue: Optional[asyncio.Queue] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_queue(self, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
        self._queue = queue
        self._loop = loop

    def emit(self, event: str, data: dict):
        if self._queue and self._loop:
            asyncio.run_coroutine_threadsafe(
                self._queue.put({"event": event, "data": data}),
                self._loop
            )

    def clear(self):
        self._queue = None
        self._loop = None


sse_emitter = SSEEmitter()


async def sse_event_generator(queue: asyncio.Queue, disconnect_check=None):
    """从队列中读取事件并生成 SSE 格式字符串"""
    while True:
        if disconnect_check and await disconnect_check():
            break
        msg = await queue.get()
        if msg is None:  # sentinel
            break
        event = msg["event"]
        data = json.dumps(msg["data"], ensure_ascii=False)
        yield f"event: {event}\ndata: {data}\n\n"
