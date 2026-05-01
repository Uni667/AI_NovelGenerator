import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from backend.app.services import project_service
from utils import read_file

router = APIRouter(tags=["文件读取"])

ALLOWED_FILES = [
    "Novel_architecture.txt",
    "Novel_directory.txt",
    "global_summary.txt",
    "character_state.txt",
    "plot_arcs.txt"
]


@router.get("/api/v1/projects/{project_id}/files/{filename}")
def get_file(project_id: str, filename: str):
    project = project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if filename not in ALLOWED_FILES:
        raise HTTPException(status_code=400, detail=f"不允许访问该文件: {filename}")
    filepath = os.path.join(project["filepath"], filename)
    if not os.path.exists(filepath):
        return PlainTextResponse("", status_code=200)
    content = read_file(filepath)
    return PlainTextResponse(content, media_type="text/plain; charset=utf-8")
