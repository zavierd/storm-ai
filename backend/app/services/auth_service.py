from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.database import get_session
from app.models.db_models import CreditRecord, User

logger = logging.getLogger(__name__)

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

INITIAL_CREDITS = 1000.0


def hash_password(plain: str) -> str:
    return pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)


def create_token(user_id: str, username: str) -> str:
    settings = get_settings()
    payload = {
        "sub": user_id,
        "username": username,
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> dict | None:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


async def register_user(username: str, email: str, password: str) -> dict:
    try:
        async with get_session() as session:
            existing = await session.execute(
                select(User).where((User.username == username) | (User.email == email))
            )
            if existing.scalar_one_or_none():
                raise ValueError("用户名或邮箱已存在")

            user = User(
                username=username,
                email=email,
                password_hash=hash_password(password),
                credits_balance=INITIAL_CREDITS,
            )
            session.add(user)
            await session.flush()

            record = CreditRecord(
                user_id=user.id,
                amount=INITIAL_CREDITS,
                reason="新用户注册赠送",
            )
            session.add(record)

            token = create_token(user.id, user.username)
            return {
                "token": token,
                "user": _user_dict(user),
            }
    except IntegrityError as e:
        logger.warning(
            "注册唯一约束冲突 username=%s email=%s err=%s",
            username,
            email,
            e,
        )
        raise ValueError("用户名或邮箱已存在") from e


async def login_user(username: str, password: str) -> dict:
    async with get_session() as session:
        result = await session.execute(
            select(User).where((User.username == username) | (User.email == username))
        )
        user = result.scalar_one_or_none()
        if not user or not verify_password(password, user.password_hash):
            raise ValueError("用户名或密码错误")

        token = create_token(user.id, user.username)
        return {
            "token": token,
            "user": _user_dict(user),
        }


async def get_user_by_id(user_id: str) -> dict | None:
    async with get_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        return _user_dict(user) if user else None


def _user_dict(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "avatar_url": user.avatar_url,
        "credits_balance": user.credits_balance,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }
