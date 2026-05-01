from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from backend.app.services import user_service
from backend.app.auth import get_current_user

router = APIRouter(tags=["用户认证"])


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=30)
    password: str = Field(..., min_length=6, max_length=100)


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/api/v1/auth/register")
def register(data: RegisterRequest):
    try:
        return user_service.register_user(data.username, data.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/v1/auth/login")
def login(data: LoginRequest):
    try:
        return user_service.login_user(data.username, data.password)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/api/v1/auth/me")
def me(request: Request):
    user_id = get_current_user(request)
    user = user_service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user
