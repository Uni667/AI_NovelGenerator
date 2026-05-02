import os
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse
from backend.app.services import project_service, chapter_service
from backend.app.auth import get_current_user
from utils import read_file

router = APIRouter(tags=["文件读取"])

ALLOWED_FILES = [
    "Novel_architecture.txt",
    "architecture_core_seed.txt",
    "architecture_character_dynamics.txt",
    "architecture_world_building.txt",
    "architecture_plot.txt",
    "Novel_directory.txt",
    "global_summary.txt",
    "character_state.txt",
    "plot_arcs.txt",
    "partial_architecture.json",
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


@router.delete("/api/v1/projects/{project_id}/files/{filename}")
def delete_file(project_id: str, filename: str, request: Request):
    user_id = get_current_user(request)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"项目不存在或无权访问: {project_id}")
    if filename not in ALLOWED_FILES:
        allowed = "、".join(ALLOWED_FILES)
        raise HTTPException(status_code=400, detail=f"不允许删除该文件: {filename}。可删除文件: {allowed}")

    filepath = os.path.abspath(os.path.join(project["filepath"], filename))
    project_root = os.path.abspath(project["filepath"])
    if not filepath.startswith(project_root + os.sep):
        raise HTTPException(status_code=400, detail="文件路径非法")
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"文件不存在: {filename}")

    os.remove(filepath)
    if filename == "Novel_directory.txt":
        chapter_service.clear_chapter_directory(project_id)

    return {
        "message": "已删除章节目录，并清空章节规划记录" if filename == "Novel_directory.txt" else f"已删除文件: {filename}",
        "filename": filename,
    }
