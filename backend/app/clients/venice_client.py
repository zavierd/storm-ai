from __future__ import annotations

import base64
import logging
from urllib.parse import unquote

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.clients.base_client import EngineType, GenerationResult
from app.exceptions import GeminiAPIError
from app.clients.newapi_client import NewAPIClient
from app.utils.image_processing import invert_mask_image, score_masked_edit_result

logger = logging.getLogger(__name__)

_VENICE_NATIVE_PASSTHROUGH = frozenset({
    "negative_prompt", "seed", "steps", "cfg_scale", "style_preset",
    "width", "height", "safe_mode", "format", "hide_watermark",
    "return_binary", "variants", "resolution",
})


class VeniceClient(NewAPIClient):
    """Venice AI 客户端

    - 文生图优先走 Venice 原生端点 POST /image/generate
    - 图生图 / 文本推理沿用父类 NewAPIClient（OpenAI 兼容协议）
    """

    engine_type = EngineType.VENICE

    def _extract_b64_from_data_url(self, url: str) -> str | None:
        if not url.startswith("data:"):
            return None
        try:
            _, b64 = url.split(",", 1)
            return b64
        except Exception:
            return None

    async def _to_base64_image(self, images: list[bytes] | None, image_urls: list[str] | None) -> str | None:
        if images:
            return base64.b64encode(images[0]).decode()
        if image_urls:
            first = image_urls[0]
            data_b64 = self._extract_b64_from_data_url(first)
            if data_b64:
                return data_b64
            try:
                resp = await self._http.get(first)
                resp.raise_for_status()
                return base64.b64encode(resp.content).decode()
            except Exception as e:
                logger.warning("[Venice] 下载参考图失败: %s", e)
        return None

    async def _to_base64_images(
        self,
        images: list[bytes] | None,
        image_urls: list[str] | None,
        max_items: int = 3,
    ) -> list[str]:
        """将输入图片统一转为 base64 列表（最多 max_items 张）。"""
        encoded: list[str] = []
        for img in images or []:
            encoded.append(base64.b64encode(img).decode())
            if len(encoded) >= max_items:
                return encoded

        for url in image_urls or []:
            data_b64 = self._extract_b64_from_data_url(url)
            if data_b64:
                encoded.append(data_b64)
            else:
                try:
                    resp = await self._http.get(url)
                    resp.raise_for_status()
                    encoded.append(base64.b64encode(resp.content).decode())
                except Exception as e:
                    logger.warning("[Venice] 下载参考图失败: %s", e)
            if len(encoded) >= max_items:
                return encoded

        return encoded

    async def _generate_via_venice_native(
        self,
        prompt: str,
        model: str,
        config: dict | None = None,
    ) -> GenerationResult | None:
        """调用 Venice 原生 POST /image/generate，成功返回 GenerationResult，失败返回 None"""
        body: dict = {"model": model, "prompt": prompt}

        if config:
            ar = config.get("aspect_ratio")
            if ar and ar not in ("default", ""):
                body["aspect_ratio"] = ar

            for key in _VENICE_NATIVE_PASSTHROUGH:
                if key in config:
                    body[key] = config[key]

        logger.info(
            "[Venice] POST /image/generate model=%s prompt=%s...",
            model, prompt[:80],
        )

        try:
            resp = await self._http.post("/image/generate", json=body)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning(
                "[Venice] /image/generate 失败，将 fallback 到 OpenAI 兼容端点: %s", e,
            )
            return None

        raw_images = data.get("images", [])
        if not raw_images:
            logger.warning("[Venice] /image/generate 返回空 images，将 fallback")
            return None

        result = GenerationResult(raw_response=data)
        for b64_str in raw_images:
            try:
                result.images.append(base64.b64decode(b64_str))
            except Exception:
                logger.warning("[Venice] base64 解码失败，跳过该条目")

        if not result.images:
            logger.warning("[Venice] /image/generate 解码后无有效图片，将 fallback")
            return None

        timing = data.get("timing", {})
        result.usage = {
            "model": model,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "inference_duration_ms": timing.get("total", 0),
        }
        logger.info(
            "[Venice] /image/generate 成功，获得 %d 张图片 (%.1fs)",
            len(result.images),
            timing.get("total", 0) / 1000 if timing.get("total") else 0,
        )
        return result

    async def _edit_via_venice_native(
        self,
        prompt: str,
        images: list[bytes] | None,
        image_urls: list[str] | None,
        config: dict | None = None,
    ) -> GenerationResult | None:
        """调用 Venice 原生 POST /image/edit（图生图）。"""
        b64_image = await self._to_base64_image(images, image_urls)
        if not b64_image:
            logger.warning("[Venice] /image/edit 缺少可用参考图")
            return None

        body = {"prompt": prompt, "image": b64_image}
        edit_model = (config or {}).get("venice_edit_model")
        if edit_model:
            body["modelId"] = edit_model
        logger.info("[Venice] POST /image/edit prompt=%s...", prompt[:80])

        try:
            resp = await self._http.post("/image/edit", json=body)
            resp.raise_for_status()
        except Exception as e:
            logger.warning("[Venice] /image/edit 失败: %s", e)
            return None

        result = GenerationResult(raw_response={})
        ctype = (resp.headers.get("content-type") or "").lower()

        # Venice /image/edit 常见返回是二进制图片
        if ctype.startswith("image/"):
            result.images.append(resp.content)
            result.usage = {"model": "venice-image-edit", "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            logger.info("[Venice] /image/edit 成功（二进制图片）")
            return result

        # 兼容 JSON 返回（若后续接口形态变化）
        try:
            data = resp.json()
            result.raw_response = data
            for b64_str in data.get("images", []):
                try:
                    result.images.append(base64.b64decode(unquote(b64_str)))
                except Exception:
                    logger.warning("[Venice] /image/edit JSON 图片解码失败，跳过")
            if result.images:
                result.usage = {"model": "venice-image-edit", "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
                logger.info("[Venice] /image/edit 成功（JSON图片）")
                return result
        except Exception:
            logger.warning("[Venice] /image/edit 返回非 JSON 且非图片类型: %s", ctype)

        return None

    async def _multi_edit_via_venice_native(
        self,
        prompt: str,
        images: list[bytes] | None,
        image_urls: list[str] | None,
        config: dict | None = None,
    ) -> GenerationResult | None:
        """调用 Venice 原生 POST /image/multi-edit（最多 3 图，常用 base+mask）。"""
        async def _request_multi_edit(b64_images: list[str], tag: str) -> GenerationResult | None:
            body = {"prompt": prompt, "images": b64_images}
            edit_model = (config or {}).get("venice_edit_model")
            if edit_model:
                body["modelId"] = edit_model
            logger.info(
                "[Venice] POST /image/multi-edit[%s] modelId=%s images=%d prompt=%s...",
                tag,
                edit_model or "default",
                len(b64_images),
                prompt[:80],
            )
            try:
                resp = await self._http.post("/image/multi-edit", json=body)
                resp.raise_for_status()
            except Exception as e:
                logger.warning("[Venice] /image/multi-edit[%s] 失败: %s", tag, e)
                return None

            result = GenerationResult(raw_response={})
            ctype = (resp.headers.get("content-type") or "").lower()
            if ctype.startswith("image/"):
                result.images.append(resp.content)
                result.usage = {"model": "venice-image-multi-edit", "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
                return result
            try:
                data = resp.json()
                result.raw_response = data
                for b64_str in data.get("images", []):
                    try:
                        result.images.append(base64.b64decode(unquote(b64_str)))
                    except Exception:
                        logger.warning("[Venice] /image/multi-edit[%s] JSON 图片解码失败，跳过", tag)
                if result.images:
                    result.usage = {"model": "venice-image-multi-edit", "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
                    return result
            except Exception:
                logger.warning("[Venice] /image/multi-edit[%s] 返回非 JSON 且非图片类型: %s", tag, ctype)
            return None

        # 区域三图模式：做顺序/遮罩候选重试，自动选最优结果
        if images and len(images) >= 3 and not image_urls:
            base_img, mask_img, ref_img = images[0], images[1], images[2]
            candidates: list[tuple[str, list[bytes], bytes]] = [
                ("base-mask-ref", [base_img, mask_img, ref_img], mask_img),
            ]
            try:
                inv_mask = invert_mask_image(mask_img)
                candidates.append(("base-invertMask-ref", [base_img, inv_mask, ref_img], inv_mask))
            except Exception:
                inv_mask = None
            # 备用顺序（实测某些场景更稳）
            candidates.append(("ref-mask-base", [ref_img, mask_img, base_img], mask_img))

            best_result: GenerationResult | None = None
            best_score = float("-inf")
            best_tag = ""
            for idx, (tag, raw_imgs, score_mask) in enumerate(candidates):
                b64_images = [base64.b64encode(x).decode() for x in raw_imgs]
                result = await _request_multi_edit(b64_images, tag)
                if result is None or not result.images:
                    continue
                metrics = score_masked_edit_result(
                    base_image=base_img,
                    mask_image=score_mask,
                    output_image=result.images[0],
                )
                score = metrics["score"]
                logger.info(
                    "[Venice] /image/multi-edit[%s] 评分 score=%.2f inside=%.2f outside=%.2f ratio=%.2f aspect=%.4f",
                    tag,
                    score,
                    metrics["inside_mean_diff"],
                    metrics["outside_mean_diff"],
                    metrics["inside_outside_ratio"],
                    metrics["aspect_delta"],
                )
                if score > best_score:
                    best_score = score
                    best_result = result
                    best_tag = tag

                # 首个候选质量已足够时提前返回，降低延迟
                if (
                    idx == 0
                    and metrics["outside_mean_diff"] <= 10.0
                    and metrics["inside_outside_ratio"] >= 1.45
                    and metrics["aspect_delta"] <= 0.18
                ):
                    logger.info("[Venice] /image/multi-edit[%s] 质量达标，提前采用", tag)
                    return result

            if best_result is not None:
                logger.info("[Venice] /image/multi-edit 采用最优候选: %s (score=%.2f)", best_tag, best_score)
                return best_result

            return None

        # 普通两图/URL模式：单次调用
        b64_images = await self._to_base64_images(images, image_urls, max_items=3)
        if len(b64_images) < 2:
            logger.warning("[Venice] /image/multi-edit 至少需要两张图片（base + mask/overlay）")
            return None
        return await _request_multi_edit(b64_images, "default")

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
        requested_resolution = str((config or {}).get("resolution") or "").upper()
        use_multi_edit = bool((config or {}).get("venice_use_multi_edit"))

        if has_input_images:
            # 区域硬约束工具优先使用 /image/multi-edit（base + mask）
            if use_multi_edit:
                result = await self._multi_edit_via_venice_native(prompt, images, image_urls, config)
                if result is not None:
                    return result
                logger.info("[Venice] /image/multi-edit 不可用，回退 /image/edit")

            # 图生图优先使用 Venice 原生 /image/edit，避免 nano-banana-2 在 chat/completions 上 404
            result = await self._edit_via_venice_native(prompt, images, image_urls, config)
            if result is not None:
                return result
            logger.info("[Venice] /image/edit 不可用，fallback 到 OpenAI 兼容 /chat/completions")
        else:
            result = await self._generate_via_venice_native(prompt, model, config)
            if result is not None:
                return result
            # /images/generations 不支持 resolution=2K/4K，若降级会静默回落成 1024，直接报错更符合用户预期
            if requested_resolution in {"2K", "4K"}:
                raise GeminiAPIError(
                    message=f"Venice 原生高分辨率通道暂不可用，无法保证输出 {requested_resolution}，请重试",
                    detail="/image/generate failed and /images/generations cannot guarantee 2K/4K output",
                )
            logger.info("[Venice] 原生端点不可用，fallback 到 OpenAI 兼容 /images/generations")

        return await super().generate(prompt, images, image_urls, config)
