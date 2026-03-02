from __future__ import annotations

from typing import Literal

from app.models.common import GenerationRequest


class WhiteModelRequest(GenerationRequest):
    """白膜出图"""

    space_type: str = "客厅"
    material_preference: str | None = None


class RoughHouseRequest(GenerationRequest):
    """毛坯房出图"""

    design_style: str = "现代简约"
    budget_level: Literal["经济", "中等", "高端"] = "中等"


class StyleTransferRequest(GenerationRequest):
    """室内风格转化"""

    target_style: str
    preserve_level: float = 0.5


class SketchRenderRequest(GenerationRequest):
    """手绘线稿出图"""

    color_tone: str | None = None


class QualityEnhanceRequest(GenerationRequest):
    """质感增强"""

    enhance_level: Literal[1, 2, 3] = 2


class AtmosphereRequest(GenerationRequest):
    """氛围转换"""

    target_atmosphere: str


class LightingMasterRequest(GenerationRequest):
    """光影大师"""

    lighting_type: Literal["natural", "artificial", "mixed"] = "mixed"
    enhancement_focus: str | None = None


class CollageRenderRequest(GenerationRequest):
    """软装拼贴出图"""

    space_type: str = "客厅"
    layout_guide: str | None = None


# ---------------------------------------------------------------------------
# Batch 3 — 高级室内 AI 功能
# ---------------------------------------------------------------------------


class LockedMaterialRequest(GenerationRequest):
    """锁定材质出图"""

    material_description: str | None = None
    has_reference_material: bool = False


class MaterialReplaceRequest(GenerationRequest):
    """指定材质替换"""

    target_material: str


class PartialReplaceRequest(GenerationRequest):
    """软硬装局部替换"""

    replace_description: str


class LocalMaterialRequest(GenerationRequest):
    """局部材质修改"""

    new_material: str


class LocalLightingRequest(GenerationRequest):
    """局部开灯"""

    light_type: Literal["warm", "cool", "colored"] = "warm"
    brightness: float = 0.7


class MultiViewRequest(GenerationRequest):
    """多视角一致性"""

    target_views: list[str] = ["左侧45度", "正面"]


class ColorFloorPlanRequest(GenerationRequest):
    """彩平图"""

    color_scheme: str | None = None
    show_labels: bool = True


class FloorPlanLayoutRequest(GenerationRequest):
    """家装平面方案"""

    family_info: str | None = None
    functional_needs: list[str] | None = None


class MaterialChannelRequest(GenerationRequest):
    """材质通道图"""


class FurnitureListRequest(GenerationRequest):
    """软装物料清单"""
