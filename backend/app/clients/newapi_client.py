from __future__ import annotations

import base64
import logging
import re
from dataclasses import dataclass

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.clients.base_client import BaseAIClient, EngineType, GenerationResult
from app.exceptions import GeminiAPIError

logger = logging.getLogger(__name__)


@dataclass
class NewAPIConfig:
    api_key: str
    base_url: str = "https://zapi.aicc0.com/v1"
    default_model: str = "gpt-4o"
    timeout: int = 120


class NewAPIClient(BaseAIClient):
    """NewAPI 分发站客户端，兼容 OpenAI Chat Completions 协议"""

    engine_type = EngineType.NEWAPI

    def __init__(self, config: NewAPIConfig):
        self._config = config
        self._http = httpx.AsyncClient(
            base_url=config.base_url.rstrip("/"),
            timeout=config.timeout,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {config.api_key}",
            },
        )
        logger.info(
            "NewAPIClient 初始化完成，base_url=%s, 默认模型: %s",
            config.base_url,
            config.default_model,
        )

    def _resolve_model(self, config: dict | None) -> str:
        if config and config.get("model"):
            return config["model"]
        return self._config.default_model

    def _build_image_content(
        self,
        image_data: bytes | None = None,
        image_url: str | None = None,
    ) -> dict:
        """构建 OpenAI 多模态 image_url content 块"""
        if image_url:
            if image_url.startswith("data:"):
                return {"type": "image_url", "image_url": {"url": image_url}}
            return {"type": "image_url", "image_url": {"url": image_url}}
        if image_data:
            b64 = base64.b64encode(image_data).decode()
            return {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64}"},
            }
        raise ValueError("image_data 或 image_url 至少提供一个")

    def _build_messages(
        self,
        prompt: str,
        images: list[bytes] | None = None,
        image_urls: list[str] | None = None,
        system_prompt: str | None = None,
    ) -> list[dict]:
        messages: list[dict] = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        has_images = bool(images) or bool(image_urls)

        if not has_images:
            messages.append({"role": "user", "content": prompt})
            return messages

        content_parts: list[dict] = [{"type": "text", "text": prompt}]

        if image_urls:
            for url in image_urls:
                content_parts.append(self._build_image_content(image_url=url))

        if images:
            for img_data in images:
                content_parts.append(self._build_image_content(image_data=img_data))

        messages.append({"role": "user", "content": content_parts})
        return messages

    def _absolute_url(self, url: str) -> str:
        """将相对路径（如 /v1/files/image/...）补全为绝对 URL"""
        if url.startswith(("http://", "https://", "data:")):
            return url
        base = self._config.base_url.rstrip("/")
        if base.endswith("/v1"):
            base = base[:-3]
        return base.rstrip("/") + "/" + url.lstrip("/")

    async def _generate_via_images_api(
        self,
        prompt: str,
        model: str,
        config: dict | None = None,
    ) -> GenerationResult | None:
        """调用 POST /images/generations，成功返回 GenerationResult，失败返回 None"""
        body: dict = {"model": model, "prompt": prompt, "n": 1}
        if config:
            if "size" in config:
                body["size"] = config["size"]
            if "response_format" in config:
                body["response_format"] = config["response_format"]

        logger.info("[NewAPI] POST /images/generations model=%s prompt=%s...", model, prompt[:60])

        try:
            resp = await self._http.post("/images/generations", json=body)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning("[NewAPI] /images/generations 失败，将 fallback 到 chat/completions: %s", e)
            return None

        items = data.get("data", [])
        if not items:
            logger.warning("[NewAPI] /images/generations 返回空 data，将 fallback")
            return None

        result = GenerationResult(raw_response=data)
        for item in items:
            url = item.get("url")
            b64 = item.get("b64_json")
            if url:
                result.image_urls.append(self._absolute_url(url))
            elif b64:
                try:
                    result.images.append(base64.b64decode(b64))
                except Exception:
                    logger.warning("[NewAPI] b64_json 解码失败，跳过该条目")

        if not result.image_urls and not result.images:
            logger.warning("[NewAPI] /images/generations 解析后无有效图片，将 fallback")
            return None

        result.usage = {"model": model, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        logger.info("[NewAPI] /images/generations 成功，获得 %d 张图片", len(result.image_urls) + len(result.images))
        return result

    async def _generate_via_chat(
        self,
        prompt: str,
        model: str,
        images: list[bytes] | None = None,
        image_urls: list[str] | None = None,
        config: dict | None = None,
    ) -> GenerationResult:
        """原有 chat/completions 逻辑"""
        system_prompt = (config or {}).get("system_prompt")
        messages = self._build_messages(prompt, images, image_urls, system_prompt)

        body: dict = {"model": model, "messages": messages}
        if config:
            for k in ("temperature", "max_tokens", "top_p"):
                if k in config:
                    body[k] = config[k]

        logger.info(
            "[NewAPI] POST /chat/completions model=%s images=%d prompt=%s...",
            model, len(images or []) + len(image_urls or []), prompt[:60],
        )

        try:
            resp = await self._http.post("/chat/completions", json=body)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            logger.error("NewAPI HTTP 错误 [%s]: %s %s", model, e.response.status_code, e.response.text[:200])
            raise GeminiAPIError(message=f"NewAPI 错误: {e.response.status_code}", detail=e.response.text[:500]) from e
        except Exception as e:
            logger.error("NewAPI 调用异常 [%s]: %s", model, e)
            raise GeminiAPIError(message=f"NewAPI 调用失败: {e}", detail=str(e)) from e

        result = GenerationResult(raw_response=data)

        for choice in data.get("choices", []):
            text = choice.get("message", {}).get("content", "")
            if text:
                result.texts.append(text)

        if result.texts:
            for text in result.texts:
                urls = re.findall(r'https?://\S+\.(?:png|jpg|jpeg|gif|webp)', text)
                result.image_urls.extend(urls)
                md_urls = re.findall(r'!\[.*?\]\((https?://\S+)\)', text)
                for u in md_urls:
                    if u not in result.image_urls:
                        result.image_urls.append(u)

        usage_data = data.get("usage", {})
        result.usage = {
            "model": model,
            "prompt_tokens": usage_data.get("prompt_tokens", 0),
            "completion_tokens": usage_data.get("completion_tokens", 0),
            "total_tokens": usage_data.get("total_tokens", 0),
        }
        return result

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
        model = self._resolve_model(config)
        has_input_images = bool(images) or bool(image_urls)

        if not has_input_images:
            result = await self._generate_via_images_api(prompt, model, config)
            if result is not None:
                return result
            logger.info("[NewAPI] /images/generations 不可用，fallback 到 chat/completions")

        return await self._generate_via_chat(prompt, model, images, image_urls, config)

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
        model = self._config.default_model
        result = await self._generate_via_chat(prompt, model, images=images, image_urls=image_urls)
        return "\n".join(result.texts) if result.texts else ""

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.ReadTimeout)),
        reraise=True,
    )
    async def list_models(self) -> list[dict]:
        try:
            resp = await self._http.get("/models")
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning("NewAPI list_models 失败，返回默认: %s", e)
            return [{"id": self._config.default_model, "object": "model"}]

        models = data.get("data", [])
        return [
            {"id": m.get("id", ""), "object": m.get("object", "model"), "owned_by": m.get("owned_by", "")}
            for m in models
        ]

    async def close(self):
        await self._http.aclose()
