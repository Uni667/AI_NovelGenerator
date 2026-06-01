import os
import json
import logging
from datetime import datetime
from backend.app.services import state_file_service

logger = logging.getLogger(__name__)

def get_outline_diffs_dir(project_id: str) -> str:
    memory_dir = state_file_service.get_memory_dir(project_id)
    diffs_dir = os.path.join(memory_dir, "outline_diffs")
    os.makedirs(diffs_dir, exist_ok=True)
    return diffs_dir

def save_outline_diff(project_id: str, diff: dict) -> dict:
    """保存大纲调整建议。"""
    diffs_dir = get_outline_diffs_dir(project_id)
    diff_id = diff.get("diff_id")
    if not diff_id:
        raise ValueError("Diff missing diff_id")
        
    filepath = os.path.join(diffs_dir, f"{diff_id}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(diff, f, ensure_ascii=False, indent=2)
    return diff

def list_outline_diffs(project_id: str) -> list[dict]:
    """获取大纲调整建议列表。"""
    diffs_dir = get_outline_diffs_dir(project_id)
    diffs = []
    if os.path.exists(diffs_dir):
        for f in os.listdir(diffs_dir):
            if f.endswith(".json"):
                try:
                    with open(os.path.join(diffs_dir, f), "r", encoding="utf-8") as pf:
                        diffs.append(json.load(pf))
                except Exception as e:
                    logger.error(f"Failed to read diff {f}: {e}")
                    
    # Sort by created_at descending
    diffs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return diffs

def get_outline_diff(project_id: str, diff_id: str) -> dict | None:
    diffs_dir = get_outline_diffs_dir(project_id)
    filepath = os.path.join(diffs_dir, f"{diff_id}.json")
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def apply_outline_diff(project_id: str, diff_id: str) -> dict:
    """用户确认后应用 diff 到 outline_state.json。增量更新，备份原文件。"""
    diff = get_outline_diff(project_id, diff_id)
    if not diff:
        raise ValueError(f"Diff {diff_id} not found")
        
    status = diff.get("status")
    if status == "applied":
        raise ValueError("该建议已被应用，无法重复应用。")
    if status == "discarded":
        raise ValueError("该建议已被放弃，无法应用。")
    if status == "failed":
        raise ValueError("该建议因验证失败已被拦截，无法应用。")
        
    # 读取最新的 outline_state
    outline_state = state_file_service.read_outline_state(project_id)
    
    # 二次校验
    from backend.app.services.outline_evolution_validator import validate_outline_evolution_diff
    is_valid, errors, risk_level = validate_outline_evolution_diff(diff, outline_state)
    if not is_valid:
        raise ValueError(f"重新校验失败，无法应用: {'; '.join(errors)}")
        
    # 备份现有文件
    import shutil
    memory_dir = state_file_service.get_memory_dir(project_id)
    backups_dir = os.path.join(memory_dir, "backups")
    os.makedirs(backups_dir, exist_ok=True)
    src_outline = os.path.join(memory_dir, "outline_state.json")
    if os.path.exists(src_outline):
        backup_filename = f"outline_state_before_{diff_id}.json"
        shutil.copy2(src_outline, os.path.join(backups_dir, backup_filename))
        
    # 执行增量修改
    outline_map = {ch["chapter_index"]: ch for ch in outline_state.get("chapters", [])}
    allowed_fields = [
        "title", "planned_summary", "chapter_goal", "key_events",
        "expected_characters", "foreshadowing", "notes"
    ]
    
    for change in diff.get("changes", []):
        cn = change.get("chapter_index")
        change_type = change.get("change_type", "modify")
        field = change.get("field")
        after = change.get("after")
        
        # 只处理 modify (Phase 6 建议) 和 mark_conflict
        if change_type == "modify":
            if cn in outline_map:
                ch = outline_map[cn]
                if field in allowed_fields and ch.get("status") == "planned" and not ch.get("locked"):
                    ch[field] = after
        elif change_type == "mark_conflict":
            if cn in outline_map:
                ch = outline_map[cn]
                ch["notes"] = f"{ch.get('notes', '')}\n[冲突提醒]: {change.get('reason', '')}"
        
    # 写入更新后的 outline_state
    state_file_service.write_memory_file(project_id, "outline_state.json", outline_state)
    
    # 更新 diff 状态
    diff["status"] = "applied"
    diff["applied_at"] = datetime.now().isoformat()
    save_outline_diff(project_id, diff)
    
    return diff

def discard_outline_diff(project_id: str, diff_id: str) -> dict:
    """放弃大纲调整建议。"""
    diff = get_outline_diff(project_id, diff_id)
    if not diff:
        raise ValueError(f"Diff {diff_id} not found")
        
    if diff.get("status") == "applied":
        raise ValueError("已应用的建议无法放弃。")
        
    diff["status"] = "discarded"
    diff["discarded_at"] = datetime.now().isoformat()
    save_outline_diff(project_id, diff)
    return diff
