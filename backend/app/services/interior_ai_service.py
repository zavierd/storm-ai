from __future__ import annotations

import json
import logging
from datetime import datetime
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

from app.clients.base_client import EngineType, GenerationResult
from app.clients.gemini_client import GeminiClient
from app.exceptions import ValidationError
from app.models.common import GenerationRequest, GenerationResponse
from app.prompts.engine import PromptEngine
from app.prompts.registry import FeatureConfig, registry
from app.services.base_service import BaseAIService

logger = logging.getLogger(__name__)

_FURNITURE_LIST_RESPONSE_SCHEMA: dict = {
    "type": "object",
    "required": [
        "room_type",
        "design_style",
        "total_items",
        "categories",
        "color_palette",
        "style_summary",
        "items",
    ],
    "properties": {
        "room_type": {"type": "string"},
        "design_style": {"type": "string"},
        "total_items": {"type": "integer"},
        "categories": {
            "type": "array",
            "items": {"type": "string"},
        },
        "color_palette": {
            "type": "array",
            "items": {"type": "string"},
        },
        "style_summary": {"type": "string"},
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "name",
                    "category",
                    "material",
                    "color",
                    "dimensions_cm_estimate",
                    "quantity_estimate",
                    "style_note",
                    "confidence",
                ],
                "properties": {
                    "name": {"type": "string"},
                    "category": {
                        "type": "string",
                        "enum": ["家具", "灯具", "织物", "装饰品", "植物", "收纳"],
                    },
                    "material": {"type": "string"},
                    "color": {"type": "string"},
                    "dimensions_cm_estimate": {"type": "string"},
                    "quantity_estimate": {"type": "integer"},
                    "style_note": {"type": "string"},
                    "confidence": {"type": "number"},
                },
            },
        },
    },
}

_CARD_WIDTH = 1280
_CARD_PADDING = 32
_CARD_BG = (16, 18, 22)
_CARD_PANEL = (26, 29, 35)
_CARD_LINE = (56, 62, 74)
_CARD_TEXT = (232, 235, 242)
_CARD_TEXT_MUTED = (158, 167, 184)
_CARD_ACCENT = (139, 150, 255)


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    )
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except Exception:
            continue
    try:
        return ImageFont.truetype("arial.ttf", size=size)
    except Exception:
        return ImageFont.load_default()

INTERIOR_FEATURES: list[FeatureConfig] = [
    FeatureConfig(
        feature_key="white-model-render",
        name="白膜出图",
        category="interior_ai",
        template_path="interior_ai/white_model_render.j2",
        description="白模型截图一键生成写实效果图",
        input_type="single_image",
    ),
    FeatureConfig(
        feature_key="rough-house-render",
        name="毛坯房出图",
        category="interior_ai",
        template_path="interior_ai/rough_house_render.j2",
        description="毛坯房照片转精装效果图",
        input_type="single_image",
    ),
    FeatureConfig(
        feature_key="style-transfer",
        name="室内风格转化",
        category="interior_ai",
        template_path="interior_ai/style_transfer.j2",
        description="一键切换全屋设计风格",
        input_type="single_image",
    ),
    FeatureConfig(
        feature_key="sketch-render",
        name="手绘线稿出图",
        category="interior_ai",
        template_path="interior_ai/sketch_render.j2",
        description="手绘线稿还原写实空间效果",
        input_type="single_image",
    ),
    FeatureConfig(
        feature_key="line-render",
        name="线稿生图",
        category="interior_ai",
        template_path="interior_ai/sketch_render.j2",
        description="手绘线稿转写实效果图",
        input_type="single_image",
    ),
    FeatureConfig(
        feature_key="quality-enhance",
        name="室内质感增强",
        category="interior_ai",
        template_path="interior_ai/quality_enhance.j2",
        description="精修空间肌理与光影层次",
        input_type="single_image",
    ),
    FeatureConfig(
        feature_key="atmosphere-change",
        name="室内氛围转换",
        category="interior_ai",
        template_path="interior_ai/atmosphere_change.j2",
        description="一键切换光影色调风格",
        input_type="single_image",
    ),
    FeatureConfig(
        feature_key="lighting-master",
        name="光影大师",
        category="interior_ai",
        template_path="interior_ai/lighting_master.j2",
        description="智能调校空间光影层次",
        input_type="single_image",
    ),
    FeatureConfig(
        feature_key="collage-render",
        name="软装拼贴出图",
        category="interior_ai",
        template_path="interior_ai/collage_render.j2",
        description="软装拼贴秒转实景效果图；支持单图(拼贴)或双图(目标空间+拼贴)",
        input_type="multi_image",
    ),
    # ------------------------------------------------------------------
    # Batch 3 — 局部编辑类（支持遮罩）
    # ------------------------------------------------------------------
    FeatureConfig(
        feature_key="locked-material-render",
        name="锁定材质出图",
        category="interior_ai",
        template_path="interior_ai/locked_material_render.j2",
        description="精准保留原始材质属性，生成高写实效果图",
        input_type="single_image",
    ),
    FeatureConfig(
        feature_key="material-replace",
        name="指定材质替换",
        category="interior_ai",
        template_path="interior_ai/material_replace.j2",
        description="精准定位目标区域，一键更换材质",
        input_type="single_image",
        supports_mask=True,
    ),
    FeatureConfig(
        feature_key="partial-replace",
        name="软硬装局部替换",
        category="interior_ai",
        template_path="interior_ai/partial_replace.j2",
        description="选区域替换造型",
        input_type="single_image",
        supports_mask=True,
    ),
    FeatureConfig(
        feature_key="local-material-change",
        name="局部材质修改",
        category="interior_ai",
        template_path="interior_ai/local_material_change.j2",
        description="选区域更换材质",
        input_type="single_image",
        supports_mask=True,
    ),
    FeatureConfig(
        feature_key="local-lighting",
        name="局部开灯",
        category="interior_ai",
        template_path="interior_ai/local_lighting.j2",
        description="选区域添加灯光效果",
        input_type="single_image",
        supports_mask=True,
    ),
    # ------------------------------------------------------------------
    # Batch 3 — 特殊生成类
    # ------------------------------------------------------------------
    FeatureConfig(
        feature_key="multi-view",
        name="多视角一致性",
        category="interior_ai",
        template_path="interior_ai/multi_view.j2",
        description="一张图生成多角度一致效果图",
        input_type="single_image",
    ),
    FeatureConfig(
        feature_key="color-floor-plan",
        name="一键彩平图",
        category="interior_ai",
        template_path="interior_ai/color_floor_plan.j2",
        description="智能生成标准彩色平面图",
        input_type="single_image",
    ),
    FeatureConfig(
        feature_key="floor-plan-layout",
        name="家装平面方案",
        category="interior_ai",
        template_path="interior_ai/floor_plan_layout.j2",
        description="智能解析户型生成布局方案",
        input_type="single_image",
    ),
    FeatureConfig(
        feature_key="material-channel",
        name="材质通道图",
        category="interior_ai",
        template_path="interior_ai/material_channel.j2",
        description="一键生成材质分层通道图",
        input_type="single_image",
    ),
    FeatureConfig(
        feature_key="furniture-list",
        name="软装物料清单",
        category="interior_ai",
        template_path="interior_ai/furniture_list.j2",
        description="AI识别物品生成结构化清单",
        input_type="single_image",
    ),
]

_FEATURE_KEYS = {fc.feature_key for fc in INTERIOR_FEATURES}


class InteriorAIService(BaseAIService):
    """室内 AI 服务，统一管理 18 个室内设计功能"""

    def __init__(self, gemini_client: GeminiClient, prompt_engine: PromptEngine):
        super().__init__(gemini_client, prompt_engine)
        for fc in INTERIOR_FEATURES:
            registry.register(fc)
        logger.info("InteriorAIService 初始化完成，已注册 %d 个功能", len(INTERIOR_FEATURES))

    # ------------------------------------------------------------------
    # 输入校验
    # ------------------------------------------------------------------

    def validate_input(self, request: GenerationRequest) -> None:
        """室内 AI：建议上传图片，无图时降级为文生图（需有提示词）"""
        if not request.images and not request.prompt_text:
            raise ValidationError(message="请上传图片或输入提示词")

    # ------------------------------------------------------------------
    # 主处理流程
    # ------------------------------------------------------------------

    async def process(
        self, feature_key: str, request: GenerationRequest
    ) -> GenerationResponse:
        if feature_key not in _FEATURE_KEYS:
            raise ValidationError(message=f"不支持的室内AI功能: {feature_key}")

        handler = self._DISPATCH.get(feature_key)
        if handler:
            return await handler(self, feature_key, request)

        return await super().process(feature_key, request)

    # ------------------------------------------------------------------
    # 功能专用处理器
    # ------------------------------------------------------------------

    async def _process_white_model(
        self, feature_key: str, request: GenerationRequest
    ) -> GenerationResponse:
        """白膜出图 — 将专用字段注入 extra_params"""
        self._inject_extra(request, "space_type", default="客厅")
        self._inject_extra(request, "material_preference")
        return await super().process(feature_key, request)

    async def _process_rough_house(
        self, feature_key: str, request: GenerationRequest
    ) -> GenerationResponse:
        self._inject_extra(request, "design_style", default="现代简约")
        self._inject_extra(request, "budget_level", default="中等")
        return await super().process(feature_key, request)

    async def _process_style_transfer(
        self, feature_key: str, request: GenerationRequest
    ) -> GenerationResponse:
        self._inject_extra(request, "target_style")
        self._inject_extra(request, "preserve_level", default=0.5)
        return await super().process(feature_key, request)

    async def _process_sketch_render(
        self, feature_key: str, request: GenerationRequest
    ) -> GenerationResponse:
        self._inject_extra(request, "color_tone")
        return await super().process(feature_key, request)

    async def _process_quality_enhance(
        self, feature_key: str, request: GenerationRequest
    ) -> GenerationResponse:
        self._inject_extra(request, "enhance_level", default=2)
        return await super().process(feature_key, request)

    async def _process_atmosphere(
        self, feature_key: str, request: GenerationRequest
    ) -> GenerationResponse:
        self._inject_extra(request, "target_atmosphere")
        return await super().process(feature_key, request)

    async def _process_lighting_master(
        self, feature_key: str, request: GenerationRequest
    ) -> GenerationResponse:
        self._inject_extra(request, "lighting_type", default="mixed")
        self._inject_extra(request, "enhancement_focus")
        return await super().process(feature_key, request)

    async def _process_collage_render(
        self, feature_key: str, request: GenerationRequest
    ) -> GenerationResponse:
        self._inject_extra(request, "space_type", default="客厅")
        self._inject_extra(request, "layout_guide")
        return await super().process(feature_key, request)

    # ------------------------------------------------------------------
    # Batch 3 — 局部编辑类
    # ------------------------------------------------------------------

    async def _process_locked_material(
        self, feature_key: str, request: GenerationRequest
    ) -> GenerationResponse:
        self._inject_extra(request, "material_description")
        if request.extra_params is None:
            request.extra_params = {}
        if not request.extra_params.get("material_description") and request.prompt_text:
            request.extra_params["material_description"] = request.prompt_text
        self._inject_extra(request, "has_reference_material", default=False)
        return await super().process(feature_key, request)

    async def _process_material_replace(
        self, feature_key: str, request: GenerationRequest
    ) -> GenerationResponse:
        self._inject_extra(request, "target_material")
        if request.extra_params is None:
            request.extra_params = {}
        if not request.extra_params.get("target_material") and request.prompt_text:
            request.extra_params["target_material"] = request.prompt_text
        self._inject_region_description(request)
        return await super().process(feature_key, request)

    async def _process_partial_replace(
        self, feature_key: str, request: GenerationRequest
    ) -> GenerationResponse:
        self._inject_extra(request, "replace_description")
        if request.extra_params is None:
            request.extra_params = {}
        if not request.extra_params.get("replace_description") and request.prompt_text:
            request.extra_params["replace_description"] = request.prompt_text
        self._inject_region_description(request)
        return await super().process(feature_key, request)

    async def _process_local_material(
        self, feature_key: str, request: GenerationRequest
    ) -> GenerationResponse:
        self._inject_extra(request, "new_material")
        if request.extra_params is None:
            request.extra_params = {}
        if not request.extra_params.get("new_material") and request.prompt_text:
            request.extra_params["new_material"] = request.prompt_text
        # Venice 局部材质编辑实测：flux-2-max-edit 在区域稳定性和构图保持上更优。
        request.extra_params.setdefault("venice_edit_model", "flux-2-max-edit")
        request.extra_params.setdefault(
            "has_reference_material",
            len(request.images) >= 2,
        )
        request.extra_params.setdefault("has_region_mask", request.region is not None)
        # 局部材质修改对材质词汇敏感，默认跳过“极简翻译”避免语义丢失。
        if request.skip_translation is None:
            request.skip_translation = True
        self._inject_region_description(request)
        return await super().process(feature_key, request)

    async def _process_local_lighting(
        self, feature_key: str, request: GenerationRequest
    ) -> GenerationResponse:
        self._inject_extra(request, "light_type", default="warm")
        self._inject_extra(request, "brightness", default=0.7)
        self._inject_region_description(request)
        return await super().process(feature_key, request)

    # ------------------------------------------------------------------
    # Batch 3 — 特殊生成类
    # ------------------------------------------------------------------

    async def _process_multi_view(
        self, feature_key: str, request: GenerationRequest
    ) -> GenerationResponse:
        self._inject_extra(request, "target_views")
        return await super().process(feature_key, request)

    async def _process_color_floor_plan(
        self, feature_key: str, request: GenerationRequest
    ) -> GenerationResponse:
        self._inject_extra(request, "color_scheme")
        self._inject_extra(request, "show_labels", default=True)
        return await super().process(feature_key, request)

    async def _process_floor_plan_layout(
        self, feature_key: str, request: GenerationRequest
    ) -> GenerationResponse:
        self._inject_extra(request, "family_info")
        self._inject_extra(request, "functional_needs")
        return await super().process(feature_key, request)

    async def _process_material_channel(
        self, feature_key: str, request: GenerationRequest
    ) -> GenerationResponse:
        return await super().process(feature_key, request)

    async def _process_furniture_list(
        self, feature_key: str, request: GenerationRequest
    ) -> GenerationResponse:
        """软装物料清单 — 仅使用模型直出清单图。"""
        self.validate_input(request)
        images = self.preprocess_images(request.images[:1]) if request.images else []
        client = self._resolve_request_client(request)
        model_prompt = self._build_furniture_list_image_prompt(request.prompt_text or "")
        model_config = self._build_engine_config(request) or {}
        model_config.setdefault("aspect_ratio", "1:1")

        model_result = await client.generate(
            model_prompt,
            images=images or None,
            config=model_config,
        )
        if not model_result.images and not model_result.image_urls:
            raise ValidationError(message="模型未返回清单图片，请重试")
        return self.postprocess_result(model_result)

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------

    @staticmethod
    def _inject_extra(
        request: GenerationRequest, field: str, *, default: object = None
    ) -> None:
        """若专用请求模型携带该字段，则自动复制到 extra_params 供模板使用"""
        if request.extra_params is None:
            request.extra_params = {}
        if field in request.extra_params:
            return
        value = getattr(request, field, None)
        if value is not None:
            request.extra_params[field] = value
        elif default is not None:
            request.extra_params.setdefault(field, default)

    @staticmethod
    def _inject_region_description(request: GenerationRequest) -> None:
        """将 region 信息转为自然语言描述，注入 extra_params 供模板使用"""
        if request.extra_params is None:
            request.extra_params = {}
        if "region_description" in request.extra_params:
            return
        if not request.region:
            request.extra_params["region_description"] = ""
            return

        region = request.region
        if region.type == "mask" and region.mask_data:
            desc = "Focus on the masked/selected region of the image."
        elif region.type == "rect" and region.coordinates:
            coords = region.coordinates
            desc = (
                f"Focus on the rectangular region at "
                f"top-left ({coords[0][0]:.2f}, {coords[0][1]:.2f}) "
                f"to bottom-right ({coords[1][0]:.2f}, {coords[1][1]:.2f}) (normalized 0-1)."
            )
        elif region.type == "polygon" and region.coordinates:
            desc = "Focus on the polygon-selected region of the image."
        else:
            desc = "Focus on the specified region of the image."
        request.extra_params["region_description"] = desc

    @staticmethod
    def _normalize_json_text(text: str) -> str:
        """尽量返回格式化 JSON；解析失败时回退原文本。"""
        cleaned = (text or "").strip()
        if not cleaned:
            return ""
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()
        try:
            parsed = json.loads(cleaned)
            return json.dumps(parsed, ensure_ascii=False, indent=2)
        except Exception:
            return cleaned

    @staticmethod
    def _parse_furniture_payload(normalized_text: str) -> dict:
        """将模型文本解析为字典；失败时回退为可渲染的兜底结构。"""
        fallback = {
            "room_type": "未知",
            "design_style": "未知",
            "total_items": 0,
            "categories": [],
            "color_palette": [],
            "style_summary": normalized_text or "未生成可用清单，请重试。",
            "items": [],
        }
        if not normalized_text:
            return fallback
        try:
            payload = json.loads(normalized_text)
            if isinstance(payload, dict):
                return payload
            return {**fallback, "style_summary": str(payload)}
        except Exception:
            return fallback

    @staticmethod
    def _build_furniture_list_image_prompt(user_prompt: str) -> str:
        extra = user_prompt.strip()
        base = """根据输入的室内图片，生成一张“软装物料清单墙”图片（中文）。
版式要求：
1) 白色背景，网格卡片布局，视觉整洁；
2) 每个卡片展示一个软装/家具/灯具单品（尽量抠出主体）；
3) 每个卡片下方用简洁中文标注名称；
4) 按类别分组（如：家具、灯具、地毯、装饰、窗帘等）；
5) 不要出现多余说明文字、水印、英文段落。
内容要求：
- 只列出图片中可见且较明确的物件；
- 优先包含核心单品（沙发、茶几、边几、地毯、灯具、窗帘、抱枕、装饰件）；
- 风格统一，排版对齐，避免重叠。"""
        if extra:
            return f"{base}\n附加要求：{extra}"
        return base

    @staticmethod
    def _wrap_text(
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.ImageFont,
        max_width: int,
    ) -> list[str]:
        content = (text or "").replace("\r", "").replace("\n", " ").strip()
        if not content:
            return []
        lines: list[str] = []
        # 中英文混排：按字符累积，避免中文无空格场景无法换行。
        current = ""
        for ch in content:
            candidate = f"{current}{ch}"
            box = draw.textbbox((0, 0), candidate, font=font)
            if (box[2] - box[0]) <= max_width or not current:
                current = candidate
            else:
                lines.append(current)
                current = ch
        if current:
            lines.append(current)
        return lines

    @staticmethod
    def _render_furniture_list_card(
        payload: dict,
        source_image: bytes | None = None,
    ) -> bytes:
        """
        将结构化清单渲染为 PNG 卡片图。
        设计依据：先结构化输出，再本地排版，避免模型端文字渲染不稳定。
        """
        title_font = _load_font(40, bold=True)
        sub_font = _load_font(24)
        body_font = _load_font(20)
        mono_font = _load_font(18)

        room_type = str(payload.get("room_type") or "未知")
        design_style = str(payload.get("design_style") or "未知")
        total_items = int(payload.get("total_items") or 0)
        categories = payload.get("categories") or []
        palette = payload.get("color_palette") or []
        style_summary = str(payload.get("style_summary") or "")
        items = payload.get("items") or []
        if not isinstance(items, list):
            items = []

        # 估算高度：头部 + 摘要 + 列表（最多展示18项）
        show_items = items[:18]
        header_h = 140
        summary_h = 220
        table_row_h = 42
        table_h = 74 + len(show_items) * table_row_h + 30
        canvas_h = header_h + summary_h + table_h + _CARD_PADDING * 2

        img = Image.new("RGB", (_CARD_WIDTH, canvas_h), _CARD_BG)
        draw = ImageDraw.Draw(img)

        # Header
        draw.rectangle(
            (_CARD_PADDING, _CARD_PADDING, _CARD_WIDTH - _CARD_PADDING, _CARD_PADDING + 108),
            fill=_CARD_PANEL,
            outline=_CARD_LINE,
            width=2,
        )
        draw.text(
            (_CARD_PADDING + 20, _CARD_PADDING + 18),
            "软装物料清单",
            font=title_font,
            fill=_CARD_TEXT,
        )
        draw.text(
            (_CARD_PADDING + 22, _CARD_PADDING + 68),
            f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            font=mono_font,
            fill=_CARD_TEXT_MUTED,
        )

        # Source thumbnail + summary
        y = _CARD_PADDING + 126
        draw.rectangle(
            (_CARD_PADDING, y, _CARD_WIDTH - _CARD_PADDING, y + summary_h),
            fill=_CARD_PANEL,
            outline=_CARD_LINE,
            width=2,
        )

        text_x = _CARD_PADDING + 24
        if source_image:
            try:
                thumb = Image.open(BytesIO(source_image)).convert("RGB")
                thumb.thumbnail((300, 180), Image.LANCZOS)
                thumb_bg = Image.new("RGB", (308, 188), (38, 42, 52))
                tx = (thumb_bg.width - thumb.width) // 2
                ty = (thumb_bg.height - thumb.height) // 2
                thumb_bg.paste(thumb, (tx, ty))
                img.paste(thumb_bg, (_CARD_PADDING + 20, y + 16))
                text_x = _CARD_PADDING + 350
            except Exception:
                pass

        draw.text((text_x, y + 18), f"空间类型：{room_type}", font=sub_font, fill=_CARD_TEXT)
        draw.text((text_x, y + 56), f"设计风格：{design_style}", font=sub_font, fill=_CARD_TEXT)
        draw.text((text_x, y + 94), f"识别总数：{total_items}", font=sub_font, fill=_CARD_ACCENT)
        draw.text(
            (text_x, y + 132),
            f"分类：{', '.join(str(x) for x in categories[:6]) or '无'}",
            font=body_font,
            fill=_CARD_TEXT_MUTED,
        )
        draw.text(
            (text_x, y + 164),
            f"色板：{', '.join(str(x) for x in palette[:8]) or '无'}",
            font=body_font,
            fill=_CARD_TEXT_MUTED,
        )

        # Style summary
        wrap_w = _CARD_WIDTH - text_x - _CARD_PADDING - 24
        summary_lines = InteriorAIService._wrap_text(draw, style_summary, body_font, wrap_w)[:3]
        for idx, line in enumerate(summary_lines):
            draw.text(
                (text_x, y + 194 + idx * 26),
                line,
                font=body_font,
                fill=_CARD_TEXT_MUTED,
            )

        # Table
        y2 = y + summary_h + 16
        draw.rectangle(
            (_CARD_PADDING, y2, _CARD_WIDTH - _CARD_PADDING, y2 + table_h),
            fill=_CARD_PANEL,
            outline=_CARD_LINE,
            width=2,
        )
        draw.text((_CARD_PADDING + 20, y2 + 16), "识别条目", font=sub_font, fill=_CARD_TEXT)

        col_x = [
            _CARD_PADDING + 20,   # name
            _CARD_PADDING + 350,  # category
            _CARD_PADDING + 490,  # material
            _CARD_PADDING + 690,  # color
            _CARD_PADDING + 860,  # quantity
            _CARD_PADDING + 980,  # confidence
        ]
        headers = ["名称", "类别", "材质", "颜色", "数量", "置信度"]
        table_top = y2 + 56
        draw.rectangle(
            (_CARD_PADDING + 18, table_top, _CARD_WIDTH - _CARD_PADDING - 18, table_top + 36),
            fill=(34, 39, 50),
        )
        for i, h in enumerate(headers):
            draw.text((col_x[i], table_top + 8), h, font=body_font, fill=_CARD_TEXT)

        for idx, item in enumerate(show_items):
            row_y = table_top + 36 + idx * table_row_h
            if idx % 2 == 1:
                draw.rectangle(
                    (_CARD_PADDING + 18, row_y, _CARD_WIDTH - _CARD_PADDING - 18, row_y + table_row_h),
                    fill=(30, 34, 43),
                )
            name = str(item.get("name", ""))[:18]
            category = str(item.get("category", ""))[:8]
            material = str(item.get("material", ""))[:12]
            color = str(item.get("color", ""))[:12]
            qty = str(item.get("quantity_estimate", ""))
            conf = item.get("confidence", "")
            try:
                conf = f"{float(conf):.2f}"
            except Exception:
                conf = str(conf)
            row_vals = [name, category, material, color, qty, conf]
            for col_idx, val in enumerate(row_vals):
                draw.text((col_x[col_idx], row_y + 10), val, font=mono_font, fill=_CARD_TEXT_MUTED)

        if len(items) > len(show_items):
            draw.text(
                (_CARD_PADDING + 20, y2 + table_h - 24),
                f"* 仅展示前 {len(show_items)} 条，完整共 {len(items)} 条",
                font=mono_font,
                fill=_CARD_TEXT_MUTED,
            )

        out = BytesIO()
        img.save(out, format="PNG")
        return out.getvalue()

    # 功能 → 处理器映射
    _DISPATCH: dict[str, object] = {
        "white-model-render": _process_white_model,
        "rough-house-render": _process_rough_house,
        "style-transfer": _process_style_transfer,
        "sketch-render": _process_sketch_render,
        "line-render": _process_sketch_render,
        "quality-enhance": _process_quality_enhance,
        "atmosphere-change": _process_atmosphere,
        "lighting-master": _process_lighting_master,
        "collage-render": _process_collage_render,
        "locked-material-render": _process_locked_material,
        "material-replace": _process_material_replace,
        "partial-replace": _process_partial_replace,
        "local-material-change": _process_local_material,
        "local-lighting": _process_local_lighting,
        "multi-view": _process_multi_view,
        "color-floor-plan": _process_color_floor_plan,
        "floor-plan-layout": _process_floor_plan_layout,
        "material-channel": _process_material_channel,
        "furniture-list": _process_furniture_list,
    }
