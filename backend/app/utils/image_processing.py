from __future__ import annotations

import base64
import io

from PIL import Image, ImageDraw, ImageOps, ImageStat

from app.exceptions import ImageProcessingError
from app.models.common import RegionSelect


def decode_base64_image(data: str) -> bytes:
    """Base64 字符串解码为图片字节"""
    try:
        if "," in data:
            data = data.split(",", 1)[1]
        return base64.b64decode(data)
    except Exception as e:
        raise ImageProcessingError(
            message="Base64 图片解码失败", detail=str(e)
        ) from e


def encode_image_to_base64(data: bytes) -> str:
    """图片字节编码为 Base64 字符串"""
    return base64.b64encode(data).decode("utf-8")


def resize_image(data: bytes, max_width: int, max_height: int, quality: int = 80) -> bytes:
    """按最大宽高等比缩放并压缩为 JPEG"""
    try:
        img = Image.open(io.BytesIO(data))
        img.thumbnail((max_width, max_height), Image.LANCZOS)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        return buf.getvalue()
    except Exception as e:
        raise ImageProcessingError(
            message="图片缩放失败", detail=str(e)
        ) from e


def validate_image(data: bytes) -> tuple[str, int, int]:
    """校验图片并返回 (format, width, height)"""
    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
        img = Image.open(io.BytesIO(data))
        return (img.format or "UNKNOWN", img.width, img.height)
    except Exception as e:
        raise ImageProcessingError(
            message="图片校验失败，文件可能损坏或格式不支持", detail=str(e)
        ) from e


def create_mask_from_region(
    image_size: tuple[int, int], region: RegionSelect
) -> bytes:
    """根据区域信息生成遮罩 PNG"""
    width, height = image_size
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)

    if region.type == "rect" and region.coordinates:
        if len(region.coordinates) >= 2:
            x1 = int(region.coordinates[0][0] * width)
            y1 = int(region.coordinates[0][1] * height)
            x2 = int(region.coordinates[1][0] * width)
            y2 = int(region.coordinates[1][1] * height)
            draw.rectangle([x1, y1, x2, y2], fill=255)

    elif region.type == "polygon" and region.coordinates:
        points = [
            (int(pt[0] * width), int(pt[1] * height))
            for pt in region.coordinates
        ]
        if len(points) >= 3:
            draw.polygon(points, fill=255)

    elif region.type == "mask" and region.mask_data:
        mask_bytes = decode_base64_image(region.mask_data)
        mask = Image.open(io.BytesIO(mask_bytes)).convert("L").resize((width, height))

    buf = io.BytesIO()
    mask.save(buf, format="PNG")
    return buf.getvalue()


def is_black_placeholder_image(data: bytes) -> bool:
    """
    判断是否为黑屏占位图（安全拦截常见返回）。

    判定较严格，避免误伤夜景图：
    - 下采样后几乎所有像素都接近纯黑
    - 且整体像素方差极低（接近纯色）
    """
    try:
        img = Image.open(io.BytesIO(data)).convert("RGB").resize((256, 256), Image.NEAREST)
        pixels = list(img.getdata())
        if not pixels:
            return False

        black_like = 0
        total = len(pixels)
        sum_r = sum_g = sum_b = 0
        for r, g, b in pixels:
            sum_r += r
            sum_g += g
            sum_b += b
            if r <= 3 and g <= 3 and b <= 3:
                black_like += 1

        black_ratio = black_like / total
        mean_r = sum_r / total
        mean_g = sum_g / total
        mean_b = sum_b / total

        var_acc = 0.0
        for r, g, b in pixels:
            var_acc += (
                (r - mean_r) ** 2
                + (g - mean_g) ** 2
                + (b - mean_b) ** 2
            ) / 3
        variance = var_acc / total

        return black_ratio >= 0.995 and variance < 1.5
    except Exception:
        # 无法解析时交给后续流程，不在这里阻断
        return False


def fit_image_to_size(data: bytes, target_size: tuple[int, int]) -> bytes:
    """
    将图片按目标尺寸进行等比缩放 + 补边（不裁剪），避免局部编辑结果尺寸漂移。
    输出统一为 PNG，兼容透明通道。
    """
    try:
        img = Image.open(io.BytesIO(data))
        preview = img.convert("RGB").resize((64, 64), Image.BILINEAR)
        stat = ImageStat.Stat(preview)
        pad_color = tuple(int(v) for v in stat.mean[:3])
        fitted = ImageOps.pad(
            img,
            target_size,
            method=Image.LANCZOS,
            color=pad_color,
            centering=(0.5, 0.5),
        )
        buf = io.BytesIO()
        fitted.save(buf, format="PNG")
        return buf.getvalue()
    except Exception as e:
        raise ImageProcessingError(
            message="图片尺寸对齐失败", detail=str(e)
        ) from e


def invert_mask_image(data: bytes) -> bytes:
    """反相遮罩图（黑白互换）。"""
    try:
        mask = Image.open(io.BytesIO(data)).convert("L")
        inv = ImageOps.invert(mask)
        buf = io.BytesIO()
        inv.save(buf, format="PNG")
        return buf.getvalue()
    except Exception as e:
        raise ImageProcessingError(
            message="遮罩反相失败", detail=str(e)
        ) from e


def score_masked_edit_result(
    *,
    base_image: bytes,
    mask_image: bytes,
    output_image: bytes,
    eval_size: int = 256,
) -> dict[str, float]:
    """
    评估局部编辑质量（越高越好）：
    - inside_mean_diff: 选区内变化强度（希望高）
    - outside_mean_diff: 选区外变化强度（希望低）
    - inside_outside_ratio: 内外变化比（希望高）
    - aspect_delta: 输出与原图宽高比偏移（希望低）
    - score: 综合分
    """
    try:
        base = Image.open(io.BytesIO(base_image)).convert("RGB")
        out = Image.open(io.BytesIO(output_image)).convert("RGB")
        mask = Image.open(io.BytesIO(mask_image)).convert("L")
    except Exception:
        return {
            "inside_mean_diff": 0.0,
            "outside_mean_diff": 1e6,
            "inside_outside_ratio": 0.0,
            "aspect_delta": 1.0,
            "score": -1e6,
        }

    base_w, base_h = base.size
    out_w, out_h = out.size
    aspect_delta = abs((out_w / max(out_h, 1)) - (base_w / max(base_h, 1)))

    # 对齐到 base 尺寸，不裁剪内容。
    out = ImageOps.pad(
        out,
        base.size,
        method=Image.BILINEAR,
        color=(128, 128, 128),
        centering=(0.5, 0.5),
    )
    mask = mask.resize(base.size, Image.NEAREST)

    base_s = base.resize((eval_size, eval_size), Image.BILINEAR)
    out_s = out.resize((eval_size, eval_size), Image.BILINEAR)
    mask_s = mask.resize((eval_size, eval_size), Image.NEAREST)

    inside_sum = 0.0
    outside_sum = 0.0
    inside_count = 0
    outside_count = 0

    for (br, bg, bb), (or_, og, ob), mv in zip(
        base_s.getdata(),
        out_s.getdata(),
        mask_s.getdata(),
    ):
        d = (abs(br - or_) + abs(bg - og) + abs(bb - ob)) / 3.0
        if mv > 127:
            inside_sum += d
            inside_count += 1
        else:
            outside_sum += d
            outside_count += 1

    inside_mean = inside_sum / max(inside_count, 1)
    outside_mean = outside_sum / max(outside_count, 1)
    ratio = inside_mean / (outside_mean + 1e-6)

    # 评分偏好：选区内有变化、选区外少变化、比例不漂移
    score = inside_mean + min(ratio, 6.0) * 4.0 - outside_mean * 2.2 - aspect_delta * 25.0
    return {
        "inside_mean_diff": inside_mean,
        "outside_mean_diff": outside_mean,
        "inside_outside_ratio": ratio,
        "aspect_delta": aspect_delta,
        "score": score,
    }
