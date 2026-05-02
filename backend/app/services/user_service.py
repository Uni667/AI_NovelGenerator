import uuid
import datetime
from backend.app.database import get_db
from backend.app.auth import hash_password, verify_password, create_token
from backend.app.utils.crypto import encrypt, decrypt, mask_key


def _clean_text(value):
    return value.strip() if isinstance(value, str) else value


def _clean_payload(payload: dict) -> dict:
    return {key: _clean_text(value) for key, value in payload.items()}


def _normalize_name(name: str, kind: str) -> str:
    clean_name = (name or "").strip()
    if not clean_name:
        raise ValueError(f"{kind} 配置名称不能为空")
    return clean_name


def _requires_api_key(interface_format: str) -> bool:
    return (interface_format or "").strip().lower() not in {"ollama"}


def _validate_common_config(kind: str, config: dict, require_api_key: bool = True):
    interface_format = (config.get("interface_format") or "").strip()
    model_name = (config.get("model_name") or "").strip()
    base_url = (config.get("base_url") or "").strip()
    api_key = config.get("api_key")
    if not interface_format:
        raise ValueError(f"{kind} 配置缺少接口类型")
    if not model_name:
        raise ValueError(f"{kind} 配置缺少模型名称")
    if not base_url and interface_format.lower() != "gemini":
        raise ValueError(f"{kind} 配置缺少 Base URL")
    if require_api_key and _requires_api_key(interface_format) and not (api_key or "").strip():
        raise ValueError(f"{kind} 配置缺少 API Key")


def _config_exists(conn, table: str, user_id: str, name: str) -> bool:
    row = conn.execute(
        f"SELECT id FROM {table} WHERE user_id = ? AND name = ?", (user_id, name)
    ).fetchone()
    return bool(row)


def register_user(username: str, password: str) -> dict:
    user_id = str(uuid.uuid4())
    now = datetime.datetime.now().isoformat()
    pw_hash = hash_password(password)
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM user WHERE username = ?", (username,)).fetchone()
        if existing:
            raise ValueError("用户名已存在")
        conn.execute(
            "INSERT INTO user (id, username, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (user_id, username, pw_hash, now)
        )
    token = create_token(user_id)
    return {"user_id": user_id, "username": username, "token": token}


def login_user(username: str, password: str) -> dict:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM user WHERE username = ?", (username,)).fetchone()
        if not row:
            raise ValueError("用户名或密码错误")
        user = dict(row)
    if not verify_password(password, user["password_hash"]):
        raise ValueError("用户名或密码错误")
    token = create_token(user["id"])
    return {"user_id": user["id"], "username": user["username"], "token": token}


def get_user(user_id: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT id, username, created_at FROM user WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


# ---- 用户级 LLM 配置 ----

def list_user_llm_configs(user_id: str) -> dict:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM user_llm_config WHERE user_id = ? ORDER BY created_at", (user_id,)
        ).fetchall()
    result = {}
    for row in rows:
        r = dict(row)
        try:
            key = decrypt(r["api_key"])
        except Exception:
            key = r["api_key"]
        result[r["name"]] = {
            "name": r["name"],
            "base_url": r["base_url"],
            "model_name": r["model_name"],
            "temperature": r["temperature"],
            "max_tokens": r["max_tokens"],
            "timeout": r["timeout"],
            "interface_format": r["interface_format"],
            "usage": r["usage"] if r["usage"] else "general",
            "api_key_masked": mask_key(key),
        }
    return result


def add_user_llm_config(user_id: str, name: str, config: dict) -> dict:
    name = _normalize_name(name, "LLM")
    config = _clean_payload(config)
    _validate_common_config("LLM", config)
    now = datetime.datetime.now().isoformat()
    encrypted_key = encrypt(config["api_key"])
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM user_llm_config WHERE user_id = ? AND name = ?", (user_id, name)
        ).fetchone()
        if existing:
            raise ValueError(f"LLM 配置 '{name}' 已存在")
        conn.execute(
            "INSERT INTO user_llm_config (user_id, name, interface_format, api_key, base_url, model_name, temperature, max_tokens, timeout, usage, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, name,
             config.get("interface_format", "OpenAI"),
             encrypted_key,
             config.get("base_url", ""),
             config.get("model_name", ""),
             config.get("temperature", 0.7),
             config.get("max_tokens", 8192),
             config.get("timeout", 600),
             config.get("usage", "general"),
             now, now)
        )
    return {"name": name, "api_key_masked": mask_key(config["api_key"])}


def update_user_llm_config(user_id: str, name: str, updates: dict) -> dict:
    name = _normalize_name(name, "LLM")
    updates = _clean_payload(updates)
    allowed = ["api_key", "base_url", "model_name", "temperature", "max_tokens", "timeout", "interface_format", "usage"]
    sets = []
    params = []
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM user_llm_config WHERE name = ? AND user_id = ?", (name, user_id)
        ).fetchone()
        if not row:
            raise ValueError(f"LLM 配置 '{name}' 不存在")
        current = dict(row)

    merged = {**current, **updates}
    if "api_key" in updates:
        effective_api_key = updates.get("api_key")
    else:
        try:
            effective_api_key = decrypt(current.get("api_key", ""))
        except Exception:
            effective_api_key = current.get("api_key", "")
    if _requires_api_key(merged.get("interface_format", "")) and not (effective_api_key or "").strip():
        raise ValueError(f"LLM 配置 '{name}' 缺少 API Key")
    merged["api_key"] = effective_api_key
    _validate_common_config("LLM", merged, require_api_key=False)

    for key in allowed:
        if key in updates and updates[key] is not None:
            val = updates[key]
            if key == "api_key":
                val = encrypt(val)
            sets.append(f"{key} = ?")
            params.append(val)
    if not sets:
        raise ValueError(f"LLM 配置 '{name}' 没有可更新的字段")
    sets.append("updated_at = ?")
    params.append(datetime.datetime.now().isoformat())
    params.extend([name, user_id])
    with get_db() as conn:
        cursor = conn.execute(
            f"UPDATE user_llm_config SET {', '.join(sets)} WHERE name = ? AND user_id = ?", params
        )
        if cursor.rowcount == 0:
            raise ValueError(f"LLM 配置 '{name}' 不存在")
    return {"name": name, "message": f"LLM 配置 '{name}' 已更新"}


def delete_user_llm_config(user_id: str, name: str):
    name = _normalize_name(name, "LLM")
    with get_db() as conn:
        if not _config_exists(conn, "user_llm_config", user_id, name):
            raise ValueError(f"LLM 配置 '{name}' 不存在")
        count = conn.execute(
            "SELECT COUNT(*) FROM user_llm_config WHERE user_id = ?", (user_id,)
        ).fetchone()[0]
        if count <= 1:
            raise ValueError("至少需要保留一个 LLM 配置")
        conn.execute("DELETE FROM user_llm_config WHERE name = ? AND user_id = ?", (name, user_id))


def test_user_llm_config(user_id: str, name: str) -> dict:
    name = _normalize_name(name, "LLM")
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM user_llm_config WHERE name = ? AND user_id = ?", (name, user_id)
        ).fetchone()
        if not row:
            raise ValueError(f"LLM 配置 '{name}' 不存在")
        conf = dict(row)
    from llm_adapters import create_llm_adapter
    try:
        api_key = decrypt(conf["api_key"])
    except Exception:
        api_key = conf["api_key"]
    conf["api_key"] = api_key
    _validate_common_config("LLM", conf)
    provider = conf["interface_format"]
    model = conf["model_name"]
    base_url = conf["base_url"] or "默认地址"
    try:
        adapter = create_llm_adapter(
            interface_format=provider,
            base_url=conf["base_url"],
            model_name=model,
            api_key=api_key,
            temperature=conf["temperature"],
            max_tokens=conf["max_tokens"],
            timeout=conf["timeout"]
        )
    except Exception as e:
        return {
            "success": False,
            "message": f"LLM 初始化失败（配置: {name}, 接口: {provider}, 模型: {model}, 地址: {base_url}）: {e}",
        }
    response = adapter.invoke("Please reply 'OK'")
    if response:
        return {"success": True, "message": f"测试成功！回复: {response[:200]}"}
    err = getattr(adapter, "last_error", "") or "未获取到响应"
    return {
        "success": False,
        "message": f"LLM 测试失败（配置: {name}, 接口: {provider}, 模型: {model}, 地址: {base_url}）: {err}",
    }


def get_user_llm_config_raw(user_id: str, name: str) -> dict:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM user_llm_config WHERE name = ? AND user_id = ?", (name, user_id)
        ).fetchone()
        if not row:
            return {}
        conf = dict(row)
    try:
        conf["api_key"] = decrypt(conf["api_key"])
    except Exception:
        pass
    return conf


# ---- 用户级 Embedding 配置 ----

def list_user_embedding_configs(user_id: str) -> dict:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM user_embedding_config WHERE user_id = ? ORDER BY created_at", (user_id,)
        ).fetchall()
    result = {}
    for row in rows:
        r = dict(row)
        try:
            key = decrypt(r["api_key"])
        except Exception:
            key = r["api_key"]
        result[r["name"]] = {
            "name": r["name"],
            "base_url": r["base_url"],
            "model_name": r["model_name"],
            "retrieval_k": r["retrieval_k"],
            "interface_format": r["interface_format"],
            "api_key_masked": mask_key(key)
        }
    return result


def add_user_embedding_config(user_id: str, name: str, config: dict) -> dict:
    name = _normalize_name(name, "Embedding")
    config = _clean_payload(config)
    _validate_common_config("Embedding", config)
    now = datetime.datetime.now().isoformat()
    encrypted_key = encrypt(config["api_key"])
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM user_embedding_config WHERE user_id = ? AND name = ?", (user_id, name)
        ).fetchone()
        if existing:
            raise ValueError(f"Embedding 配置 '{name}' 已存在")
        conn.execute(
            "INSERT INTO user_embedding_config (user_id, name, interface_format, api_key, base_url, model_name, retrieval_k, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, name,
             config.get("interface_format", "OpenAI"),
             encrypted_key,
             config.get("base_url", ""),
             config.get("model_name", ""),
             config.get("retrieval_k", 4),
             now, now)
        )
    return {"name": name, "api_key_masked": mask_key(config["api_key"])}


def update_user_embedding_config(user_id: str, name: str, updates: dict) -> dict:
    name = _normalize_name(name, "Embedding")
    updates = _clean_payload(updates)
    allowed = ["api_key", "base_url", "model_name", "retrieval_k", "interface_format"]
    sets = []
    params = []
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM user_embedding_config WHERE name = ? AND user_id = ?", (name, user_id)
        ).fetchone()
        if not row:
            raise ValueError(f"Embedding 配置 '{name}' 不存在")
        current = dict(row)

    merged = {**current, **updates}
    if "api_key" in updates:
        effective_api_key = updates.get("api_key")
    else:
        try:
            effective_api_key = decrypt(current.get("api_key", ""))
        except Exception:
            effective_api_key = current.get("api_key", "")
    if _requires_api_key(merged.get("interface_format", "")) and not (effective_api_key or "").strip():
        raise ValueError(f"Embedding 配置 '{name}' 缺少 API Key")
    merged["api_key"] = effective_api_key
    _validate_common_config("Embedding", merged, require_api_key=False)

    for key in allowed:
        if key in updates and updates[key] is not None:
            val = updates[key]
            if key == "api_key":
                val = encrypt(val)
            sets.append(f"{key} = ?")
            params.append(val)
    if not sets:
        raise ValueError(f"Embedding 配置 '{name}' 没有可更新的字段")
    sets.append("updated_at = ?")
    params.append(datetime.datetime.now().isoformat())
    params.extend([name, user_id])
    with get_db() as conn:
        cursor = conn.execute(
            f"UPDATE user_embedding_config SET {', '.join(sets)} WHERE name = ? AND user_id = ?", params
        )
        if cursor.rowcount == 0:
            raise ValueError(f"Embedding 配置 '{name}' 不存在")
    return {"name": name, "message": f"Embedding 配置 '{name}' 已更新"}


def delete_user_embedding_config(user_id: str, name: str):
    name = _normalize_name(name, "Embedding")
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM user_embedding_config WHERE name = ? AND user_id = ?", (name, user_id))
        if cursor.rowcount == 0:
            raise ValueError(f"Embedding 配置 '{name}' 不存在")


def test_user_embedding_config(user_id: str, name: str) -> dict:
    name = _normalize_name(name, "Embedding")
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM user_embedding_config WHERE name = ? AND user_id = ?", (name, user_id)
        ).fetchone()
        if not row:
            raise ValueError(f"Embedding 配置 '{name}' 不存在")
        conf = dict(row)
    from embedding_adapters import create_embedding_adapter
    try:
        api_key = decrypt(conf["api_key"])
    except Exception:
        api_key = conf["api_key"]
    conf["api_key"] = api_key
    _validate_common_config("Embedding", conf)
    provider = conf["interface_format"]
    model = conf["model_name"]
    base_url = conf["base_url"] or "默认地址"
    try:
        adapter = create_embedding_adapter(
            interface_format=provider,
            api_key=api_key,
            base_url=conf["base_url"],
            model_name=model
        )
    except Exception as e:
        return {
            "success": False,
            "message": f"Embedding 初始化失败（配置: {name}, 接口: {provider}, 模型: {model}, 地址: {base_url}）: {e}",
        }
    result = adapter.embed_query("测试文本")
    if result and len(result) > 0:
        return {"success": True, "message": f"测试成功！向量维度: {len(result)}"}
    err = getattr(adapter, "last_error", "") or "未获取到向量"
    return {
        "success": False,
        "message": f"Embedding 测试失败（配置: {name}, 接口: {provider}, 模型: {model}, 地址: {base_url}）: {err}",
    }


def get_user_embedding_config_raw(user_id: str, name: str) -> dict:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM user_embedding_config WHERE name = ? AND user_id = ?", (name, user_id)
        ).fetchone()
        if not row:
            return {}
        conf = dict(row)
    try:
        conf["api_key"] = decrypt(conf["api_key"])
    except Exception:
        pass
    return conf
