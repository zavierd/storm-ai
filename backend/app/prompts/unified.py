"""
统一提示词构建器
参考 mujiang-ai 的核心原则：
1. 用户输入优先 — 用户说什么就是什么
2. 最小化增强 — 只添加必要的技术约束
3. 简洁直接 — Gemini responds best to direct, clear instructions
"""
from __future__ import annotations


def build_prompt(
    feature_key: str,
    user_prompt: str = "",
    has_image: bool = False,
    extra_params: dict | None = None,
) -> str:
    """统一提示词入口：根据 feature_key 路由到对应构建函数"""
    params = extra_params or {}
    builder = _BUILDERS.get(feature_key, _default_image_to_image)
    return builder(user_prompt, has_image, params)


# ================================================================
# 图生图类（有参考图 + 文字指令）
# 格式：{用户指令}\n\n{最小约束}
# ================================================================

def _image_to_image(user_prompt: str, has_image: bool, params: dict) -> str:
    """通用图生图：保持布局+角度"""
    if not user_prompt:
        user_prompt = "Transform this into a photorealistic rendering"
    if len(user_prompt) > 50:
        return f"{user_prompt}\n\nKeep the same layout, proportions and viewing angle as the reference image."
    return f"{user_prompt}\n\nBased on the reference image layout. Keep the same viewing angle and spatial arrangement."


def _sketch_render(user_prompt: str, has_image: bool, params: dict) -> str:
    """草图大师方案渲染 / 线稿生图"""
    base = user_prompt or "Render this sketch into a photorealistic interior visualization"
    return f"""{base}

Transform the SketchUp/sketch into a photorealistic interior rendering.
Keep the exact layout, wall positions, and spatial proportions from the reference image.
Style: photorealistic, professional architectural visualization, natural lighting."""


def _white_model_render(user_prompt: str, has_image: bool, params: dict) -> str:
    """白膜出图"""
    space = params.get("space_type", "interior space")
    base = user_prompt or f"Render this white 3D model into a photorealistic {space}"
    return f"""{base}

Transform the untextured white model into a fully realized photorealistic rendering.
Add realistic materials, furniture, lighting, and atmosphere.
Keep the exact room geometry and camera angle from the reference."""


def _rough_house_render(user_prompt: str, has_image: bool, params: dict) -> str:
    """毛坯房出图"""
    style = params.get("design_style", "modern minimalist")
    budget = params.get("budget_level", "中等")
    base = user_prompt or f"Design this bare room in {style} style"
    return f"""{base}

Transform this bare/unfinished room into a fully decorated {style} interior.
Budget level: {budget}. Add flooring, wall finishes, furniture, and decorations.
Keep the exact room structure and camera angle."""


def _style_transfer(user_prompt: str, has_image: bool, params: dict) -> str:
    """室内风格迁移"""
    target = params.get("target_style", "modern minimalist")
    preserve = float(params.get("preserve_level", 0.5))
    base = user_prompt or f"Transform this interior to {target} style"
    constraint = "Preserve the main layout and major furniture placement." if preserve > 0.5 else "Redesign the space while keeping the room shell."
    return f"""{base}

Restyle this interior to {target}. {constraint}
Keep the same room structure, camera angle, and spatial proportions."""


def _atmosphere_change(user_prompt: str, has_image: bool, params: dict) -> str:
    """室内氛围转换"""
    atmosphere = params.get("target_atmosphere", "warm afternoon light")
    base = user_prompt or f"Change the atmosphere to {atmosphere}"
    return f"""{base}

Change the lighting and atmosphere to: {atmosphere}.
Keep all furniture, objects, and room structure exactly the same.
Only modify lighting, shadows, and color temperature."""


def _lighting_master(user_prompt: str, has_image: bool, params: dict) -> str:
    """光影大师"""
    light_type = params.get("lighting_type", "mixed")
    base = user_prompt or f"Enhance the lighting with {light_type} light"
    return f"""{base}

Optimize the lighting quality. Type: {light_type}.
Enhance shadow depth, light reflections, and overall atmosphere.
Keep all objects and composition unchanged."""


def _quality_enhance(user_prompt: str, has_image: bool, params: dict) -> str:
    """室内质感增强"""
    level = params.get("enhance_level", "2")
    base = user_prompt or "Enhance the material quality and details"
    return f"""{base}

Enhance image quality level {level}/3. Improve material textures, lighting transitions, and fine details.
Do NOT change composition, objects, or room layout. Only improve visual quality."""


def _partial_replace(user_prompt: str, has_image: bool, params: dict) -> str:
    """室内局部替换 / 软硬装局部替换"""
    desc = params.get("replace_description", user_prompt)
    region = params.get("region_description", "")
    base = desc or user_prompt or "Replace the selected furniture"
    return f"""Replace in this image: {base}
{f'Target area: {region}' if region else ''}
Keep all other elements unchanged. Maintain the original style, lighting, and composition."""


def _locked_material_render(user_prompt: str, has_image: bool, params: dict) -> str:
    """锁定材质出图"""
    material_desc = params.get("material_description", "")
    base = user_prompt or "Enhance this 3D model to photorealistic rendering"
    return f"""{base}

Lock and preserve ALL existing materials exactly — no color shifts, no texture changes.
Only enhance lighting, shadows, and environmental realism. {f'Materials to preserve: {material_desc}' if material_desc else ''}"""


def _local_lighting(user_prompt: str, has_image: bool, params: dict) -> str:
    """局部开灯"""
    light_type = params.get("light_type", "warm")
    brightness = params.get("brightness", 0.7)
    region = params.get("region_description", "")
    base = user_prompt or f"Add {light_type} light to the selected area"
    return f"""Add realistic lighting effect: {base}
Light type: {light_type}, brightness: {brightness}. {'Target region: ' + region if region else ''}
Simulate turning on a light fixture. Keep all other elements unchanged."""


def _local_material_change(user_prompt: str, has_image: bool, params: dict) -> str:
    """局部材质修改"""
    material = params.get("new_material", user_prompt)
    region = params.get("region_description", "")
    base = material or user_prompt or "Change the material"
    return f"""Modify material in this image: {base}
{f'Target area: {region}' if region else ''}
Change only the surface material/texture. Keep object shape and all other elements unchanged."""


def _multi_view(user_prompt: str, has_image: bool, params: dict) -> str:
    """室内多角度生图"""
    views = params.get("target_views", "left 45 degrees")
    base = user_prompt or f"Generate a view from {views}"
    return f"""{base}

Generate a new view of this same room from: {views}.
Maintain consistent materials, colors, furniture, and lighting across views."""


def _collage_render(user_prompt: str, has_image: bool, params: dict) -> str:
    """软装拼贴出图"""
    space = params.get("space_type", "living room")
    base = user_prompt or f"Create a {space} from this mood board"
    return f"""{base}

Transform this mood board/collage into a photorealistic {space} interior.
Extract colors, materials, and furniture style from the collage. Create a cohesive space."""


def _furniture_list(user_prompt: str, has_image: bool, params: dict) -> str:
    """软装物料清单 — 纯文本/JSON 输出"""
    base = """Analyze this interior photograph and return ONLY valid JSON (no markdown, no commentary).
Use this exact top-level structure:
{
  "room_type": string,
  "design_style": string,
  "total_items": integer,
  "categories": string[],
  "color_palette": string[],
  "style_summary": string,
  "items": [
    {
      "name": string,
      "category": one of ["家具","灯具","织物","装饰品","植物","收纳"],
      "material": string,
      "color": string,
      "dimensions_cm_estimate": string,
      "quantity_estimate": integer,
      "style_note": string,
      "confidence": number (0 to 1)
    }
  ]
}
If an item is ambiguous, keep it but lower confidence instead of omitting it."""
    if user_prompt:
        return f"""{base}
Focus areas or additional requirements: {user_prompt}"""
    return base


# ================================================================
# 纯文生图类（无参考图）
# ================================================================

def _text_to_image(user_prompt: str, has_image: bool, params: dict) -> str:
    """文生图"""
    if not user_prompt:
        return "Create a photorealistic interior design image"
    if len(user_prompt) > 50:
        return f"Create an image of: {user_prompt}\nStyle: photorealistic, professional quality, high resolution."
    return f"Create a photorealistic image of {user_prompt}.\nComposition: Well-balanced, professional framing.\nLighting: Natural, appealing lighting.\nQuality: High resolution, sharp details."


# ================================================================
# 工具箱类
# ================================================================

def _remove_watermark(user_prompt: str, has_image: bool, params: dict) -> str:
    """去水印"""
    hint = params.get("watermark_hint", "")
    return f"""Remove all watermarks and text overlays from this image.
{f'Watermark location: {hint}' if hint else ''}
Reconstruct the underlying image content seamlessly. Keep original image quality."""


def _universal_edit(user_prompt: str, has_image: bool, params: dict) -> str:
    """万能修改"""
    instruction = params.get("edit_instruction", user_prompt)
    base = instruction or user_prompt or "Edit this image"
    return f"""Modify this image: {base}
Keep all other elements unchanged. Maintain the original style, lighting, and composition."""


def _style_mimic(user_prompt: str, has_image: bool, params: dict) -> str:
    """图片模仿/风格迁移"""
    intensity = float(params.get("mimic_intensity", 0.7))
    base = user_prompt or "Transfer the style from the reference"
    level = "strong" if intensity > 0.7 else "moderate" if intensity > 0.4 else "subtle"
    return f"""{base}

Image 1 is the target (preserve content). Image 2 is the style reference.
Apply {level} style transfer. Preserve target composition and content."""


def _add_model(user_prompt: str, has_image: bool, params: dict) -> str:
    """场景加模特"""
    base = user_prompt or "Add a professional model into this scene"
    return f"""{base}

Add the described person naturally into the scene.
Match the lighting direction, perspective, and style of the original image.
The person should look like they belong in the space."""


def _default_image_to_image(user_prompt: str, has_image: bool, params: dict) -> str:
    """默认兜底"""
    if has_image:
        return _image_to_image(user_prompt, has_image, params)
    return _text_to_image(user_prompt, has_image, params)


# feature_key → 构建函数映射
_BUILDERS: dict[str, callable] = {
    # 超级AI
    "banana-pro-edit": _image_to_image,
    "banana-pro-t2i": _text_to_image,
    "banana-pro-dual": _style_mimic,
    # 室内AI
    "sketch-render": _sketch_render,
    "line-render": _sketch_render,
    "white-model-render": _white_model_render,
    "rough-house-render": _rough_house_render,
    "style-transfer": _style_transfer,
    "atmosphere-change": _atmosphere_change,
    "lighting-master": _lighting_master,
    "quality-enhance": _quality_enhance,
    "partial-replace": _partial_replace,
    "local-material-change": _local_material_change,
    "local-lighting": _local_lighting,
    "multi-view": _multi_view,
    "collage-render": _collage_render,
    "locked-material-render": _locked_material_render,
    "material-replace": _local_material_change,
    "color-floor-plan": _image_to_image,
    "floor-plan-layout": _image_to_image,
    "material-channel": _image_to_image,
    "furniture-list": _furniture_list,
    # 工具箱
    "toolbox-t2i": _text_to_image,
    "universal-edit": _universal_edit,
    "style-mimic": _style_mimic,
    "remove-watermark": _remove_watermark,
    "material-extract": _image_to_image,
    # 人物
    "add-model": _add_model,
    "remove-bg": _universal_edit,
}
