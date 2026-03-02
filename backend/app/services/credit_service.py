from __future__ import annotations

import base64
import json
import logging
import uuid
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from sqlalchemy import select

from app.config import get_settings
from app.database import get_session
from app.exceptions import InsufficientCreditsError
from app.models.db_models import CreditRecord, GenerationHistory, Project, User

logger = logging.getLogger(__name__)

_GENERATED_IMAGES_DIR = Path(__file__).resolve().parents[2] / "generated_images"
_GENERATED_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

_MIN_GENERATION_COST = 1.0
_DEFAULT_FEATURE_RATES: dict[str, float] = {
    "banana-pro-edit": 15.0,
    "banana-pro-t2i": 12.0,
    "banana-pro-dual": 18.0,
    "toolbox-t2i": 10.0,
}


@dataclass(frozen=True)
class CreditReservation:
    reservation_id: str
    user_id: str
    feature_key: str
    amount: float


def _guess_image_ext(raw: bytes) -> str:
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if raw.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if raw.startswith(b"RIFF") and b"WEBP" in raw[:16]:
        return "webp"
    if raw.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    return "png"


def _normalize_positive_cost(raw: float | int | str | None, fallback: float) -> float:
    try:
        amount = float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        amount = fallback
    if amount <= 0:
        return fallback
    return amount


@lru_cache
def _load_feature_rate_overrides() -> dict[str, float]:
    settings = get_settings()
    raw = settings.credits_feature_rates_json.strip()
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except Exception as e:
        logger.warning("解析 CREDITS_FEATURE_RATES_JSON 失败，将使用默认费率: %s", e)
        return {}
    if not isinstance(payload, dict):
        logger.warning("CREDITS_FEATURE_RATES_JSON 格式无效，应为 JSON 对象")
        return {}

    normalized: dict[str, float] = {}
    for feature_key, value in payload.items():
        key = str(feature_key).strip()
        if not key:
            continue
        normalized[key] = _normalize_positive_cost(value, _MIN_GENERATION_COST)
    return normalized


_RESOLUTION_COST_MULTIPLIER: dict[str, int] = {
    "720P": 1,
    "1K": 2,
    "2K": 3,
    "4K": 4,
}
_DEFAULT_RESOLUTION_PRESET = "1K"


def get_feature_credit_cost(feature_key: str) -> float:
    settings = get_settings()
    default_cost = _normalize_positive_cost(
        settings.credits_default_generation_cost,
        _MIN_GENERATION_COST,
    )
    baseline = _DEFAULT_FEATURE_RATES.get(feature_key, default_cost)
    overrides = _load_feature_rate_overrides()
    return _normalize_positive_cost(overrides.get(feature_key), baseline)


def get_credit_cost_with_resolution(
    feature_key: str,
    resolution_preset: str | None = None,
) -> float:
    """基础费率 × 分辨率系数。preset 为 None 时按 1K (1080p) 计费。"""
    base = get_feature_credit_cost(feature_key)
    preset = (resolution_preset or _DEFAULT_RESOLUTION_PRESET).upper()
    multiplier = _RESOLUTION_COST_MULTIPLIER.get(preset, _RESOLUTION_COST_MULTIPLIER[_DEFAULT_RESOLUTION_PRESET])
    return base * multiplier


async def _get_user_for_update(session, user_id: str) -> User:
    result = await session.execute(select(User).where(User.id == user_id).with_for_update())
    user = result.scalar_one_or_none()
    if not user:
        raise ValueError("用户不存在")
    return user


def ensure_result_image_url(
    user_id: str,
    feature_key: str,
    result_image_url: str | None = None,
    result_image_base64: str | None = None,
) -> str | None:
    """确保生成图有可访问 URL：优先沿用已有 URL，否则将 base64 落盘为静态文件。"""
    if result_image_url:
        return result_image_url
    if not result_image_base64:
        return None

    b64 = result_image_base64.split(",", 1)[-1].strip()
    if not b64:
        return None

    try:
        raw = base64.b64decode(b64, validate=False)
    except Exception as e:
        logger.warning("生成图 base64 解码失败，无法归档 URL: %s", e)
        return None

    ext = _guess_image_ext(raw)
    safe_feature = feature_key.replace("/", "-").replace(" ", "-")
    filename = f"{user_id}_{safe_feature}_{uuid.uuid4().hex[:12]}.{ext}"
    path = _GENERATED_IMAGES_DIR / filename

    try:
        path.write_bytes(raw)
    except Exception as e:
        logger.warning("生成图落盘失败，无法归档 URL: %s", e)
        return None

    base_url = get_settings().backend_public_url.rstrip("/")
    return f"{base_url}/generated-images/{filename}"


async def get_balance(user_id: str) -> float:
    async with get_session() as session:
        result = await session.execute(select(User.credits_balance).where(User.id == user_id))
        balance = result.scalar_one_or_none()
        return balance if balance is not None else 0.0


async def deduct_credits(
    user_id: str,
    amount: float,
    feature_key: str,
    reason: str = "AI生成消耗",
) -> float:
    """扣除积分，返回扣除后余额。余额不足抛出 InsufficientCreditsError。"""
    try:
        normalized_amount = float(amount)
    except (TypeError, ValueError):
        raise ValueError("扣减积分金额无效")
    if normalized_amount <= 0:
        raise ValueError("扣减积分金额必须大于0")
    async with get_session() as session:
        user = await _get_user_for_update(session, user_id)
        balance = float(user.credits_balance or 0.0)
        if balance < normalized_amount:
            raise InsufficientCreditsError(current_balance=balance, required=normalized_amount)
        user.credits_balance = balance - normalized_amount

        record = CreditRecord(
            user_id=user_id,
            amount=-normalized_amount,
            reason=reason,
            feature_key=feature_key,
        )
        session.add(record)
        return float(user.credits_balance or 0.0)


async def reserve_generation_credits(
    user_id: str,
    feature_key: str,
    amount: float | None = None,
    reason: str = "AI生成预扣",
) -> CreditReservation:
    debit_amount = _normalize_positive_cost(
        amount if amount is not None else get_feature_credit_cost(feature_key),
        _MIN_GENERATION_COST,
    )
    reservation_id = uuid.uuid4().hex
    async with get_session() as session:
        user = await _get_user_for_update(session, user_id)
        balance = float(user.credits_balance or 0.0)
        if balance < debit_amount:
            raise InsufficientCreditsError(current_balance=balance, required=debit_amount)

        user.credits_balance = balance - debit_amount
        session.add(
            CreditRecord(
                user_id=user_id,
                amount=-debit_amount,
                reason=f"{reason}[{reservation_id}]",
                feature_key=feature_key,
            )
        )
        logger.info(
            "积分预扣成功 user=%s feature=%s amount=%.2f balance_after=%.2f hold=%s",
            user_id,
            feature_key,
            debit_amount,
            float(user.credits_balance or 0.0),
            reservation_id,
        )
    return CreditReservation(
        reservation_id=reservation_id,
        user_id=user_id,
        feature_key=feature_key,
        amount=debit_amount,
    )


async def rollback_generation_credits(
    reservation: CreditReservation,
    reason: str = "AI生成失败回滚",
) -> float:
    if reservation.amount <= 0:
        return await get_balance(reservation.user_id)

    async with get_session() as session:
        user = await _get_user_for_update(session, reservation.user_id)
        user.credits_balance = float(user.credits_balance or 0.0) + reservation.amount
        session.add(
            CreditRecord(
                user_id=reservation.user_id,
                amount=reservation.amount,
                reason=f"{reason}[{reservation.reservation_id}]",
                feature_key=reservation.feature_key,
            )
        )
        balance_after = float(user.credits_balance or 0.0)
        logger.warning(
            "积分回滚完成 user=%s feature=%s amount=%.2f balance_after=%.2f hold=%s",
            reservation.user_id,
            reservation.feature_key,
            reservation.amount,
            balance_after,
            reservation.reservation_id,
        )
        return balance_after


async def add_credits(user_id: str, amount: float, reason: str = "充值") -> float:
    try:
        normalized_amount = float(amount)
    except (TypeError, ValueError):
        raise ValueError("充值积分金额无效")
    if normalized_amount <= 0:
        raise ValueError("充值积分金额必须大于0")
    async with get_session() as session:
        user = await _get_user_for_update(session, user_id)
        user.credits_balance = float(user.credits_balance or 0.0) + normalized_amount

        record = CreditRecord(
            user_id=user_id,
            amount=normalized_amount,
            reason=reason,
        )
        session.add(record)
        return float(user.credits_balance or 0.0)


async def record_generation(
    user_id: str,
    feature_key: str,
    project_id: str | None = None,
    prompt_text: str | None = None,
    room_type: str | None = None,
    input_image_url: str | None = None,
    result_image_url: str | None = None,
    credits_cost: float = 0,
) -> str:
    async with get_session() as session:
        record = GenerationHistory(
            user_id=user_id,
            project_id=project_id,
            feature_key=feature_key,
            prompt_text=prompt_text,
            room_type=room_type,
            input_image_url=input_image_url,
            result_image_url=result_image_url,
            credits_cost=credits_cost,
        )
        session.add(record)
        if project_id and result_image_url:
            proj_result = await session.execute(
                select(Project).where(
                    Project.id == project_id,
                    Project.user_id == user_id,
                )
            )
            project = proj_result.scalar_one_or_none()
            if project and not project.cover_image_url:
                project.cover_image_url = result_image_url
        await session.flush()
        return record.id


async def get_history(user_id: str, limit: int = 20, offset: int = 0) -> list[dict]:
    async with get_session() as session:
        result = await session.execute(
            select(CreditRecord)
            .where(CreditRecord.user_id == user_id)
            .order_by(CreditRecord.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        records = result.scalars().all()
        return [
            {
                "id": r.id,
                "amount": float(r.amount or 0.0),
                "reason": r.reason,
                "feature_key": r.feature_key,
                # 兼容旧前端字段：历史上使用 credits_cost 表示消耗值
                "credits_cost": max(-float(r.amount or 0.0), 0.0),
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ]
