import os
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse
from backend.app.services import project_service
from backend.app.auth import get_current_user
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
def get_file(project_id: str, filename: str, request: Request):
    user_id = get_current_user(request)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"项目不存在或无权访问: {project_id}")
    if filename not in ALLOWED_FILES:
        allowed = "、".join(ALLOWED_FILES)
        raise HTTPException(status_code=400, detail=f"不允许访问该文件: {filename}。可访问文件: {allowed}")
    filepath = os.path.join(project["filepath"], filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"文件不存在: {filename}。请先生成对应内容后再读取。")
    content = read_file(filepath)
    if content == "":
        raise HTTPException(status_code=404, detail=f"文件为空或读取失败: {filename}")
    return PlainTextResponse(content, media_type="text/plain; charset=utf-8")
