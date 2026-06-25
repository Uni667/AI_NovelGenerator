import os
import json
import logging
import datetime

logger = logging.getLogger(__name__)

DB_DIR = os.getenv("DATA_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data"))
CONFIG_FILE = os.path.join(DB_DIR, "local_library_config.json")


def get_default_config() -> dict:
    """获取基于环境变量和默认路径的初始配置。"""
    from backend.app.services.local_file_guard import get_file_access_flag
    
    default_base = os.path.join(DB_DIR, "reference_library")
    
    return {
        "id": 1,
        "source_dir": os.getenv("REFERENCE_BOOKS_DIR", os.path.join(default_base, "books")),
        "essence_dir": os.getenv("REFERENCE_ESSENCE_DIR", os.path.join(default_base, "essence")),
        "cache_dir": os.getenv("REFERENCE_CACHE_DIR", os.path.join(default_base, "cache")),
        "log_dir": os.getenv("REFERENCE_LOG_DIR", os.path.join(default_base, "logs")),
        "allow_local_file_access": get_file_access_flag(),
        "max_file_mb": int(os.getenv("REFERENCE_MAX_FILE_MB", "500")),
        "allowed_extensions": os.getenv("REFERENCE_ALLOWED_EXTENSIONS", ".txt,.md,.epub,.docx").split(","),
        "watcher_enabled": os.getenv("REFERENCE_ENABLE_WATCHER", "false").lower() == "true",
        "created_at": "2026-06-22T00:00:00Z",
        "updated_at": "2026-06-22T00:00:00Z",
    }


def load_config() -> dict:
    """加载持久化配置文件，若不存在则创建默认值。"""
    defaults = get_default_config()
    if not os.path.exists(CONFIG_FILE):
        try:
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(defaults, f, ensure_ascii=False, indent=2)
            return defaults
        except Exception as e:
            logger.error(f"Failed to create default config file: {e}")
            return defaults

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            stored = json.load(f)
            # 补齐默认字段防止升级过程中缺字段
            updated = False
            for k, v in defaults.items():
                if k not in stored:
                    stored[k] = v
                    updated = True
            if updated:
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(stored, f, ensure_ascii=False, indent=2)
            return stored
    except Exception as e:
        logger.error(f"Failed to read local library config JSON: {e}")
        return defaults


def get_local_library_config() -> dict:
    """获取当前书库配置。"""
    return load_config()


def update_local_library_config(config_data: dict) -> dict:
    """更新并持久化保存书库配置。"""
    current = load_config()
    for key, value in config_data.items():
        if key != "id":
            current[key] = value
    current["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
    
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(current, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to write local library config JSON: {e}")
        
    return current


def check_directory_status(dir_path: str) -> dict:
    """检测文件夹的存在状态、物理可读与物理可写性。"""
    if not dir_path:
        return {"exists": False, "readable": False, "writable": False, "error": "路径为空"}
    
    try:
        exists = os.path.exists(dir_path)
        if not exists:
            return {"exists": False, "readable": False, "writable": False, "error": "路径不存在"}
        
        readable = os.access(dir_path, os.R_OK)
        
        # 物理检测可写能力（防止网络挂载目录只读或无写权限，通过真实写删临时文件测试）
        writable = False
        temp_file = os.path.join(dir_path, f".write_test_{os.getpid()}")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write("test")
            os.remove(temp_file)
            writable = True
        except Exception:
            writable = False

        error_msg = None
        if not readable:
            error_msg = "目录不可读"
        elif not writable:
            error_msg = "目录不可写"

        return {
            "exists": True,
            "readable": readable,
            "writable": writable,
            "error": error_msg
        }
    except Exception as e:
        logger.error(f"Error checking directory status for {dir_path}: {e}")
        return {"exists": False, "readable": False, "writable": False, "error": str(e)}
