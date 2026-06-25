"""
Generation Context Builder Service — 负责组装生成小说各阶段所需的上下文对象。
"""

import logging
from fastapi import HTTPException

from backend.app.services.config_resolver import ConfigError, RuntimeConfig, get_runtime_config
from backend.app.services.model_runtime import _provider_to_interface
from novel_generator.context import ChapterParams, GenerationContext, ProjectConfig
from novel_generator.cancel_token import CancelToken

logger = logging.getLogger(__name__)


def get_runtime_config_or_400(user_id: str, purpose: str, project_id: str) -> RuntimeConfig:
    """获取指定用途的运行时配置。如果配置有误抛出 400 错误。"""
    try:
        return get_runtime_config(user_id, purpose, project_id)
    except ConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))


def _runtime_to_llm_conf(rt: RuntimeConfig) -> dict:
    return {
        "api_key": rt.api_key,
        "base_url": rt.base_url,
        "model_name": rt.model,
        "interface_format": _provider_to_interface(rt.provider),
        "temperature": rt.temperature or 0.7,
        "max_tokens": rt.max_tokens or 8192,
        "timeout": 600,
    }


def _runtime_to_emb_conf(rt: RuntimeConfig) -> dict:
    return {
        "api_key": rt.api_key,
        "base_url": rt.base_url,
        "model_name": rt.model,
        "interface_format": _provider_to_interface(rt.provider),
    }


def _optional_embedding_conf(user_id: str, project_id: str) -> dict:
    try:
        return _runtime_to_emb_conf(get_runtime_config(user_id, "embedding", project_id))
    except ConfigError:
        return {}


def make_ctx(
    llm_conf: dict,
    emb_conf: dict,
    filepath: str,
    project_id: str = "",
    user_id: str = "",
    cancel_token: CancelToken | None = None,
    runtime_config: object = None,
) -> GenerationContext:
    return GenerationContext.from_dicts(
        llm_dict=llm_conf,
        emb_dict=emb_conf,
        filepath=filepath,
        project_id=project_id,
        user_id=user_id,
        cancel_token=cancel_token,
        runtime_config=runtime_config,
    )


def make_project_cfg(pconfig: dict) -> ProjectConfig:
    return ProjectConfig(
        topic=pconfig.get("topic", ""),
        genre=pconfig.get("genre", ""),
        category=pconfig.get("category", ""),
        platform=pconfig.get("platform", "tomato"),
        num_chapters=pconfig.get("num_chapters", 0),
        word_number=pconfig.get("word_number", 3000),
        language=pconfig.get("language", "zh"),
        user_guidance=pconfig.get("user_guidance", ""),
        target_reader=pconfig.get("target_reader", ""),
        reader_direction=pconfig.get("reader_direction", ""),
        trend_key=pconfig.get("trend_key", ""),
        custom_trend=pconfig.get("custom_trend", ""),
        trend_translation=pconfig.get("trend_translation", ""),
        forbidden=pconfig.get("forbidden", ""),
        style_requirement=pconfig.get("style_requirement", ""),
    )


def make_chapter_params(pconfig: dict, chapter_number: int) -> ChapterParams:
    return ChapterParams(
        chapter_number=chapter_number,
        word_number=pconfig.get("word_number", 3000),
        user_guidance=pconfig.get("user_guidance", ""),
        platform=pconfig.get("platform", "tomato"),
        target_reader=pconfig.get("target_reader", ""),
        reader_direction=pconfig.get("reader_direction", ""),
        trend_key=pconfig.get("trend_key", ""),
        custom_trend=pconfig.get("custom_trend", ""),
        trend_translation=pconfig.get("trend_translation", ""),
        forbidden=pconfig.get("forbidden", ""),
        style_requirement=pconfig.get("style_requirement", ""),
    )


def mask_api_key(api_key: str) -> str:
    api_key = (api_key or "").strip()
    if not api_key:
        return ""
    if len(api_key) <= 8:
        return "*" * len(api_key)
    return f"{api_key[:4]}***{api_key[-4:]}"


def sanitize_base_url(base_url: str) -> str:
    return (base_url or "").strip().rstrip("/")


def log_llm_selection(task_id: str, project: dict, llm_conf: dict, kind: str) -> None:
    logger.info(
        "Generation preflight [task_id=%s kind=%s project_id=%s project_name=%s provider=%s model=%s base_url=%s api_key=%s timeout=%s max_tokens=%s]",
        task_id,
        kind,
        project.get("id"),
        project.get("name"),
        llm_conf.get("interface_format", ""),
        llm_conf.get("model_name", ""),
        sanitize_base_url(llm_conf.get("base_url", "")),
        mask_api_key(llm_conf.get("api_key", "")),
        llm_conf.get("timeout"),
        llm_conf.get("max_tokens"),
    )


def build_full_context(user_id: str, project: dict, pconfig: dict, purpose: str, cancel_token: CancelToken | None, task_id: str | None = None) -> tuple[GenerationContext, ProjectConfig, RuntimeConfig]:
    """一键组装大模型上下文、项目参数和配置对象。"""
    rt = get_runtime_config_or_400(user_id, purpose, project["id"])
    llm_conf = _runtime_to_llm_conf(rt)
    emb_conf = _optional_embedding_conf(user_id, project["id"])
    
    if task_id:
        log_llm_selection(task_id, project, llm_conf, purpose)
        
    ctx = make_ctx(llm_conf, emb_conf, project["filepath"], project_id=project["id"], user_id=user_id, cancel_token=cancel_token, runtime_config=rt)
    proj_cfg = make_project_cfg(pconfig)
    
    return ctx, proj_cfg, rt
