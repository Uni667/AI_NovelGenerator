import os
import json
import logging
from fastapi import APIRouter, HTTPException, Request, Body
from backend.app.services import state_file_service, project_service, state_patch_service, state_patch_merger, project_health_service, project_export_service
from backend.app.auth import get_current_user
from fastapi.responses import PlainTextResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["项目状态系统"])

@router.get("/api/v1/projects/{project_id}/health")
def check_health(project_id: str, request: Request):
    user_id = get_current_user(request)
    return project_health_service.check_project_health(project_id, user_id)

@router.get("/api/v1/projects/{project_id}/export/story-bible", response_class=PlainTextResponse)
def export_story_bible(project_id: str, request: Request):
    user_id = get_current_user(request)
    try:
        content = project_export_service.export_story_bible_markdown(project_id, user_id)
        return content
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v1/projects/{project_id}/state")
def get_project_state(project_id: str, request: Request):
    user_id = get_current_user(request)
    
    # Ensure memory files are initialized
    state_file_service.ensure_memory_files(project_id)
    
    return {
        "character_state": state_file_service.read_character_state(project_id),
        "global_summary": state_file_service.read_global_summary(project_id),
        "plot_threads": state_file_service.read_plot_threads(project_id),
        "name_usage_rules": state_file_service.read_name_usage_rules(project_id),
        "outline_state": state_file_service.read_outline_state(project_id)
    }

@router.get("/api/v1/projects/{project_id}/state/characters")
def get_character_state(project_id: str, request: Request):
    user_id = get_current_user(request)
    return state_file_service.read_character_state(project_id)

@router.get("/api/v1/projects/{project_id}/state/summary")
def get_global_summary(project_id: str, request: Request):
    user_id = get_current_user(request)
    return {"summary": state_file_service.read_global_summary(project_id)}

@router.get("/api/v1/projects/{project_id}/state/plot-threads")
def get_plot_threads(project_id: str, request: Request):
    user_id = get_current_user(request)
    return state_file_service.read_plot_threads(project_id)

@router.get("/api/v1/projects/{project_id}/state/name-rules")
def get_name_rules(project_id: str, request: Request):
    user_id = get_current_user(request)
    return state_file_service.read_name_usage_rules(project_id)

@router.get("/api/v1/projects/{project_id}/state/outline")
def get_outline_state(project_id: str, request: Request):
    user_id = get_current_user(request)
    return state_file_service.read_outline_state(project_id)

@router.get("/api/v1/projects/{project_id}/state/patches")
def list_patches(project_id: str, request: Request):
    user_id = get_current_user(request)
    memory_dir = state_file_service.get_memory_dir(project_id)
    patches_dir = os.path.join(memory_dir, "patches")
    
    if not os.path.exists(patches_dir):
        return {"patches": []}
        
    patches = []
    for filename in os.listdir(patches_dir):
        if filename.endswith(".json"):
            filepath = os.path.join(patches_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    patch_data = json.load(f)
                    # Don't return raw_model_output in list for efficiency
                    if "raw_model_output" in patch_data:
                        del patch_data["raw_model_output"]
                    patches.append(patch_data)
            except Exception as e:
                logger.error(f"Failed to read patch {filename}: {e}")
                
    # Sort by created_at desc
    patches.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return {"patches": patches}

@router.get("/api/v1/projects/{project_id}/state/patches/{patch_id}")
def get_patch(project_id: str, patch_id: str, request: Request):
    user_id = get_current_user(request)
    memory_dir = state_file_service.get_memory_dir(project_id)
    patches_dir = os.path.join(memory_dir, "patches")
    patch_file = os.path.join(patches_dir, f"{patch_id}.json")
    
    if not os.path.exists(patch_file):
        raise HTTPException(status_code=404, detail="Patch not found")
        
    try:
        with open(patch_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read patch: {e}")

@router.post("/api/v1/projects/{project_id}/state/patches/{patch_id}/discard")
def discard_patch(project_id: str, patch_id: str, request: Request):
    user_id = get_current_user(request)
    memory_dir = state_file_service.get_memory_dir(project_id)
    patch_file = os.path.join(memory_dir, "patches", f"{patch_id}.json")
    
    if not os.path.exists(patch_file):
        raise HTTPException(status_code=404, detail="Patch not found")
        
    try:
        with open(patch_file, "r", encoding="utf-8") as f:
            patch_data = json.load(f)
            
        patch_data["status"] = "discarded"
        
        with open(patch_file, "w", encoding="utf-8") as f:
            json.dump(patch_data, f, ensure_ascii=False, indent=2)
            
        return {"success": True, "status": "discarded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to discard patch: {e}")

@router.post("/api/v1/projects/{project_id}/state/patches/{patch_id}/merge")
def merge_patch(project_id: str, patch_id: str, request: Request):
    user_id = get_current_user(request)
    try:
        result = state_patch_merger.merge_state_patch(project_id, patch_id)
        return result
    except Exception as e:
        logger.exception("Failed to merge patch")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/v1/projects/{project_id}/chapters/{chapter_id}/state-patch")
def manual_generate_patch(project_id: str, chapter_id: int, request: Request):
    """手动重新生成或补生成定稿章节的状态补丁"""
    user_id = get_current_user(request)
    try:
        # Check if chapter is finalized
        from backend.app.database import get_db
        with get_db() as conn:
            ch = conn.execute("SELECT chapter_number, status FROM chapter WHERE project_id=? AND chapter_number=?", (project_id, chapter_id)).fetchone()
            if not ch:
                raise HTTPException(status_code=404, detail="Chapter not found")
            if ch["status"] not in ("final", "finalized"):
                raise HTTPException(status_code=400, detail="Chapter is not finalized")
                
        # Generate patch
        result = state_patch_service.generate_state_patch_for_finalized_chapter(project_id, chapter_id)
        return result
    except Exception as e:
        logger.exception("Failed to generate state patch manually")
        raise HTTPException(status_code=500, detail=str(e))
