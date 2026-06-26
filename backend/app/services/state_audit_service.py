import os
import json
import logging
from datetime import datetime
import uuid
from backend.app.services import state_file_service

logger = logging.getLogger(__name__)

def get_audit_log_path(project_id: str) -> str:
    memory_dir = state_file_service.get_memory_dir(project_id)
    audit_dir = os.path.join(memory_dir, "audit_logs")
    os.makedirs(audit_dir, exist_ok=True)
    # 每天一个日志文件，或者统一写到一个文件里。为了简单可迁移，统一写到 state_audit.jsonl
    return os.path.join(audit_dir, "state_audit.jsonl")

def log_audit_event(
    project_id: str,
    event_type: str,
    file: str,
    entity_type: str,
    entity_id: str,
    field_path: str,
    old_value: any,
    new_value: any,
    reason: str,
    risk_level: str = "low",
    source: str = "manual_edit"
) -> dict:
    """
    记录一次状态审计日志。
    """
    filepath = get_audit_log_path(project_id)
    
    event = {
        "event_id": f"audit_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}",
        "project_id": project_id,
        "event_type": event_type,
        "file": file,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "field_path": field_path,
        "old_value": old_value,
        "new_value": new_value,
        "reason": reason,
        "risk_level": risk_level,
        "source": source,
        "created_at": datetime.now().isoformat()
    }
    
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
        
    return event

def get_audit_logs(project_id: str, limit: int = 100) -> list[dict]:
    """
    获取最近的审计日志（按时间倒序）。
    """
    filepath = get_audit_log_path(project_id)
    logs = []
    if not os.path.exists(filepath):
        return logs
        
    try:
        # 如果文件很大，倒序读会比较麻烦。这里直接读全量然后截断，因为初版数据量不会无限大
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        logs.append(json.loads(line))
                    except Exception:
                        logger.warning("Failed to parse audit log line: %s", line.strip()[:200], exc_info=True)
    except Exception as e:
        logger.error(f"Error reading audit logs: {e}")
        
    logs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return logs[:limit]
