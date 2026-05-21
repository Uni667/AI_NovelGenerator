"""用户认证服务 — 注册、登录、信息查询。旧 LLM/Embedding 配置已移除。"""

import uuid
import datetime
from backend.app.database import get_db
from backend.app.auth import hash_password, verify_password, create_access_token, create_refresh_token


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
    access_token = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)
    return {"user_id": user_id, "username": username, "token": access_token, "refresh_token": refresh_token}


def login_user(username: str, password: str) -> dict:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM user WHERE username = ?", (username,)).fetchone()
        if not row:
            raise ValueError("用户名或密码错误")
        user = dict(row)
    if not verify_password(password, user["password_hash"]):
        raise ValueError("用户名或密码错误")
    access_token = create_access_token(user["id"])
    refresh_token = create_refresh_token(user["id"])
    return {"user_id": user["id"], "username": user["username"], "token": access_token, "refresh_token": refresh_token}


def refresh_access_token(refresh_token: str) -> dict:
    """使用 refresh token 获取新的 access token。"""
    from backend.app.auth import verify_refresh_token, create_access_token
    payload = verify_refresh_token(refresh_token)
    user_id = payload["user_id"]
    new_access_token = create_access_token(user_id)
    return {"token": new_access_token}


def get_user(user_id: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT id, username, created_at FROM user WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None
