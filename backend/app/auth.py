import os
import secrets
import datetime
import logging
from fastapi import HTTPException, Request
from backend.app.database import get_db

logger = logging.getLogger(__name__)

try:
    import jwt
except ImportError:
    jwt = None

try:
    from argon2 import PasswordHasher
except ImportError:
    PasswordHasher = None

SECRET_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", ".jwt_secret")


def _get_or_create_secret() -> str:
    env_secret = os.getenv("NEXTAUTH_SECRET") or os.getenv("JWT_SECRET")
    if env_secret:
        return env_secret
    os.makedirs(os.path.dirname(SECRET_FILE), exist_ok=True)
    if os.path.exists(SECRET_FILE):
        with open(SECRET_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    logger.warning(
        "JWT_SECRET/NEXTAUTH_SECRET 环境变量未设置，已生成随机密钥。"
        "多实例部署时各实例密钥不同会导致 token 失效，请在环境变量中设置固定密钥。"
    )
    secret = secrets.token_hex(32)
    with open(SECRET_FILE, "w", encoding="utf-8") as f:
        f.write(secret)
    return secret


def hash_password(password: str) -> str:
    if PasswordHasher is None:
        raise ImportError("argon2-cffi not installed")
    return PasswordHasher().hash(password)


def verify_password(password: str, hash: str) -> bool:
    if PasswordHasher is None:
        raise ImportError("argon2-cffi not installed")
    try:
        PasswordHasher().verify(hash, password)
        return True
    except Exception:
        return False


def create_access_token(user_id: str) -> str:
    """创建短期访问令牌（2 小时）。"""
    if jwt is None:
        raise ImportError("pyjwt not installed")
    secret = _get_or_create_secret()
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "user_id": user_id,
        "type": "access",
        "iat": now,
        "exp": now + datetime.timedelta(hours=2),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def create_refresh_token(user_id: str) -> str:
    """创建长期刷新令牌（7 天）。"""
    if jwt is None:
        raise ImportError("pyjwt not installed")
    secret = _get_or_create_secret()
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "user_id": user_id,
        "type": "refresh",
        "iat": now,
        "exp": now + datetime.timedelta(days=7),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def verify_access_token(token: str) -> dict:
    """验证访问令牌。"""
    if jwt is None:
        raise ImportError("pyjwt not installed")
    secret = _get_or_create_secret()
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="令牌类型错误")
        return payload
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="无效或过期的认证令牌")


def verify_refresh_token(token: str) -> dict:
    """验证刷新令牌。"""
    if jwt is None:
        raise ImportError("pyjwt not installed")
    secret = _get_or_create_secret()
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="令牌类型错误")
        return payload
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="无效或过期的刷新令牌")

def create_stream_token(user_id: str) -> str:
    """创建流式/临时连接令牌（5 分钟）。"""
    if jwt is None:
        raise ImportError("pyjwt not installed")
    secret = _get_or_create_secret()
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "user_id": user_id,
        "type": "stream",
        "aud": "sse",
        "iat": now,
        "exp": now + datetime.timedelta(minutes=5),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def verify_stream_token(token: str) -> dict:
    """验证流式/临时连接令牌。"""
    if jwt is None:
        raise ImportError("pyjwt not installed")
    secret = _get_or_create_secret()
    try:
        payload = jwt.decode(token, secret, audience="sse", algorithms=["HS256"])
        if payload.get("type") != "stream":
            raise HTTPException(status_code=401, detail="令牌类型错误")
        return payload
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="无效或过期的流式认证令牌")


def create_token(user_id: str) -> str:
    """兼容旧版，返回 access token。"""
    return create_access_token(user_id)


def verify_token(token: str) -> dict:
    """兼容旧版，验证 access token。"""
    return verify_access_token(token)


def get_current_user(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth.removeprefix("Bearer ")
        payload = verify_access_token(token)
        return payload["user_id"]
    # SSE 端点从 query param 传 token（EventSource API 限制）
    token = request.query_params.get("token", "")
    if token:
        payload = verify_stream_token(token)
        return payload["user_id"]
    raise HTTPException(status_code=401, detail="缺少认证令牌")
