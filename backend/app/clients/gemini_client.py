from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from google import genai
from google.genai import types
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.clients.base_client import BaseAIClient, EngineType, GenerationResult
from app.exceptions import GeminiAPIError

logger = logging.getLogger(__name__)


class GeminiClient(BaseAIClient):
    """Google Gemini API 直连客户端"""

    engine_type = EngineType.GEMINI_DIRECT

    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash-exp"):
        self._client = genai.Client(api_key=api_key)
        self._model_name = model_name
        logger.info("GeminiClient 初始化完成，模型: %s", model_name)

    @staticmethod
    def _detect_mime_type(data: bytes) -> str:
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if data.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if data.startswith(b"RIFF") and len(data) > 12 and data[8:12] == b"WEBP":
            return "image/webp"
        return "image/png"

    def _resolve_model(self, config: dict | None = None) -> str:
        if not config:
            return self._model_name
        return (
            config.get("model")
            or config.get("model_name")
            or config.get("model_slug")
            or self._model_name
        )

    def _build_contents(
        self, prompt: str, images: list[bytes] | None = None
    ) -> list:
        """构建请求的 contents 列表"""
        contents: list = []
        if images:
            for img in images:
                contents.append(
                    types.Part.from_bytes(data=img, mime_type=self._detect_mime_type(img))
                )
        contents.append(prompt)
        return contents

    def _parse_response(self, response) -> GenerationResult:
        """从 Gemini 响应中提取图片和文本"""
        result = GenerationResult()

        if not response.candidates:
            logger.warning("Gemini 返回空候选结果")
            return result

        for candidate in response.candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None) or []
            for part in parts:
                if getattr(part, "inline_data", None):
                    result.images.append(part.inline_data.data)
                elif getattr(part, "text", None):
                    result.texts.append(part.text)

        if hasattr(response, "usage_metadata") and response.usage_metadata:
            result.usage = {
                "prompt_tokens": getattr(
                    response.usage_metadata, "prompt_token_count", 0
                ),
                "candidates_tokens": getattr(
                    response.usage_metadata, "candidates_token_count", 0
                ),
                "total_tokens": getattr(
                    response.usage_metadata, "total_token_count", 0
                ),
            }

        return result

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        reraise=True,
    )
    async def list_models(self) -> list[dict]:
        return [{"slug": self._model_name, "name": "Gemini Direct", "engine": "gemini_direct"}]

    async def generate(
        self,
        prompt: str,
        images: list[bytes] | None = None,
        image_urls: list[str] | None = None,
        config: dict | None = None,
    ) -> GenerationResult:
        """生成内容（图片+文本混合模式）"""
        contents = self._build_contents(prompt, images)
        model_name = self._resolve_model(config)

        gen_config = types.GenerateContentConfig(
            response_modalities=["Text", "Image"],
            candidate_count=1,
        )
        runtime_config = dict(config or {})
        aspect_ratio = runtime_config.pop("aspect_ratio", None)
        resolution = runtime_config.pop("resolution", None)

        if aspect_ratio or resolution:
            image_config = types.ImageConfig()
            has_any = False
            if aspect_ratio and hasattr(image_config, "aspect_ratio"):
                setattr(image_config, "aspect_ratio", aspect_ratio)
                has_any = True
            if resolution:
                if hasattr(image_config, "image_size"):
                    setattr(image_config, "image_size", resolution)
                    has_any = True
                elif hasattr(image_config, "size"):
                    setattr(image_config, "size", resolution)
                    has_any = True
            if has_any and hasattr(gen_config, "image_config"):
                setattr(gen_config, "image_config", image_config)

        for k, v in runtime_config.items():
            if k in {"model", "model_name", "model_slug"}:
                continue
            if hasattr(gen_config, k):
                setattr(gen_config, k, v)

        try:
            response = await asyncio.to_thread(
                self._client.models.generate_content,
                model=model_name,
                contents=contents,
                config=gen_config,
            )
            return self._parse_response(response)
        except (ConnectionError, TimeoutError):
            raise
        except Exception as e:
            logger.error("Gemini API 调用异常: %s", e)
            raise GeminiAPIError(
                message=f"Gemini API 调用失败: {e}", detail=str(e)
            ) from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        reraise=True,
    )
    async def generate_text(
        self,
        prompt: str,
        images: list[bytes] | None = None,
        image_urls: list[str] | None = None,
    ) -> str:
        """纯文本生成（用于物料清单等场景）"""
        contents = self._build_contents(prompt, images)

        gen_config = types.GenerateContentConfig(
            response_modalities=["Text"],
        )

        try:
            response = await asyncio.to_thread(
                self._client.models.generate_content,
                model=self._model_name,
                contents=contents,
                config=gen_config,
            )
            result = self._parse_response(response)
            return "\n".join(result.texts) if result.texts else ""
        except (ConnectionError, TimeoutError):
            raise
        except Exception as e:
            logger.error("Gemini 文本生成异常: %s", e)
            raise GeminiAPIError(
                message=f"Gemini 文本生成失败: {e}", detail=str(e)
            ) from e
