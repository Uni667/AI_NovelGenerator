from fastapi import APIRouter, HTTPException, Request
from backend.app.services import project_service, chapter_service
from backend.app.auth import get_current_user
from backend.app.models.chapter import ChapterUpdate

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
    if data.content:
        result = chapter_service.update_chapter_content(project_id, chapter_number, project["filepath"], data.content)
        return {"message": "已保存", "meta": result}
    raise HTTPException(status_code=400, detail="未提供内容")
