from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

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


@dataclass
class VertexConfig:
    account: str
    project_id: str
    location: str = "us-central1"
    model_name: str = "gemini-3.1-flash-image-preview"
    credentials_path: str | None = None


class VertexClient(BaseAIClient):
    """Vertex AI 客户端（google-genai Vertex 模式）"""

    engine_type = EngineType.VERTEX

    def __init__(self, config: VertexConfig):
        self._config = config
        self._client = self._build_client(config)
        logger.info(
            "VertexClient 初始化完成，account=%s project=%s location=%s model=%s",
            config.account,
            config.project_id,
            config.location,
            config.model_name,
        )

    def _build_client(self, config: VertexConfig):
        credentials = None
        if config.credentials_path:
            from google.oauth2 import service_account

            credentials = service_account.Credentials.from_service_account_file(
                config.credentials_path,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )

        kwargs = {
            "vertexai": True,
            "project": config.project_id,
            "location": config.location,
        }

        if credentials:
            kwargs["credentials"] = credentials

        try:
            return genai.Client(**kwargs)
        except TypeError as exc:
            # 多账号场景下，禁止通过进程级环境变量切换凭证，避免账号串用。
            if credentials:
                raise RuntimeError(
                    "当前 google-genai 版本不支持显式 credentials 参数。"
                    "请升级 google-genai，或改用 ADC（不传 credentials_path）。"
                ) from exc
            kwargs.pop("credentials", None)
            return genai.Client(**kwargs)

    def _resolve_model(self, config: dict | None = None) -> str:
        if not config:
            return self._config.model_name
        return (
            config.get("model")
            or config.get("model_name")
            or config.get("model_slug")
            or self._config.model_name
        )

    @staticmethod
    def _detect_mime_type(data: bytes) -> str:
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if data.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if data.startswith(b"RIFF") and len(data) > 12 and data[8:12] == b"WEBP":
            return "image/webp"
        return "image/png"

    def _build_contents(
        self, prompt: str, images: list[bytes] | None = None
    ) -> list:
        contents: list = []
        if images:
            for img in images:
                contents.append(
                    types.Part.from_bytes(data=img, mime_type=self._detect_mime_type(img))
                )
        contents.append(prompt)
        return contents

    def _parse_response(self, response) -> GenerationResult:
        result = GenerationResult(raw_response={})

        if not getattr(response, "candidates", None):
            logger.warning("Vertex 返回空候选结果")
            result.usage = {
                "channel": "vertex",
                "account": self._config.account,
                "model": self._config.model_name,
            }
            return result

        for candidate in response.candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None) or []
            for part in parts:
                if getattr(part, "inline_data", None):
                    result.images.append(part.inline_data.data)
                elif getattr(part, "text", None):
                    result.texts.append(part.text)

        usage = {
            "channel": "vertex",
            "account": self._config.account,
            "model": self._config.model_name,
        }
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            usage.update(
                {
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
            )
        result.usage = usage
        return result

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        reraise=True,
    )
    async def generate(
        self,
        prompt: str,
        images: list[bytes] | None = None,
        image_urls: list[str] | None = None,
        config: dict | None = None,
    ) -> GenerationResult:
        contents = self._build_contents(prompt, images)
        model = self._resolve_model(config)

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
                model=model,
                contents=contents,
                config=gen_config,
            )
            result = self._parse_response(response)
            if result.usage:
                result.usage["model"] = model
            return result
        except (ConnectionError, TimeoutError):
            raise
        except Exception as e:
            logger.error("Vertex API 调用异常: %s", e)
            raise GeminiAPIError(
                message=f"Vertex API 调用失败: {e}",
                detail=str(e),
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
        contents = self._build_contents(prompt, images)
        gen_config = types.GenerateContentConfig(response_modalities=["Text"])

        try:
            response = await asyncio.to_thread(
                self._client.models.generate_content,
                model=self._config.model_name,
                contents=contents,
                config=gen_config,
            )
            result = self._parse_response(response)
            return "\n".join(result.texts) if result.texts else ""
        except (ConnectionError, TimeoutError):
            raise
        except Exception as e:
            logger.error("Vertex 文本生成异常: %s", e)
            raise GeminiAPIError(
                message=f"Vertex 文本生成失败: {e}",
                detail=str(e),
            ) from e

    async def list_models(self) -> list[dict]:
        return [
            {
                "slug": self._config.model_name,
                "name": f"Vertex ({self._config.account})",
                "engine": "vertex",
                "account": self._config.account,
                "project_id": self._config.project_id,
                "location": self._config.location,
            }
        ]
