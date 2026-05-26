import os
import logging
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from backend.app.services.project_service import get_project
from backend.app.auth import get_current_user
from utils import read_file, save_string_to_txt

router = APIRouter(tags=["伏笔暗线管理"])
logger = logging.getLogger(__name__)

class PlotArcsUpdate(BaseModel):
    content: str

@router.get("/api/v1/projects/{project_id}/plot_arcs")
def get_plot_arcs(project_id: str, request: Request):
    user_id = get_current_user(request)
    project = get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
        
    filepath = project["filepath"]
    
    # Sync missing files from DB to disk
    from backend.app.services import file_service
    file_service.sync_project_files_to_disk(project_id, filepath, user_id)

    pa_file = os.path.join(filepath, "plot_arcs.txt")
    if not os.path.exists(pa_file):
        return {"content": "（尚未生成伏笔暗线台账）"}
        
    content = read_file(pa_file)
    return {"content": content}

@router.put("/api/v1/projects/{project_id}/plot_arcs")
def update_plot_arcs(project_id: str, data: PlotArcsUpdate, request: Request):
    user_id = get_current_user(request)
    project = get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
        
    filepath = project["filepath"]
    os.makedirs(filepath, exist_ok=True)
    pa_file = os.path.join(filepath, "plot_arcs.txt")
    
    try:
        # Use existing save util which clears first
        from utils import clear_file_content
        if os.path.exists(pa_file):
            clear_file_content(pa_file)
        save_string_to_txt(data.content, pa_file)
        
        # Save to database
        from backend.app.services import file_service
        file_service.create_project_file(
            project_id=project_id,
            user_id=user_id,
            type="plot_arcs",
            title="伏笔暗线台账",
            filename="plot_arcs.txt",
            content=data.content,
            source="user_edited",
            is_current=True
        )
        return {"message": "伏笔暗线台账已更新"}
    except Exception as e:
        logger.error(f"Failed to update plot arcs for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail="保存失败")
