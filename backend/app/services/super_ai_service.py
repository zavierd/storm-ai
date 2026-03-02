from __future__ import annotations

import logging

from app.clients.gemini_client import GeminiClient
from app.exceptions import ValidationError
from app.models.common import GenerationRequest, GenerationResponse
from app.models.super_ai import (
    BananaDualImageRequest,
    BananaEditRequest,
    BananaTextToImageRequest,
)
from app.prompts.engine import PromptEngine
from app.prompts.registry import FeatureConfig, registry
from app.services.base_service import BaseAIService

logger = logging.getLogger(__name__)

FEATURES = [
    FeatureConfig(
        feature_key="banana-pro-edit",
        name="香蕉Pro图像编辑",
        category="super_ai",
        template_path="super_ai/banana_pro_edit.j2",
        description="基于参考图+文字指令的AI图像编辑，支持1K/2K/4K分辨率",
        input_type="single_image",
    ),
    FeatureConfig(
        feature_key="banana-pro-t2i",
        name="香蕉Pro文生图",
        category="super_ai",
        template_path="super_ai/banana_pro_t2i.j2",
        description="纯文字描述生成高品质图片",
        input_type="text_only",
    ),
    FeatureConfig(
        feature_key="banana-pro-dual",
        name="香蕉Pro双图模式",
        category="super_ai",
        template_path="super_ai/banana_pro_dual.j2",
        description="融合两张参考图特征生成新图",
        input_type="multi_image",
    ),
]

_REQUEST_TYPE_MAP: dict[str, type[GenerationRequest]] = {
    "banana-pro-edit": BananaEditRequest,
    "banana-pro-t2i": BananaTextToImageRequest,
    "banana-pro-dual": BananaDualImageRequest,
}


class SuperAIService(BaseAIService):
    """超级AI服务 — 图像编辑 / 文生图 / 双图融合"""

    def __init__(self, gemini_client: GeminiClient, prompt_engine: PromptEngine):
        super().__init__(gemini_client, prompt_engine)
        for feat in FEATURES:
            registry.register(feat)
        logger.info("SuperAIService 初始化完成，已注册 %d 个功能", len(FEATURES))

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    async def process(
        self, feature_key: str, request: GenerationRequest
    ) -> GenerationResponse:
        handler = {
            "banana-pro-edit": self._process_edit,
            "banana-pro-t2i": self._process_t2i,
            "banana-pro-dual": self._process_dual,
        }.get(feature_key)

        if handler is None:
            return await super().process(feature_key, request)

        try:
            return await handler(request)
        except ValidationError:
            raise
        except Exception as e:
            logger.error("处理失败 [%s]: %s", feature_key, e)
            return GenerationResponse(success=False, error=str(e))

    # ------------------------------------------------------------------
    # 香蕉Pro图像编辑
    # ------------------------------------------------------------------

    async def _process_edit(
        self, request: GenerationRequest
    ) -> GenerationResponse:
        req = self._cast_request(request, BananaEditRequest)
        config = self._build_engine_config(req)
        client = self._resolve_request_client(req)

        if not req.images:
            raise ValidationError(message="图像编辑需要提供一张参考图片")

        images = self.preprocess_images(req.images[:1])

        prompt = self._prompt_engine.render(
            "super_ai/banana_pro_edit.j2",
            edit_instruction=req.edit_instruction,
            resolution_level=req.resolution_level,
            style=req.style,
            resolution=req.resolution,
            region=req.region,
        )

        if req.resolution_level in {"1K", "2K", "4K"}:
            if config is None:
                config = {}
            config.setdefault("resolution", req.resolution_level)

        result = await client.generate(prompt, images, config=config)
        return self.postprocess_result(result)

    # ------------------------------------------------------------------
    # 香蕉Pro文生图
    # ------------------------------------------------------------------

    async def _process_t2i(
        self, request: GenerationRequest
    ) -> GenerationResponse:
        req = self._cast_request(request, BananaTextToImageRequest)
        config = self._build_engine_config(req)
        client = self._resolve_request_client(req)

        prompt = self._prompt_engine.render(
            "super_ai/banana_pro_t2i.j2",
            description=req.description,
            aspect_ratio=req.aspect_ratio,
            style_preset=req.style_preset,
            style=req.style,
            resolution=req.resolution,
        )

        result = await client.generate(prompt, config=config)
        return self.postprocess_result(result)

    # ------------------------------------------------------------------
    # 香蕉Pro双图模式
    # ------------------------------------------------------------------

    async def _process_dual(
        self, request: GenerationRequest
    ) -> GenerationResponse:
        req = self._cast_request(request, BananaDualImageRequest)
        config = self._build_engine_config(req)
        client = self._resolve_request_client(req)

        if len(req.images) < 2:
            raise ValidationError(message="双图模式需要提供两张参考图片")

        images = self.preprocess_images(req.images[:2])

        prompt = self._prompt_engine.render(
            "super_ai/banana_pro_dual.j2",
            blend_instruction=req.blend_instruction,
            weight_a=req.weight_a,
            weight_b=req.weight_b,
            style=req.style,
            resolution=req.resolution,
        )

        result = await client.generate(prompt, images, config=config)
        return self.postprocess_result(result)

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------

    @staticmethod
    def _cast_request(
        request: GenerationRequest, target_type: type[GenerationRequest]
    ) -> GenerationRequest:
        """将通用请求转换为具体子类型（兼容通用端点和专用端点）"""
        if isinstance(request, target_type):
            return request
        return target_type.model_validate(request.model_dump())
