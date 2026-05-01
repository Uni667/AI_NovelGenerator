from fastapi import APIRouter, HTTPException
from backend.app.services import project_service, chapter_service

router = APIRouter(tags=["项目管理"])


@router.get("/api/v1/projects")
def list_projects():
    return project_service.list_projects()


@router.post("/api/v1/projects")
def create_project(data: dict):
    try:
        return project_service.create_project(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/projects/{project_id}")
def get_project(project_id: str):
    project = project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


@router.put("/api/v1/projects/{project_id}")
def update_project(project_id: str, data: dict):
    result = project_service.update_project(project_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="项目不存在")
    return result


@router.delete("/api/v1/projects/{project_id}")
def delete_project(project_id: str):
    if not project_service.delete_project(project_id):
        raise HTTPException(status_code=404, detail="项目不存在")
    return {"message": "项目已删除"}


@router.get("/api/v1/projects/{project_id}/config")
def get_project_config(project_id: str):
    config = project_service.get_project_config(project_id)
    if not config:
        raise HTTPException(status_code=404, detail="项目配置不存在")
    return config


@router.put("/api/v1/projects/{project_id}/config")
def update_project_config(project_id: str, data: dict):
    try:
        return project_service.update_project_config(project_id, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
