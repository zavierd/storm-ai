from __future__ import annotations

from pydantic import Field, model_validator

from app.models.common import GenerationRequest


class ToolboxTextToImageRequest(GenerationRequest):
    """文生图"""

    description: str = Field(default="", description="图像描述")
    style_hint: str | None = Field(default=None, description="可选风格方向提示")
    aspect_ratio: str = Field(default="1:1", description="宽高比，如 1:1, 16:9, 4:3")

    @model_validator(mode="before")
    @classmethod
    def prompt_to_description(cls, data: dict) -> dict:
        """前端可能只传 prompt_text，映射为 description"""
        if isinstance(data, dict) and not data.get("description") and data.get("prompt_text"):
            data = {**data, "description": data["prompt_text"]}
        return data


class UniversalEditRequest(GenerationRequest):
    """万能修改"""

    edit_instruction: str = Field(default="", description="自然语言修改指令")

    @model_validator(mode="before")
    @classmethod
    def prompt_to_edit_instruction(cls, data: dict) -> dict:
        """前端可能只传 prompt_text，映射为 edit_instruction"""
        if isinstance(data, dict) and not data.get("edit_instruction") and data.get("prompt_text"):
            data = {**data, "edit_instruction": data["prompt_text"]}
        return data


class StyleMimicRequest(GenerationRequest):
    """图片模仿 — images[0]=目标图, images[1]=风格参考"""

    mimic_intensity: float = Field(
        default=0.7, ge=0.0, le=1.0, description="风格迁移强度"
    )


class RemoveWatermarkRequest(GenerationRequest):
    """去水印"""

    watermark_hint: str | None = Field(
        default=None, description="可选水印位置提示，如'右下角'"
    )


class MaterialExtractRequest(GenerationRequest):
    """材质贴图提取"""

    target_area: str | None = Field(
        default=None, description="目标材质区域描述，如'地板木纹'"
    )
