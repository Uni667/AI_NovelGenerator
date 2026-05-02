import uuid
import datetime
from backend.app.database import get_db
from backend.app.auth import hash_password, verify_password, create_token
from backend.app.utils.crypto import encrypt, decrypt, mask_key


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
            "api_key": key
        }
    return result


def add_user_llm_config(user_id: str, name: str, config: dict) -> dict:
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
    allowed = ["api_key", "base_url", "model_name", "temperature", "max_tokens", "timeout", "interface_format", "usage"]
    sets = []
    params = []
    for key in allowed:
        if key in updates and updates[key] is not None:
            val = updates[key]
            if key == "api_key":
                val = encrypt(val)
            sets.append(f"{key} = ?")
            params.append(val)
    if not sets:
        return {"name": name}
    sets.append("updated_at = ?")
    params.append(datetime.datetime.now().isoformat())
    params.extend([name, user_id])
    with get_db() as conn:
        cursor = conn.execute(
            f"UPDATE user_llm_config SET {', '.join(sets)} WHERE name = ? AND user_id = ?", params
        )
        if cursor.rowcount == 0:
            raise ValueError(f"LLM 配置 '{name}' 不存在")
    return {"name": name}


def delete_user_llm_config(user_id: str, name: str):
    with get_db() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM user_llm_config WHERE user_id = ?", (user_id,)
        ).fetchone()[0]
        if count <= 1:
            raise ValueError("至少需要保留一个 LLM 配置")
        conn.execute("DELETE FROM user_llm_config WHERE name = ? AND user_id = ?", (name, user_id))


def test_user_llm_config(user_id: str, name: str) -> dict:
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
    adapter = create_llm_adapter(
        interface_format=conf["interface_format"],
        base_url=conf["base_url"],
        model_name=conf["model_name"],
        api_key=api_key,
        temperature=conf["temperature"],
        max_tokens=conf["max_tokens"],
        timeout=conf["timeout"]
    )
    response = adapter.invoke("Please reply 'OK'")
    if response:
        return {"success": True, "message": f"测试成功！回复: {response[:200]}"}
    err = getattr(adapter, "last_error", "") or "未获取到响应"
    return {"success": False, "message": f"测试失败: {err}"}


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


def delete_user_embedding_config(user_id: str, name: str):
    with get_db() as conn:
        conn.execute("DELETE FROM user_embedding_config WHERE name = ? AND user_id = ?", (name, user_id))


def test_user_embedding_config(user_id: str, name: str) -> dict:
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
    adapter = create_embedding_adapter(
        interface_format=conf["interface_format"],
        api_key=api_key,
        base_url=conf["base_url"],
        model_name=conf["model_name"]
    )
    result = adapter.embed_query("测试文本")
    if result and len(result) > 0:
        return {"success": True, "message": f"测试成功！向量维度: {len(result)}"}
    err = getattr(adapter, "last_error", "") or "未获取到向量"
    return {"success": False, "message": f"测试失败: {err}"}


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
