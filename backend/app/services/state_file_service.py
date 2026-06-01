import os
import json
import logging
import shutil
from datetime import datetime
from backend.app.services import project_service

logger = logging.getLogger(__name__)

# Constants for default file content
DEFAULT_CHARACTER_STATE = {
    "version": 1,
    "characters": [],
    "last_updated_chapter": None,
    "notes": "人物状态文件。记录人物出场、身份、称呼、关系、秘密和当前状态。"
}

DEFAULT_GLOBAL_SUMMARY = """# 全局剧情摘要

## 当前进度
暂无已固化章节状态。

## 已发生关键事件
暂无。

## 当前主线
暂无。

## 人物状态摘要
暂无。

## 已揭露秘密
暂无。

## 未揭露秘密
暂无。

## 不可违背事实
暂无。

## 下一章注意事项
暂无。"""

DEFAULT_PLOT_THREADS = {
    "version": 1,
    "threads": [],
    "last_updated_chapter": None
}

DEFAULT_NAME_USAGE_RULES = {
    "version": 1,
    "rules": [],
    "last_updated_chapter": None
}

DEFAULT_OUTLINE_STATE = {
    "version": 1,
    "chapters": [],
    "last_updated_chapter": None
}

def get_memory_dir(project_id: str) -> str:
    # Get project via project_service. Since project_id may be passed as str or int, handle it.
    # We need user_id? We can just use get_project_config to get filepath if we have standard layout.
    # Wait, project_service.get_project requires user_id.
    # However, sometimes we only have project_id. Let's provide a way to get the filepath directly.
    # Let's import database and query it directly to be safe.
    from backend.app.database import get_db
    with get_db() as conn:
        project = conn.execute("SELECT filepath FROM project WHERE id = ?", (project_id,)).fetchone()
        if not project:
            raise ValueError(f"Project {project_id} not found")
        filepath = project["filepath"]
    return os.path.join(filepath, "memory")

def ensure_memory_files(project_id: str) -> dict:
    """
    确保 memory 目录和基础状态文件存在。
    旧项目第一次进入状态系统时自动初始化。
    """
    memory_dir = get_memory_dir(project_id)
    patches_dir = os.path.join(memory_dir, "patches")
    backups_dir = os.path.join(memory_dir, "backups")
    
    os.makedirs(memory_dir, exist_ok=True)
    os.makedirs(patches_dir, exist_ok=True)
    os.makedirs(backups_dir, exist_ok=True)
    
    _ensure_file(os.path.join(memory_dir, "character_state.json"), DEFAULT_CHARACTER_STATE)
    _ensure_file(os.path.join(memory_dir, "global_summary.md"), DEFAULT_GLOBAL_SUMMARY, is_json=False)
    _ensure_file(os.path.join(memory_dir, "plot_threads.json"), DEFAULT_PLOT_THREADS)
    _ensure_file(os.path.join(memory_dir, "name_usage_rules.json"), DEFAULT_NAME_USAGE_RULES)
    _ensure_file(os.path.join(memory_dir, "outline_state.json"), DEFAULT_OUTLINE_STATE)
    
    return {"status": "initialized", "memory_dir": memory_dir}

def _ensure_file(filepath: str, default_content, is_json=True):
    if not os.path.exists(filepath):
        with open(filepath, "w", encoding="utf-8") as f:
            if is_json:
                json.dump(default_content, f, ensure_ascii=False, indent=2)
            else:
                f.write(default_content)

def read_memory_file(project_id: str, filename: str, is_json=True):
    memory_dir = get_memory_dir(project_id)
    filepath = os.path.join(memory_dir, filename)
    if not os.path.exists(filepath):
        ensure_memory_files(project_id)
        
    with open(filepath, "r", encoding="utf-8") as f:
        if is_json:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
        else:
            return f.read()

def write_memory_file(project_id: str, filename: str, content, is_json=True):
    memory_dir = get_memory_dir(project_id)
    filepath = os.path.join(memory_dir, filename)
    os.makedirs(memory_dir, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        if is_json:
            json.dump(content, f, ensure_ascii=False, indent=2)
        else:
            f.write(content)

def read_character_state(project_id: str) -> dict:
    return read_memory_file(project_id, "character_state.json")

def read_plot_threads(project_id: str) -> dict:
    return read_memory_file(project_id, "plot_threads.json")

def read_name_usage_rules(project_id: str) -> dict:
    return read_memory_file(project_id, "name_usage_rules.json")

def read_outline_state(project_id: str) -> dict:
    memory_dir = get_memory_dir(project_id)
    filepath = os.path.join(memory_dir, "outline_state.json")
    if not os.path.exists(filepath):
        # Auto-initialize from legacy directory if outline_state doesn't exist
        try:
            return initialize_outline_state_from_legacy(project_id)
        except Exception as e:
            logger.error(f"Failed to initialize outline_state from legacy: {e}")
            raise RuntimeError(f"Failed to initialize outline_state from legacy: {e}")
            
    return read_memory_file(project_id, "outline_state.json")

def initialize_outline_state_from_legacy(project_id: str) -> dict:
    """从旧版 Novel_directory.txt 和数据库 chapter 表初始化 outline_state.json"""
    from backend.app.services.chapter_service import list_chapters
    import os
    from backend.app.database import get_db
    
    with get_db() as conn:
        project = conn.execute("SELECT filepath FROM project WHERE id = ?", (project_id,)).fetchone()
        if not project:
            raise ValueError(f"Project {project_id} not found")
        filepath = project["filepath"]
    
    directory_file = os.path.join(filepath, "Novel_directory.txt")
    if not os.path.exists(directory_file):
        # If even Novel_directory doesn't exist, just return default
        ensure_memory_files(project_id)
        return DEFAULT_OUTLINE_STATE
        
    from chapter_directory_parser import parse_chapter_blueprint
    from utils import read_file
    content = read_file(directory_file)
    legacy_chapters = parse_chapter_blueprint(content)
    
    db_chapters = list_chapters(project_id)
    db_chapter_map = {ch["chapter_number"]: ch for ch in db_chapters}
    
    outline_chapters = []
    last_updated_chapter = None
    
    for lc in legacy_chapters:
        cn = lc["chapter_number"]
        db_ch = db_chapter_map.get(cn, {})
        status = db_ch.get("status", "pending")
        
        # Determine outline status
        if status in ["final", "finalized"]:
            outline_status = "finalized"
            locked = True
            last_updated_chapter = max(last_updated_chapter or 0, cn)
        elif status in ["draft", "drafted"]:
            outline_status = "drafted"
            locked = False
        else:
            outline_status = "planned"
            locked = False
            
        outline_chapters.append({
            "chapter_index": cn,
            "title": lc.get("chapter_title", f"第{cn}章"),
            "planned_summary": lc.get("chapter_summary", ""),
            "chapter_goal": lc.get("chapter_purpose", ""),
            "key_events": "",
            "expected_characters": lc.get("chapter_role", ""),
            "foreshadowing": lc.get("foreshadowing", ""),
            "status": outline_status,
            "locked": locked,
            "actual_summary": "", # We don't have actual_summary from legacy directory usually
            "notes": f"悬念:{lc.get('suspense_level', '')} 反转:{lc.get('plot_twist_level', '')}"
        })
        
    outline_state = {
        "version": 1,
        "chapters": outline_chapters,
        "last_updated_chapter": last_updated_chapter
    }
    
    ensure_memory_files(project_id)
    write_memory_file(project_id, "outline_state.json", outline_state)
    return outline_state

def read_global_summary(project_id: str) -> str:
    return read_memory_file(project_id, "global_summary.md", is_json=False)

def backup_memory_files(project_id: str, patch_id: str, chapter_index: int) -> dict:
    """
    合并 patch 前备份现有状态文件。
    备份文件名中包含 chapter_index 和 patch_id，避免重复覆盖。
    """
    memory_dir = get_memory_dir(project_id)
    backups_dir = os.path.join(memory_dir, "backups")
    os.makedirs(backups_dir, exist_ok=True)
    
    files_to_backup = [
        "character_state.json",
        "global_summary.md",
        "plot_threads.json",
        "name_usage_rules.json",
        "outline_state.json"
    ]
    
    backup_records = {}
    for filename in files_to_backup:
        src = os.path.join(memory_dir, filename)
        if os.path.exists(src):
            base, ext = os.path.splitext(filename)
            backup_filename = f"{base}_before_chapter_{chapter_index:03d}_{patch_id}{ext}"
            dst = os.path.join(backups_dir, backup_filename)
            shutil.copy2(src, dst)
            backup_records[filename] = dst
            
    return backup_records
