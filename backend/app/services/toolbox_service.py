from __future__ import annotations

import logging

from app.clients.gemini_client import GeminiClient
from app.exceptions import ValidationError
from app.models.common import GenerationRequest, GenerationResponse
from app.models.toolbox import (
    MaterialExtractRequest,
    RemoveWatermarkRequest,
    StyleMimicRequest,
    ToolboxTextToImageRequest,
    UniversalEditRequest,
)
from app.prompts.engine import PromptEngine
from app.prompts.registry import FeatureConfig, registry
from app.services.base_service import BaseAIService

logger = logging.getLogger(__name__)

TOOLBOX_FEATURES = [
    FeatureConfig(
        feature_key="toolbox-t2i",
        name="文生图",
        category="toolbox",
        template_path="toolbox/text_to_image.j2",
        description="文字描述生成图片",
        input_type="text_only",
    ),
    FeatureConfig(
        feature_key="universal-edit",
        name="万能修改",
        category="toolbox",
        template_path="toolbox/universal_edit.j2",
        description="精准定位区域，按需修改细节",
        input_type="single_image",
        supports_mask=True,
    ),
    FeatureConfig(
        feature_key="style-mimic",
        name="图片模仿",
        category="toolbox",
        template_path="toolbox/style_mimic.j2",
        description="图像风格复刻迁移",
        input_type="multi_image",
    ),
    FeatureConfig(
        feature_key="remove-watermark",
        name="一键去水印",
        category="toolbox",
        template_path="toolbox/remove_watermark.j2",
        description="AI检测并去除图片水印",
        input_type="single_image",
    ),
    FeatureConfig(
        feature_key="material-extract",
        name="材质贴图提取",
        category="toolbox",
        template_path="toolbox/material_extract.j2",
        description="从图片中提取可复用材质纹理",
        input_type="single_image",
        supports_mask=True,
    ),
]

_REQUEST_TYPE_MAP: dict[str, type[GenerationRequest]] = {
    "toolbox-t2i": ToolboxTextToImageRequest,
    "universal-edit": UniversalEditRequest,
    "style-mimic": StyleMimicRequest,
    "remove-watermark": RemoveWatermarkRequest,
    "material-extract": MaterialExtractRequest,
}


class ToolboxService(BaseAIService):
    """AI 工具箱服务 — 文生图 / 万能修改 / 风格迁移 / 去水印 / 材质提取"""

    def __init__(self, gemini_client: GeminiClient, prompt_engine: PromptEngine):
        super().__init__(gemini_client, prompt_engine)
        for feat in TOOLBOX_FEATURES:
            registry.register(feat)
        logger.info("ToolboxService 初始化完成，已注册 %d 个功能", len(TOOLBOX_FEATURES))

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    async def process(
        self, feature_key: str, request: GenerationRequest
    ) -> GenerationResponse:
        handler = {
            "toolbox-t2i": self._process_t2i,
            "universal-edit": self._process_universal_edit,
            "style-mimic": self._process_style_mimic,
            "remove-watermark": self._process_remove_watermark,
            "material-extract": self._process_material_extract,
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
    # 文生图
    # ------------------------------------------------------------------

    async def _process_t2i(
        self, request: GenerationRequest
    ) -> GenerationResponse:
        req = self._cast_request(request, ToolboxTextToImageRequest)
        config = self._build_engine_config(req)
        client = self._resolve_request_client(req)

        prompt = self._prompt_engine.render(
            "toolbox/text_to_image.j2",
            description=req.description,
            style_hint=req.style_hint,
            aspect_ratio=req.aspect_ratio,
            style=req.style,
            resolution=req.resolution,
        )

        result = await client.generate(prompt, config=config)
        return self.postprocess_result(result)

    # ------------------------------------------------------------------
    # 万能修改
    # ------------------------------------------------------------------

    async def _process_universal_edit(
        self, request: GenerationRequest
    ) -> GenerationResponse:
        req = self._cast_request(request, UniversalEditRequest)
        config = self._build_engine_config(req)
        client = self._resolve_request_client(req)

        if not req.images:
            raise ValidationError(message="万能修改需要提供一张图片")

        # 支持可选第二张参考图（如“场景加模特”中的人物参考）。
        images = self.preprocess_images(req.images[:2])
        has_person_reference = len(images) > 1

        extra_params = {
            "edit_instruction": req.edit_instruction,
            "region_description": req.region.type if req.region else None,
            "has_person_reference": has_person_reference,
            **(req.extra_params or {}),
        }
        prompt = self._prompt_engine.render(
            "toolbox/universal_edit.j2",
            edit_instruction=req.edit_instruction,
            extra_params=extra_params,
            prompt_text=req.prompt_text or "",
            style=req.style,
            resolution=req.resolution,
            region=req.region,
        )

        result = await client.generate(prompt, images, config=config)
        return self.postprocess_result(result)

    # ------------------------------------------------------------------
    # 图片模仿 / 风格迁移
    # ------------------------------------------------------------------

    async def _process_style_mimic(
        self, request: GenerationRequest
    ) -> GenerationResponse:
        req = self._cast_request(request, StyleMimicRequest)
        config = self._build_engine_config(req)
        client = self._resolve_request_client(req)

        if len(req.images) < 2:
            raise ValidationError(message="风格迁移需要提供两张图片（目标图 + 风格参考图）")

        images = self.preprocess_images(req.images[:2])

        extra_params = {"mimic_intensity": req.mimic_intensity}
        prompt = self._prompt_engine.render(
            "toolbox/style_mimic.j2",
            extra_params=extra_params,
            style=req.style,
            resolution=req.resolution,
        )

        result = await client.generate(prompt, images, config=config)
        return self.postprocess_result(result)

    # ------------------------------------------------------------------
    # 一键去水印
    # ------------------------------------------------------------------

    async def _process_remove_watermark(
        self, request: GenerationRequest
    ) -> GenerationResponse:
        req = self._cast_request(request, RemoveWatermarkRequest)
        config = self._build_engine_config(req)
        client = self._resolve_request_client(req)

        if not req.images:
            raise ValidationError(message="去水印需要提供一张图片")

        images = self.preprocess_images(req.images[:1])

        prompt = self._prompt_engine.render(
            "toolbox/remove_watermark.j2",
            extra_params={"watermark_hint": req.watermark_hint},
            prompt_text=req.prompt_text or "",
            style=req.style,
            resolution=req.resolution,
        )

        result = await client.generate(prompt, images, config=config)
        return self.postprocess_result(result)

    # ------------------------------------------------------------------
    # 材质贴图提取
    # ------------------------------------------------------------------

    async def _process_material_extract(
        self, request: GenerationRequest
    ) -> GenerationResponse:
        req = self._cast_request(request, MaterialExtractRequest)
        config = self._build_engine_config(req)
        client = self._resolve_request_client(req)

        if not req.images and not req.prompt_text:
            raise ValidationError(
                message="材质提取需要提供至少一张图片或文字描述"
            )

        images = (
            self.preprocess_images(req.images[:1]) if req.images else []
        )
        extra_params = {"target_area": req.target_area}
        prompt = self._prompt_engine.render(
            "toolbox/material_extract.j2",
            extra_params=extra_params,
            prompt_text=req.prompt_text or "",
            style=req.style,
            resolution=req.resolution,
            region=req.region,
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
