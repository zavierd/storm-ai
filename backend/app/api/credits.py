from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user_id
from app.services import credit_service

router = APIRouter(prefix="/credits", tags=["积分/算力"])


@router.get("/balance")
async def get_balance(user_id: str = Depends(get_current_user_id)):
    balance = await credit_service.get_balance(user_id)
    return {"success": True, "balance": balance}


@router.get("/history")
async def get_history(
    limit: int = 20,
    offset: int = 0,
    user_id: str = Depends(get_current_user_id),
):
    records = await credit_service.get_history(user_id, limit, offset)
    normalized_records = records if isinstance(records, list) else []
    return {"success": True, "records": normalized_records, "count": len(normalized_records)}
