"""Instagram 4-layer layout (1920×1080) — düzbucaq + transform parametrləri."""
from __future__ import annotations

import json
from typing import Any, Dict

from orvix.instagram_layer_transform import default_transform_keys, merge_layer_dict

CANVAS_W = 1920
CANVAS_H = 1080

_LAYER_KEYS = ("bg", "top", "bottom", "center")


def default_layout() -> Dict[str, Dict[str, Any]]:
    return {
        "bg": merge_layer_dict({"x": 0, "y": 0, "w": CANVAS_W, "h": CANVAS_H}, None),
        "top": merge_layer_dict({"x": 0, "y": 0, "w": CANVAS_W, "h": 240}, None),
        "bottom": merge_layer_dict({"x": 0, "y": 840, "w": CANVAS_W, "h": 240}, None),
        "center": merge_layer_dict({"x": 360, "y": 180, "w": 1200, "h": 720}, None),
    }


def parse_layout_json(raw: str | None) -> Dict[str, Dict[str, Any]]:
    base = default_layout()
    if not raw or not str(raw).strip():
        return base
    try:
        d: Any = json.loads(raw)
        if not isinstance(d, dict):
            return base
        for k in _LAYER_KEYS:
            if k not in d or not isinstance(d[k], dict):
                continue
            r = d[k]
            rect = {
                "x": int(r.get("x", base[k]["x"])),
                "y": int(r.get("y", base[k]["y"])),
                "w": int(r.get("w", base[k]["w"])),
                "h": int(r.get("h", base[k]["h"])),
            }
            base[k] = merge_layer_dict(rect, r)
        return _clamp_layout(base)
    except Exception:
        return base


def layout_to_json(layout: Dict[str, Dict[str, Any]]) -> str:
    return json.dumps(_clamp_layout(layout), separators=(",", ":"))


def _clamp_layout(layout: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out = default_layout()
    for k in _LAYER_KEYS:
        if k not in layout:
            continue
        r = layout[k]
        x = max(0, min(int(r.get("x", 0)), CANVAS_W - 2))
        y = max(0, min(int(r.get("y", 0)), CANVAS_H - 2))
        w = max(2, min(int(r.get("w", 100)), CANVAS_W - x))
        h = max(2, min(int(r.get("h", 100)), CANVAS_H - y))
        rect = {"x": x, "y": y, "w": w, "h": h}
        merged = merge_layer_dict(rect, r)
        # crop həddi
        merged["crop_x1"] = max(0, int(merged.get("crop_x1", 0)))
        merged["crop_y1"] = max(0, int(merged.get("crop_y1", 0)))
        merged["crop_x2"] = max(merged["crop_x1"] + 1, int(merged.get("crop_x2", CANVAS_W)))
        merged["crop_y2"] = max(merged["crop_y1"] + 1, int(merged.get("crop_y2", CANVAS_H)))
        merged["zoom"] = max(0.05, min(8.0, float(merged.get("zoom", 1.0))))
        merged["zoom_x"] = max(0.05, min(8.0, float(merged.get("zoom_x", 1.0))))
        merged["zoom_y"] = max(0.05, min(8.0, float(merged.get("zoom_y", 1.0))))
        merged["pan_x"] = max(-CANVAS_W, min(CANVAS_W, float(merged.get("pan_x", 0.0))))
        merged["pan_y"] = max(-CANVAS_H, min(CANVAS_H, float(merged.get("pan_y", 0.0))))
        merged["rotate_z"] = max(-360.0, min(360.0, float(merged.get("rotate_z", 0.0))))
        out[k] = merged
    return out
