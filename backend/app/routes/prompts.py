# -*- coding: utf-8 -*-
"""
提示词实验室 API
GET  /api/v1/projects/{project_id}/prompts          → 获取所有提示词（含用户覆盖）
PUT  /api/v1/projects/{project_id}/prompts/{key}    → 覆盖指定提示词（含变量校验与备份）
DELETE /api/v1/projects/{project_id}/prompts/{key} → 恢复默认
GET  /api/v1/prompts/keys                           → 获取所有可编辑的 prompt key 清单
GET  /api/v1/projects/{project_id}/prompts/{key}/snapshots → 获取历史快照
POST /api/v1/projects/{project_id}/prompts/{key}/restore   → 恢复指定快照
GET  /api/v1/projects/{project_id}/prompts/export          → 导出自定义提示词
POST /api/v1/projects/{project_id}/prompts/import          → 导入自定义提示词
"""
import json
import os
import time
import datetime
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from backend.app.auth import get_current_user
from backend.app.services import project_service

router = APIRouter(tags=["提示词实验室"])

# ── 可管理的 Prompt 键定义 ─────────────────────────────────────────────
PROMPT_CATALOG = [
    {
        "key": "core_seed_prompt",
        "label": "核心种子",
        "group": "架构生成",
        "description": "用「雪花写作法」生成一句话故事核心，是整部小说的基石。",
    },
    {
        "key": "character_dynamics_prompt",
        "label": "角色动力学",
        "group": "架构生成",
        "description": "基于核心种子，设计 3-6 个具有动态变化潜力的核心角色，包含关系网与成长路线。",
    },
    {
        "key": "world_building_prompt",
        "label": "世界观构建",
        "group": "架构生成",
        "description": "构建物理维度、社会维度、隐喻维度三位一体的世界观体系。",
    },
    {
        "key": "plot_architecture_prompt",
        "label": "三幕式情节架构",
        "group": "架构生成",
        "description": "基于核心种子和角色体系，生成完整的三幕式情节主线蓝图，含追读钩子和伏笔规划。",
    },
    {
        "key": "initial_global_summary_prompt",
        "label": "初始全局摘要",
        "group": "架构生成",
        "description": "将架构四要素提炼成可持续维护的「全局摘要」工作文档，供章节写作实时读取。",
    },
    {
        "key": "initial_plot_arcs_prompt",
        "label": "伏笔暗线台账",
        "group": "架构生成",
        "description": "生成可追踪的伏笔与暗线清单，每条包含埋设状态、预计回收章节和风险提醒。",
    },
    {
        "key": "create_character_state_prompt",
        "label": "初始角色状态表",
        "group": "架构生成",
        "description": "从角色架构中生成结构化的角色状态追踪文档，包含资源/能力/秘密等字段。",
    },
    {
        "key": "architecture_section_polish_prompt",
        "label": "架构文风去策划腔",
        "group": "架构生成",
        "description": "将策划案腔的架构文档润色为更贴近创作现场的工作文档语言，不改动核心设定。",
    },
    {
        "key": "chapter_blueprint_prompt",
        "label": "全书章节目录（一次性）",
        "group": "章节目录",
        "description": "根据小说架构一次性生成完整的章节目录，适合篇幅较短的项目。",
    },
    {
        "key": "chunked_chapter_blueprint_prompt",
        "label": "章节目录（分批续写）",
        "group": "章节目录",
        "description": "当章节数超出模型容量时，分批生成并衔接前文目录，确保剧情连贯。",
    },
    {
        "key": "blueprint_polish_prompt",
        "label": "目录精修润色",
        "group": "章节目录",
        "description": "对生成的章节目录进行平台节奏校准与剧情钩子强化。",
    },
    {
        "key": "first_chapter_draft_prompt",
        "label": "第一章初稿",
        "group": "正文生成",
        "description": "专用于第一章的写作提示词，包含开场吸引力、世界观引入、主角登场节奏等要求。",
    },
    {
        "key": "next_chapter_draft_prompt",
        "label": "后续章节初稿",
        "group": "正文生成",
        "description": "后续章节通用写作提示词，结合前文摘要、角色状态、伏笔台账和章节目标生成初稿。",
    },
    {
        "key": "platform_chapter_guidance_prompt",
        "label": "平台创作指南注入",
        "group": "正文生成",
        "description": "将平台读者口味、节奏偏好和禁忌规则注入章节写作提示词，实现平台定向优化。",
    },
    {
        "key": "summarize_recent_chapters_prompt",
        "label": "近章摘要压缩",
        "group": "正文生成",
        "description": "将最近 N 章内容压缩为连贯摘要，用于给下一章提供上下文而不超出 Token 限制。",
    },
    {
        "key": "de_ai_style_revision_prompt",
        "label": "去 AI 腔润色",
        "group": "修订与质检",
        "description": "识别并消除机器生成感，将初稿改写为更自然、更有人味的网文文风。",
    },
    {
        "key": "chapter_quality_rewrite_prompt",
        "label": "质检驱动重写",
        "group": "修订与质检",
        "description": "结合质检分析报告（开头/结尾/中段/台词）对章节进行定向强化重写。",
    },
    {
        "key": "mid_section_quality_prompt",
        "label": "中段质量分析",
        "group": "修订与质检",
        "description": "专门分析章节中段（最易拖沓的区域）的质量问题并给出具体改写建议。",
    },
    {
        "key": "dialogue_voice_check_prompt",
        "label": "台词声线校验",
        "group": "修订与质检",
        "description": "检查章节中各角色的台词是否符合其人设声线，识别「台词同质化」问题。",
    },
    {
        "key": "enrich_prompt",
        "label": "内容扩写增量",
        "group": "修订与质检",
        "description": "对字数不足的章节进行扩写，重点充实场景细节、心理描写和伏笔埋设。",
    },
    {
        "key": "summary_prompt",
        "label": "全局摘要更新",
        "group": "状态更新",
        "description": "章节定稿后，将本章新增的事件、信息、角色变化同步更新到全局摘要文档。",
    },
    {
        "key": "compress_global_summary_prompt",
        "label": "全局摘要过长压缩",
        "group": "状态更新",
        "description": "全局大摘要超出设定阈值时，自动触发的长线情节无损瘦身提示词。",
    },
    {
        "key": "update_character_state_prompt",
        "label": "角色状态更新",
        "group": "状态更新",
        "description": "根据本章内容更新角色的目标、立场、秘密、资源等字段，防止设定漂移。",
    },
    {
        "key": "update_plot_arcs_prompt",
        "label": "伏笔台账更新",
        "group": "状态更新",
        "description": "根据本章内容更新伏笔的埋设/回收状态，并添加新发现的风险提醒。",
    },
    {
        "key": "single_chapter_summary_prompt",
        "label": "单章微型摘要生成",
        "group": "状态更新",
        "description": "定稿时为当前章节生成 200-300 字的精简微摘要，用于长篇创作的滑动上下文优化。",
    },
]

PROMPT_KEY_SET = {p["key"] for p in PROMPT_CATALOG}

# ── 占位符白名单映射 ──────────────────────────────────────────────────
PROMPT_ALLOWED_VARIABLES = {
    "core_seed_prompt": {
        "topic", "genre", "category", "number_of_chapters", "word_number", 
        "user_guidance", "knowledge_context"
    },
    "character_dynamics_prompt": {
        "core_seed", "user_guidance"
    },
    "world_building_prompt": {
        "core_seed", "user_guidance"
    },
    "plot_architecture_prompt": {
        "core_seed", "user_guidance"
    },
    "initial_global_summary_prompt": {
        "core_seed", "character_dynamics", "world_building", "plot_architecture"
    },
    "initial_plot_arcs_prompt": {
        "core_seed", "character_dynamics", "world_building", "plot_architecture"
    },
    "create_character_state_prompt": {
        "core_seed", "characters_involved"
    },
    "architecture_section_polish_prompt": {
        "platform", "role", "content"
    },
    "chapter_blueprint_prompt": {
        "novel_setting", "number_of_chapters", "user_guidance"
    },
    "chunked_chapter_blueprint_prompt": {
        "novel_setting", "current_blueprint", "start_chapter", "end_chapter", "user_guidance"
    },
    "blueprint_polish_prompt": {
        "novel_setting", "blueprint", "user_guidance"
    },
    "first_chapter_draft_prompt": {
        "novel_number", "word_number", "chapter_title", "chapter_role", "chapter_purpose", 
        "suspense_level", "foreshadowing", "plot_twist_level", "chapter_summary", 
        "characters_involved", "key_items", "scene_location", "time_constraint", 
        "user_guidance", "novel_setting", "plot_arcs", "graph_context", "platform_guidance"
    },
    "next_chapter_draft_prompt": {
        "global_summary", "previous_chapter_excerpt", "user_guidance", "character_state", 
        "plot_arcs", "graph_context", "short_summary", "platform_guidance", "novel_number", 
        "chapter_title", "chapter_role", "chapter_purpose", "suspense_level", "foreshadowing", 
        "plot_twist_level", "chapter_summary", "word_number", "characters_involved", "key_items", 
        "scene_location", "time_constraint", "next_chapter_number", "next_chapter_title", 
        "next_chapter_role", "next_chapter_purpose", "next_chapter_suspense_level", 
        "next_chapter_foreshadowing", "next_chapter_plot_twist_level", "next_chapter_summary", 
        "filtered_context"
    },
    "platform_chapter_guidance_prompt": {
        "platform_label", "platform_rules"
    },
    "summarize_recent_chapters_prompt": {
        "combined_text", "novel_number", "chapter_title", "chapter_role", "chapter_purpose", 
        "suspense_level", "foreshadowing", "plot_twist_level", "chapter_summary", 
        "next_chapter_number", "next_chapter_title", "next_chapter_role", "next_chapter_purpose", 
        "next_chapter_summary", "next_chapter_suspense_level", "next_chapter_foreshadowing", 
        "next_chapter_plot_twist_level"
    },
    "de_ai_style_revision_prompt": {
        "platform_label", "platform_rules", "novel_number", "chapter_title", "chapter_role", 
        "chapter_purpose", "suspense_level", "foreshadowing", "plot_twist_level", 
        "chapter_summary", "word_number", "chapter_text"
    },
    "chapter_quality_rewrite_prompt": {
        "platform_label", "platform_rules", "novel_number", "chapter_title", "chapter_role", 
        "chapter_purpose", "suspense_level", "foreshadowing", "plot_twist_level", 
        "chapter_summary", "opening_feedback", "ending_feedback", "chapter_text"
    },
    "mid_section_quality_prompt": {
        "chapter_text"
    },
    "dialogue_voice_check_prompt": {
        "chapter_text"
    },
    "enrich_prompt": {
        "word_number", "chapter_text"
    },
    "summary_prompt": {
        "chapter_text", "global_summary"
    },
    "compress_global_summary_prompt": {
        "global_summary"
    },
    "update_character_state_prompt": {
        "chapter_text", "old_state"
    },
    "update_plot_arcs_prompt": {
        "chapter_number", "chapter_text", "global_summary", "character_state", "old_plot_arcs"
    },
    "graph_extraction_prompt": {
        "chapter_text"
    },
    "single_chapter_summary_prompt": {
        "chapter_text"
    },
    "reader_agent_prompt": {
        "global_summary", "chapter_info", "character_state", "plot_arcs"
    },
    "villain_agent_prompt": {
        "chapter_info", "reader_critique", "character_state", "plot_arcs"
    },
    "director_agent_prompt": {
        "chapter_info", "reader_critique", "villain_plan", "character_state", "plot_arcs"
    },
    "interactive_rewrite_prompt": {
        "context_before", "selected_text", "context_after", "user_instruction"
    },
    "knowledge_search_prompt": {
        "chapter_number", "chapter_title", "characters_involved", "key_items", "scene_location", 
        "chapter_role", "chapter_purpose", "foreshadowing", "short_summary", "user_guidance", 
        "time_constraint"
    },
    "knowledge_filter_prompt": {
        "chapter_info", "retrieved_texts"
    },
    "Character_Import_Prompt": {
        "content"
    }
}

def validate_prompt_template(key: str, template: str):
    """
    检查提示词模版中的格式化变量占位符是否合法。
    如果存在未知变量或语法错误，抛出 ValueError。
    """
    allowed = PROMPT_ALLOWED_VARIABLES.get(key)
    if allowed is None:
        return

    import string
    try:
        parsed = list(string.Formatter().parse(template))
    except ValueError as e:
        raise ValueError(f"提示词模板括号匹配或定义格式非法: {e}")

    placeholders = {name for _, name, _, _ in parsed if name is not None}
    placeholders = {p for p in placeholders if not p.isdigit()}

    invalid = placeholders - allowed
    if invalid:
        invalid_str = ", ".join(f"{{{x}}}" for x in sorted(invalid))
        allowed_str = ", ".join(f"{{{x}}}" for x in sorted(allowed))
        raise ValueError(f"发现未知的占位变量: {invalid_str}。该模板仅允许变量: {allowed_str}")


def _save_prompt_snapshot(project_id: str, key: str, content: str):
    """
    保存自定义提示词快照，保留最近 10 次的备份。
    备份路径：{project_dir}/custom_prompts_backup/{key}_{timestamp}.txt
    """
    from backend.app.database import get_db
    with get_db() as conn:
        row = conn.execute("SELECT filepath FROM project WHERE id=?", (project_id,)).fetchone()
    if not row or not row["filepath"]:
        return
        
    backup_dir = os.path.join(row["filepath"], "custom_prompts_backup")
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = int(time.time() * 1000)
    filename = f"{key}_{timestamp}.txt"
    backup_file = os.path.join(backup_dir, filename)
    
    with open(backup_file, "w", encoding="utf-8") as f:
        f.write(content)
        
    try:
        files = [
            f for f in os.listdir(backup_dir) 
            if f.startswith(f"{key}_") and f.endswith(".txt")
        ]
        def get_timestamp(fname):
            try:
                ts_part = fname.rsplit("_", 1)[-1].replace(".txt", "")
                return int(ts_part)
            except Exception:
                return 0
        files.sort(key=get_timestamp)
        while len(files) > 10:
            oldest = files.pop(0)
            os.remove(os.path.join(backup_dir, oldest))
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to rotate prompt snapshots: {e}")


# ── 辅助函数：读写自定义 prompt JSON 文件 ───────────────────────────────

def _get_custom_prompts_file(project_id: str) -> str:
    from backend.app.database import get_db
    with get_db() as conn:
        row = conn.execute("SELECT filepath FROM project WHERE id=?", (project_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="项目不存在")
    return os.path.join(row["filepath"], "custom_prompts.json")


def _load_custom_prompts(project_id: str) -> dict:
    path = _get_custom_prompts_file(project_id)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_custom_prompts(project_id: str, data: dict):
    path = _get_custom_prompts_file(project_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── 路由 ──────────────────────────────────────────────────────────────

class PromptUpdate(BaseModel):
    content: str


@router.get("/api/v1/prompts/keys")
def list_prompt_keys():
    """返回所有可编辑的 prompt key 元数据（不含内容）。"""
    return {"prompts": PROMPT_CATALOG}


@router.get("/api/v1/projects/{project_id}/prompts")
def get_project_prompts(project_id: str, request: Request):
    """返回项目所有 prompt（默认值 + 用户覆盖内容合并）。"""
    user_id = get_current_user(request)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    import novel_generator.prompts as _pd
    custom = _load_custom_prompts(project_id)

    result = []
    for meta in PROMPT_CATALOG:
        key = meta["key"]
        default_text = getattr(_pd, key, "")
        result.append({
            **meta,
            "default_content": default_text,
            "custom_content": custom.get(key),
            "is_overridden": key in custom,
        })

    return {"prompts": result}


@router.put("/api/v1/projects/{project_id}/prompts/{key}")
def update_project_prompt(project_id: str, key: str, body: PromptUpdate, request: Request):
    """覆盖指定 prompt（增加白名单变量安全校验与快照备份）。"""
    user_id = get_current_user(request)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if key not in PROMPT_KEY_SET:
        raise HTTPException(status_code=400, detail=f"未知的 prompt key: {key}")

    # 1. 安全校验变量占位符，防止 KeyError 格式化崩坏
    try:
        validate_prompt_template(key, body.content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 2. 备份当前内容到历史快照
    custom = _load_custom_prompts(project_id)
    current_content = custom.get(key)
    if current_content:
        _save_prompt_snapshot(project_id, key, current_content)

    # 3. 覆盖保存
    custom[key] = body.content
    _save_custom_prompts(project_id, custom)
    return {"message": "已成功保存并备份", "key": key, "is_overridden": True}


@router.delete("/api/v1/projects/{project_id}/prompts/{key}")
def reset_project_prompt(project_id: str, key: str, request: Request):
    """恢复指定 prompt 为系统默认值（同样备份当前内容以防丢失）。"""
    user_id = get_current_user(request)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if key not in PROMPT_KEY_SET:
        raise HTTPException(status_code=400, detail=f"未知的 prompt key: {key}")

    custom = _load_custom_prompts(project_id)
    current_content = custom.get(key)
    if current_content:
        _save_prompt_snapshot(project_id, key, current_content)

    custom.pop(key, None)
    _save_custom_prompts(project_id, custom)
    return {"message": "已恢复默认值并备份历史内容", "key": key, "is_overridden": False}


# ── 新增：快照历史获取与恢复路由 ───────────────────────────────────────────────

@router.get("/api/v1/projects/{project_id}/prompts/{key}/snapshots")
def get_prompt_snapshots(project_id: str, key: str, request: Request):
    """获取指定 prompt 的历史快照列表。"""
    user_id = get_current_user(request)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if key not in PROMPT_KEY_SET:
        raise HTTPException(status_code=400, detail=f"未知的 prompt key: {key}")
        
    backup_dir = os.path.join(project["filepath"], "custom_prompts_backup")
    if not os.path.exists(backup_dir):
        return {"snapshots": []}
        
    snapshots = []
    try:
        for fname in os.listdir(backup_dir):
            if fname.startswith(f"{key}_") and fname.endswith(".txt"):
                ts_part = fname.rsplit("_", 1)[-1].replace(".txt", "")
                timestamp = int(ts_part)
                filepath = os.path.join(backup_dir, fname)
                content = ""
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                dt = datetime.datetime.fromtimestamp(timestamp / 1000.0)
                readable_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                snapshots.append({
                    "id": ts_part,
                    "timestamp": timestamp,
                    "readable_time": readable_time,
                    "preview": content[:120] + ("..." if len(content) > 120 else ""),
                    "content": content
                })
        snapshots.sort(key=lambda x: x["timestamp"], reverse=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取快照列表失败: {e}")
        
    return {"snapshots": snapshots}


class PromptRestore(BaseModel):
    snapshot_id: str


@router.post("/api/v1/projects/{project_id}/prompts/{key}/restore")
def restore_prompt_snapshot(project_id: str, key: str, body: PromptRestore, request: Request):
    """从指定历史快照恢复提示词（恢复前自动备份当前版本）。"""
    user_id = get_current_user(request)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if key not in PROMPT_KEY_SET:
        raise HTTPException(status_code=400, detail=f"未知的 prompt key: {key}")
        
    backup_dir = os.path.join(project["filepath"], "custom_prompts_backup")
    snapshot_file = os.path.join(backup_dir, f"{key}_{body.snapshot_id}.txt")
    if not os.path.exists(snapshot_file):
        raise HTTPException(status_code=404, detail="快照不存在或已失效")
        
    with open(snapshot_file, "r", encoding="utf-8") as f:
        content = f.read()
        
    custom = _load_custom_prompts(project_id)
    current_content = custom.get(key)
    if current_content:
        _save_prompt_snapshot(project_id, key, current_content)
        
    custom[key] = content
    _save_custom_prompts(project_id, custom)
    return {"message": "已从历史快照恢复", "key": key, "content": content}


# ── 新增：配置文件导入与导出路由 ───────────────────────────────────────────────

@router.get("/api/v1/projects/{project_id}/prompts/export")
def export_project_prompts(project_id: str, request: Request):
    """导出当前项目的所有自定义提示词为 JSON 文件结构。"""
    user_id = get_current_user(request)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
        
    custom = _load_custom_prompts(project_id)
    return {"custom_prompts": custom}


class PromptImport(BaseModel):
    custom_prompts: dict[str, str]


@router.post("/api/v1/projects/{project_id}/prompts/import")
def import_project_prompts(project_id: str, body: PromptImport, request: Request):
    """批量导入并覆盖当前项目的所有自定义提示词（覆盖前自动创建快照备份）。"""
    user_id = get_current_user(request)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
        
    imported = {}
    errors = []
    for key, content in body.custom_prompts.items():
        if key not in PROMPT_KEY_SET:
            continue
        try:
            validate_prompt_template(key, content)
            imported[key] = content
        except ValueError as e:
            errors.append(f"提示词 [{key}] 校验失败: {e}")
            
    if errors:
        raise HTTPException(status_code=400, detail="导入提示词包含格式校验错误:\n" + "\n".join(errors))
        
    current = _load_custom_prompts(project_id)
    for key, content in current.items():
        if content:
            _save_prompt_snapshot(project_id, key, content)
            
    for key, content in imported.items():
        current[key] = content
        
    _save_custom_prompts(project_id, current)
    return {"message": f"成功导入 {len(imported)} 个自定义提示词配置，原有自定义内容已创建历史备份"}
