import os
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from backend.app.services import project_service, chapter_service
from backend.app.auth import get_current_user
from backend.app.models.project import ProjectCreate, ProjectUpdate, ConfigUpdate
from utils import read_file

router = APIRouter(tags=["项目管理"])


@router.get("/api/v1/projects")
def list_projects(request: Request):
    user_id = get_current_user(request)
    return project_service.list_projects(user_id)


@router.post("/api/v1/projects")
def create_project(data: ProjectCreate, request: Request):
    user_id = get_current_user(request)
    try:
        return project_service.create_project(data.model_dump(), user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/projects/{project_id}")
def get_project(project_id: str, request: Request):
    user_id = get_current_user(request)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


@router.put("/api/v1/projects/{project_id}")
def update_project(project_id: str, data: ProjectUpdate, request: Request):
    user_id = get_current_user(request)
    result = project_service.update_project(project_id, data.model_dump(exclude_none=True), user_id)
    if not result:
        raise HTTPException(status_code=404, detail="项目不存在")
    return result


@router.delete("/api/v1/projects/{project_id}")
def delete_project(project_id: str, request: Request):
    user_id = get_current_user(request)
    if not project_service.delete_project(project_id, user_id):
        raise HTTPException(status_code=404, detail="项目不存在")
    return {"message": "项目已删除"}


@router.get("/api/v1/projects/{project_id}/config")
def get_project_config(project_id: str, request: Request):
    user_id = get_current_user(request)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    config = project_service.get_project_config(project_id)
    if not config:
        raise HTTPException(status_code=404, detail="项目配置不存在")
    return config


@router.put("/api/v1/projects/{project_id}/config")
def update_project_config(project_id: str, data: ConfigUpdate, request: Request):
    user_id = get_current_user(request)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    try:
        return project_service.update_project_config(project_id, data.model_dump(exclude_none=True))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/api/v1/projects/{project_id}/export")
def export_project(project_id: str, request: Request, format: str = Query("txt", pattern="^(txt|html)$")):
    user_id = get_current_user(request)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    filepath = project["filepath"]
    chapters_dir = os.path.join(filepath, "chapters")
    chapters = chapter_service.list_chapters(project_id, user_id)

    if not chapters:
        raise HTTPException(status_code=400, detail="没有章节可导出")

    parts = []
    parts.append(f"{project['name']}\n{'=' * 40}\n")

    for ch in sorted(chapters, key=lambda c: c.get("chapter_number", 0)):
        num = ch.get("chapter_number", 0)
        title = ch.get("chapter_title", "")
        ch_file = os.path.join(chapters_dir, f"chapter_{num}.txt")
        content = read_file(ch_file) if os.path.exists(ch_file) else ""

        if format == "html":
            parts.append(f"<h2>第{num}章 {title}</h2>")
            parts.append(f"<div>{content.replace(chr(10), '<br>')}</div>")
            parts.append("<hr>")
        else:
            parts.append(f"\n第{num}章 {title}\n{'-' * 30}")
            parts.append(content)
            parts.append("")

    full = "\n".join(parts) if format == "txt" else f"<html><body>{''.join(parts)}</body></html>"
    media = "text/html; charset=utf-8" if format == "html" else "text/plain; charset=utf-8"

    return PlainTextResponse(full, media_type=media, headers={
        "Content-Disposition": f"attachment; filename={project['name']}.{format}"
    })
