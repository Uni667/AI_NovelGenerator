from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from backend.app.auth import get_current_user
from backend.app.services import project_service, state_edit_service, state_conflict_service, state_audit_service
from backend.app.services.state_edit_service import StateEditError

router = APIRouter(tags=["状态编辑与审查"])

class StateEditRequest(BaseModel):
    updates: dict = Field(..., description="要更新的字段")
    reason: str = Field(..., description="修改原因，必填")
    confirm_high_risk: bool = Field(False, description="如果涉及高风险字段，是否确认覆盖")

def _check_project(project_id: str, request: Request) -> str:
    user_id = get_current_user(request)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return user_id

def _handle_edit_error(e: Exception):
    if isinstance(e, StateEditError):
        raise HTTPException(status_code=400, detail={
            "error": e.code,
            "message": str(e),
            "details": e.details
        })
    raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v1/projects/{project_id}/state/conflicts")
def get_state_conflicts(project_id: str, request: Request, enable_ai: bool = False):
    user_id = _check_project(project_id, request)
    return state_conflict_service.detect_state_conflicts(project_id, enable_ai, user_id)

@router.patch("/api/v1/projects/{project_id}/state/characters/{character_id}")
def update_character_state(project_id: str, character_id: str, req: StateEditRequest, request: Request):
    _check_project(project_id, request)
    try:
        return state_edit_service.update_character_state(
            project_id, character_id, req.updates, req.reason, req.confirm_high_risk
        )
    except Exception as e:
        _handle_edit_error(e)

@router.patch("/api/v1/projects/{project_id}/state/name-rules/{character_id}")
def update_name_rules(project_id: str, character_id: str, req: StateEditRequest, request: Request):
    _check_project(project_id, request)
    try:
        return state_edit_service.update_name_usage_rule(
            project_id, character_id, req.updates, req.reason, req.confirm_high_risk
        )
    except Exception as e:
        _handle_edit_error(e)

@router.patch("/api/v1/projects/{project_id}/state/plot-threads/{thread_id}")
def update_plot_thread(project_id: str, thread_id: str, req: StateEditRequest, request: Request):
    _check_project(project_id, request)
    try:
        return state_edit_service.update_plot_thread(
            project_id, thread_id, req.updates, req.reason, req.confirm_high_risk
        )
    except Exception as e:
        _handle_edit_error(e)

@router.patch("/api/v1/projects/{project_id}/state/summary")
def update_global_summary(project_id: str, req: StateEditRequest, request: Request):
    _check_project(project_id, request)
    try:
        # updates is expected to have 'text' key for global summary
        text = req.updates.get("text", "")
        return state_edit_service.update_global_summary(
            project_id, text, req.reason, req.confirm_high_risk
        )
    except Exception as e:
        _handle_edit_error(e)

@router.patch("/api/v1/projects/{project_id}/state/outline/chapters/{chapter_index}")
def update_outline_chapter(project_id: str, chapter_index: int, req: StateEditRequest, request: Request):
    _check_project(project_id, request)
    try:
        return state_edit_service.update_outline_chapter(
            project_id, chapter_index, req.updates, req.reason, req.confirm_high_risk
        )
    except Exception as e:
        _handle_edit_error(e)

@router.get("/api/v1/projects/{project_id}/state/audit-logs")
def get_audit_logs(project_id: str, request: Request, limit: int = 100):
    _check_project(project_id, request)
    return state_audit_service.get_audit_logs(project_id, limit)

@router.get("/api/v1/projects/{project_id}/state/backups")
def get_backups(project_id: str, request: Request):
    _check_project(project_id, request)
    return state_edit_service.get_backups(project_id)

class RestoreRequest(BaseModel):
    reason: str = Field(..., description="回滚原因，必填")

@router.post("/api/v1/projects/{project_id}/state/backups/{backup_id}/restore")
def restore_backup(project_id: str, backup_id: str, req: RestoreRequest, request: Request):
    _check_project(project_id, request)
    try:
        return state_edit_service.restore_backup(project_id, backup_id, req.reason)
    except Exception as e:
        _handle_edit_error(e)
