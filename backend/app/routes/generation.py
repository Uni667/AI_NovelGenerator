import os
import logging
from fastapi import APIRouter, HTTPException, Request

from backend.app.auth import get_current_user
from backend.app.services import chapter_service, file_service, project_service
from backend.app.services.model_runtime import mark_used
from backend.app.services.sse_manager import make_streaming_response
from backend.app.services.task_orchestrator import prepare_generation_task, run_orchestrated_task
from backend.app.services.generation_context_builder import build_full_context, make_chapter_params
from backend.app.utils.sse import SSEEmitter
from novel_generator.cancel_token import CancelToken
from novel_generator.task_manager import (
    bind_cancel_token,
    get_task,
    raise_if_cancelled,
    request_cancel,
    task_payload,
    unbind_cancel_token,
)
from utils import read_file, get_word_count

router = APIRouter(tags=["AI 生成"])
logger = logging.getLogger(__name__)


def _check_project(project_id: str, request: Request) -> tuple[dict, dict, str]:
    user_id = get_current_user(request)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    pconfig = project_service.get_project_config(project_id)
    if not pconfig:
        raise HTTPException(status_code=404, detail="项目配置不存在")
    return project, pconfig, user_id


def _require_project_file(project_path: str, filename: str, label: str):
    if not os.path.exists(os.path.join(project_path, filename)):
        raise RuntimeError(f"缺少必备文件：{label} ({filename})，请先生成。")


def _build_terminal_error_payload(task_id: str, step: str, msg: str) -> dict:
    return {"step": step, "task_id": task_id, "message": msg}


@router.get("/api/v1/projects/{project_id}/generate/tasks/{task_id}")
def get_generation_task(project_id: str, task_id: str, request: Request):
    _check_project(project_id, request)
    task = get_task(task_id)
    if not task or task.project_id != project_id:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task_payload(task_id)


@router.post("/api/v1/projects/{project_id}/generate/tasks/{task_id}/cancel")
def cancel_generation_task(project_id: str, task_id: str, request: Request):
    _check_project(project_id, request)
    task = get_task(task_id)
    if not task or task.project_id != project_id:
        raise HTTPException(status_code=404, detail="任务不存在")
    if not request_cancel(task_id):
        raise HTTPException(status_code=404, detail="任务不存在")
    return task_payload(task_id)


@router.post("/api/v1/projects/{project_id}/generate/architecture")
@router.get("/api/v1/projects/{project_id}/generate/architecture")
async def generate_architecture(project_id: str, request: Request, task_id: str | None = None):
    project, pconfig, user_id = _check_project(project_id, request)
    resolved_task_id = prepare_generation_task(
        project_id, user_id, "generate_architecture", task_id,
        {"project_name": project.get("name", ""), "chapter_count": pconfig.get("num_chapters", 0)}
    )
    return make_streaming_response(request, resolved_task_id, run_orchestrated_task, _run_architecture, project, pconfig, user_id)


def _run_architecture(emitter: SSEEmitter, project: dict, pconfig: dict, user_id: str, task_id: str | None = None):
    from novel_generator.architecture import Novel_architecture_generate
    cancel_token = CancelToken()
    previous_status = project.get("status", "draft")
    
    if task_id:
        bind_cancel_token(task_id, cancel_token)

    ctx, proj_cfg, rt = build_full_context(user_id, project, pconfig, "architecture", cancel_token, task_id)

    try:
        project_service.update_project(project["id"], {"status": "generating"}, user_id)
        Novel_architecture_generate(ctx, proj_cfg, emitter=emitter, task_id=task_id)

        # 自动同步角色设定从 character_state.txt 到数据库，以便人物规划页立即可见
        try:
            from backend.app.services.sync_service import sync_txt_to_db
            sync_txt_to_db(project["id"])
        except Exception as e:
            logger.warning(f"自动同步角色设定到数据库失败: {e}")

        arch_path = os.path.join(project["filepath"], "Novel_architecture.txt")
        arch_content = read_file(arch_path) if os.path.exists(arch_path) else ""
        if arch_content.strip():
            file_service.create_project_file(
                project_id=project["id"], user_id=user_id, type="architecture",
                title=f"{project.get('name', '')} 架构", filename="Novel_architecture.txt",
                content=arch_content, source="ai_generated", is_current=True,
            )

        project_service.update_project(project["id"], {"status": "ready"}, user_id)
        mark_used(user_id, rt.api_credential_id, rt.model_profile_id)
    except Exception:
        project_service.update_project(project["id"], {"status": previous_status}, user_id)
        raise
    finally:
        if task_id:
            unbind_cancel_token(task_id)


@router.post("/api/v1/projects/{project_id}/generate/blueprint")
@router.get("/api/v1/projects/{project_id}/generate/blueprint")
async def generate_blueprint(project_id: str, request: Request, task_id: str | None = None):
    project, pconfig, user_id = _check_project(project_id, request)
    resolved_task_id = prepare_generation_task(
        project_id, user_id, "generate_outline", task_id,
        {"project_name": project.get("name", ""), "chapter_count": pconfig.get("num_chapters", 0)}
    )
    return make_streaming_response(request, resolved_task_id, run_orchestrated_task, _run_blueprint, project, pconfig, user_id)


def _run_blueprint(emitter: SSEEmitter, project: dict, pconfig: dict, user_id: str, task_id: str | None = None):
    from novel_generator.blueprint import Chapter_blueprint_generate
    cancel_token = CancelToken()
    if task_id:
        bind_cancel_token(task_id, cancel_token)

    # Sync missing files from DB to disk
    file_service.sync_project_files_to_disk(project["id"], project["filepath"], user_id)

    _require_project_file(project["filepath"], "Novel_architecture.txt", "小说架构")
    ctx, proj_cfg, rt = build_full_context(user_id, project, pconfig, "outline", cancel_token, task_id)

    try:
        Chapter_blueprint_generate(ctx, proj_cfg, emitter=emitter, task_id=task_id)
        if task_id:
            raise_if_cancelled(task_id)

        dir_path = os.path.join(project["filepath"], "Novel_directory.txt")
        dir_content = read_file(dir_path) if os.path.exists(dir_path) else ""
        if dir_content.strip():
            file_service.create_project_file(
                project_id=project["id"], user_id=user_id, type="outline",
                title=f"{project.get('name', '')} 章节目录", filename="Novel_directory.txt",
                content=dir_content, source="ai_generated", is_current=True,
            )

        chapter_service.sync_chapters_from_directory(project["id"], project["filepath"], user_id)
        mark_used(user_id, rt.api_credential_id, rt.model_profile_id)
    finally:
        if task_id:
            unbind_cancel_token(task_id)


@router.post("/api/v1/projects/{project_id}/generate/chapter/{chapter_number}")
@router.get("/api/v1/projects/{project_id}/generate/chapter/{chapter_number}")
async def generate_chapter(project_id: str, chapter_number: int, request: Request, task_id: str | None = None, start_step: str | None = None, enable_brainstorming: bool = False):
    project, pconfig, user_id = _check_project(project_id, request)
    resolved_task_id = prepare_generation_task(
        project_id, user_id, "generate_chapter", task_id,
        {"project_name": project.get("name", ""), "chapter_number": chapter_number, "enable_brainstorming": enable_brainstorming}
    )
    return make_streaming_response(request, resolved_task_id, run_orchestrated_task, _run_chapter_generation, project, pconfig, chapter_number, user_id, start_step, enable_brainstorming)


@router.post("/api/v1/projects/{project_id}/generate/chapters")
@router.get("/api/v1/projects/{project_id}/generate/chapters")
async def generate_chapter_batch(project_id: str, request: Request, start_chapter: int = 1, count: int = 1, task_id: str | None = None, start_step: str | None = None, enable_brainstorming: bool = False):
    if start_chapter < 1 or count < 1 or count > 20:
        raise HTTPException(status_code=400, detail="参数有误：起始章节需>0，且本轮生成数需在1-20 之间")
    project, pconfig, user_id = _check_project(project_id, request)
    resolved_task_id = prepare_generation_task(
        project_id, user_id, "generate_chapter_batch", task_id,
        {"project_name": project.get("name", ""), "start_chapter": start_chapter, "count": count, "enable_brainstorming": enable_brainstorming}
    )
    return make_streaming_response(request, resolved_task_id, run_orchestrated_task, _run_chapter_batch_generation, project, pconfig, start_chapter, count, user_id, start_step, enable_brainstorming)


def _run_chapter_batch_generation(emitter: SSEEmitter, project: dict, pconfig: dict, start_chapter: int, count: int, user_id: str, start_step: str | None = None, enable_brainstorming: bool = False, task_id: str | None = None):
    cancel_token = CancelToken()
    if task_id:
        bind_cancel_token(task_id, cancel_token)
    try:
        for offset in range(count):
            chapter_number = start_chapter + offset
            emitter.emit("progress", {"step": "batch", "status": "running", "message": f"开始生成第 {chapter_number} 章（{offset + 1}/{count}）"})
            _run_chapter_generation(emitter, project, pconfig, chapter_number, user_id, start_step=start_step if offset == 0 else None, enable_brainstorming=enable_brainstorming, task_id=task_id, cancel_token=cancel_token)
    finally:
        if task_id:
            unbind_cancel_token(task_id)


def _run_chapter_generation(emitter: SSEEmitter, project: dict, pconfig: dict, chapter_number: int, user_id: str, start_step: str | None = None, enable_brainstorming: bool = False, task_id: str | None = None, cancel_token: CancelToken | None = None):
    from novel_generator.chapter import build_chapter_prompt, generate_chapter_draft
    own_token = False
    if cancel_token is None:
        cancel_token = CancelToken()
        if task_id:
            bind_cancel_token(task_id, cancel_token)
        own_token = True

    try:
        # Sync missing files from DB to disk
        file_service.sync_project_files_to_disk(project["id"], project["filepath"], user_id)

        _require_project_file(project["filepath"], "Novel_architecture.txt", "小说架构")
        _require_project_file(project["filepath"], "Novel_directory.txt", "章节目录")
        ctx, _, rt = build_full_context(user_id, project, pconfig, "draft", cancel_token, task_id)
        params = make_chapter_params(pconfig, chapter_number)

        if enable_brainstorming and (not start_step or start_step == "drafting"):
            from novel_generator.chapter_pipeline.brainstorm import run_multi_agent_brainstorming
            from chapter_directory_parser import get_chapter_info_from_blueprint

            global_summary_text = read_file(os.path.join(project["filepath"], "global_summary.txt")).strip() or "（尚未生成全局摘要）"
            blueprint_text = read_file(os.path.join(project["filepath"], "Novel_directory.txt")).strip() or "（尚未生成章节目录）"
            chapter_info = get_chapter_info_from_blueprint(blueprint_text, chapter_number)

            def _cancel_check():
                if task_id:
                    raise_if_cancelled(task_id)

            director_guidance = run_multi_agent_brainstorming(
                ctx,
                global_summary=global_summary_text,
                chapter_info=chapter_info,
                task_id=task_id,
                emitter=emitter,
                cancel_check=_cancel_check
            )
            original_guidance = getattr(params, "user_guidance", "") or ""
            params.user_guidance = original_guidance + director_guidance

        emitter.emit("progress", {"step": "build_prompt", "status": "running", "message": f"正在构建第 {chapter_number} 章提示词..."})
        prompt_text = build_chapter_prompt(ctx, params, task_id=task_id)
        emitter.emit("progress", {"step": "build_prompt", "status": "done", "message": "提示词构建完成"})

        emitter.emit("progress", {"step": "draft", "status": "running", "message": f"正在生成第 {chapter_number} 章草稿..."})
        draft_text = generate_chapter_draft(ctx, params, custom_prompt_text=prompt_text, emitter=emitter, task_id=task_id, start_step=start_step, enable_brainstorming=enable_brainstorming)

        if draft_text:
            if task_id:
                raise_if_cancelled(task_id)
            wc = get_word_count(draft_text)
            chapter_service.mark_chapter_draft(project["id"], chapter_number, wc)
            mark_used(user_id, rt.api_credential_id, rt.model_profile_id)
            emitter.emit("progress", {"step": "draft", "status": "done", "message": f"第 {chapter_number} 章草稿生成完成"})
            emitter.emit("partial", {"step": "draft", "content": draft_text[:500] + "..."})
        else:
            emitter.emit("error", _build_terminal_error_payload(task_id or "", "draft", "草稿生成返回空内容"))
            raise RuntimeError("草稿生成返回空内容")
    finally:
        if own_token and task_id:
            unbind_cancel_token(task_id)


@router.post("/api/v1/projects/{project_id}/generate/finalize/{chapter_number}")
@router.get("/api/v1/projects/{project_id}/generate/finalize/{chapter_number}")
async def finalize_chapter_route(project_id: str, chapter_number: int, request: Request, task_id: str | None = None):
    project, pconfig, user_id = _check_project(project_id, request)
    resolved_task_id = prepare_generation_task(
        project_id, user_id, "finalize_chapter", task_id,
        {"project_name": project.get("name", ""), "chapter_number": chapter_number}
    )
    return make_streaming_response(request, resolved_task_id, run_orchestrated_task, _run_finalize, project, pconfig, chapter_number, user_id)


def _run_finalize(emitter: SSEEmitter, project: dict, pconfig: dict, chapter_number: int, user_id: str, task_id: str | None = None):
    from novel_generator.finalization import finalize_chapter
    cancel_token = CancelToken()
    if task_id:
        bind_cancel_token(task_id, cancel_token)

    try:
        # Sync missing files from DB to disk
        file_service.sync_project_files_to_disk(project["id"], project["filepath"], user_id)

        _require_project_file(project["filepath"], os.path.join("chapters", f"chapter_{chapter_number}.txt"), f"第 {chapter_number} 章草稿")
        ctx, _, rt = build_full_context(user_id, project, pconfig, "polish", cancel_token, task_id)
        params = make_chapter_params(pconfig, chapter_number)

        emitter.emit("progress", {"step": "finalize", "status": "running", "message": f"正在定稿第 {chapter_number} 章..."})
        chapter_content = finalize_chapter(ctx, params, emitter=emitter, task_id=task_id)
        if task_id:
            raise_if_cancelled(task_id)

        chapter_text = read_file(os.path.join(project["filepath"], "chapters", f"chapter_{chapter_number}.txt"))
        wc = get_word_count(chapter_text)
        chapter_service.mark_chapter_final(project["id"], chapter_number, wc)
        mark_used(user_id, rt.api_credential_id, rt.model_profile_id)
        emitter.emit("progress", {"step": "finalize", "status": "done", "message": f"第 {chapter_number} 章定稿完成"})
    finally:
        if task_id:
            unbind_cancel_token(task_id)


@router.post("/api/v1/projects/{project_id}/generate/sync/architecture")
def generate_architecture_sync(project_id: str, request: Request):
    """直接同步生成架构，返回结果文本。不依赖 SSE/线程池。"""
    project, pconfig, user_id = _check_project(project_id, request)
    from novel_generator.architecture import Novel_architecture_generate
    
    ctx, proj_cfg, rt = build_full_context(user_id, project, pconfig, "architecture", None)
    project_service.update_project(project_id, {"status": "generating"}, user_id)

    try:
        Novel_architecture_generate(ctx, proj_cfg)
        arch_path = os.path.join(project["filepath"], "Novel_architecture.txt")
        content = read_file(arch_path) if os.path.exists(arch_path) else ""
        file_service.create_project_file(
            project_id=project_id, user_id=user_id, type="architecture",
            title="架构", filename="Novel_architecture.txt", content=content,
            source="ai_generated", is_current=True,
        )
        project_service.update_project(project_id, {"status": "ready"}, user_id)
        mark_used(user_id, rt.api_credential_id, rt.model_profile_id)
        return {"success": True, "message": "架构生成完成", "length": len(content)}
    except Exception as exc:
        project_service.update_project(project_id, {"status": "draft"}, user_id)
        logger.exception("Sync architecture generation failed")
        raise HTTPException(status_code=500, detail=f"架构生成失败: {exc}")


@router.get("/api/v1/projects/{project_id}/generate/tasks")
def list_generation_tasks(project_id: str, request: Request):
    _check_project(project_id, request)
    from novel_generator.task_manager import list_tasks
    tasks = list_tasks(project_id)
    results = [task_payload(t.task_id) for t in tasks]
    results.sort(key=lambda p: p.get("created_at", 0), reverse=True)
    return results


@router.post("/api/v1/projects/{project_id}/generate/tasks/{task_id}/retry")
async def retry_generation_task(project_id: str, task_id: str, request: Request):
    project, _, _ = _check_project(project_id, request)
    task = get_task(task_id)
    if not task or task.project_id != project_id:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.status not in ("failed", "cancelled"):
        raise HTTPException(status_code=400, detail="只能重试失败或已取消的任务")

    kind, metadata = task.kind, task.metadata or {}
    start_step = task.current_step if task.current_step not in ("completed", "") else None
    
    if kind == "generate_architecture":
        return await generate_architecture(project_id, request, task_id=task_id)
    elif kind == "generate_outline":
        return await generate_blueprint(project_id, request, task_id=task_id)
    elif kind == "finalize_chapter":
        return await finalize_chapter_route(project_id, metadata.get("chapter_number", 1), request, task_id=task_id)
    elif kind == "generate_chapter":
        return await generate_chapter(
            project_id, metadata.get("chapter_number", 1), request,
            task_id=task_id, start_step=start_step,
            enable_brainstorming=metadata.get("enable_brainstorming", False)
        )
    elif kind == "generate_chapter_batch":
        return await generate_chapter_batch(
            project_id, request, start_chapter=metadata.get("start_chapter", 1),
            count=metadata.get("count", 1), task_id=task_id, start_step=start_step,
            enable_brainstorming=metadata.get("enable_brainstorming", False)
        )
    else:
        raise HTTPException(status_code=400, detail=f"不支持重试该任务类型: {kind}")


from pydantic import BaseModel
from novel_generator.json_parser import extract_json_from_text

class InferConfigRequest(BaseModel):
    user_guidance: str
    platform: str = "tomato"

INFER_CONFIG_PROMPT = """\
你是一名经验极其丰富的网络小说编辑，擅长分析大纲创意并进行平台定位与分类设计。
请分析以下小说梗概/大纲创意，并严格以 JSON 格式输出推荐的小说配置参数。

目标平台标签：{platform}

待分析的小说梗概/创意：
{user_guidance}

请输出以下 JSON 格式数据（不要包含 ```json 等任何标记，确保可以直接被 JSON 解析）：
{{
  "name": "推荐的书名（结合梗概创意生成，20字以内）",
  "category": "推荐的平台大类分区（如果发布平台是番茄小说，推荐'都市脑洞'、'玄幻脑洞'、'悬疑恋爱'、'悬疑脑洞'等平台真实分类；如果是起点，推荐'都市'、'轻小说'、'玄幻'等起点分类）",
  "genre": "推荐的流派风格（必须从以下列表中选择一个最贴切的：'系统流', '重生流', '穿越流', '凡人流', '无敌流', '废柴流', '种田流', '无限流', '洪荒流', '末世流', '异能流', '灵气复苏', '诸天流', '反派流', '退婚流', '传统升级流', '其他'）",
  "topic": "推荐的核心主题/金手指（20字以内，如：提取技能、时间回溯、神豪返利、反向毒奶）",
  "target_reader": "目标受众定位（15字以内，如：18-25岁年轻爽文读者、核心科幻爱好者）",
  "style_requirement": "推荐的文风要求描述（20字以内，如：冷峻克制、快节奏爽文、热血搞笑、轻小说吐槽风）",
  "forbidden": "推荐的避雷/禁改限制（如：不可降智、主角性格必须杀伐果断、千万不能洗白反派、单女主、不圣母，写2到3条，用换行分隔）"
}}
"""

@router.post("/api/v1/projects/infer-config")
def infer_project_config(payload: InferConfigRequest, request: Request):
    user_id = get_current_user(request)
    if not payload.user_guidance.strip():
        raise HTTPException(status_code=400, detail="内容指导/大纲不能为空")
        
    prompt = INFER_CONFIG_PROMPT.format(
        platform=payload.platform,
        user_guidance=payload.user_guidance
    )
    
    from backend.app.services.model_runtime import call_chat
    try:
        response = call_chat(user_id, prompt, purpose="general")
        if not response:
            raise HTTPException(status_code=502, detail="大模型节点未响应或返回空内容")
            
        parsed = extract_json_from_text(response)
        if parsed and isinstance(parsed, dict):
            return {"success": True, "data": parsed}
        else:
            logger.warning("Failed to parse inferred config JSON: %s", response[:300])
            raise HTTPException(status_code=502, detail="大模型节点返回的数据格式异常，无法解析为 JSON")
    except Exception as exc:
        logger.exception("AI config inference failed")
        raise HTTPException(status_code=500, detail=f"智能推断失败: {exc}")
