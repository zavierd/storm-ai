from __future__ import annotations

import logging
from abc import ABC
from typing import TYPE_CHECKING

from app.clients.base_client import BaseAIClient, EngineType, GenerationResult
from app.exceptions import AppException, ContentBlockedImageError, ValidationError
from app.models.common import GenerationRequest, GenerationResponse, ImageInput
from app.services.pipeline import TwoStagePipeline
from app.utils.image_processing import (
    create_mask_from_region,
    decode_base64_image,
    encode_image_to_base64,
    fit_image_to_size,
    is_black_placeholder_image,
    resize_image,
    validate_image,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.clients.engine_manager import EngineManager

_VENICE_HARD_REGION_FEATURES = frozenset(
    {
        "partial-replace",
        "material-replace",
        "local-material-change",
        "local-lighting",
    }
)


class BaseAIService(ABC):
    """AI 服务基类 — 两阶段管线 + 多引擎"""

    def __init__(self, client: BaseAIClient, prompt_engine=None, pipeline: TwoStagePipeline | None = None):
        self._client = client
        self._gemini = client
        self._prompt_engine = prompt_engine
        self._pipeline = pipeline
        self._engine_manager: EngineManager | None = None
        self._vertex_default_account: str = "master"

    def set_pipeline(self, pipeline: TwoStagePipeline) -> None:
        self._pipeline = pipeline

    def swap_client(self, client: BaseAIClient) -> None:
        self._client = client
        self._gemini = client

    def set_engine_manager(self, engine_manager: EngineManager, vertex_default_account: str = "master") -> None:
        self._engine_manager = engine_manager
        self._vertex_default_account = vertex_default_account or "master"

    async def process(
        self, feature_key: str, request: GenerationRequest
    ) -> GenerationResponse:
        try:
            self.validate_input(request)
            images = self.preprocess_images(request.images) if request.images else []
            original_images = list(images)
            config = self._build_engine_config(request)

            if self._pipeline:
                images, config = self._prepare_hard_region_edit_inputs(
                    feature_key=feature_key,
                    request=request,
                    images=images,
                    config=config,
                )
                extra = request.extra_params or {}
                layout_strict = request.layout_strict if request.layout_strict is not None else extra.get("layout_strict", False)
                skip_translation = request.skip_translation if request.skip_translation is not None else extra.get("skip_translation", False)
                result = await self._pipeline.generate(
                    feature_key=feature_key,
                    user_prompt=request.prompt_text or "",
                    images=images or None,
                    config=config,
                    room_type=extra.get("room_type"),
                    extra_params=extra,
                    layout_strict=layout_strict,
                    skip_translation=skip_translation,
                )
            else:
                from app.prompts.unified import build_prompt
                prompt = build_prompt(
                    feature_key=feature_key,
                    user_prompt=request.prompt_text or "",
                    has_image=len(images) > 0,
                    extra_params=request.extra_params,
                )
                runtime_client = self._resolve_request_client(request)
                result = await runtime_client.generate(prompt, images=images or None, config=config)

            result = self._normalize_local_edit_output_size(
                feature_key=feature_key,
                source_images=original_images,
                result=result,
            )
            return self.postprocess_result(result)
        except ValidationError:
            raise
        except AppException:
            raise
        except Exception as e:
            logger.error("处理失败 [%s]: %s", feature_key, e)
            return GenerationResponse(success=False, error=str(e))

    def _resolve_request_client(self, request: GenerationRequest) -> BaseAIClient:
        """按请求 extra_params 选择客户端。当前仅处理 channel=vertex。"""
        if not self._engine_manager:
            return self._client

        extra = request.extra_params or {}
        channel = str(extra.get("channel", "")).strip().lower()
        if channel != "vertex":
            return self._client

        requested_account = str(extra.get("vertex_account") or "").strip()
        candidates = [requested_account, self._vertex_default_account, "master"]
        seen: set[str] = set()
        for account in candidates:
            if not account or account in seen:
                continue
            seen.add(account)
            key = f"vertex:{account}"
            if self._engine_manager.has(key):
                return self._engine_manager.get(key)

        logger.warning(
            "请求 channel=vertex 但账号不可用（request=%s, default=%s），回退默认客户端",
            requested_account or None,
            self._vertex_default_account,
        )
        return self._client

    def _build_engine_config(self, request: GenerationRequest) -> dict | None:
        extra = request.extra_params or {}
        config: dict = {}
        if "quality" in extra:
            config["quality"] = extra["quality"]
        if "model_slug" in extra:
            config["model_slug"] = extra["model_slug"]
        if "venice_edit_model" in extra:
            config["venice_edit_model"] = extra["venice_edit_model"]
        aspect_ratio = request.aspect_ratio if request.aspect_ratio and request.aspect_ratio != "default" else None
        if aspect_ratio:
            config["aspect_ratio"] = aspect_ratio

        if request.resolution:
            preset = (request.resolution.preset or "").upper() if request.resolution.preset else ""
            if preset in {"1K", "2K", "4K"}:
                config["resolution"] = preset
            if request.resolution.width and request.resolution.height:
                config["width"] = request.resolution.width
                config["height"] = request.resolution.height
        return config if config else None

    def preprocess_images(self, images: list[ImageInput]) -> list[bytes]:
        MAX_DIM = 2048
        result = []
        for img in images:
            data = decode_base64_image(img.base64_data)
            if len(data) > 500_000:
                data = resize_image(data, MAX_DIM, MAX_DIM)
            result.append(data)
        return result

    def _prepare_hard_region_edit_inputs(
        self,
        feature_key: str,
        request: GenerationRequest,
        images: list[bytes],
        config: dict | None,
    ) -> tuple[list[bytes], dict | None]:
        """区域工具启用硬约束：自动构造 mask，并提示 Venice 走 /image/multi-edit。"""
        if feature_key not in _VENICE_HARD_REGION_FEATURES or not images:
            return images, config

        # local-material-change 允许不圈选：若有第 2 张参考材质图，走 [base, ref] 的 multi-edit。
        if feature_key == "local-material-change" and len(images) > 1 and not request.region:
            extra = request.extra_params or {}
            channel = str(extra.get("channel", "")).strip().lower()
            is_venice_runtime = (
                self._client.engine_type == EngineType.VENICE and channel != "vertex"
            )
            if request.extra_params is None:
                request.extra_params = {}
            updated_config = dict(config or {})
            if is_venice_runtime:
                updated_config["venice_use_multi_edit"] = True
                request.extra_params["_image_order"] = "ref_base"
                # Venice two-image multi-edit 对顺序敏感，使用 [ref, base]。
                logger.info("local-material-change 无圈选（Venice），使用顺序: [ref, base]")
                return [images[1], images[0]], updated_config
            request.extra_params["_image_order"] = "base_ref"
            # Gemini/Vertex 路径保持自然顺序 [base, ref]，避免构图与比例漂移。
            logger.info("local-material-change 无圈选（Gemini/Vertex），使用顺序: [base, ref]")
            return images, config
        if not request.region:
            return images, config

        try:
            _, width, height = validate_image(images[0])
            mask_png = create_mask_from_region((width, height), request.region)
            updated_images = [images[0], mask_png]
            if feature_key == "local-material-change" and len(images) > 1:
                # local-material-change 支持第 2 张材质参考图，作为 multi-edit 第 3 张输入。
                updated_images.append(images[1])
            updated_config = dict(config or {})
            extra = request.extra_params or {}
            channel = str(extra.get("channel", "")).strip().lower()
            is_venice_runtime = (
                self._client.engine_type == EngineType.VENICE and channel != "vertex"
            )
            if is_venice_runtime:
                updated_config["venice_use_multi_edit"] = True
            return updated_images, updated_config
        except Exception as e:
            logger.warning(
                "区域遮罩构建失败 [%s]，回退普通图生图: %s",
                feature_key,
                e,
            )
            return images, config

    def postprocess_result(self, result: GenerationResult) -> GenerationResponse:
        if result.images:
            blocked_count = sum(1 for img in result.images if is_black_placeholder_image(img))
            if blocked_count == len(result.images):
                raise ContentBlockedImageError(
                    message="生成结果触发内容安全策略，请调整提示词后重试",
                    detail={
                        "hint": "请避免敏感词或歧义年龄描述，可改为“成年女性/成人人物/物体替换”等更明确表达。",
                        "blocked_images": blocked_count,
                    },
                )
            if blocked_count > 0:
                logger.warning("检测到占位黑图，已忽略 %d 张", blocked_count)
                result.images = [img for img in result.images if not is_black_placeholder_image(img)]

        encoded = [encode_image_to_base64(img) for img in result.images]
        return GenerationResponse(
            success=True,
            images=encoded,
            image_urls=result.image_urls if result.image_urls else None,
            texts=result.texts if result.texts else None,
            usage=result.usage if result.usage else None,
        )

    def _normalize_local_edit_output_size(
        self,
        feature_key: str,
        source_images: list[bytes],
        result: GenerationResult,
    ) -> GenerationResult:
        """
        局部编辑结果对齐回原图尺寸，避免 multi-edit 输出比例漂移导致前端观感异常。
        """
        if (
            feature_key not in _VENICE_HARD_REGION_FEATURES
            or not source_images
            or not result.images
        ):
            return result

        try:
            _, target_w, target_h = validate_image(source_images[0])
        except Exception:
            return result

        normalized: list[bytes] = []
        resized_count = 0
        for out in result.images:
            try:
                _, w, h = validate_image(out)
                if (w, h) != (target_w, target_h):
                    out = fit_image_to_size(out, (target_w, target_h))
                    resized_count += 1
            except Exception:
                # 无法识别时保持原样，不阻断主流程
                pass
            normalized.append(out)

        if resized_count > 0:
            logger.info(
                "局部编辑输出已尺寸对齐: %d 张 -> %dx%d",
                resized_count,
                target_w,
                target_h,
            )
        result.images = normalized
        return result

    def validate_input(self, request: GenerationRequest) -> None:
        if not request.images and not request.prompt_text:
            raise ValidationError(message="请上传图片或输入提示词")

    def build_prompt(self, feature_key: str, request: GenerationRequest) -> str:
        from app.prompts.unified import build_prompt
        return build_prompt(
            feature_key=feature_key,
            user_prompt=request.prompt_text or "",
            has_image=len(request.images) > 0,
            extra_params=request.extra_params,
        )
