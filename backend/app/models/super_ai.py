from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from app.models.common import GenerationRequest


class BananaEditRequest(GenerationRequest):
    """香蕉Pro图像编辑请求"""

    edit_instruction: str = Field(default="", description="编辑指令")
    resolution_level: Literal["1K", "2K", "4K"] = Field(
        default="1K", description="输出分辨率等级"
    )

    @model_validator(mode="before")
    @classmethod
    def prompt_to_edit_instruction(cls, data: dict) -> dict:
        """前端可能只传 prompt_text，映射为 edit_instruction"""
        if isinstance(data, dict) and not data.get("edit_instruction") and data.get("prompt_text"):
            data = {**data, "edit_instruction": data["prompt_text"]}
        return data


class BananaTextToImageRequest(GenerationRequest):
    """香蕉Pro文生图请求"""

    description: str = Field(default="", description="图像描述")
    aspect_ratio: str = Field(default="1:1", description="宽高比，如 1:1, 16:9, 4:3")
    style_preset: str | None = Field(default=None, description="可选风格预设")

    @model_validator(mode="before")
    @classmethod
    def prompt_to_description(cls, data: dict) -> dict:
        """前端可能只传 prompt_text，映射为 description"""
        if isinstance(data, dict) and not data.get("description") and data.get("prompt_text"):
            data = {**data, "description": data["prompt_text"]}
        return data


class BananaDualImageRequest(GenerationRequest):
    """香蕉Pro双图模式请求"""

    blend_instruction: str = Field(default="", description="融合指令")
    weight_a: float = Field(default=0.5, ge=0.0, le=1.0, description="图A权重")
    weight_b: float = Field(default=0.5, ge=0.0, le=1.0, description="图B权重")

    @model_validator(mode="before")
    @classmethod
    def prompt_to_blend_instruction(cls, data: dict) -> dict:
        """前端可能只传 prompt_text，映射为 blend_instruction"""
        if isinstance(data, dict) and not data.get("blend_instruction") and data.get("prompt_text"):
            data = {**data, "blend_instruction": data["prompt_text"]}
        return data
