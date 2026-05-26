from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional
import os
import asyncio
from sse_starlette.sse import EventSourceResponse

from backend.app.dependencies import get_generation_context
from novel_generator.context import GenerationContext
from novel_generator.chapter_pipeline.revision import stream_interactive_rewrite

router = APIRouter(prefix="/projects/{project_id}/interactive", tags=["Interactive Editing"])

class InteractiveRewriteRequest(BaseModel):
    context_before: str
    selected_text: str
    context_after: str
    user_instruction: str

class SSEEmitter:
    def __init__(self, queue: asyncio.Queue):
        self.queue = queue

    def emit(self, event_type: str, data: dict):
        self.queue.put_nowait({"event": event_type, "data": data})

@router.post("/rewrite")
async def interactive_rewrite_stream(
    project_id: str,
    req: InteractiveRewriteRequest,
    request: Request,
    ctx: GenerationContext = Depends(get_generation_context)
):
    """
    流式局部重写接口
    """
    if not req.selected_text.strip():
        raise HTTPException(status_code=400, detail="未选中任何文本")

    from backend.app.services import project_service
    pconfig = project_service.get_project_config(project_id) or {}

    queue = asyncio.Queue()
    emitter = SSEEmitter(queue)

    async def _run_generation():
        try:
            # 运行在线程池中，避免阻塞主事件循环
            result = await asyncio.to_thread(
                stream_interactive_rewrite,
                ctx,
                req.context_before,
                req.selected_text,
                req.context_after,
                req.user_instruction,
                emitter,
                project_config=pconfig
            )
            emitter.emit("done", {"step": "interactive_rewrite", "content": result})
        except Exception as e:
            emitter.emit("error", {"step": "interactive_rewrite", "message": str(e)})
        finally:
            queue.put_nowait(None)

    asyncio.create_task(_run_generation())

    async def event_generator():
        while True:
            msg = await queue.get()
            if msg is None:
                break
            
            import json
            yield {
                "event": msg["event"],
                "data": json.dumps(msg["data"], ensure_ascii=False)
            }

    return EventSourceResponse(event_generator())
