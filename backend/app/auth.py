import os
import uuid
import datetime
from fastapi import HTTPException, Request
from backend.app.database import get_db

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
    os.makedirs(os.path.dirname(SECRET_FILE), exist_ok=True)
    if os.path.exists(SECRET_FILE):
        with open(SECRET_FILE, "r") as f:
            return f.read().strip()
    secret = uuid.uuid4().hex
    with open(SECRET_FILE, "w") as f:
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


def create_token(user_id: str) -> str:
    if jwt is None:
        raise ImportError("pyjwt not installed")
    secret = _get_or_create_secret()
    payload = {
        "user_id": user_id,
        "iat": datetime.datetime.now(datetime.timezone.utc)
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def verify_token(token: str) -> dict:
    if jwt is None:
        raise ImportError("pyjwt not installed")
    secret = _get_or_create_secret()
    try:
        return jwt.decode(token, secret, algorithms=["HS256"])
    except Exception:
        raise HTTPException(status_code=401, detail="无效或过期的认证令牌")


def get_current_user(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        # SSE 端点从 query param 传 token
        token = request.query_params.get("token", "")
        if token:
            payload = verify_token(token)
            return payload["user_id"]
        raise HTTPException(status_code=401, detail="缺少认证令牌")
    token = auth.removeprefix("Bearer ")
    payload = verify_token(token)
    return payload["user_id"]
