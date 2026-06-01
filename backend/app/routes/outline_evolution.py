from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from backend.app.auth import get_current_user
from backend.app.services import project_service, outline_evolution_service, outline_diff_service

router = APIRouter(tags=["大纲演化"])

class EvolveRequest(BaseModel):
    from_chapter: int = 1
    scope: str = "future_only"
    reason: str = "根据已定稿剧情调整后续规划"

def _check_project(project_id: str, request: Request) -> str:
    user_id = get_current_user(request)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return user_id

@router.post("/api/v1/projects/{project_id}/outline/evolve")
def evolve_outline(project_id: str, req: EvolveRequest, request: Request):
    user_id = _check_project(project_id, request)
    try:
        diff = outline_evolution_service.propose_outline_evolution(
            project_id, user_id, req.from_chapter, req.scope
        )
        outline_diff_service.save_outline_diff(project_id, diff)
        return {
            "success": diff["status"] != "failed",
            "diff_id": diff["diff_id"],
            "status": diff["status"],
            "affected_chapters": diff["affected_chapters"],
            "risk_level": diff["risk_level"],
            "summary": diff["summary"],
            "warnings": diff.get("warnings", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v1/projects/{project_id}/outline/diffs")
def list_outline_diffs(project_id: str, request: Request):
    _check_project(project_id, request)
    return outline_diff_service.list_outline_diffs(project_id)

@router.get("/api/v1/projects/{project_id}/outline/diffs/{diff_id}")
def get_outline_diff(project_id: str, diff_id: str, request: Request):
    _check_project(project_id, request)
    diff = outline_diff_service.get_outline_diff(project_id, diff_id)
    if not diff:
        raise HTTPException(status_code=404, detail="Diff not found")
    return diff

@router.post("/api/v1/projects/{project_id}/outline/diffs/{diff_id}/apply")
def apply_outline_diff(project_id: str, diff_id: str, request: Request):
    _check_project(project_id, request)
    try:
        diff = outline_diff_service.apply_outline_diff(project_id, diff_id)
        return diff
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/v1/projects/{project_id}/outline/diffs/{diff_id}/discard")
def discard_outline_diff(project_id: str, diff_id: str, request: Request):
    _check_project(project_id, request)
    try:
        diff = outline_diff_service.discard_outline_diff(project_id, diff_id)
        return diff
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
