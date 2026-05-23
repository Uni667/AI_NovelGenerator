# backend/app/routes/material_processor.py

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.app.auth import get_current_user
from backend.app.services import project_service
from backend.app.services.model_runtime import get_runtime_config, _build_chat_adapter
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
    from backend.app.services.model_runtime import ConfigError
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
