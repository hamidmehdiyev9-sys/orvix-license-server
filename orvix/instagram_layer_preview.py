"""Instagram 1920×1080 önizləmə: video + qat şəkilləri (transform ilə)."""
from __future__ import annotations

import os
from typing import Dict, Optional, Tuple

import numpy as np
from PIL import Image

from orvix.instagram_layer_layout import CANVAS_H, CANVAS_W
from orvix.instagram_layer_transform import main_video_frame_to_dest_box, paste_layer_on_canvas

_VIDEO_EXT = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".wmv", ".flv", ".ts", ".mpg", ".m4v"}


def _norm_layer_path(path: str) -> str:
    """Windows: C:/... və C:\\... eyni faylı göstərir; boşluq/tırnak təmizlənir."""
    if not path or not str(path).strip():
        return ""
    p = str(path).strip().strip('"').strip("'")
    try:
        return os.path.normpath(os.path.abspath(p))
    except Exception:
        return p


def _open_layer_rgba(path: str) -> Optional[Image.Image]:
    """Şəkil və ya video faylının ilk kadırı (önizləmə üçün)."""
    pn = _norm_layer_path(path)
    if not pn or not os.path.isfile(pn):
        return None
    ext = os.path.splitext(pn)[1].lower()
    if ext in _VIDEO_EXT:
        import time

        import cv2

        # Eyni faylı əsas pleyer də açanda bəzən birinci oxuma uğursuz olur — bir neçə cəhd.
        for attempt in range(5):
            cap = None
            try:
                cap = cv2.VideoCapture(pn)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        return Image.fromarray(np.ascontiguousarray(rgb)).convert("RGBA")
            except Exception:
                pass
            finally:
                if cap is not None:
                    try:
                        cap.release()
                    except Exception:
                        pass
            time.sleep(0.05 * (attempt + 1))
        return None
    try:
        return Image.open(pn).convert("RGBA")
    except Exception:
        return None


class _ImgCache:
    def __init__(self) -> None:
        self._path: Optional[str] = None
        self._img: Optional[Image.Image] = None

    def get(self, path: str) -> Optional[Image.Image]:
        pn = _norm_layer_path(path)
        if not pn or not os.path.isfile(pn):
            return None
        if self._path == pn and self._img is not None:
            return self._img.copy()
        im = _open_layer_rgba(pn)
        if im is None:
            self._path = None
            self._img = None
            return None
        self._path = pn
        self._img = im
        return im.copy()

    def clear(self) -> None:
        self._path = None
        self._img = None


_cache_bg = _ImgCache()
_cache_top = _ImgCache()
_cache_bot = _ImgCache()
_cache_cen = _ImgCache()


def composite_1920_frame(
    frame_rgb: np.ndarray,
    layout: Dict[str, Dict[str, Any]],
    paths: Dict[str, str],
) -> np.ndarray:
    """
    frame_rgb: mənbə video kadrı (RGB).
    Çıxış: 1920×1080 RGB uint8 (qatlar + video mərkəzdə).
    """
    if frame_rgb is None or frame_rgb.size == 0:
        return frame_rgb
    out = Image.new("RGB", (CANVAS_W, CANVAS_H), (0, 0, 0))

    def paste_img(key: str, cache: _ImgCache) -> None:
        p = (paths.get(key) or "").strip()
        if not p or not os.path.isfile(p):
            return
        layer = layout.get(key) or {}
        im = cache.get(p)
        if im is None:
            return
        paste_layer_on_canvas(out, im, layer)

    paste_img("bg", _cache_bg)
    paste_img("top", _cache_top)
    paste_img("bottom", _cache_bot)

    rc = layout.get("center") or {}
    try:
        vid = Image.fromarray(np.ascontiguousarray(frame_rgb)).convert("RGB")
        tile = main_video_frame_to_dest_box(vid, rc)
        cx, cy = int(rc.get("x", 0)), int(rc.get("y", 0))
        if tile.mode == "RGBA":
            out.paste(tile, (cx, cy), tile)
        else:
            out.paste(tile, (cx, cy))
    except Exception:
        pass

    p = _norm_layer_path((paths.get("center") or "").strip())
    if p and os.path.isfile(p):
        im = _cache_cen.get(p)
        if im is not None:
            paste_layer_on_canvas(out, im, rc)

    return np.asarray(out, dtype=np.uint8)


def clear_preview_caches() -> None:
    _cache_bg.clear()
    _cache_top.clear()
    _cache_bot.clear()
    _cache_cen.clear()


def crop_window_1920_for_output(tw: int, th: int) -> Tuple[int, int, int, int]:
    """
    1920×1080 kadrda mərkəz kəsmə pəncərəsi (video_player._crop_frame_to_aspect ilə eyni məntiq).
    Qaytarır: x0, y0, crop_w, crop_h (mənbə koordinatlarında).
    """
    W, H = CANVAS_W, CANVAS_H
    if tw < 1 or th < 1:
        return 0, 0, W, H
    tar = tw / float(th)
    sar = W / float(H)
    if sar > tar:
        crop_w = int(round(H * tar))
        x0 = max(0, (W - crop_w) // 2)
        return x0, 0, crop_w, H
    crop_h = int(round(W / tar))
    y0 = max(0, (H - crop_h) // 2)
    return 0, y0, W, crop_h
