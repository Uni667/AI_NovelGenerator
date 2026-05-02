from fastapi import APIRouter, HTTPException, Request
from backend.app.services import user_service
from backend.app.auth import get_current_user
from backend.app.models.config import (
    LLMConfigCreate,
    LLMConfigUpdate,
    EmbeddingConfigCreate,
    EmbeddingConfigUpdate,
)

router = APIRouter(tags=["API 配置"])


def _config_error_status(message: str) -> int:
    return 404 if "不存在" in message else 400


@router.get("/api/v1/config/llm")
def list_llm_configs(request: Request):
    user_id = get_current_user(request)
    return user_service.list_user_llm_configs(user_id)


@router.post("/api/v1/config/llm")
def create_llm_config(data: LLMConfigCreate, request: Request):
    user_id = get_current_user(request)
    try:
        return user_service.add_user_llm_config(user_id, data.name, data.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=_config_error_status(str(e)), detail=str(e))


@router.put("/api/v1/config/llm/{name:path}")
def update_llm_config(name: str, data: LLMConfigUpdate, request: Request):
    user_id = get_current_user(request)
    try:
        return user_service.update_user_llm_config(user_id, name, data.model_dump(exclude_none=True))
    except ValueError as e:
        raise HTTPException(status_code=_config_error_status(str(e)), detail=str(e))


@router.delete("/api/v1/config/llm/{name:path}")
def delete_llm_config(name: str, request: Request):
    user_id = get_current_user(request)
    try:
        user_service.delete_user_llm_config(user_id, name)
        return {"message": f"LLM 配置 '{name}' 已删除"}
    except ValueError as e:
        raise HTTPException(status_code=_config_error_status(str(e)), detail=str(e))


@router.post("/api/v1/config/llm/{name:path}/test")
def test_llm_config_route(name: str, request: Request):
    user_id = get_current_user(request)
    try:
        return user_service.test_user_llm_config(user_id, name)
    except ValueError as e:
        raise HTTPException(status_code=_config_error_status(str(e)), detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM 配置 '{name}' 测试异常: {e}")


@router.get("/api/v1/config/embedding")
def list_embedding_configs(request: Request):
    user_id = get_current_user(request)
    return user_service.list_user_embedding_configs(user_id)


@router.post("/api/v1/config/embedding")
def create_embedding_config(data: EmbeddingConfigCreate, request: Request):
    user_id = get_current_user(request)
    try:
        return user_service.add_user_embedding_config(user_id, data.name, data.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=_config_error_status(str(e)), detail=str(e))


@router.put("/api/v1/config/embedding/{name:path}")
def update_embedding_config(name: str, data: EmbeddingConfigUpdate, request: Request):
    user_id = get_current_user(request)
    try:
        return user_service.update_user_embedding_config(user_id, name, data.model_dump(exclude_none=True))
    except ValueError as e:
        raise HTTPException(status_code=_config_error_status(str(e)), detail=str(e))


@router.delete("/api/v1/config/embedding/{name:path}")
def delete_embedding_config(name: str, request: Request):
    user_id = get_current_user(request)
    try:
        user_service.delete_user_embedding_config(user_id, name)
        return {"message": f"Embedding 配置 '{name}' 已删除"}
    except ValueError as e:
        raise HTTPException(status_code=_config_error_status(str(e)), detail=str(e))


@router.post("/api/v1/config/embedding/{name:path}/test")
def test_embedding_config_route(name: str, request: Request):
    user_id = get_current_user(request)
    try:
        return user_service.test_user_embedding_config(user_id, name)
    except ValueError as e:
        raise HTTPException(status_code=_config_error_status(str(e)), detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding 配置 '{name}' 测试异常: {e}")
