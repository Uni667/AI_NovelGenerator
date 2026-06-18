import os
import json
import logging
from backend.app.services import project_service, state_file_service, chapter_service, state_conflict_service

logger = logging.getLogger(__name__)


def check_project_health(project_id: str, user_id: str) -> dict:
    """
    执行项目健康检查。
    返回结构: { "status": "healthy|warning|danger|broken", "summary": "...", "checks": [...] }
    """
    project = project_service.get_project(project_id, user_id)
    if not project:
        return {"status": "broken", "summary": "项目不存在", "checks": []}
        
    filepath = project["filepath"]
    memory_dir = os.path.join(filepath, "memory")
    
    checks = []
    status_levels = []
    
    def add_check(key, level, msg, action):
        checks.append({"key": key, "level": level, "message": msg, "action": action})
        status_levels.append(level)
        
    # 1. 检查 memory 目录及基础状态文件
    if not os.path.exists(memory_dir):
        add_check("memory_dir", "warning", "尚未初始化 memory 目录", "系统将在需要时自动创建")
    else:
        # 检查四大 JSON
        for fname in ["character_state.json", "plot_threads.json", "name_usage_rules.json", "outline_state.json"]:
            fpath = os.path.join(memory_dir, fname)
            if not os.path.exists(fpath):
                add_check(f"missing_{fname}", "warning", f"缺少状态文件 {fname}", "系统将使用默认空状态")
            else:
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        json.load(f)
                except Exception:
                    add_check(f"corrupt_{fname}", "broken", f"状态文件 {fname} 损坏或无法解析", "请前往备份页恢复最近可用备份")
                    
        # 检查全局摘要
        if not os.path.exists(os.path.join(memory_dir, "global_summary.md")):
            add_check("missing_global_summary", "warning", "缺少 global_summary.md", "系统将使用默认空状态")
            
    # 2. 检查补丁状态
    patches_dir = os.path.join(memory_dir, "patches")
    pending_patches = 0
    high_risk_patches = 0
    failed_patches = 0
    
    if os.path.exists(patches_dir):
        for fname in os.listdir(patches_dir):
            if fname.endswith(".json"):
                try:
                    with open(os.path.join(patches_dir, fname), "r", encoding="utf-8") as f:
                        patch = json.load(f)
                        if patch.get("status") == "pending_review":
                            pending_patches += 1
                            if patch.get("risk_level") == "high":
                                high_risk_patches += 1
                        elif patch.get("status") == "failed":
                            failed_patches += 1
                except Exception:
                    pass
                    
    if failed_patches > 0:
        add_check("failed_patches", "danger", f"存在 {failed_patches} 个失败的 State Patch", "请到状态页查看并废弃或修正")
    if high_risk_patches > 0:
        add_check("high_risk_patches", "danger", f"存在 {high_risk_patches} 个高风险待处理 Patch", "请优先审查合并，否则影响新章节生成")
    elif pending_patches > 0:
        add_check("pending_patches", "warning", f"存在 {pending_patches} 个待处理 Patch", "请前往状态页查看并决定合并或放弃")
        
    # 3. 检查大纲 diff 状态
    diffs_dir = os.path.join(memory_dir, "outline_diffs")
    pending_diffs = 0
    failed_diffs = 0
    if os.path.exists(diffs_dir):
        for fname in os.listdir(diffs_dir):
            if fname.endswith(".json"):
                try:
                    with open(os.path.join(diffs_dir, fname), "r", encoding="utf-8") as f:
                        diff = json.load(f)
                        if diff.get("status") == "pending_review":
                            pending_diffs += 1
                        elif diff.get("status") == "failed":
                            failed_diffs += 1
                except Exception:
                    pass
                    
    if failed_diffs > 0:
        add_check("failed_diffs", "warning", f"存在 {failed_diffs} 个生成失败的大纲演化建议", "请到状态页废弃")
    if pending_diffs > 0:
        add_check("pending_diffs", "warning", f"存在 {pending_diffs} 个待处理大纲演化建议", "请前往状态页审查")
        
    # 4. 检查冲突
    conflicts_res = state_conflict_service.detect_state_conflicts(project_id, enable_ai_conflict_check=False, user_id=user_id)
    conflicts = conflicts_res.get("conflicts", [])
    if conflicts:
        high_risk_conflicts = sum(1 for c in conflicts if c.get("severity") == "high")
        if high_risk_conflicts > 0:
            add_check("high_risk_conflicts", "danger", f"发现 {high_risk_conflicts} 个高风险状态冲突", "请立刻前往状态编辑页修正")
        else:
            add_check("conflicts", "warning", f"发现 {len(conflicts)} 个一般状态冲突", "建议前往状态编辑页确认")
            
    # 5. 检查定稿章节状态
    all_chapters = chapter_service.list_chapters(project_id, user_id)
    finalized_but_unlocked = [ch for ch in all_chapters if ch.get("status") in ("final", "finalized") and not ch.get("locked")]
    if finalized_but_unlocked:
        add_check("unlocked_chapters", "warning", f"存在 {len(finalized_but_unlocked)} 个定稿但未锁定的章节", "建议在工作台将其锁定防止意外修改")
        
    # 6. Novel_directory.txt 检查
    if not os.path.exists(os.path.join(filepath, "Novel_directory.txt")):
        add_check("missing_directory", "broken", "缺少旧版 Novel_directory.txt 文件", "请检查项目完整性")
        
    # 判断最终状态
    final_status = "healthy"
    if "broken" in status_levels:
        final_status = "broken"
    elif "danger" in status_levels:
        final_status = "danger"
    elif "warning" in status_levels:
        final_status = "warning"
        
    # 生成摘要
    summary = "项目状态良好，可正常连载。"
    if final_status == "broken":
        summary = "项目核心文件损坏，建议立即恢复备份！"
    elif final_status == "danger":
        summary = "存在高风险问题待处理，建议暂缓生成新章节。"
    elif final_status == "warning":
        summary = f"项目可正常使用，但存在 {len(status_levels)} 个待处理或建议事项。"
        
    res = {
        "status": final_status,
        "summary": summary,
        "checks": checks
    }
    logger.info(f"HEALTH CHECK RESULT FOR PROJECT {project_id}: {json.dumps(res, ensure_ascii=False)}")
    return res
