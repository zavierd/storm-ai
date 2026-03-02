from __future__ import annotations

import asyncio
import base64
import logging
import re
from dataclasses import dataclass

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.clients.base_client import BaseAIClient, EngineType, GenerationResult
from app.exceptions import GeminiAPIError

logger = logging.getLogger(__name__)

API_BASE = "https://graphql.swiftask.ai"

QUALITY_MODELS: dict[str, dict] = {
    "fast": {
        "slug": "imagen_4_fast",
        "name": "Imagen-4 Fast",
        "cost_per_image": 16666,
        "supports_image_input": False,
    },
    "basic": {
        "slug": "gemini---nano-banana",
        "name": "Nano Banana",
        "cost_per_image": 17000,
        "supports_image_input": True,
    },
    "standard": {
        "slug": "imagen_4",
        "name": "Imagen-4",
        "cost_per_image": 33333,
        "supports_image_input": False,
    },
    "hd": {
        "slug": "imagen_4_ultra",
        "name": "Imagen-4 Ultra",
        "cost_per_image": 50000,
        "supports_image_input": False,
    },
    "pro": {
        "slug": "nano_banana_pro",
        "name": "Nano Banana Pro",
        "cost_per_image": 76924,
        "supports_image_input": True,
        "max_resolution": "4K",
    },
    "reasoning": {
        "slug": "gemini-3-pro",
        "name": "Gemini 3 Pro",
        "cost_per_image": 0,
        "supports_image_input": True,
        "is_text_model": True,
    },
}

DEFAULT_MODEL_SLUG = "nano_banana_pro"


@dataclass
class SwiftaskConfig:
    api_key: str
    default_model: str = DEFAULT_MODEL_SLUG
    timeout: int = 120


class SwiftaskClient(BaseAIClient):
    """Swiftask AI 中转站客户端，支持多模型切换"""

    engine_type = EngineType.SWIFTASK

    def __init__(self, config: SwiftaskConfig):
        self._config = config
        self._http = httpx.AsyncClient(
            base_url=API_BASE,
            timeout=config.timeout,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {config.api_key}",
            },
        )
        logger.info(
            "SwiftaskClient 初始化完成，默认模型: %s",
            config.default_model,
        )

    async def _upload_image(self, image_data: bytes, filename: str = "upload.png") -> str:
        """通过 S3 签名 URL 上传图片，返回公开 URL"""
        # widget 端点需要 clientToken 作为查询参数
        async with httpx.AsyncClient(base_url=API_BASE, timeout=60) as client:
            sign_resp = await client.get(
                "/widget/get-signed-url",
                params={
                    "fileName": filename,
                    "clientToken": self._config.api_key,
                },
            )
            sign_resp.raise_for_status()
            sign_data = sign_resp.json()

            # Swiftask 返回 url (bare S3 path, 支持 PUT) 和 fileUrl (签名 GET, 仅供下载)
            upload_url = sign_data.get("url")
            if not upload_url:
                logger.error("签名URL响应缺少url字段: %s", list(sign_data.keys()))
                raise GeminiAPIError(message="图片上传服务不可用", detail=str(sign_data))

            mime = "image/jpeg" if filename.endswith((".jpg", ".jpeg")) else "image/png"
            put_resp = await client.put(
                upload_url,
                content=image_data,
                headers={"Content-Type": mime},
            )
            put_resp.raise_for_status()
            logger.info("图片上传成功: %s (%dKB)", upload_url[:60], len(image_data) // 1024)

        return upload_url

    def _resolve_model_slug(self, config: dict | None) -> str:
        if not config:
            return self._config.default_model
        quality = config.get("quality")
        if quality and quality in QUALITY_MODELS:
            return QUALITY_MODELS[quality]["slug"]
        return config.get("model_slug", self._config.default_model)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.ReadTimeout)),
        reraise=True,
    )
    async def generate(
        self,
        prompt: str,
        images: list[bytes] | None = None,
        image_urls: list[str] | None = None,
        config: dict | None = None,
    ) -> GenerationResult:
        model_slug = self._resolve_model_slug(config)

        # Imagen 系列不支持图生图，有图时自动降级到 nano_banana_pro
        if (images or image_urls) and config:
            quality = config.get("quality")
            if quality and quality in QUALITY_MODELS and not QUALITY_MODELS[quality]["supports_image_input"]:
                logger.info(
                    "Imagen 系列不支持图生图，已自动降级到 nano_banana_pro (quality=%s)",
                    quality,
                )
                model_slug = "nano_banana_pro"

        files_payload: list[dict] = []

        if image_urls:
            for i, url in enumerate(image_urls):
                files_payload.append({"url": url, "name": f"ref_{i}.jpg", "type": "image/jpeg", "size": 0})

        if images:
            for i, img_data in enumerate(images):
                try:
                    url = await self._upload_image(img_data, f"input_{i}.jpg")
                    files_payload.append({"url": url, "name": f"input_{i}.jpg", "type": "image/jpeg", "size": len(img_data)})
                except Exception as upload_err:
                    logger.warning("图片上传失败，降级为 base64 data URL: %s", upload_err)
                    b64 = base64.b64encode(img_data).decode()
                    files_payload.append({
                        "url": f"data:image/png;base64,{b64}",
                        "type": "image/png",
                    })

        body: dict = {
            "input": prompt,
            "files": files_payload,
        }

        # 有文件时使用 ADVANCED 模式深度分析图片
        if files_payload:
            body["documentAnalysisMode"] = "ADVANCED"

        session_id = (config or {}).get("session_id")
        if session_id:
            body["sessionId"] = session_id

        logger.info("[Swiftask] POST /api/ai/%s files=%d prompt=%s...", model_slug, len(files_payload), body["input"][:60])

        try:
            resp = await self._http.post(f"/api/ai/{model_slug}", json=body)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            logger.error("Swiftask API HTTP 错误 [%s]: %s %s", model_slug, e.response.status_code, e.response.text[:200])
            raise GeminiAPIError(
                message=f"Swiftask API 错误: {e.response.status_code}",
                detail=e.response.text[:500],
            ) from e
        except Exception as e:
            logger.error("Swiftask API 调用异常 [%s]: %s", model_slug, e)
            raise GeminiAPIError(
                message=f"Swiftask API 调用失败: {e}",
                detail=str(e),
            ) from e

        if data.get("isBotError"):
            raise GeminiAPIError(
                message=f"模型返回错误: {data.get('text', 'unknown')}",
                detail=str(data),
            )

        result = GenerationResult(raw_response=data)

        if data.get("text"):
            result.texts.append(data["text"])

        for f in data.get("files", []):
            url = f.get("url")
            if url:
                result.image_urls.append(url)

        # 部分模型（如 nano-banana）将图片 URL 嵌入 markdown 文本
        if not result.image_urls and result.texts:
            md_urls = re.findall(r'!\[.*?\]\((https?://\S+)\)', result.texts[0])
            result.image_urls.extend(md_urls)

        result.usage = {
            "model": model_slug,
            "session_id": data.get("sessionId"),
            "total_usage": data.get("totalBotUsage"),
        }

        return result

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.ReadTimeout)),
        reraise=True,
    )
    async def generate_text(
        self,
        prompt: str,
        images: list[bytes] | None = None,
        image_urls: list[str] | None = None,
    ) -> str:
        result = await self.generate(
            prompt,
            images=images,
            image_urls=image_urls,
            config={"model_slug": "gemini-3-pro"},
        )
        return "\n".join(result.texts) if result.texts else ""

    async def list_models(self) -> list[dict]:
        return [
            {
                "quality": k,
                "slug": v["slug"],
                "name": v["name"],
                "cost_per_image": v["cost_per_image"],
                "supports_image_input": v["supports_image_input"],
            }
            for k, v in QUALITY_MODELS.items()
        ]

    async def close(self):
        await self._http.aclose()
