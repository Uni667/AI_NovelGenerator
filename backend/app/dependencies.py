import os
import sys
from functools import lru_cache

# 将项目根目录加入 path，以便导入现有的 novel_generator 等模块
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT_DIR)

from config_manager import load_config


CONFIG_FILE = os.path.join(ROOT_DIR, "config.json")


@lru_cache()
def get_config() -> dict:
    return load_config(CONFIG_FILE) or {}


def get_llm_config(config_name: str) -> dict:
    cfg = get_config()
    llm_configs = cfg.get("llm_configs", {})
    return llm_configs.get(config_name, {})


def get_embedding_config(config_name: str) -> dict:
    cfg = get_config()
    emb_configs = cfg.get("embedding_configs", {})
    return emb_configs.get(config_name, {})
