from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class ImageInput(BaseModel):
    """图片输入"""

    base64_data: str
    format: str = "png"


class RegionSelect(BaseModel):
    """区域选择"""

    type: Literal["rect", "polygon", "mask"]
    coordinates: list[list[float]] | None = None
    mask_data: str | None = Field(default=None, description="Base64 编码的遮罩数据")


class StyleConfig(BaseModel):
    """风格配置"""

    style_name: str
    intensity: float = Field(default=0.8, ge=0.0, le=1.0)


class ResolutionConfig(BaseModel):
    """分辨率配置"""

    preset: Literal["720P", "1K", "2K", "4K"] | None = "1K"
    width: int | None = None
    height: int | None = None


class GenerationRequest(BaseModel):
    """生成请求基类"""

    images: list[ImageInput] = Field(default_factory=list)
    prompt_text: str | None = None
    style: StyleConfig | None = None
    resolution: ResolutionConfig | None = None
    region: RegionSelect | None = None
    extra_params: dict | None = None
    project_id: str | None = Field(default=None, description="归档项目ID，未传则自动使用默认项目")
    aspect_ratio: str | None = Field(default=None, description="宽高比，如 1:1, 16:9, 4:3")
    # P0-1: 布局保持强化，默认关闭（过度约束可能削弱风格/材质变化）
    layout_strict: Optional[bool] = None
    # P0-2: 翻译层可配置化，为 true 时跳过 _translate_style_keywords，直接使用 user_prompt
    skip_translation: Optional[bool] = None


class GenerationResponse(BaseModel):
    """生成响应"""

    success: bool
    images: list[str] = Field(default_factory=list, description="Base64 编码的图片列表")
    image_urls: list[str] | None = None
    texts: list[str] | None = None
    usage: dict | None = None
    error: str | None = None


class FeatureInfo(BaseModel):
    """功能信息"""

    key: str
    name: str
    category: str
    description: str
    input_type: str
    supports_mask: bool


class FeatureListResponse(BaseModel):
    """功能列表响应"""

    features: list[FeatureInfo]
