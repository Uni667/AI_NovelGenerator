import os
import json
import logging
from backend.app.services import state_file_service

logger = logging.getLogger(__name__)

def build_generation_context_for_chapter(project_id: str, chapter_id: int, max_chars: int = 18000) -> dict:
    """
    为第 N 章草稿生成构建上下文。
    只读，不修改任何状态文件。
    只使用已合并状态，不读取 pending_review patch 作为事实。
    """
    memory_dir = state_file_service.get_memory_dir(project_id)
    
    context_data = {
        "chapter_id": chapter_id,
        "chapter_index": chapter_id,
        "has_memory_state": False,
        "used_merged_state_only": True,
        "pending_patch_ignored_count": 0,
        "context_warnings": [],
        "context": {
            "current_chapter_plan": {},
            "locked_previous_facts": [],
            "character_state_brief": "",
            "name_usage_rules_brief": "",
            "plot_threads_brief": "",
            "global_summary": "",
            "forbidden_violations": [],
            "allowed_progress": []
        }
    }

    if not os.path.exists(memory_dir):
        context_data["context_warnings"].append("未找到 memory 目录，系统将回退到旧生成逻辑。")
        return context_data
        
    try:
        # 1. Read files
        char_state = state_file_service.read_character_state(project_id)
        global_summary = state_file_service.read_global_summary(project_id)
        plot_threads = state_file_service.read_plot_threads(project_id)
        name_rules = state_file_service.read_name_usage_rules(project_id)
        outline_state = state_file_service.read_outline_state(project_id)
        
        context_data["has_memory_state"] = True
        context_data["context"]["global_summary"] = global_summary
        
        # 2. Check pending patches
        patches_dir = os.path.join(memory_dir, "patches")
        if os.path.exists(patches_dir):
            for pf in os.listdir(patches_dir):
                if pf.endswith(".json"):
                    with open(os.path.join(patches_dir, pf), "r", encoding="utf-8") as f:
                        patch_content = json.load(f)
                        if patch_content.get("status") in ["pending_review", "failed", "discarded"]:
                            context_data["pending_patch_ignored_count"] += 1
                            
        # 3. Build locked_previous_facts from outline_state
        locked_facts = []
        for ch in outline_state.get("chapters", []):
            if ch.get("locked") and ch.get("chapter_index", 0) < chapter_id:
                locked_facts.append(f"第 {ch['chapter_index']} 章事实: {ch.get('actual_summary', '')}")
        context_data["context"]["locked_previous_facts"] = locked_facts
        
        # 4. Build character_state_brief
        char_briefs = []
        forbidden_names = []
        for c in char_state.get("characters", []):
            c_brief = f"【{c.get('display_name')}】 定位: {c.get('role_in_story')}, 状态: {c.get('current_status')}"
            
            # 十四叔原则判断
            if c.get("true_name"):
                if c.get("true_name_revealed_to_reader"):
                    c_brief += f", 真名已对读者揭露: {c['true_name']}"
                else:
                    c_brief += ", 真名绝对禁止在正文和旁白出现"
                    forbidden_names.append(c["true_name"])
            else:
                c_brief += ", 真名尚未设定或揭露"
                
            char_briefs.append(c_brief)
        context_data["context"]["character_state_brief"] = "\n".join(char_briefs)
        
        if forbidden_names:
            context_data["context"]["forbidden_violations"].append("禁止写出以下尚未揭露的真实姓名: " + ", ".join(forbidden_names))
            
        # 5. Build name_usage_rules_brief
        name_rules_briefs = []
        for r in name_rules.get("rules", []):
            stages = r.get("stages", [])
            if stages:
                latest_stage = stages[-1]
                name_rules_briefs.append(f"关于【{r.get('character_id')}】的称呼限制: {latest_stage.get('new_rule')}")
        context_data["context"]["name_usage_rules_brief"] = "\n".join(name_rules_briefs)
        
        # 6. Build plot_threads_brief
        plot_briefs = []
        for pt in plot_threads.get("threads", []):
            if pt.get("status") != "resolved":
                plot_briefs.append(f"【活跃线索】{pt.get('title')} ({pt.get('type')}): {pt.get('description')}")
        context_data["context"]["plot_threads_brief"] = "\n".join(plot_briefs)
        
    except Exception as e:
        logger.error(f"Error building generation context: {e}")
        context_data["has_memory_state"] = False
        context_data["context_warnings"].append(f"读取 memory 状态失败，已回退到旧生成逻辑。原因: {str(e)}")
        
    return context_data

def validate_draft_against_generation_context(draft_text: str, generation_context: dict) -> dict:
    """
    轻量级规则检查，检查是否违禁称呼等硬逻辑。
    """
    warnings = []
    
    if not generation_context.get("has_memory_state"):
        return {"passed": True, "warnings": []}
        
    ctx = generation_context.get("context", {})
    forbidden_violations = ctx.get("forbidden_violations", [])
    
    for f_rule in forbidden_violations:
        if "禁止写出以下尚未揭露的真实姓名" in f_rule:
            names_part = f_rule.split(":")[-1]
            names = [n.strip() for n in names_part.split(",") if n.strip()]
            for name in names:
                if name in draft_text:
                    warnings.append({
                        "type": "name_usage_violation",
                        "message": f"严重警告：违规提前写出了未揭露的人物真实姓名【{name}】"
                    })
                    
    # 死亡复活等检测可以通过正则表达式做，但目前只依赖基础 name 检测
    return {
        "passed": len(warnings) == 0,
        "warnings": warnings
    }
