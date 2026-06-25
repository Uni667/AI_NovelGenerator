import logging
from typing import List
from fastapi import APIRouter, HTTPException, Request

from backend.app.auth import get_current_user
from backend.app.models.local_library import (
    ProjectReferenceBindingRequest,
    ProjectReferenceBindingResponse,
)
from backend.app.services.local_reference_context_service import (
    get_bindings,
    bind_book,
    update_binding,
    unbind_book,
    build_reference_context
)

router = APIRouter(tags=["项目参考绑定"])
logger = logging.getLogger(__name__)


def assert_local_file_access_enabled():
    """验证是否开启了本地目录访问。若未开启，抛出 403。"""
    from backend.app.services.local_file_guard import get_file_access_flag
    if not get_file_access_flag():
        raise HTTPException(
            status_code=403,
            detail="本地文件访问功能已禁用(Feature Flag ALLOW_LOCAL_FILE_ACCESS 为 false)。"
        )


@router.get("/api/v1/projects/{project_id}/local-reference-books", response_model=List[ProjectReferenceBindingResponse])
def route_get_project_bindings(project_id: str, request: Request):
    get_current_user(request)
    assert_local_file_access_enabled()
    return get_bindings(project_id)


@router.post("/api/v1/projects/{project_id}/local-reference-books/{book_id}/attach", response_model=ProjectReferenceBindingResponse)
def route_bind_reference_book(project_id: str, book_id: str, data: ProjectReferenceBindingRequest, request: Request):
    get_current_user(request)
    assert_local_file_access_enabled()
    return bind_book(project_id, book_id, data.model_dump())

@router.post("/api/v1/projects/{project_id}/local-reference-books", response_model=ProjectReferenceBindingResponse)
def route_bind_reference_book_legacy(project_id: str, data: ProjectReferenceBindingRequest, request: Request):
    # for backward compatibility with the skipped test if it uses the old endpoint
    get_current_user(request)
    assert_local_file_access_enabled()
    return bind_book(project_id, data.book_id, data.model_dump())

@router.patch("/api/v1/projects/{project_id}/local-reference-books/{book_id}", response_model=ProjectReferenceBindingResponse)
def route_update_reference_book(project_id: str, book_id: str, data: ProjectReferenceBindingRequest, request: Request):
    get_current_user(request)
    assert_local_file_access_enabled()
    return update_binding(project_id, book_id, data.model_dump())


@router.delete("/api/v1/projects/{project_id}/local-reference-books/{book_id}")
def route_unbind_reference_book(project_id: str, book_id: str, request: Request):
    get_current_user(request)
    assert_local_file_access_enabled()
    unbind_book(project_id, book_id)
    return {"message": "解绑成功", "project_id": project_id, "book_id": book_id}


@router.post("/api/v1/projects/{project_id}/reference-context/preview")
def route_preview_reference_context(project_id: str, request: Request):
    get_current_user(request)
    assert_local_file_access_enabled()
    context = build_reference_context(project_id)
    return context
