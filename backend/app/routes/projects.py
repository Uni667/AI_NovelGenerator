import os
import logging
from fastapi import APIRouter, HTTPException, Query, Request, UploadFile, File
from fastapi.responses import PlainTextResponse
from backend.app.services import project_service, chapter_service
from backend.app.auth import get_current_user
from backend.app.models.project import ProjectCreate, ProjectUpdate, ConfigUpdate
from utils import read_file

logger = logging.getLogger(__name__)

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
        logger.exception("Failed to create project")
        raise HTTPException(status_code=500, detail="创建项目失败")


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
    except ValueError:
        raise HTTPException(status_code=404, detail="项目配置不存在")


@router.get("/api/v1/projects/{project_id}/export")
def export_project(project_id: str, request: Request, format: str = Query("txt", pattern="^(txt|html)$")):
    user_id = get_current_user(request)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    filepath = project["filepath"]
    
    # Restores any missing files from database to disk before exporting
    from backend.app.services import file_service
    file_service.sync_project_files_to_disk(project_id, filepath, user_id)

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


@router.get("/api/v1/projects/{project_id}/backup")
def backup_project(project_id: str, request: Request):
    """备份项目：打包所有的项目文件、章节、配置、visualizer数据及头像资源为ZIP"""
    import io
    import zipfile
    import json
    from fastapi.responses import StreamingResponse
    
    project = project_service.get_project(project_id, get_current_user(request))
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
        
    filepath = project["filepath"]
    if not filepath or not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="项目路径不存在")
        
    config = project_service.get_project_config(project_id) or {}
    
    with get_db() as conn:
        db_chars = conn.execute("SELECT * FROM character_profile WHERE project_id = ?", (project_id,)).fetchall()
        db_chars_list = [dict(c) for c in db_chars]
        
        chapters = conn.execute("SELECT * FROM chapter WHERE project_id = ?", (project_id,)).fetchall()
        chapters_list = [dict(ch) for ch in chapters]
        
    metadata = {
        "project": {
            "name": project["name"],
            "description": project.get("description", ""),
            "status": project.get("status", "draft"),
        },
        "config": config,
        "characters": db_chars_list,
        "chapters": chapters_list
    }
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("metadata.json", json.dumps(metadata, ensure_ascii=False, indent=2))
        
        for root, dirs, files in os.walk(filepath):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, filepath)
                zf.write(full_path, rel_path)
                
    zip_buffer.seek(0)
    safe_filename = f"backup_{project['name']}_{datetime.now().strftime('%Y%m%d%H%M%S')}.zip"
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={safe_filename}"}
    )


@router.post("/api/v1/projects/import-backup")
async def import_backup(request: Request, file: UploadFile = File(...)):
    """恢复/导入项目备份 ZIP 文件，自动还原数据并迁移 visualizer schema"""
    import io
    import zipfile
    import json
    import uuid
    from datetime import datetime
    
    user_id = get_current_user(request)
    content = await file.read()
    zip_buffer = io.BytesIO(content)
    
    try:
        with zipfile.ZipFile(zip_buffer, "r") as zf:
            if "metadata.json" not in zf.namelist():
                raise HTTPException(status_code=400, detail="备份文件损坏：未找到 metadata.json")
                
            metadata = json.loads(zf.read("metadata.json").decode("utf-8"))
            proj_meta = metadata["project"]
            config_meta = metadata.get("config", {})
            chars_meta = metadata.get("characters", [])
            chapters_meta = metadata.get("chapters", [])
            
            new_project_id = str(uuid.uuid4())
            now_str = datetime.now().isoformat()
            
            from backend.app.services.project_service import _ensure_data_dir_path
            filepath = _ensure_data_dir_path(os.path.join("data", "projects", new_project_id))
            
            with get_db() as conn:
                conn.execute(
                    """INSERT INTO project (id, user_id, name, description, status, filepath, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (new_project_id, user_id, proj_meta["name"], proj_meta.get("description", ""), proj_meta.get("status", "draft"), filepath, now_str, now_str)
                )
                
                config_fields = [
                    "topic", "genre", "num_chapters", "word_number", "user_guidance",
                    "language", "platform", "category", "target_reader", "reader_direction",
                    "trend_key", "custom_trend", "trend_translation", "forbidden", "style_requirement"
                ]
                cfg_vals = [config_meta.get(f, "") for f in config_fields]
                conn.execute(
                    f"""INSERT INTO project_config (project_id, {', '.join(config_fields)}, updated_at)
                       VALUES (?, {', '.join('?' for _ in config_fields)}, ?)""",
                    [new_project_id] + cfg_vals + [now_str]
                )
                
                db_char_id_map = {}
                for char in chars_meta:
                    cursor = conn.execute(
                        """INSERT INTO character_profile (project_id, name, description, status, source, first_appearance_chapter, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (new_project_id, char["name"], char.get("description", ""), char.get("status", "appeared"), char.get("source", "user"), char.get("first_appearance_chapter"), now_str)
                    )
                    db_char_id_map[char["id"]] = cursor.lastrowid
                    
                for ch in chapters_meta:
                    conn.execute(
                        """INSERT INTO chapter (project_id, chapter_number, chapter_title, status, word_count, chapter_summary, draft_file, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (new_project_id, ch["chapter_number"], ch.get("chapter_title", ""), ch.get("status", "pending"), ch.get("word_count", 0), ch.get("chapter_summary", ch.get("outline", "")), ch.get("draft_file", ch.get("content", "")), now_str, now_str)
                    )
                conn.commit()
                
            for f in zf.namelist():
                if f == "metadata.json":
                    continue
                out_path = os.path.join(filepath, f)
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                with open(out_path, "wb") as out_file:
                    out_file.write(zf.read(f))
                    
            from backend.app.routes.visualizer import _migrate_and_sync_visualizer_data
            _migrate_and_sync_visualizer_data(filepath, new_project_id)
            
            return {
                "message": "项目备份恢复成功",
                "projectId": new_project_id,
                "name": proj_meta["name"]
            }
    except Exception as e:
        logger.exception("Failed to import backup ZIP")
        raise HTTPException(status_code=500, detail=f"恢复备份失败: {str(e)}")


@router.get("/api/v1/admin/data-backup")
def backup_all_data(request: Request):
    """
    全量数据备份 — 打包 /app/data 目录（含 SQLite 数据库 + 所有项目文件）。
    仅限已登录的管理员用户。
    """
    import io
    import zipfile
    from datetime import datetime
    from fastapi.responses import StreamingResponse
    
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="需要登录")
    
    data_root = "/app/data"
    if not os.path.exists(data_root):
        raise HTTPException(status_code=404, detail="数据目录不存在")
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(data_root):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, data_root)
                try:
                    zf.write(full_path, rel_path)
                except Exception as e:
                    logger.warning(f"备份跳过文件 {rel_path}: {e}")
    
    zip_buffer.seek(0)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="railway_data_backup_{timestamp}.zip"'}
    )
