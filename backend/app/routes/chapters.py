import re

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, Depends
from backend.app.services import project_service, chapter_service
from backend.app.auth import get_current_user
from backend.app.models.chapter import ChapterUpdate
from backend.app.dependencies import get_generation_context
from novel_generator.context import GenerationContext

router = APIRouter(tags=["章节管理"])


def _check_project(project_id: str, request: Request) -> tuple[dict, str]:
    user_id = get_current_user(request)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project, user_id


@router.get("/api/v1/projects/{project_id}/chapters")
def list_chapters(project_id: str, request: Request):
    project, user_id = _check_project(project_id, request)
    chapter_service.sync_chapters_from_directory(project_id, project["filepath"], user_id)
    return chapter_service.list_chapters(project_id, user_id)


@router.get("/api/v1/projects/{project_id}/chapters/{chapter_number}")
def get_chapter(project_id: str, chapter_number: int, request: Request):
    project, _user_id = _check_project(project_id, request)
    meta = chapter_service.get_chapter(project_id, chapter_number)
    content = chapter_service.get_chapter_content(project_id, chapter_number, project["filepath"])
    return {
        "chapter_number": chapter_number,
        "content": content,
        "meta": meta
    }


@router.put("/api/v1/projects/{project_id}/chapters/{chapter_number}")
def update_chapter(project_id: str, chapter_number: int, data: ChapterUpdate, request: Request):
    project, _user_id = _check_project(project_id, request)
    
    meta_updated = False
    meta_fields = ["chapter_title", "chapter_role", "chapter_purpose", "suspense_level", "foreshadowing", "plot_twist_level", "chapter_summary"]
    if any(getattr(data, f) is not None for f in meta_fields):
        chapter_service.update_chapter_meta(project_id, chapter_number, data)
        meta_updated = True
        
    status_updated = False
    if data.status is not None:
        import datetime
        from backend.app.database import get_db
        now = datetime.datetime.now().isoformat()
        with get_db() as conn:
            conn.execute(
                "UPDATE chapter SET status=?, updated_at=? WHERE project_id=? AND chapter_number=?",
                (data.status, now, project_id, chapter_number)
            )
        status_updated = True
        
    result = None
    if data.content is not None:
        result = chapter_service.update_chapter_content(project_id, chapter_number, project["filepath"], data.content, status=data.status)
    elif meta_updated or status_updated:
        result = chapter_service.get_chapter(project_id, chapter_number)
        
    if result:
        return {"message": "已保存", "meta": result}
        
    raise HTTPException(status_code=400, detail="未提供修改内容")


@router.post("/api/v1/projects/{project_id}/chapters/{chapter_number}/copy")
def copy_chapter(project_id: str, chapter_number: int, request: Request):
    project, _user_id = _check_project(project_id, request)
    result = chapter_service.copy_chapter(project_id, chapter_number, project["filepath"])
    if not result:
        raise HTTPException(status_code=404, detail="章节不存在，复制失败")
    return {"message": "复制成功", "meta": result}



def _parse_chapter_number(filename: str) -> int | None:
    """从文件名提取章节号。支持: chapter_0001.txt, chapter_1.txt, 第1章.txt"""
    name = filename.rsplit(".", 1)[0]  # 去掉扩展名
    # chapter_0001 / chapter_1
    m = re.match(r"^chapter_0*(\d+)$", name, re.IGNORECASE)
    if m:
        return int(m.group(1))
    # 第1章
    m = re.match(r"^第\s*(\d+)\s*章$", name)
    if m:
        return int(m.group(1))
    # 纯数字 0001 / 1
    m = re.match(r"^0*(\d+)$", name)
    if m:
        return int(m.group(1))
    return None


MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB per file
MAX_BATCH_FILES = 100


@router.post("/api/v1/projects/{project_id}/chapters/upload")
async def upload_chapters(
    project_id: str,
    request: Request,
    files: list[UploadFile] = File(...),
):
    project, user_id = _check_project(project_id, request)

    if len(files) > MAX_BATCH_FILES:
        raise HTTPException(status_code=400, detail=f"单次最多上传 {MAX_BATCH_FILES} 个文件")

    chapters_data: list[dict] = []
    skipped: list[str] = []
    for f in files:
        if not f.filename:
            skipped.append("(unnamed)")
            continue
        cn = _parse_chapter_number(f.filename)
        if cn is None or cn < 1:
            skipped.append(f.filename)
            continue
        raw = await f.read()
        if len(raw) > MAX_UPLOAD_BYTES:
            skipped.append(f"{f.filename} (过大)")
            continue
        content = raw.decode("utf-8", errors="replace").strip()
        if not content:
            skipped.append(f"{f.filename} (空)")
            continue
        chapters_data.append({"chapter_number": cn, "content": content})

    if not chapters_data:
        raise HTTPException(status_code=400, detail="未识别到有效章节文件，请确认文件名格式为 chapter_0001.txt 或 第1章.txt")

    chapters_data.sort(key=lambda x: x["chapter_number"])
    results = chapter_service.batch_upsert_from_upload(project_id, project["filepath"], chapters_data, user_id)

    return {
        "message": f"成功导入 {len(results)} 章",
        "uploaded": len(results),
        "skipped": len(skipped),
        "skipped_files": skipped[:20],
        "chapters": results,
    }


@router.delete("/api/v1/projects/{project_id}/chapters/{chapter_number}")
def delete_chapter(project_id: str, chapter_number: int, request: Request):
    project, _user_id = _check_project(project_id, request)
    success = chapter_service.delete_chapter(project_id, chapter_number, project["filepath"])
    if not success:
        raise HTTPException(status_code=404, detail="章节不存在")
    return {"message": f"第{chapter_number}章已删除", "chapter_number": chapter_number}


@router.post("/api/v1/projects/{project_id}/chapters/{chapter_number}/sync-subsequent")
def sync_subsequent_chapters_route(
    project_id: str,
    chapter_number: int,
    request: Request,
):
    project, user_id = _check_project(project_id, request)
    try:
        updated_chapters = chapter_service.sync_subsequent_chapters(project_id, chapter_number, user_id)
        return {
            "message": "同步成功",
            "chapters": updated_chapters
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/projects/{project_id}/chapters/{chapter_number}/ask-ai")
async def ask_ai_route(
    project_id: str,
    chapter_number: int,
    question: str,
    request: Request,
    selected_text: str | None = None,
    ctx: GenerationContext = Depends(get_generation_context)
):
    import asyncio
    import json
    from sse_starlette.sse import EventSourceResponse
    from novel_generator.chapter_pipeline.revision import stream_chapter_ask_ai
    
    project, _user_id = _check_project(project_id, request)
    pconfig = project_service.get_project_config(project_id) or {}
    chapter_meta = chapter_service.get_chapter(project_id, chapter_number) or {}
    chapter_content = chapter_service.get_chapter_content(project_id, chapter_number, project["filepath"])
    
    queue = asyncio.Queue()
    
    class RouteSSEEmitter:
        def __init__(self, q: asyncio.Queue):
            self.q = q
        def emit(self, event_type: str, data: dict):
            self.q.put_nowait({"event": event_type, "data": data})
            
    emitter = RouteSSEEmitter(queue)
    
    async def _run_ask():
        try:
            await asyncio.to_thread(
                stream_chapter_ask_ai,
                ctx,
                chapter_number,
                chapter_meta,
                chapter_content,
                question,
                selected_text,
                emitter,
                project_config=pconfig
            )
            emitter.emit("done", {"step": "ask_ai"})
        except Exception as e:
            emitter.emit("error", {"step": "ask_ai", "message": str(e)})
        finally:
            queue.put_nowait(None)
            
    asyncio.create_task(_run_ask())
    
    async def event_generator():
        while True:
            msg = await queue.get()
            if msg is None:
                break
            yield {
                "event": msg["event"],
                "data": json.dumps(msg["data"], ensure_ascii=False)
            }
            
    return EventSourceResponse(event_generator())
