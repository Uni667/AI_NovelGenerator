import json
import os
import datetime
import threading
from config_manager import load_config, save_config
from llm_adapters import create_llm_adapter
from embedding_adapters import create_embedding_adapter

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
CONFIG_FILE = os.path.join(ROOT_DIR, "config.json")


def get_all_llm_configs() -> dict:
    cfg = load_config(CONFIG_FILE) or {}
    return cfg.get("llm_configs", {})


def get_all_embedding_configs() -> dict:
    cfg = load_config(CONFIG_FILE) or {}
    return cfg.get("embedding_configs", {})


def add_llm_config(name: str, config: dict) -> dict:
    cfg = load_config(CONFIG_FILE) or {}
    if "llm_configs" not in cfg:
        cfg["llm_configs"] = {}
    if name in cfg["llm_configs"]:
        raise ValueError(f"LLM 配置 '{name}' 已存在")
    cfg["llm_configs"][name] = {
        "api_key": config["api_key"],
        "base_url": config["base_url"],
        "model_name": config["model_name"],
        "temperature": config["temperature"],
        "max_tokens": config["max_tokens"],
        "timeout": config["timeout"],
        "interface_format": config["interface_format"],
        "created_at": datetime.datetime.now().isoformat()
    }
    save_config(cfg, CONFIG_FILE)
    return cfg["llm_configs"][name]


def update_llm_config(name: str, updates: dict) -> dict:
    cfg = load_config(CONFIG_FILE) or {}
    if "llm_configs" not in cfg or name not in cfg["llm_configs"]:
        raise ValueError(f"LLM 配置 '{name}' 不存在")
    for key in ["api_key", "base_url", "model_name", "temperature", "max_tokens", "timeout", "interface_format"]:
        if key in updates and updates[key] is not None:
            cfg["llm_configs"][name][key] = updates[key]
    cfg["llm_configs"][name]["updated_at"] = datetime.datetime.now().isoformat()
    save_config(cfg, CONFIG_FILE)
    return cfg["llm_configs"][name]


def delete_llm_config(name: str):
    cfg = load_config(CONFIG_FILE) or {}
    llm_configs = cfg.get("llm_configs", {})
    if name not in llm_configs:
        raise ValueError(f"LLM 配置 '{name}' 不存在")
    if len(llm_configs) <= 1:
        raise ValueError("至少需要保留一个 LLM 配置")
    del llm_configs[name]
    save_config(cfg, CONFIG_FILE)


def test_llm_config(name: str) -> dict:
    cfg = load_config(CONFIG_FILE) or {}
    llm_configs = cfg.get("llm_configs", {})
    if name not in llm_configs:
        raise ValueError(f"LLM 配置 '{name}' 不存在")
    llm_conf = llm_configs[name]
    adapter = create_llm_adapter(
        interface_format=llm_conf["interface_format"],
        base_url=llm_conf["base_url"],
        model_name=llm_conf["model_name"],
        api_key=llm_conf["api_key"],
        temperature=llm_conf["temperature"],
        max_tokens=llm_conf["max_tokens"],
        timeout=llm_conf["timeout"]
    )
    response = adapter.invoke("Please reply 'OK'")
    if response:
        return {"success": True, "message": f"测试成功！回复: {response[:200]}"}
    return {"success": False, "message": "未获取到响应"}


def add_embedding_config(name: str, config: dict) -> dict:
    cfg = load_config(CONFIG_FILE) or {}
    if "embedding_configs" not in cfg:
        cfg["embedding_configs"] = {}
    if name in cfg["embedding_configs"]:
        raise ValueError(f"Embedding 配置 '{name}' 已存在")
    cfg["embedding_configs"][name] = {
        "api_key": config["api_key"],
        "base_url": config["base_url"],
        "model_name": config["model_name"],
        "retrieval_k": config.get("retrieval_k", 4),
        "interface_format": config["interface_format"]
    }
    save_config(cfg, CONFIG_FILE)
    return cfg["embedding_configs"][name]


def delete_embedding_config(name: str):
    cfg = load_config(CONFIG_FILE) or {}
    emb_configs = cfg.get("embedding_configs", {})
    if name not in emb_configs:
        raise ValueError(f"Embedding 配置 '{name}' 不存在")
    del emb_configs[name]
    save_config(cfg, CONFIG_FILE)


def test_embedding_config(name: str) -> dict:
    cfg = load_config(CONFIG_FILE) or {}
    emb_configs = cfg.get("embedding_configs", {})
    if name not in emb_configs:
        raise ValueError(f"Embedding 配置 '{name}' 不存在")
    emb_conf = emb_configs[name]
    adapter = create_embedding_adapter(
        interface_format=emb_conf["interface_format"],
        api_key=emb_conf["api_key"],
        base_url=emb_conf["base_url"],
        model_name=emb_conf["model_name"]
    )
    result = adapter.embed_query("测试文本")
    if result and len(result) > 0:
        return {"success": True, "message": f"测试成功！向量维度: {len(result)}"}
    return {"success": False, "message": "未获取到向量"}
