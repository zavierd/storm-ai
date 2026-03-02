from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.deps import get_current_user_id
from app.exceptions import AppException
from app.models.common import GenerationRequest, GenerationResponse
from app.models.toolbox import (
    MaterialExtractRequest,
    RemoveWatermarkRequest,
    StyleMimicRequest,
    ToolboxTextToImageRequest,
    UniversalEditRequest,
)
from app.services import credit_service, project_service

router = APIRouter(prefix="/toolbox", tags=["工具箱"])
logger = logging.getLogger(__name__)


async def _process_and_record(
    feature_key: str,
    request_body: GenerationRequest,
    request: Request,
    user_id: str,
) -> GenerationResponse:
    service = request.app.state.toolbox_service
    try:
        project_id = await project_service.resolve_project_id(user_id, request_body.project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    resolution_preset = request_body.resolution.preset if request_body.resolution else None
    cost = credit_service.get_credit_cost_with_resolution(feature_key, resolution_preset)
    reservation = await credit_service.reserve_generation_credits(
        user_id=user_id,
        feature_key=feature_key,
        amount=cost,
    )
    try:
        result = await service.process(feature_key, request_body)
        if not result.success:
            raise HTTPException(status_code=502, detail=result.error or "生成失败")
        extra = request_body.extra_params or {}
        result_image_url = credit_service.ensure_result_image_url(
            user_id=user_id,
            feature_key=feature_key,
            result_image_url=result.image_urls[0] if result.image_urls else None,
            result_image_base64=result.images[0] if result.images else None,
        )
        if result_image_url and not result.image_urls:
            result.image_urls = [result_image_url]
        await credit_service.record_generation(
            user_id=user_id,
            feature_key=feature_key,
            project_id=project_id,
            prompt_text=request_body.prompt_text,
            room_type=extra.get("room_type"),
            result_image_url=result_image_url,
            credits_cost=reservation.amount,
        )
        logger.info(
            "toolbox 生成成功 user=%s feature=%s cost=%.2f",
            user_id,
            feature_key,
            reservation.amount,
        )
        return result
    except Exception as e:
        trace_id = uuid.uuid4().hex
        try:
            await credit_service.rollback_generation_credits(reservation)
        except Exception as rollback_error:
            logger.exception(
                "toolbox 生成失败且回滚失败 trace=%s user=%s feature=%s hold=%s origin_err=%r rollback_err=%r",
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
                message="生成失败且积分回滚失败，请联系管理员",
                detail={
                    "trace_id": trace_id,
                    "reservation_id": reservation.reservation_id,
                    "feature_key": feature_key,
                },
            ) from rollback_error
        if isinstance(e, (AppException, HTTPException)):
            raise
        raise HTTPException(status_code=502, detail=f"生成失败：{e}") from e


@router.post("/toolbox-t2i", response_model=GenerationResponse)
async def toolbox_text_to_image(
    request_body: ToolboxTextToImageRequest,
    request: Request,
    user_id: str = Depends(get_current_user_id),
) -> GenerationResponse:
    """文生图 — 文字描述生成图片"""
    return await _process_and_record("toolbox-t2i", request_body, request, user_id)


@router.post("/universal-edit", response_model=GenerationResponse)
async def universal_edit(
    request_body: UniversalEditRequest,
    request: Request,
    user_id: str = Depends(get_current_user_id),
) -> GenerationResponse:
    """万能修改 — 精准定位区域，按需修改细节"""
    return await _process_and_record("universal-edit", request_body, request, user_id)


@router.post("/style-mimic", response_model=GenerationResponse)
async def style_mimic(
    request_body: StyleMimicRequest,
    request: Request,
    user_id: str = Depends(get_current_user_id),
) -> GenerationResponse:
    """图片模仿 — 图像风格复刻迁移"""
    return await _process_and_record("style-mimic", request_body, request, user_id)


@router.post("/remove-watermark", response_model=GenerationResponse)
async def remove_watermark(
    request_body: RemoveWatermarkRequest,
    request: Request,
    user_id: str = Depends(get_current_user_id),
) -> GenerationResponse:
    """一键去水印 — AI检测并去除图片水印"""
    return await _process_and_record("remove-watermark", request_body, request, user_id)


@router.post("/material-extract", response_model=GenerationResponse)
async def material_extract(
    request_body: MaterialExtractRequest,
    request: Request,
    user_id: str = Depends(get_current_user_id),
) -> GenerationResponse:
    """材质贴图提取 — 从图片中提取可复用材质纹理"""
    return await _process_and_record("material-extract", request_body, request, user_id)


@router.post("/{feature}", response_model=GenerationResponse)
async def process_feature(
    feature: str,
    request_body: GenerationRequest,
    request: Request,
    user_id: str = Depends(get_current_user_id),
) -> GenerationResponse:
    """工具箱通用功能端点（兜底）"""
    return await _process_and_record(feature, request_body, request, user_id)
