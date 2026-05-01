from fastapi import APIRouter, HTTPException
from backend.app.services import config_service
from backend.app.utils.crypto import mask_key

router = APIRouter(tags=["全局配置"])


@router.get("/api/v1/config/llm")
def list_llm_configs():
    configs = config_service.get_all_llm_configs()
    result = {}
    for name, conf in configs.items():
        result[name] = {
            "name": name,
            "base_url": conf.get("base_url", ""),
            "model_name": conf.get("model_name", ""),
            "temperature": conf.get("temperature", 0.7),
            "max_tokens": conf.get("max_tokens", 8192),
            "timeout": conf.get("timeout", 600),
            "interface_format": conf.get("interface_format", "OpenAI"),
            "api_key_masked": mask_key(conf.get("api_key", ""))
        }
    return result


@router.post("/api/v1/config/llm")
def create_llm_config(data: dict):
    try:
        result = config_service.add_llm_config(data["name"], data)
        return {"name": data["name"], "api_key_masked": mask_key(result.get("api_key", ""))}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/api/v1/config/llm/{name}")
def update_llm_config(name: str, data: dict):
    try:
        result = config_service.update_llm_config(name, data)
        return {"name": name, "api_key_masked": mask_key(result.get("api_key", ""))}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/api/v1/config/llm/{name}")
def delete_llm_config(name: str):
    try:
        config_service.delete_llm_config(name)
        return {"message": f"LLM 配置 '{name}' 已删除"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/v1/config/llm/{name}/test")
def test_llm_config_route(name: str):
    try:
        return config_service.test_llm_config(name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/config/embedding")
def list_embedding_configs():
    configs = config_service.get_all_embedding_configs()
    result = {}
    for name, conf in configs.items():
        result[name] = {
            "name": name,
            "base_url": conf.get("base_url", ""),
            "model_name": conf.get("model_name", ""),
            "retrieval_k": conf.get("retrieval_k", 4),
            "interface_format": conf.get("interface_format", "OpenAI"),
            "api_key_masked": mask_key(conf.get("api_key", ""))
        }
    return result


@router.post("/api/v1/config/embedding")
def create_embedding_config(data: dict):
    try:
        result = config_service.add_embedding_config(data["name"], data)
        return {"name": data["name"], "api_key_masked": mask_key(result.get("api_key", ""))}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/api/v1/config/embedding/{name}")
def delete_embedding_config(name: str):
    try:
        config_service.delete_embedding_config(name)
        return {"message": f"Embedding 配置 '{name}' 已删除"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/v1/config/embedding/{name}/test")
def test_embedding_config_route(name: str):
    try:
        return config_service.test_embedding_config(name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
