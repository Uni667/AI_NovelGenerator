# backend/app/routes/material_processor.py

import logging
import os
import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.app.auth import get_current_user
from backend.app.services import project_service
from backend.app.services.model_runtime import _build_chat_adapter
from backend.app.services.config_resolver import get_runtime_config
from novel_generator.material_pipeline import MaterialPipeline

logger = logging.getLogger(__name__)

router = APIRouter(tags=["素材加工流水线"])

class DecomposeRequest(BaseModel):
    raw_text: str

class DiagnoseRequest(BaseModel):
    entity: Dict[str, Any]

class OptimizeRequest(BaseModel):
    entity: Dict[str, Any]
    diagnosis: Dict[str, Any]
    user_instruction: str = ""

def _get_pipeline(user_id: str, project_id: str):
    """Helper to get initialized MaterialPipeline"""
    from backend.app.services.config_resolver import ConfigError
    try:
        rt = get_runtime_config(user_id, "draft", project_id)
    except ConfigError as e:
        raise HTTPException(status_code=500, detail="模型配置错误，请检查设置。")
    adapter = _build_chat_adapter(rt, None, None)
    return MaterialPipeline(adapter)

def _get_project_platform(project_id: str) -> str:
    pconfig = project_service.get_project_config(project_id)
    return pconfig.get("platform", "tomato") if pconfig else "tomato"

@router.post("/api/v1/projects/{project_id}/materials/decompose")
def decompose_material(project_id: str, payload: DecomposeRequest, request: Request):
    user_id = get_current_user(request)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
        
    if not payload.raw_text.strip():
        raise HTTPException(status_code=400, detail="原始素材为空")
        
    pipeline = _get_pipeline(user_id, project_id)
    try:
        entities = pipeline.decompose(payload.raw_text)
        return {"entities": entities}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/v1/projects/{project_id}/materials/diagnose")
def diagnose_material(project_id: str, payload: DiagnoseRequest, request: Request):
    user_id = get_current_user(request)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
        
    platform = _get_project_platform(project_id)
    pipeline = _get_pipeline(user_id, project_id)
    
    try:
        diagnosis = pipeline.diagnose(payload.entity, platform)
        return {"diagnosis": diagnosis}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/v1/projects/{project_id}/materials/optimize")
def optimize_material(project_id: str, payload: OptimizeRequest, request: Request):
    user_id = get_current_user(request)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
        
    pipeline = _get_pipeline(user_id, project_id)
    try:
        optimized_content = pipeline.optimize(
            payload.entity, 
            payload.diagnosis, 
            payload.user_instruction
        )
        return {"optimized_content": optimized_content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class SyncRequest(BaseModel):
    entities: List[Dict[str, Any]]

@router.post("/api/v1/projects/{project_id}/materials/sync")
def sync_materials(project_id: str, payload: SyncRequest, request: Request):
    user_id = get_current_user(request)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
        
    characters = []
    others = []
    for ent in payload.entities:
        if ent.get("type") == "character":
            characters.append(ent)
        else:
            others.append(ent)
            
    now = datetime.datetime.now().isoformat()
    # 1. Characters
    if characters:
        from backend.app.database import get_db
        with get_db() as conn:
            for char in characters:
                name = char.get("title", "").replace("主角", "").replace("反派", "").strip() or "未知角色"
                desc = char.get("content", "")
                conn.execute(
                    """INSERT INTO character_profile
                       (project_id, name, description, status, source, first_appearance_chapter, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (project_id, name, desc[:1000], "suggested", "material_pipeline", None, now)
                )

    # 2. Knowledge
    if others:
        from backend.app.database import get_db
        knowledge_dir = os.path.join(project["filepath"], "knowledge")
        os.makedirs(knowledge_dir, exist_ok=True)
        filename = "material_pipeline_exports.md"
        filepath = os.path.join(knowledge_dir, filename)
        
        md_content = "\n\n".join([f"## {ent.get('title', '设定')}\n- **类型**: {ent.get('type')}\n- **内容**: {ent.get('content', '')}" for ent in others])
        
        is_new = not os.path.exists(filepath)
        with open(filepath, "a", encoding="utf-8") as f:
            if is_new:
                f.write("# 素材流水线导入设定集\n\n")
            else:
                f.write("\n\n---\n\n")
            f.write(md_content)
            
        file_size = os.path.getsize(filepath)
        
        from backend.app.routes.knowledge import _resolve_embedding_config, _import_file_to_vector_store, _set_imported
        
        file_id = None
        with get_db() as conn:
            row = conn.execute("SELECT id FROM knowledge_file WHERE project_id = ? AND filename = ? AND user_id = ?", (project_id, filename, user_id)).fetchone()
            if row:
                file_id = row["id"]
                conn.execute("UPDATE knowledge_file SET file_size = ?, imported = 0, created_at = ? WHERE id = ?", (file_size, now, file_id))
            else:
                cursor = conn.execute(
                    "INSERT INTO knowledge_file (user_id, project_id, filename, filepath, file_size, imported, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (user_id, project_id, filename, filepath, file_size, 0, now),
                )
                file_id = cursor.lastrowid
                
        embedding_config = _resolve_embedding_config(user_id, project_id)
        import_result = _import_file_to_vector_store(project, embedding_config, filepath)
        
        if import_result.get("success") and file_id is not None:
            _set_imported(project_id, user_id, file_id, 1)
            
    return {"message": "同步成功", "characters_added": len(characters), "others_added": len(others)}

