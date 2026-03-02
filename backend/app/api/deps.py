"""FastAPI 依赖注入：JWT 认证"""
from __future__ import annotations

from typing import Optional

from fastapi import Header, HTTPException

from app.database import is_db_available
from app.services.auth_service import decode_token


async def get_current_user_id(authorization: Optional[str] = Header(default=None)) -> str:
    if not is_db_available():
        raise HTTPException(status_code=503, detail="数据库未配置")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录，请先登录")
    token = authorization.removeprefix("Bearer ").strip()
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    return payload["sub"]


async def get_optional_user_id(authorization: Optional[str] = Header(default=None)) -> Optional[str]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    payload = decode_token(token)
    return payload.get("sub") if payload else None
