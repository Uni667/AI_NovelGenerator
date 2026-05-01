import os
import sys

# 将项目根目录加入 path，以便导入现有的 novel_generator 等模块
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT_DIR)


def get_user_llm_config(user_id: str, config_name: str) -> dict:
    from backend.app.services.user_service import get_user_llm_config_raw
    return get_user_llm_config_raw(user_id, config_name)


def get_user_embedding_config(user_id: str, config_name: str) -> dict:
    from backend.app.services.user_service import get_user_embedding_config_raw
    return get_user_embedding_config_raw(user_id, config_name)
