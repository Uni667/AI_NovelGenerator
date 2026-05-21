"""API 速率限制中间件。"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse

limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """速率限制超限时的错误响应。"""
    return JSONResponse(
        status_code=429,
        content={
            "detail": "请求过于频繁，请稍后再试",
            "retry_after": exc.detail.get("retry_after", 60) if isinstance(exc.detail, dict) else 60
        }
    )
