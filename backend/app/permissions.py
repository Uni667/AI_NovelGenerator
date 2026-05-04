"""统一权限校验工具函数。"""

from fastapi import Request

from backend.app.auth import get_current_user
from backend.app.database import get_db
from backend.app.errors import auth_required, project_not_found


def require_user(request: Request) -> str:
    """获取当前登录用户 ID。未登录返回 401。"""
    user_id = get_current_user(request)
    if not user_id:
        raise auth_required()
    return user_id


def require_project_owner(project_id: str, request: Request) -> tuple[str, dict]:
    """验证项目归属，返回 (user_id, project)。"""
    user_id = get_current_user(request)
    if not user_id:
        raise auth_required()

    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM project WHERE id = ? AND user_id = ?",
            (project_id, user_id),
        ).fetchone()

    if not row:
        raise project_not_found()

    return user_id, dict(row)
