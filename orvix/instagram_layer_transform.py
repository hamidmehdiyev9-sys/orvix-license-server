"""Hər qat üçün transform: crop → zoom → rotate → pan (1920×1080 məkanında düzbucaq)."""
from __future__ import annotations

import math
from typing import Any, Dict, Tuple

from PIL import Image

# instagram_layer_layout ilə dövrəvi import yoxdur
_CANVAS_W = 1920
_CANVAS_H = 1080


def _f(r: Dict[str, Any], key: str, default: float) -> float:
    try:
        return float(r.get(key, default))
    except (TypeError, ValueError):
        return float(default)


def _i(r: Dict[str, Any], key: str, default: int) -> int:
    try:
        return int(r.get(key, default))
    except (TypeError, ValueError):
        return int(default)


def default_transform_keys() -> Dict[str, Any]:
    return {
        "zoom": 1.0,
        "zoom_x": 1.0,
        "zoom_y": 1.0,
        "pan_x": 0.0,
        "pan_y": 0.0,
        "rotate_z": 0.0,
        "crop_x1": 0,
        "crop_y1": 0,
        "crop_x2": _CANVAS_W,
        "crop_y2": _CANVAS_H,
    }


def merge_layer_dict(base_rect: Dict[str, int], raw: Dict[str, Any] | None) -> Dict[str, Any]:
    """Rect + transform açarlarını birləşdirir."""
    out: Dict[str, Any] = dict(base_rect)
    t = default_transform_keys()
    if raw and isinstance(raw, dict):
        for k, v in t.items():
            if k in raw:
                try:
                    if k in ("crop_x1", "crop_y1", "crop_x2", "crop_y2"):
                        t[k] = int(raw[k])
                    else:
                        t[k] = float(raw[k])
                except (TypeError, ValueError):
                    pass
        out.update(t)
    else:
        out.update(t)
    return out


def _clamp_crop(cx1: int, cy1: int, cx2: int, cy2: int, iw: int, ih: int) -> Tuple[int, int, int, int]:
    iw = max(1, iw)
    ih = max(1, ih)
    cx1 = max(0, min(cx1, iw - 1))
    cy1 = max(0, min(cy1, ih - 1))
    cx2 = max(cx1 + 1, min(cx2, iw))
    cy2 = max(cy1 + 1, min(cy2, ih))
    return cx1, cy1, cx2, cy2


def render_image_to_dest_box(im: Image.Image, layer: Dict[str, Any]) -> Image.Image:
    """
    Mənbə şəkli (RGBA) → layın hədəf düzbucağı (w×h) içində transform.
    Çıxış: RGBA, ölçü (w, h).
    """
    w = max(2, _i(layer, "w", 100))
    h = max(2, _i(layer, "h", 100))
    zoom = max(0.05, _f(layer, "zoom", 1.0))
    zx = max(0.05, _f(layer, "zoom_x", 1.0))
    zy = max(0.05, _f(layer, "zoom_y", 1.0))
    pan_x = _f(layer, "pan_x", 0.0)
    pan_y = _f(layer, "pan_y", 0.0)
    rot = _f(layer, "rotate_z", 0.0)
    im = im.convert("RGBA")
    iw, ih = im.size
    cx1, cy1, cx2, cy2 = _clamp_crop(
        _i(layer, "crop_x1", 0),
        _i(layer, "crop_y1", 0),
        _i(layer, "crop_x2", iw),
        _i(layer, "crop_y2", ih),
        iw,
        ih,
    )
    cropped = im.crop((cx1, cy1, cx2, cy2))
    cw, ch = cropped.size
    nw = max(1, int(round(cw * zoom * zx)))
    nh = max(1, int(round(ch * zoom * zy)))
    scaled = cropped.resize((nw, nh), Image.LANCZOS)
    # FFmpeg rotate filter: müsbət bucaq saat əqrəbi — PIL müsbət əksinə istiqamətdə
    rotated = scaled.rotate(-rot, expand=True, resample=Image.BICUBIC, fillcolor=(0, 0, 0, 0))
    box = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ox = (w - rotated.width) // 2 + int(round(pan_x))
    oy = (h - rotated.height) // 2 + int(round(pan_y))
    box.paste(rotated, (ox, oy), rotated)
    return box


def paste_layer_on_canvas(
    out: Image.Image,
    im_rgba: Image.Image,
    layer: Dict[str, Any],
) -> None:
    """im_rgba — mənbə; layer — tam açarlar; out üzərinə (x,y) yapışdırır."""
    x = max(0, _i(layer, "x", 0))
    y = max(0, _i(layer, "y", 0))
    w = max(2, _i(layer, "w", 100))
    h = max(2, _i(layer, "h", 100))
    w = min(w, _CANVAS_W - x)
    h = min(h, _CANVAS_H - y)
    layer_adj = dict(layer)
    layer_adj["w"] = w
    layer_adj["h"] = h
    tile = render_image_to_dest_box(im_rgba, layer_adj)
    out.paste(tile, (x, y), tile)


def main_video_frame_to_dest_box(frame_rgb: Image.Image, layer: Dict[str, Any]) -> Image.Image:
    """Video kadrı (RGB) → mərkəz qatı düzbucağı."""
    return render_image_to_dest_box(frame_rgb.convert("RGBA"), layer)


def ffmpeg_rotate_rad(deg: float) -> float:
    """FFmpeg rotate filter üçün radian (saat əqrəbi müsbət)."""
    return deg * math.pi / 180.0
