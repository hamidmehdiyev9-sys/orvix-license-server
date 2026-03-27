# -*- coding: utf-8 -*-
"""FFmpeg CUDA / NVENC: qabiliyyət yoxlaması və encoder arqumentləri."""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class CudaCaps:
    nvenc_h264: bool = False
    nvenc_hevc: bool = False
    cuda_hwaccel: bool = False


def probe_cuda_capabilities(ffmpeg_path: Optional[str], startupinfo=None) -> CudaCaps:
    """FFmpeg binarında h264_nvenc / hevc_nvenc və -hwaccel cuda mövcudluğu."""
    caps = CudaCaps()
    if not ffmpeg_path or not os.path.isfile(ffmpeg_path):
        return caps
    try:
        r = subprocess.run(
            [ffmpeg_path, "-hide_banner", "-encoders"],
            capture_output=True,
            text=True,
            timeout=45,
            startupinfo=startupinfo,
        )
        blob = (r.stdout or "") + (r.stderr or "")
        if "h264_nvenc" in blob:
            caps.nvenc_h264 = True
        if "hevc_nvenc" in blob:
            caps.nvenc_hevc = True
    except Exception:
        pass
    try:
        r = subprocess.run(
            [ffmpeg_path, "-hide_banner", "-hwaccels"],
            capture_output=True,
            text=True,
            timeout=20,
            startupinfo=startupinfo,
        )
        blob = (r.stdout or "") + (r.stderr or "")
        if "cuda" in blob.lower():
            caps.cuda_hwaccel = True
    except Exception:
        pass
    return caps


def map_lib_codec_to_nvenc(vc: str, caps: Optional[CudaCaps]) -> str:
    """libx264/libx265 → NVENC (GPU mövcuddursa)."""
    if not caps:
        return vc
    if vc == "libx264" and caps.nvenc_h264:
        return "h264_nvenc"
    if vc == "libx265" and caps.nvenc_hevc:
        return "hevc_nvenc"
    return vc


def hwaccel_cuda_prefix(caps: Optional[CudaCaps]) -> List[str]:
    if caps and caps.cuda_hwaccel:
        return ["-hwaccel", "cuda"]
    return []


def social_main_export_video_args(vc: str, vb: str, fps: str, caps: Optional[CudaCaps]) -> List[str]:
    """Social əsas export: -c:v … -preset … -b:v … -r … -pix_fmt (NVENC uyğun)."""
    vc = map_lib_codec_to_nvenc(vc, caps)
    if vc in ("h264_nvenc", "hevc_nvenc"):
        return ["-c:v", vc, "-preset", "p5", "-b:v", vb, "-r", str(fps), "-pix_fmt", "yuv420p"]
    if vc == "libx265":
        return ["-c:v", vc, "-preset", "fast", "-b:v", vb, "-r", str(fps), "-pix_fmt", "yuv420p"]
    return ["-c:v", vc, "-preset", "fast", "-b:v", vb, "-r", str(fps), "-pix_fmt", "yuv420p"]


def instagram_simple_video_args(
    vc: str, compress: bool, vb: str, fps: str, caps: Optional[CudaCaps]
) -> List[str]:
    """Instagram sadə convert: -r fps, sonra video parametrləri."""
    vc = map_lib_codec_to_nvenc(vc, caps)
    out: List[str] = ["-r", str(fps), "-c:v", vc, "-pix_fmt", "yuv420p"]
    if vc in ("h264_nvenc", "hevc_nvenc"):
        out += ["-preset", "p5"]
        if compress:
            out += ["-cq", "23" if vc == "h264_nvenc" else "28"]
        else:
            out += ["-b:v", vb]
    else:
        out += ["-preset", "fast"]
        if compress:
            out += ["-crf", "23" if vc == "libx264" else "28"]
        else:
            out += ["-b:v", vb]
    return out


def compose_layer_video_args(caps: Optional[CudaCaps]) -> List[str]:
    """instagram_layers_ffmpeg birləşmə."""
    vc = map_lib_codec_to_nvenc("libx264", caps)
    if vc == "h264_nvenc":
        return ["-c:v", "h264_nvenc", "-preset", "p5", "-cq", "20", "-pix_fmt", "yuv420p"]
    return ["-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p"]


def ve_preview_video_args(caps: Optional[CudaCaps]) -> List[str]:
    if caps and caps.nvenc_h264:
        return ["-c:v", "h264_nvenc", "-preset", "p1", "-cq", "23", "-an"]
    return ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "23", "-an"]


def ve_export_video_audio_args(caps: Optional[CudaCaps]) -> List[str]:
    if caps and caps.nvenc_h264:
        return ["-c:v", "h264_nvenc", "-preset", "p5", "-cq", "18", "-c:a", "aac", "-b:a", "192k"]
    return ["-c:v", "libx264", "-preset", "fast", "-crf", "18", "-c:a", "aac", "-b:a", "192k"]


def edit_export_video_args(caps: Optional[CudaCaps], crf: str = "20") -> List[str]:
    if caps and caps.nvenc_h264:
        return ["-c:v", "h264_nvenc", "-preset", "p5", "-cq", crf]
    return ["-c:v", "libx264", "-preset", "fast", "-crf", crf]
