"""
生图管线

图生图模式（有参考图）：
    直接发送：简短编辑指令 + 参考图 → 生图模型
    不经过推理模型，避免过度描述导致参考图被修改

文生图模式（无参考图）：
    Stage 1: 系统提示词 + 用户指令 → 推理模型 → 场景描述
    Stage 2: 场景描述 → 生图模型 → 效果图
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.clients.base_client import BaseAIClient, GenerationResult
from app.prompts.system_prompt_manager import system_prompt_manager

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.clients.engine_manager import EngineManager

# 文生图才用推理模型
TEXT_TO_IMAGE_META = """你是一个专业的AI图像生成提示词工程师。

用户没有上传参考图，需要从零生成一张图片。根据以下信息生成一段英文图像描述。

## 要求
- 直接输出英文提示词，不要解释或前缀
- 结构：主体 → 环境 → 材质 → 光照 → 风格 → 品质
- 长度 100-200 词
- 描述要具体可视化

## 功能规则
{system_prompt}

## 用户指令
{user_prompt}

直接输出提示词："""


class TwoStagePipeline:
    """生图管线"""

    def __init__(
        self,
        reasoning_client: BaseAIClient,
        generation_client: BaseAIClient,
        engine_manager: EngineManager | None = None,
        vertex_default_account: str = "master",
    ):
        self._reasoner = reasoning_client
        self._generator = generation_client
        self._engine_manager = engine_manager
        self._vertex_default_account = vertex_default_account or "master"

    async def generate(
        self,
        feature_key: str,
        user_prompt: str = "",
        images: list[bytes] | None = None,
        config: dict | None = None,
        room_type: str | None = None,
        extra_params: dict | None = None,
        layout_strict: bool = False,
        skip_translation: bool = False,
    ) -> GenerationResult:
        system_prompt = system_prompt_manager.get(feature_key)
        has_img = images and len(images) > 0
        reasoner, generator = self._resolve_clients(extra_params)

        # room_type 不再拼入提示词（会干扰图生图），仅在文生图时使用
        if room_type and not (images and len(images) > 0):
            user_prompt = f"Room type: {room_type}. {user_prompt}"

        if has_img:
            # ===== 图生图 =====
            # 先用推理模型把中文翻译为精准英文风格词（极简，只翻译不展开）
            # P0-2: skip_translation=true 时跳过翻译，直接使用 user_prompt
            if user_prompt and not skip_translation:
                user_prompt = await self._translate_style_keywords(reasoner, user_prompt)
                logger.info("[Pipeline][%s] 风格翻译 → %s", feature_key, user_prompt)
            prompt = self._build_image_edit_prompt(
                feature_key=feature_key,
                user_prompt=user_prompt,
                system_prompt=system_prompt,
                extra_params=extra_params,
                layout_strict=layout_strict,
                aspect_ratio=(config or {}).get("aspect_ratio"),
            )
            logger.info("[Pipeline][%s] 图生图 → %s", feature_key, prompt[:120])
            result = await generator.generate(prompt, images=images, config=config)
            logger.info("[Pipeline][%s] 出图 → %d images, %d urls",
                        feature_key, len(result.images), len(result.image_urls))
            return result
        else:
            if system_prompt:
                # ===== 文生图：经过推理模型生成详细描述 =====
                logger.info("[Pipeline][%s] 文生图模式（推理→生图）", feature_key)
                scene_prompt = await self._generate_scene_prompt(reasoner, system_prompt, user_prompt)
                ar = (config or {}).get("aspect_ratio")
                if ar:
                    scene_prompt = f"{scene_prompt}\n\nGenerate the image in **{ar}** aspect ratio."
                logger.info("[Pipeline][%s] 场景描述 → %s", feature_key, scene_prompt[:120])
                result = await generator.generate(scene_prompt, config=config)
            else:
                # ===== 无系统提示词：直接用用户输入 =====
                logger.info("[Pipeline][%s] 直出", feature_key)
                result = await generator.generate(
                    user_prompt or "Generate a photorealistic interior rendering",
                    config=config,
                )
            logger.info("[Pipeline][%s] 出图 → %d images, %d urls",
                        feature_key, len(result.images), len(result.image_urls))
            return result

    def _resolve_clients(
        self,
        extra_params: dict | None,
    ) -> tuple[BaseAIClient, BaseAIClient]:
        if not self._engine_manager:
            return self._reasoner, self._generator

        extra = extra_params or {}
        channel = str(extra.get("channel", "")).strip().lower()
        if channel != "vertex":
            return self._reasoner, self._generator

        requested_account = str(extra.get("vertex_account") or "").strip()
        fallback_default = self._vertex_default_account
        candidates = [requested_account, fallback_default, "master"]
        seen: set[str] = set()
        for account in candidates:
            if not account or account in seen:
                continue
            seen.add(account)
            key = f"vertex:{account}"
            if not self._engine_manager.has(key):
                continue
            client = self._engine_manager.get(key)
            return client, client

        logger.warning(
            "请求 channel=vertex，但未找到可用账号（request=%s, default=%s），回退默认引擎",
            requested_account or None,
            fallback_default,
        )
        return self._reasoner, self._generator

    def _build_image_edit_prompt(
        self,
        feature_key: str,
        user_prompt: str,
        system_prompt: str | None,
        extra_params: dict | None = None,
        layout_strict: bool = False,
        aspect_ratio: str | None = None,
    ) -> str:
        """
        图生图提示词结构（参考 nanobanana.io 官方编辑格式）：
        Keep (不变的) → Change (要改的) → Quality (画质)
        
        关键原则：
        1. Keep 在最前面，权重最高，防止模型乱改
        2. 用户指令被框定为 "Change style/materials" 而非 "添加内容"
        3. 画质标签在最后
        4. 不包含 room_type（模型已能看到图片内容）
        
        P0-1: layout_strict=true 时使用强约束，否则保持简短约束
        """
        # 参照 mujiang-ai 核心原则：极简、不用动词指令
        # 用户提示词作为风格修饰 + 画质标签 + 布局锁定
        parts = []

        if user_prompt:
            parts.append(user_prompt)

        if system_prompt:
            parts.append(system_prompt.strip())

        if feature_key == "local-material-change" and (extra_params or {}).get("has_reference_material"):
            if (extra_params or {}).get("has_region_mask"):
                parts.append(
                    "Use the third input image as material reference for texture/color/finish. "
                    "Apply it only to the selected region mask from the second input image."
                )
            else:
                image_order = (extra_params or {}).get("_image_order")
                if image_order == "ref_base":
                    parts.append(
                        "Use the first input image as material reference swatch for texture/color/finish, "
                        "and treat the second input image as the target scene to edit. "
                        "No explicit mask is provided: infer the target area from the prompt and keep unrelated areas unchanged. "
                        "Do not copy composition, perspective, or layout from the reference swatch image."
                    )
                else:
                    parts.append(
                        "Treat the first input image as the target scene to edit, and use the second input image "
                        "as material reference swatch for texture/color/finish. "
                        "No explicit mask is provided: infer the target area from the prompt and keep unrelated areas unchanged. "
                        "Do not copy composition, perspective, or layout from the reference swatch image."
                    )

        if feature_key == "multi-view":
            view_hint = (extra_params or {}).get("target_views")
            if view_hint:
                parts.append(
                    f"Create a new camera viewpoint: {view_hint}. Keep room geometry, object placement, materials, and lighting style consistent."
                )
            else:
                parts.append(
                    "Create a new camera viewpoint according to the prompt. Keep room geometry, object placement, materials, and lighting style consistent."
                )
            if layout_strict:
                parts.append(
                    "Preserve spatial proportions and object consistency; changing camera angle is allowed."
                )
        else:
            if layout_strict:
                parts.append(
                    "Strictly preserve layout, camera angle, and spatial proportions. Do not add or remove objects."
                )
            else:
                parts.append(
                    "Keep the same layout, proportions and viewing angle as the reference image."
                )

        if aspect_ratio and aspect_ratio != "default":
            parts.append(f"Generate the image in **{aspect_ratio}** aspect ratio.")

        return "\n\n".join(parts)

    async def _translate_style_keywords(
        self,
        reasoner: BaseAIClient,
        user_prompt: str,
    ) -> str:
        """把用户中文描述翻译为纯色调/材质/光照英文词。禁止风格名词，防止触发模型添加物体。"""
        try:
            result = await reasoner.generate_text(
                "Translate to English. Output ONLY color, material and lighting adjectives (max 6 words). "
                "Do NOT output style names like neoclassical, baroque, Victorian. "
                "Do NOT output nouns like fireplace, chandelier, decoration. "
                "Only output words about: color tone, material finish, lighting mood.\n\n"
                f"Input: {user_prompt}"
            )
            translated = result.strip().strip('"').strip("'").strip(".")
            if translated and "out of credits" not in translated.lower() and len(translated) < 80:
                return translated
        except Exception as e:
            logger.warning("[翻译失败] %s", e)
        return user_prompt

    async def _generate_scene_prompt(
        self,
        reasoner: BaseAIClient,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """文生图：经过推理模型生成场景描述"""
        meta = TEXT_TO_IMAGE_META.format(
            system_prompt=system_prompt,
            user_prompt=user_prompt or "按功能默认规则处理",
        )
        text = await reasoner.generate_text(meta)
        result = text.strip()
        if not result or "out of credits" in result.lower():
            logger.warning("[推理失败] 使用兜底提示词")
            return f"Photorealistic interior rendering. {user_prompt}"
        return result
