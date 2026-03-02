from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.api.deps import get_current_user_id
from app.exceptions import AppException
from app.prompts.system_prompt_manager import system_prompt_manager
from app.services import credit_service

router = APIRouter(prefix="/engines", tags=["引擎管理"])
logger = logging.getLogger(__name__)


class QuickTestRequest(BaseModel):
    prompt: str = "画一只鹿"
    model_slug: str | None = None
    quality: str | None = None


class QuickTestResponse(BaseModel):
    success: bool
    text: str | None = None
    image_urls: list[str] = []
    usage: dict | None = None
    error: str | None = None


@router.get("/list")
async def list_engines(request: Request):
    """列出所有已注册的 AI 引擎"""
    em = request.app.state.engine_manager
    return {"engines": em.list_engines(), "default": em.default_key}


@router.get("/models")
async def list_models(request: Request, engine_key: str | None = None):
    """列出指定引擎下可用的模型"""
    em = request.app.state.engine_manager
    client = em.get(engine_key)
    models = await client.list_models()
    return {"engine": engine_key or em.default_key, "models": models}


@router.post("/test", response_model=QuickTestResponse)
async def quick_test(
    body: QuickTestRequest,
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """快速测试：发送提示词到指定模型"""
    em = request.app.state.engine_manager
    client = em.get_default()
    feature_key = "engines_test"

    config: dict = {}
    if body.model_slug:
        config["model_slug"] = body.model_slug
    if body.quality:
        config["quality"] = body.quality

    cost = credit_service.get_feature_credit_cost(feature_key)
    reservation = await credit_service.reserve_generation_credits(
        user_id=user_id,
        feature_key=feature_key,
        amount=cost,
    )
    try:
        result = await client.generate(body.prompt, config=config)
        await credit_service.record_generation(
            user_id=user_id,
            feature_key=feature_key,
            prompt_text=body.prompt,
            result_image_url=result.image_urls[0] if result.image_urls else None,
            credits_cost=reservation.amount,
        )
        logger.info(
            "engines/test 调用成功 user=%s feature=%s cost=%.2f",
            user_id,
            feature_key,
            reservation.amount,
        )
        return QuickTestResponse(
            success=True,
            text=result.texts[0] if result.texts else None,
            image_urls=result.image_urls,
            usage=result.usage,
        )
    except Exception as e:
        trace_id = uuid.uuid4().hex
        try:
            await credit_service.rollback_generation_credits(reservation)
        except Exception as rollback_error:
            logger.exception(
                "engines/test 失败且回滚失败 trace=%s user=%s feature=%s hold=%s origin_err=%r rollback_err=%r",
                trace_id,
                user_id,
                feature_key,
                reservation.reservation_id,
                e,
                rollback_error,
            )
            raise AppException(
                status_code=500,
                code="CREDITS_ROLLBACK_FAILED",
                message="测试调用失败且积分回滚失败，请联系管理员",
                detail={
                    "trace_id": trace_id,
                    "reservation_id": reservation.reservation_id,
                    "feature_key": feature_key,
                },
            ) from rollback_error

        if isinstance(e, (AppException, HTTPException)):
            raise
        raise HTTPException(status_code=502, detail=f"测试调用失败：{e}") from e


# ---- 系统提示词管理 ----

@router.get("/system-prompts")
async def list_system_prompts():
    """列出所有已配置的系统提示词"""
    return {"prompts": system_prompt_manager.list_features()}


@router.get("/system-prompts/{feature_key}")
async def get_system_prompt(feature_key: str):
    """获取指定功能的系统提示词"""
    content = system_prompt_manager.get(feature_key)
    return {"feature_key": feature_key, "content": content, "exists": content is not None}


class UpdateSystemPromptRequest(BaseModel):
    content: str


@router.put("/system-prompts/{feature_key}")
async def update_system_prompt(feature_key: str, body: UpdateSystemPromptRequest):
    """更新/创建指定功能的系统提示词"""
    system_prompt_manager.set(feature_key, body.content)
    return {"feature_key": feature_key, "updated": True}
