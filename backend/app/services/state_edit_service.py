import os
import shutil
import json
import logging
from datetime import datetime
import uuid
from backend.app.services import state_file_service, state_audit_service, state_schema_validator

logger = logging.getLogger(__name__)

class StateEditError(Exception):
    def __init__(self, message: str, code: str = "bad_request", details: any = None):
        super().__init__(message)
        self.code = code
        self.details = details

def _backup_file_for_edit(project_id: str, filename: str) -> str:
    """为单一文件创建手动编辑前的备份，返回备份文件路径"""
    memory_dir = state_file_service.get_memory_dir(project_id)
    backups_dir = os.path.join(memory_dir, "backups")
    os.makedirs(backups_dir, exist_ok=True)
    
    src = os.path.join(memory_dir, filename)
    if not os.path.exists(src):
        return None
        
    base, ext = os.path.splitext(filename)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    uid = uuid.uuid4().hex[:6]
    backup_filename = f"{base}_before_manual_edit_{timestamp}_{uid}{ext}"
    dst = os.path.join(backups_dir, backup_filename)
    shutil.copy2(src, dst)
    return dst

def _process_edit_request(
    project_id: str,
    entity_type: str,
    entity_id: str,
    filename: str,
    read_func,
    write_func,
    update_logic_func,
    validator_func,
    updates: dict,
    reason: str,
    confirm_high_risk: bool = False
):
    """
    通用编辑流程：
    1. 缺少 reason 报错
    2. 校验 updates 类型和字段
    3. 检查高风险 (如果高风险且未 confirm_high_risk 报错)
    4. 备份文件
    5. 执行更新
    6. 写入文件
    7. 写入 audit log
    """
    if not reason:
        raise StateEditError("reason_required", "reason_required")
        
    # 2. 字段级别的预先校验
    if isinstance(updates, dict) and validator_func:
        errors = validator_func(entity_id, updates) if entity_id else validator_func(updates)
        if errors:
            raise StateEditError(f"Validation failed: {errors}", "validation_failed", errors)
            
    # 3. 检查高危
    is_high_risk, high_risk_fields = state_schema_validator.check_high_risk_update(entity_type, updates)
    if is_high_risk and not confirm_high_risk:
        state_audit_service.log_audit_event(
            project_id, "high_risk_rejected", filename, entity_type, str(entity_id),
            "multiple", None, None, reason, risk_level="high", source="manual_edit"
        )
        raise StateEditError("high_risk_required", "high_risk_required", {"high_risk_fields": high_risk_fields})
        
    # 4. 备份
    backup_path = _backup_file_for_edit(project_id, filename)
    
    # 5. 读取并更新
    data = read_func(project_id)
    old_value_snapshot = update_logic_func(data, updates)
    
    # 6. 写入 (如果是 md，直接传字符串)
    is_json = filename.endswith(".json")
    state_file_service.write_memory_file(project_id, filename, data, is_json=is_json)
    
    # 7. Audit log
    state_audit_service.log_audit_event(
        project_id=project_id,
        event_type="manual_edit",
        file=filename,
        entity_type=entity_type,
        entity_id=str(entity_id),
        field_path="multiple",
        old_value=old_value_snapshot,
        new_value=updates,
        reason=reason,
        risk_level="high" if is_high_risk else "low",
        source="manual_edit"
    )
    
    return {"success": True, "backup": backup_path, "updates": updates}

def update_character_state(project_id: str, character_id: str, updates: dict, reason: str, confirm_high_risk: bool = False):
    def update_logic(data, upd):
        target = None
        for ch in data.get("characters", []):
            if ch.get("id") == character_id:
                target = ch
                break
        if not target:
            raise StateEditError("Character not found", "not_found")
        old_vals = {}
        for k, v in upd.items():
            old_vals[k] = target.get(k)
            target[k] = v
        return old_vals
        
    return _process_edit_request(
        project_id, "character", character_id, "character_state.json",
        state_file_service.read_character_state, None,
        update_logic, state_schema_validator.validate_character_state_update,
        updates, reason, confirm_high_risk
    )

def update_name_usage_rule(project_id: str, character_id: str, updates: dict, reason: str, confirm_high_risk: bool = False):
    def update_logic(data, upd):
        target = None
        for r in data.get("rules", []):
            if r.get("character_id") == character_id:
                target = r
                break
        if not target:
            # 如果没找到，允许创建新的规则项
            target = {"character_id": character_id}
            data.setdefault("rules", []).append(target)
            
        old_vals = {}
        for k, v in upd.items():
            old_vals[k] = target.get(k)
            target[k] = v
        return old_vals
        
    return _process_edit_request(
        project_id, "name_usage_rule", character_id, "name_usage_rules.json",
        state_file_service.read_name_usage_rules, None,
        update_logic, state_schema_validator.validate_name_usage_rule_update,
        updates, reason, confirm_high_risk
    )

def update_plot_thread(project_id: str, thread_id: str, updates: dict, reason: str, confirm_high_risk: bool = False):
    def update_logic(data, upd):
        target = None
        for t in data.get("threads", []):
            if t.get("id") == thread_id:
                target = t
                break
        if not target:
            raise StateEditError("Plot thread not found", "not_found")
        old_vals = {}
        for k, v in upd.items():
            old_vals[k] = target.get(k)
            target[k] = v
        return old_vals
        
    return _process_edit_request(
        project_id, "plot_thread", thread_id, "plot_threads.json",
        state_file_service.read_plot_threads, None,
        update_logic, state_schema_validator.validate_plot_thread_update,
        updates, reason, confirm_high_risk
    )

def update_global_summary(project_id: str, new_summary: str, reason: str, confirm_high_risk: bool = False):
    # global summary has no ID
    def update_logic(data, upd):
        # We replace the whole string
        return data
        
    def val_func(dummy, upd):
        return state_schema_validator.validate_global_summary_update(upd)
        
    return _process_edit_request(
        project_id, "global_summary", "global", "global_summary.md",
        state_file_service.read_global_summary, None,
        lambda d, u: d, # returns old data directly as snapshot
        val_func, new_summary, reason, confirm_high_risk
    )

def update_outline_chapter(project_id: str, chapter_index: int, updates: dict, reason: str, confirm_high_risk: bool = False):
    def update_logic(data, upd):
        target = None
        for ch in data.get("chapters", []):
            if ch.get("chapter_index") == chapter_index:
                target = ch
                break
        if not target:
            raise StateEditError("Outline chapter not found", "not_found")
            
        # finalized/locked edits protection
        if target.get("status") == "finalized" or target.get("locked"):
            if not confirm_high_risk:
                raise StateEditError("finalized_locked_protect", "high_risk_required", {"high_risk_fields": ["locked/finalized"]})
                
        old_vals = {}
        for k, v in upd.items():
            old_vals[k] = target.get(k)
            target[k] = v
        return old_vals
        
    return _process_edit_request(
        project_id, "outline_chapter", str(chapter_index), "outline_state.json",
        state_file_service.read_outline_state, None,
        update_logic, state_schema_validator.validate_outline_chapter_update,
        updates, reason, confirm_high_risk
    )

def get_backups(project_id: str):
    memory_dir = state_file_service.get_memory_dir(project_id)
    backups_dir = os.path.join(memory_dir, "backups")
    if not os.path.exists(backups_dir):
        return []
    files = []
    for f in os.listdir(backups_dir):
        if os.path.isfile(os.path.join(backups_dir, f)):
            info = os.stat(os.path.join(backups_dir, f))
            files.append({
                "backup_id": f,
                "created_at": datetime.fromtimestamp(info.st_mtime).isoformat()
            })
    files.sort(key=lambda x: x["created_at"], reverse=True)
    return files

def restore_backup(project_id: str, backup_id: str, reason: str):
    if not reason:
        raise StateEditError("reason_required", "reason_required")
        
    # 防止路径穿越
    if "/" in backup_id or "\\" in backup_id or ".." in backup_id:
        raise StateEditError("Invalid backup ID", "invalid_path")
        
    memory_dir = state_file_service.get_memory_dir(project_id)
    backups_dir = os.path.join(memory_dir, "backups")
    backup_path = os.path.join(backups_dir, backup_id)
    
    if not os.path.exists(backup_path):
        raise StateEditError("Backup not found", "not_found")
        
    # 确定要覆盖哪个目标文件
    target_file = None
    if backup_id.startswith("character_state"): target_file = "character_state.json"
    elif backup_id.startswith("name_usage_rules"): target_file = "name_usage_rules.json"
    elif backup_id.startswith("plot_threads"): target_file = "plot_threads.json"
    elif backup_id.startswith("outline_state"): target_file = "outline_state.json"
    elif backup_id.startswith("global_summary"): target_file = "global_summary.md"
    
    if not target_file:
        raise StateEditError("Cannot determine target file for this backup", "unknown_target")
        
    # 回滚前备份当前文件
    _backup_file_for_edit(project_id, target_file)
    
    # 覆盖文件
    target_path = os.path.join(memory_dir, target_file)
    shutil.copy2(backup_path, target_path)
    
    # Audit log
    state_audit_service.log_audit_event(
        project_id, "backup_restore", target_file, "system", backup_id,
        "all", "current_state", "backup_state", reason, risk_level="high", source="manual_edit"
    )
    
    return {"success": True, "restored_file": target_file}
