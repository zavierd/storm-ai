from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field

from app.api.deps import get_current_user_id
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["用户认证"])


class RegisterRequest(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    email: str = Field(min_length=5, max_length=120)
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    success: bool
    token: str | None = None
    user: dict | None = None
    error: str | None = None


@router.post("/register", response_model=AuthResponse)
async def register(body: RegisterRequest):
    try:
        result = await auth_service.register_user(body.username, body.email, body.password)
        return AuthResponse(success=True, **result)
    except ValueError as e:
        return JSONResponse(
            status_code=409,
            content=AuthResponse(success=False, error=str(e)).model_dump(),
        )


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest):
    try:
        result = await auth_service.login_user(body.username, body.password)
        return AuthResponse(success=True, **result)
    except ValueError as e:
        return JSONResponse(
            status_code=401,
            content=AuthResponse(success=False, error=str(e)).model_dump(),
        )


@router.get("/me")
async def get_me(user_id: str = Depends(get_current_user_id)):
    user = await auth_service.get_user_by_id(user_id)
    if not user:
        return JSONResponse(status_code=404, content={"success": False, "error": "用户不存在"})
    return {"success": True, "user": user}
