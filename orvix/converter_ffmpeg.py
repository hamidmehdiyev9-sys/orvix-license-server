# -*- coding: utf-8 -*-
"""Video Converter — FFmpeg command construction and validation."""
from __future__ import annotations

import os
import re
import shlex
import subprocess
from typing import Any, Dict, List, Optional, Tuple

INPUT_EXTENSIONS = (
    ".mp4", ".mkv", ".mov", ".avi", ".flv", ".wmv", ".webm", ".m2v", ".mpg", ".mpeg",
    ".ts", ".m2ts", ".ogv", ".gif", ".hevc", ".m4v", ".3gp",
)

SCALE_FLAGS = {
    "Bilinear": "bilinear",
    "Bicubic": "bicubic",
    "Lanczos": "lanczos",
}


def validate_input_path(path: str) -> Tuple[bool, str]:
    if not path or not path.strip():
        return False, "Input path is empty."
    p = os.path.abspath(path.strip())
    if not os.path.isfile(p):
        return False, "File not found."
    if not os.access(p, os.R_OK):
        return False, "File is not readable."
    return True, ""


def probe_input_health(ffprobe_path: Optional[str], path: str, startupinfo=None) -> Tuple[bool, str]:
    """
    Whether FFprobe can read the file (quick health check).
    'moov atom not found' usually indicates a truncated or corrupt MP4/MOV.
    """
    if not ffprobe_path or not path or not os.path.isfile(path):
        return True, ""
    try:
        cmd = [
            ffprobe_path,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            path,
        ]
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            startupinfo=startupinfo,
        )
        err = (r.stderr or "").lower()
        out = (r.stdout or "").strip()
        if "moov atom not found" in err:
            return (
                False,
                "This MP4/MOV appears incomplete or corrupt (moov atom not found).\n"
                "Use a fully downloaded file or another copy.",
            )
        if "invalid data found when processing input" in err:
            return False, "Invalid or unreadable data (damaged or unsupported format)."
        if r.returncode != 0 and not out:
            tail = (r.stderr or "").strip()[:200]
            if tail:
                return False, f"FFprobe: {tail}"
        return True, ""
    except Exception:
        return True, ""


def suggest_container_for_codecs(vcodec: str, container: str) -> Tuple[str, Optional[str]]:
    warn = None
    c = container.lower().strip(".")
    if vcodec.startswith("prores") and c not in ("mov", "mkv", "mxf"):
        return "mov", "MOV is recommended for ProRes."
    return c, warn


def map_hw_video_encoder(choice: str) -> Optional[str]:
    """CUDA/NVENC çıxarılıb — yalnız proqram təminatı və Intel QSV (CUDA-dan əvvəlki məntiqlə uyğun)."""
    return {
        "Software (default)": None,
        "Intel QSV H.264": "h264_qsv",
        "Intel QSV HEVC": "hevc_qsv",
    }.get(choice)


def _win_font_file(family: str) -> str:
    fonts = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts")
    m = {"Arial": "arial.ttf", "Segoe UI": "segoeui.ttf", "Consolas": "consola.ttf", "Times": "times.ttf"}
    fn = m.get(family, "arial.ttf")
    p = os.path.join(fonts, fn)
    return p.replace("\\", "/") if os.path.isfile(p) else ""


def build_ffmpeg_command(
    ffmpeg_bin: str,
    inp: str,
    out: str,
    settings: Dict[str, Any],
    *,
    progress_pipe: bool = True,
    seek_seconds: float = 0.0,
) -> Tuple[List[str], Optional[str]]:
    """
    Returns (cmd, filter_complex_or_none). Image overlay uses filter_complex when present.
    seek_seconds: accurate input seek after -i (resume / partial re-encode).
    """
    cmd: List[str] = [ffmpeg_bin, "-y"]

    hw = settings.get("hwaccel", "none")
    if hw == "qsv":
        cmd += ["-hwaccel", "qsv"]

    # Image overlay: second input
    oimg = (settings.get("overlay_image") or "").strip()
    use_img = oimg and os.path.isfile(oimg)

    ss = max(0.0, float(seek_seconds or 0.0))
    ss_arg = [str(ss)] if ss > 0.001 else []

    if use_img:
        cmd += ["-i", inp]
        if ss_arg:
            cmd += ["-ss"] + ss_arg
        cmd += ["-i", oimg]
        main_idx, aux_idx = "0", "1"
    else:
        cmd += ["-i", inp]
        if ss_arg:
            cmd += ["-ss"] + ss_arg
        main_idx = "0"

    vf_parts: List[str] = []

    res = settings.get("resolution", "Original")
    cw = (settings.get("custom_w") or "").strip()
    ch = (settings.get("custom_h") or "").strip()
    flag = SCALE_FLAGS.get(settings.get("scale_method", "Lanczos"), "lanczos")

    if res == "Custom" and cw.isdigit() and ch.isdigit():
        vf_parts.append(f"scale={cw}:{ch}:flags={flag}")
    elif res not in ("Original", "Custom") and "x" in str(res):
        w, h = str(res).split("x", 1)
        vf_parts.append(f"scale={int(w)}:{int(h)}:flags={flag}")

    if settings.get("scan_type", "").startswith("Interlaced"):
        vf_parts.append("yadif=mode=1:parity=-1:deint=1")

    fps = settings.get("fps", "Original")
    cfps = (settings.get("custom_fps") or "").strip()
    fps_val = cfps if fps == "Custom" and cfps else (fps if fps not in ("Original", "Custom") else "")
    if fps_val:
        try:
            float(fps_val)
            vf_parts.append(f"fps={fps_val}")
        except ValueError:
            pass

    if settings.get("frame_interpolate"):
        vf_parts.append("minterpolate=fps=60:mi_mode=mci")

    otxt = (settings.get("overlay_text") or "").strip()
    if otxt:
        size = int(settings.get("overlay_text_size", 24) or 24)
        color = (settings.get("overlay_text_color") or "#FFFFFF").lstrip("#")
        op = float(settings.get("overlay_opacity", 80) or 80) / 100.0
        ox = settings.get("overlay_x", "10") or "10"
        oy = settings.get("overlay_y", "10") or "10"
        ff = _win_font_file(settings.get("overlay_font", "Arial"))
        esc = otxt.replace("'", "\\'").replace(":", "\\:")
        dt = f"drawtext=text='{esc}'"
        if ff:
            dt += f":fontfile='{ff}'"
        dt += f":fontsize={size}:fontcolor=0x{color}@{op:.2f}:x={ox}:y={oy}"
        anim = settings.get("overlay_anim", "None")
        if anim == "Fade in":
            dt += ":alpha='if(lt(t,1)\\,t\\,1)'"
        vf_parts.append(dt)

    vcodec_ui = settings.get("vcodec", "libx264")
    hw_enc = map_hw_video_encoder(settings.get("hw_encoder", "Software (default)"))
    vcodec = hw_enc or vcodec_ui

    af_parts: List[str] = []
    vol = float(settings.get("volume", 100) or 100) / 100.0
    if settings.get("mute_audio"):
        af_parts.append("volume=0")
    elif abs(vol - 1.0) > 0.001:
        af_parts.append(f"volume={vol:.4f}")
    if settings.get("normalize_audio"):
        af_parts.append("loudnorm=I=-16:TP=-1.5:LRA=11")
    ch = settings.get("audio_channels", "stereo")
    if ch == "mono":
        af_parts.append("channelmap=channel_layout=mono")
    elif ch == "5.1":
        af_parts.append("channelmap=channel_layout=5.1")

    # Video path: filter_complex or -vf
    if use_img:
        ix = settings.get("overlay_img_x", "10") or "10"
        iy = settings.get("overlay_img_y", "10") or "10"
        iw = settings.get("overlay_img_w", "-1") or "-1"
        ih = settings.get("overlay_img_h", "-1") or "-1"
        vf_chain = ",".join(vf_parts) if vf_parts else "format=yuv420p"
        fc = (
            f"[{main_idx}:v]{vf_chain}[v1];"
            f"[{aux_idx}:v]scale={iw}:{ih}[ov];"
            f"[v1][ov]overlay={ix}:{iy}[vout]"
        )
        cmd2 = cmd + ["-filter_complex", fc, "-map", "[vout]", "-map", "0:a?"]
    else:
        if vf_parts:
            cmd2 = cmd + ["-vf", ",".join(vf_parts)]
        else:
            cmd2 = cmd

    acodec = settings.get("acodec", "aac")
    bd = settings.get("bit_depth", "16-bit")
    if acodec in ("pcm_s16le", "pcm_s24le"):
        acodec = "pcm_s24le" if bd == "24-bit" else "pcm_s16le"

    cmd2 += ["-c:v", vcodec]

    abr_no_crf = bool(settings.get("abr_no_crf"))

    if vcodec in ("libx264", "libx265"):
        cmd2 += ["-preset", settings.get("preset", "medium")]
        crf = str(settings.get("crf", "23")).strip()
        if crf and not abr_no_crf:
            cmd2 += ["-crf", crf]
    elif vcodec in ("h264_qsv", "hevc_qsv"):
        cmd2 += ["-preset", settings.get("preset", "medium")]
        crf = str(settings.get("crf", "23")).strip()
        if crf and not abr_no_crf:
            cmd2 += ["-global_quality", crf]

    vb = settings.get("video_bitrate", "Auto")
    if vb and vb != "Auto" and vcodec != "copy":
        cmd2 += ["-b:v", vb]
        if abr_no_crf:
            vs = str(vb).strip().lower()
            try:
                if vs.endswith("k"):
                    nk = float(vs[:-1])
                    cmd2 += ["-maxrate", vb, "-bufsize", f"{int(max(nk * 2, 1))}k"]
                elif vs.endswith("m"):
                    nm = float(vs[:-1])
                    cmd2 += ["-maxrate", vb, "-bufsize", f"{nm * 2:.2f}M"]
            except (ValueError, TypeError):
                pass

    pix = (settings.get("pix_fmt") or "").strip()
    if pix:
        cmd2 += ["-pix_fmt", pix]

    cmd2 += ["-c:a", acodec]
    if acodec == "aac":
        cmd2 += ["-aac_coder", "fast"]
    ab = settings.get("audio_bitrate", "192k")
    if ab and ab != "Auto" and not str(acodec).startswith("pcm"):
        cmd2 += ["-b:a", ab]

    sr = settings.get("sample_rate", "Original")
    if sr and sr != "Original":
        cmd2 += ["-ar", str(sr)]

    if af_parts:
        cmd2 += ["-af", ",".join(af_parts)]

    th = str(settings.get("threads", "0") or "0").strip()
    if th == "0" or th == "":
        cmd2 += ["-threads", "0"]
    else:
        cmd2 += ["-threads", th]

    extra = (settings.get("extra_ffmpeg") or "").strip()
    if extra:
        try:
            cmd2 += shlex.split(extra, posix=os.name != "nt")
        except ValueError:
            pass

    # On Windows, -progress pipe:1 is often unreliable; stderr time= parsing is used instead.
    # -nostats suppressed that output — omitted.
    if progress_pipe:
        cmd2 += ["-hide_banner"]

    mf = (settings.get("movflags") or "").strip()
    if mf:
        cmd2 += ["-movflags", mf]

    cmd2.append(out)
    return cmd2, None


def validate_settings(settings: Dict[str, Any], inp: str, out: str) -> Tuple[bool, str]:
    ok, msg = validate_input_path(inp)
    if not ok:
        return False, msg
    if not (out or "").strip():
        return False, "Output path is empty."
    return True, ""


def unique_output_path(path: str) -> str:
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    n = 1
    while os.path.exists(f"{base}_{n}{ext}"):
        n += 1
    return f"{base}_{n}{ext}"


def pattern_to_filename(pattern: str, inp: str, settings: Dict[str, Any], ext: str) -> str:
    import datetime as _dt
    name = os.path.splitext(os.path.basename(inp))[0]
    res = settings.get("resolution", "orig")
    if res == "Original":
        res = "orig"
    fps = settings.get("fps", "fps")
    if fps == "Original":
        fps = "orig"
    codec = settings.get("vcodec", "v")
    ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    s = pattern
    s = s.replace("{name}", name)
    s = s.replace("{res}", str(res).replace(" ", ""))
    s = s.replace("{fps}", str(fps))
    s = s.replace("{codec}", str(codec))
    s = s.replace("{date}_{time}", ts)
    s = s.replace("{date}", ts.split("_")[0])
    s = s.replace("{time}", ts.split("_")[-1] if "_" in ts else ts)
    if not s.endswith(ext):
        s = s + ext
    return s
