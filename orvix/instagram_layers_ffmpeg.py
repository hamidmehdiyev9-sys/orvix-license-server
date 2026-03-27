"""FFmpeg: əsas video + 1920×1080 qatlar (transform; şəkillər əvvəlcə PIL ilə)."""
from __future__ import annotations

import math
import os
import subprocess
import tempfile
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image

from orvix.ffmpeg_core import ffmpeg_mgr
from orvix.ffmpeg_cuda import compose_layer_video_args, hwaccel_cuda_prefix
from orvix.instagram_layer_layout import CANVAS_H, CANVAS_W
from orvix.instagram_layer_transform import render_image_to_dest_box

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".wmv", ".flv", ".ts", ".mpg", ".m4v"}


def _probe_video_wh(path: str) -> Tuple[int, int]:
    try:
        import cv2

        cap = cv2.VideoCapture(path)
        if cap.isOpened():
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1920)
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 1080)
            cap.release()
            return max(16, w), max(16, h)
    except Exception:
        pass
    return 1920, 1080


def _clamp_crop(cx1: int, cy1: int, cx2: int, cy2: int, iw: int, ih: int) -> Tuple[int, int, int, int]:
    iw = max(1, iw)
    ih = max(1, ih)
    cx1 = max(0, min(cx1, iw - 1))
    cy1 = max(0, min(cy1, ih - 1))
    cx2 = max(cx1 + 1, min(cx2, iw))
    cy2 = max(cy1 + 1, min(cy2, ih))
    return cx1, cy1, cx2, cy2


def _build_main_video_filter(layout_center: Dict[str, Any], iw: int, ih: int) -> str:
    """[0:v] → [mainp] — mərkəz qatı transform (rəqəmli)."""
    r = layout_center
    cx1, cy1, cx2, cy2 = _clamp_crop(
        int(r.get("crop_x1", 0)),
        int(r.get("crop_y1", 0)),
        int(r.get("crop_x2", iw)),
        int(r.get("crop_y2", ih)),
        iw,
        ih,
    )
    cw0, ch0 = cx2 - cx1, cy2 - cy1
    zoom = float(r.get("zoom", 1.0))
    zx = float(r.get("zoom_x", 1.0))
    zy = float(r.get("zoom_y", 1.0))
    sw = max(1, int(round(cw0 * zoom * zx)))
    sh = max(1, int(round(ch0 * zoom * zy)))
    rot = float(r.get("rotate_z", 0.0))
    rad = rot * math.pi / 180.0
    dw = max(2, int(r.get("w", 100)))
    dh = max(2, int(r.get("h", 100)))
    px = int(round(float(r.get("pan_x", 0.0))))
    py = int(round(float(r.get("pan_y", 0.0))))

    fl: List[str] = [
        f"crop={cw0}:{ch0}:{cx1}:{cy1}",
        f"scale={sw}:{sh}:flags=lanczos",
    ]
    if abs(rot) > 0.01:
        fl.append("format=rgba")
        fl.append(f"rotate={rad:.6f}:fillcolor=0x00000000")
    fl.append(f"scale={dw}:{dh}:force_original_aspect_ratio=decrease")
    fl.append(f"pad={dw}:{dh}:(ow-iw)/2+{px}:(oh-ih)/2+{py}")
    body = ",".join(fl)
    return f"[0:v]{body}[mainp]"


def prerender_image_layers(
    layers: Dict[str, str],
    layout: Dict[str, Dict[str, Any]],
    cleanup_list: List[str],
) -> Dict[str, str]:
    """Şəkil qatlarını w×h PNG-ə çevirir (transform tətbiq)."""
    out: Dict[str, str] = dict(layers)
    for name in ("bg", "top", "bottom", "center"):
        p = (layers.get(name) or "").strip()
        if not p or not os.path.isfile(p):
            continue
        if os.path.splitext(p)[1].lower() in VIDEO_EXTS:
            continue
        try:
            im = Image.open(p).convert("RGBA")
            tile = render_image_to_dest_box(im, layout.get(name) or {})
            fd, tpath = tempfile.mkstemp(suffix=".png")
            os.close(fd)
            tile.save(tpath)
            cleanup_list.append(tpath)
            out[name] = tpath
        except Exception:
            pass
    return out


def _build_filter_complex(
    layer_inputs: Dict[str, int],
    layout: Dict[str, Dict[str, Any]],
    main_iw: int,
    main_ih: int,
) -> str:
    """Əvvəl [0:v]→[mainp], sonra qara [1:v] üzərində qatlar + video + orta şəkil."""
    parts: List[str] = []
    n = 0

    def nxt() -> str:
        nonlocal n
        n += 1
        return f"lay{n}"

    main_chain = _build_main_video_filter(layout.get("center") or {}, main_iw, main_ih)
    parts.append(main_chain)

    stream = "1:v"
    for name in ("bg", "top", "bottom"):
        if name not in layer_inputs:
            continue
        ix = layer_inputs[name]
        r = layout[name]
        x, y = int(r["x"]), int(r["y"])
        lab = nxt()
        parts.append(f"[{ix}:v]format=rgba[{name}p]")
        parts.append(f"[{stream}][{name}p]overlay={x}:{y}[{lab}]")
        stream = lab

    r = layout.get("center") or {}
    cx, cy = int(r.get("x", 0)), int(r.get("y", 0))
    labv = nxt()
    parts.append(f"[{stream}][mainp]overlay={cx}:{cy}[{labv}]")
    stream = labv

    if "center" in layer_inputs:
        ix = layer_inputs["center"]
        x, y = cx, cy
        lab = nxt()
        parts.append(f"[{ix}:v]format=rgba[cenp]")
        parts.append(f"[{stream}][cenp]overlay={x}:{y}[{lab}]")
        stream = lab

    parts.append(f"[{stream}]format=yuv420p[vout]")
    return ";".join(parts)


def build_compose_command(
    ffmpeg_path: str,
    main_path: str,
    layers: Dict[str, str],
    layout: Dict[str, Dict[str, Any]],
    *,
    start_t: float,
    target_dur: Optional[float],
    out_path: str,
    has_audio: bool,
    cleanup_list: Optional[List[str]] = None,
) -> List[str]:
    cleanup_list = cleanup_list if cleanup_list is not None else []
    layers_use = prerender_image_layers(layers, layout, cleanup_list)
    main_iw, main_ih = _probe_video_wh(main_path)

    cmd: List[str] = [ffmpeg_path, "-y"] + hwaccel_cuda_prefix(getattr(ffmpeg_mgr, "cuda_caps", None))
    if start_t > 0:
        cmd += ["-ss", f"{start_t:.3f}"]
    cmd += ["-i", main_path]
    cmd += ["-f", "lavfi", "-i", f"color=c=black:s={CANVAS_W}x{CANVAS_H}:r=30"]
    idx = 2
    layer_inputs: Dict[str, int] = {}
    for name in ("bg", "top", "bottom", "center"):
        p = (layers_use.get(name) or "").strip()
        if not p or not os.path.isfile(p):
            continue
        ext = os.path.splitext(p)[1].lower()
        if ext in VIDEO_EXTS:
            cmd += ["-stream_loop", "-1", "-i", p]
        else:
            cmd += ["-loop", "1", "-i", p]
        layer_inputs[name] = idx
        idx += 1

    fc = _build_filter_complex(layer_inputs, layout, main_iw, main_ih)
    cmd += ["-filter_complex", fc]
    cmd += ["-map", "[vout]"]
    if has_audio:
        cmd += ["-map", "0:a"]
    else:
        cmd += ["-an"]
    if target_dur is not None and target_dur > 0:
        cmd += ["-t", f"{target_dur:.3f}"]
    cmd += compose_layer_video_args(getattr(ffmpeg_mgr, "cuda_caps", None))
    if has_audio:
        # Meta IG video: AAC 128 kb/s, 48 kHz; MP4 + moov əvvəldə (Graph API uyğun)
        cmd += ["-c:a", "aac", "-b:a", "128k", "-ar", "48000"]
    cmd += ["-shortest", "-movflags", "+faststart", out_path]
    return cmd


def run_compose(
    ffmpeg_path: str,
    main_path: str,
    layers: Dict[str, str],
    layout: Dict[str, Dict[str, Any]],
    *,
    start_t: float,
    target_dur: Optional[float],
    out_path: str,
    has_audio: bool,
    log_fn: Optional[Any] = None,
) -> Tuple[bool, str]:
    cleanup: List[str] = []
    cmd = build_compose_command(
        ffmpeg_path,
        main_path,
        layers,
        layout,
        start_t=start_t,
        target_dur=target_dur,
        out_path=out_path,
        has_audio=has_audio,
        cleanup_list=cleanup,
    )
    if log_fn:
        try:
            log_fn("INSTAGRAM LAYER COMPOSE: " + " ".join(cmd))
        except Exception:
            pass
    try:
        si = ffmpeg_mgr._get_startupinfo()
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=7200,
            startupinfo=si,
        )
        for tp in cleanup:
            try:
                os.remove(tp)
            except Exception:
                pass
        if r.returncode != 0:
            err = (r.stderr or r.stdout or "")[-4000:]
            return False, err or "FFmpeg failed"
        return True, ""
    except Exception as e:
        for tp in cleanup:
            try:
                os.remove(tp)
            except Exception:
                pass
        return False, str(e)
