"""SSE 事件发射器 - 供 novel_generator 模块在使用时推送进度事件"""


class SSEProgressEmitter:
    """将 SSE 进度回调包装为独立对象，供生成函数使用"""

    def __init__(self):
        self._on_progress = None
        self._on_partial = None
        self._on_error = None

    def set_callbacks(self, on_progress=None, on_partial=None, on_error=None):
        self._on_progress = on_progress
        self._on_partial = on_partial
        self._on_error = on_error

    def progress(self, step: str, message: str, status: str = "running"):
        if self._on_progress:
            self._on_progress(step, message, status)

    def partial(self, step: str, content: str):
        if self._on_partial:
            self._on_partial(step, content)

    def error(self, step: str, message: str):
        if self._on_error:
            self._on_error(step, message)

    def clear(self):
        self._on_progress = None
        self._on_partial = None
        self._on_error = None


# 全局单例
progress_emitter = SSEProgressEmitter()
