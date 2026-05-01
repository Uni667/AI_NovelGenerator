from fastapi import APIRouter, HTTPException
from backend.app.services import project_service, chapter_service

router = APIRouter(tags=["章节管理"])


@router.get("/api/v1/projects/{project_id}/chapters")
def list_chapters(project_id: str):
    project = project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    # 先同步目录解析结果
    chapter_service.sync_chapters_from_directory(project_id, project["filepath"])
    return chapter_service.list_chapters(project_id)


@router.get("/api/v1/projects/{project_id}/chapters/{chapter_number}")
def get_chapter(project_id: str, chapter_number: int):
    project = project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    meta = chapter_service.get_chapter(project_id, chapter_number)
    content = chapter_service.get_chapter_content(project_id, chapter_number, project["filepath"])
    return {
        "chapter_number": chapter_number,
        "content": content,
        "meta": meta
    }


@router.put("/api/v1/projects/{project_id}/chapters/{chapter_number}")
def update_chapter(project_id: str, chapter_number: int, data: dict):
    project = project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if "content" in data:
        result = chapter_service.update_chapter_content(project_id, chapter_number, project["filepath"], data["content"])
        return {"message": "已保存", "meta": result}
    raise HTTPException(status_code=400, detail="未提供内容")
