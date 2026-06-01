import os
import json
import logging
from datetime import datetime
from backend.app.services import state_file_service, project_service
from backend.app.services.outline_evolution_validator import validate_outline_evolution_diff
import uuid

logger = logging.getLogger(__name__)

# 定义给大模型的大纲演化 Prompt
OUTLINE_EVOLUTION_PROMPT = """\
你是一个顶级小说结构编辑。你现在的任务是：根据小说的**已定稿事实**和**最新人物/剧情状态**，对**尚未写作的未来计划章节**（Planned Chapters）进行增量调整建议。

你绝对不是在续写小说，也不是重写整本大纲。你的目标是修正未来大纲中与“已发生事实”冲突的地方，或者让未来大纲更好地承接最新状态。

【核心铁律】
1. 绝对不能修改已定稿（finalized）或已锁定（locked=true）的章节。
2. 绝对不能修改已有草稿（drafted）的章节，如果发现冲突，只能使用 `mark_conflict` 标注冲突原因。
3. 只能对 `status=planned` 的未锁定章节生成调整建议（使用 `modify`, `insert_after`, `delete_planned` 等）。
4. 不要改变全书核心类型、主角设定和题材定位。
5. 不要违背已合并的名称使用规则和人物状态。如果人物在前面已经死亡，未来大纲中他不能复活。如果某人的真名已被揭露，未来大纲不应再有“首次揭露真名”的情节。

【输入信息】
项目类型: {topic} ({genre})
用户期望: {user_guidance}

[已定稿状态摘要 (Merged Memory)]
{merged_state_summary}

[称呼纪律与规则]
{name_usage_rules}

[当前大纲快照 (Outline State)]
{outline_state}

【任务要求】
请结合[当前大纲快照]和[已定稿状态摘要]，检查在第 {from_chapter} 章之后的未来章节是否存在逻辑断裂或可优化的设定承接。
请按照 JSON 格式返回一份调整建议 `diff`（必须是合法 JSON），无需任何 Markdown 代码块包装（除了最外层的纯 JSON 外不要输出任何解释说明内容）。
如果无需任何调整，请返回包含空 `changes` 列表的 JSON。

JSON 格式要求如下：
{{
  "summary": "简要说明你为什么做这些修改...",
  "affected_chapters": [修改影响的章节编号数组],
  "changes": [
    {{
      "chapter_index": 章节编号,
      "change_type": "modify" | "mark_conflict" | "delete_planned" | "insert_after",
      "field": "planned_summary" | "chapter_goal" | "foreshadowing", // 如果是 mark_conflict，此字段可留空
      "before": "修改前的内容片段",
      "after": "修改后的内容片段",
      "reason": "修改原因",
      "risk_level": "low" | "medium" | "high" // 涉及秘密揭露、人物生死、核心设定变动必须标记为 high
    }}
  ]
}}
"""

def _get_llm_and_config(user_id: str, project_id: str):
    from backend.app.services.model_runtime import _build_chat_adapter
    from backend.app.services.config_resolver import get_runtime_config
    rt = get_runtime_config(user_id, "draft", project_id)
    adapter = _build_chat_adapter(rt, None, None)
    return adapter, rt

def propose_outline_evolution(project_id: str, user_id: str, from_chapter: int = 1, scope: str = "future_only") -> dict:
    """
    根据已合并 memory 状态和当前 outline_state，生成未来章节调整建议。
    返回建议 Diff 和是否校验成功。
    """
    # 1. 提取所有已合并状态
    outline_state = state_file_service.read_outline_state(project_id)
    character_state = state_file_service.read_character_state(project_id)
    global_summary = state_file_service.read_global_summary(project_id)
    plot_threads = state_file_service.read_plot_threads(project_id)
    name_usage_rules = state_file_service.read_name_usage_rules(project_id)
    
    # 2. 获取项目配置
    config = project_service.get_project_config(project_id) or {}
    
    # 3. 统计被拦截的 Pending Patches（用于确认没有被污染）
    memory_dir = state_file_service.get_memory_dir(project_id)
    patches_dir = os.path.join(memory_dir, "patches")
    pending_patch_ignored_count = 0
    if os.path.exists(patches_dir):
        for f in os.listdir(patches_dir):
            if f.endswith(".json"):
                with open(os.path.join(patches_dir, f), "r", encoding="utf-8") as pf:
                    try:
                        patch_data = json.load(pf)
                        if patch_data.get("status") == "pending_review":
                            pending_patch_ignored_count += 1
                    except Exception:
                        pass
                        
    # 4. 构建大模型 Prompt
    merged_state_summary = f"全局摘要：\n{global_summary}\n\n人物状态摘要：\n{json.dumps(character_state.get('characters', []), ensure_ascii=False)}\n\n活跃伏笔：\n{json.dumps(plot_threads.get('threads', []), ensure_ascii=False)}"
    rules_text = json.dumps(name_usage_rules.get("rules", []), ensure_ascii=False)
    outline_text = json.dumps(outline_state.get("chapters", []), ensure_ascii=False)
    
    prompt = OUTLINE_EVOLUTION_PROMPT.format(
        topic=config.get("topic", "未知"),
        genre=config.get("genre", "未知"),
        user_guidance=config.get("user_guidance", "无"),
        merged_state_summary=merged_state_summary,
        name_usage_rules=rules_text,
        outline_state=outline_text,
        from_chapter=from_chapter
    )
    
    # 5. 调用大模型 (强制 JSON 模式)
    try:
        llm, rt = _get_llm_and_config(user_id, project_id)
        # We explicitly request low temperature for structured output
        llm.model.temperature = 0.2
        response_text = llm.invoke(prompt)
        
        # 尝试解析 JSON
        try:
            # 去除可能的 markdown 标记
            clean_text = response_text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.startswith("```"):
                clean_text = clean_text[3:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            clean_text = clean_text.strip()
            
            diff_output = json.loads(clean_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse outline diff JSON: {e}")
            diff_output = {
                "summary": "解析大模型返回结果失败",
                "affected_chapters": [],
                "changes": [],
                "error": str(e)
            }
            
    except Exception as e:
        logger.exception("Outline evolution failed")
        diff_output = {
            "summary": "生成大纲演化失败",
            "affected_chapters": [],
            "changes": [],
            "error": str(e)
        }
        response_text = str(e)
        
    # 6. 校验 Diff
    is_valid, errors, risk_level = validate_outline_evolution_diff(diff_output, outline_state, character_state, name_usage_rules)
    
    diff_status = "pending_review" if is_valid else "failed"
    
    # 7. 组装最终 Diff 结构
    final_diff = {
        "diff_id": f"outline_diff_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}",
        "project_id": project_id,
        "status": diff_status,
        "created_at": datetime.now().isoformat(),
        "scope": scope,
        "from_chapter": from_chapter,
        "used_merged_state_only": True,
        "pending_patch_ignored_count": pending_patch_ignored_count,
        "summary": diff_output.get("summary", ""),
        "affected_chapters": diff_output.get("affected_chapters", []),
        "changes": diff_output.get("changes", []),
        "warnings": errors,
        "risk_level": risk_level,
        "raw_model_output": response_text if diff_status == "failed" else None
    }
    
    return final_diff
