# -*- coding: utf-8 -*-
from fastapi import Request, HTTPException, Depends
from backend.app.auth import get_current_user
from backend.app.services import project_service
from backend.app.services.generation_context_builder import build_full_context
from novel_generator.context import GenerationContext

async def get_generation_context(project_id: str, request: Request) -> GenerationContext:
    """
    FastAPI 依赖项：根据 project_id 和当前认证用户构建 GenerationContext。
    """
    user_id = get_current_user(request)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    pconfig = project_service.get_project_config(project_id)
    if not pconfig:
        raise HTTPException(status_code=404, detail="项目配置不存在")
    ctx, _, _ = build_full_context(user_id, project, pconfig, "polish", None)
    return ctx
