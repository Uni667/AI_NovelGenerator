import os
import uuid

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import PlainTextResponse

from backend.app.auth import get_current_user
from backend.app.services import chapter_service, file_service, project_service
from utils import read_file

router = APIRouter(tags=["文件管理"])

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


# ── 新增：文件导入、列表、设为当前、获取当前架构/目录 ──

ALLOWED_IMPORT_EXTENSIONS = {".txt", ".md", ".json"}


@router.post("/api/v1/projects/{project_id}/files/import")
async def import_file(
    project_id: str,
    request: Request,
    file: UploadFile = File(...),
    file_type: str = Form(...),
    set_current: bool = Form(True),
):
    user_id = get_current_user(request)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    if file_type not in ("architecture", "outline"):
        raise HTTPException(status_code=400, detail="file_type 必须是 architecture 或 outline")

    if file.filename:
        ext = os.path.splitext(file.filename)[1].lower()
    else:
        ext = ".txt"
    if ext not in ALLOWED_IMPORT_EXTENSIONS:
        raise HTTPException(status_code=400, detail="仅支持 .txt、.md、.json 文件")

    content = (await file.read()).decode("utf-8", errors="replace")
    if not content.strip():
        raise HTTPException(status_code=400, detail="文件内容为空")

    title = os.path.splitext(file.filename or "imported")[0]
    safe_name = os.path.basename(file.filename or f"imported{ext}")
    filename = f"imported_{file_type}_{uuid.uuid4().hex[:8]}{ext}"

    result = file_service.create_project_file(
        project_id=project_id,
        type=file_type,
        title=title,
        filename=filename,
        content=content,
        source="user_imported",
        is_current=set_current,
    )

    # 同步到文件系统
    if file_type == "architecture":
        from utils import clear_file_content, save_string_to_txt
        arch_file = os.path.join(project["filepath"], "Novel_architecture.txt")
        clear_file_content(arch_file)
        save_string_to_txt(content, arch_file)
    elif file_type == "outline":
        from utils import clear_file_content, save_string_to_txt
        dir_file = os.path.join(project["filepath"], "Novel_directory.txt")
        clear_file_content(dir_file)
        save_string_to_txt(content, dir_file)
        chapter_service.sync_chapters_from_directory(project_id, project["filepath"])

    return result


@router.get("/api/v1/projects/{project_id}/project-files")
def list_project_files_route(project_id: str, request: Request, type: str | None = None):
    user_id = get_current_user(request)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return file_service.list_project_files(project_id, type)


@router.put("/api/v1/projects/{project_id}/project-files/{file_id}/set-current")
def set_file_as_current(project_id: str, file_id: str, request: Request):
    user_id = get_current_user(request)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    result = file_service.set_current_file(file_id)
    if not result:
        raise HTTPException(status_code=404, detail="文件不存在")

    # 同步到文件系统
    if result["type"] == "architecture":
        from utils import clear_file_content, save_string_to_txt
        arch_file = os.path.join(project["filepath"], "Novel_architecture.txt")
        clear_file_content(arch_file)
        save_string_to_txt(result["content"], arch_file)
    elif result["type"] == "outline":
        from utils import clear_file_content, save_string_to_txt
        dir_file = os.path.join(project["filepath"], "Novel_directory.txt")
        clear_file_content(dir_file)
        save_string_to_txt(result["content"], dir_file)
        chapter_service.sync_chapters_from_directory(project_id, project["filepath"])

    return result


@router.delete("/api/v1/projects/{project_id}/project-files/{file_id}")
def delete_project_file_route(project_id: str, file_id: str, request: Request):
    user_id = get_current_user(request)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    success = file_service.delete_project_file(file_id)
    if not success:
        raise HTTPException(status_code=404, detail="文件不存在")
    return {"message": f"已删除文件: {file_id}"}


@router.get("/api/v1/projects/{project_id}/current-architecture")
def get_current_architecture(project_id: str, request: Request):
    user_id = get_current_user(request)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    current = file_service.get_current_file(project_id, "architecture")
    if not current:
        raise HTTPException(status_code=404, detail="当前项目没有架构，请先生成或导入架构")
    return current


@router.get("/api/v1/projects/{project_id}/current-outline")
def get_current_outline(project_id: str, request: Request):
    user_id = get_current_user(request)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    current = file_service.get_current_file(project_id, "outline")
    if not current:
        raise HTTPException(status_code=404, detail="当前项目没有章节目录，请先生成或导入目录")
    return current
