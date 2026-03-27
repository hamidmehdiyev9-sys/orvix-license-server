"""
VIDEO ENHANCEMENT — FFmpeg filter graph from boolean flags.
Order: deinterlace → stabilize → denoise → scale → color/HDR → sharpen → artifacts → frame → analog.
Where a dedicated engine is unavailable (AI, QTGMC, Dolby Vision), FFmpeg approximations and notes apply.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Tuple


def _lut_path_ffmpeg(path: str) -> str:
    p = os.path.normpath(path).replace("\\", "/")
    p = p.replace(":", r"\:", 1) if os.name == "nt" else p
    p = p.replace("'", r"\'")
    return p


def _on(flags: Dict[str, Any], k: str) -> bool:
    try:
        return bool(flags.get(k))
    except Exception:
        return False


def build_ve_video_filter(flags: Dict[str, Any], lut_path: str = "") -> Tuple[str, List[str]]:
    """
    Returns (comma-separated -vf chain, list of human-readable notes/warnings).
    """
    warnings: List[str] = []

    deint: List[str] = []
    if _on(flags, "ve_bwdif"):
        deint.append("bwdif=mode=send_field:parity=auto")
    elif _on(flags, "ve_yadif") or _on(flags, "ve_qtgmc"):
        deint.append("yadif=mode=1:parity=-1:deint=1")
        if _on(flags, "ve_qtgmc"):
            warnings.append("QTGMC: requires VapourSynth/Avisynth; using yadif instead.")
    elif _on(flags, "ve_auto_deint"):
        deint.append("yadif=mode=0:parity=-1:deint=1")

    stab: List[str] = []
    if any(_on(flags, k) for k in ("ve_vid_stab", "ve_motion_stab", "ve_shake_reduce", "ve_warp_stab")):
        stab.append("deshake")
        if _on(flags, "ve_warp_stab"):
            warnings.append("Warp stabilization: using deshake (libvidstab not bundled).")

    noise: List[str] = []
    if _on(flags, "ve_denoise_3d"):
        noise.append("hqdn3d=4:3:6:4.5")
    elif _on(flags, "ve_vid_denoise"):
        noise.append("hqdn3d=2:1:2:3")
    if _on(flags, "ve_temporal_denoise"):
        noise.append("atadenoise=0.02:0.02:0.02:0.02")
    if _on(flags, "ve_spatial_denoise"):
        noise.append("nlmeans=s=1")
    if any(_on(flags, k) for k in ("ve_film_grain", "ve_analog_noise", "ve_vhs_noise")):
        noise.append("hqdn3d=3:2:4:3")

    scale: List[str] = []
    ai_stack = any(
        _on(flags, k)
        for k in (
            "ve_ai_upscale",
            "ve_ai_video",
            "ve_ai_detail",
            "ve_ai_face",
            "ve_ai_object",
        )
    )
    if ai_stack:
        scale.append("scale=iw*2:ih*2:flags=lanczos")
        warnings.append(
            "AI upscale/enhance: approximated with 2× Lanczos + subsequent filters (no neural model)."
        )
    elif _on(flags, "ve_super_res"):
        scale.append("scale=iw*2:ih*2:flags=lanczos+accurate_rnd")
    elif _on(flags, "ve_lanczos"):
        scale.append("scale=-2:1080:flags=lanczos")
    elif _on(flags, "ve_bicubic"):
        scale.append("scale=-2:1080:flags=bicubic")
    elif _on(flags, "ve_pixel_resize"):
        scale.append("scale=-2:720:flags=neighbor")
    elif _on(flags, "ve_res_change"):
        scale.append("scale=1920:-2:flags=lanczos")

    if _on(flags, "ve_aspect_fix"):
        scale.append("setsar=1")

    # --- Color (single eq) ---
    br = 0.0
    ct = 1.0
    sat = 1.0
    gm = 1.0
    if _on(flags, "ve_brightness"):
        br += 0.06
    if _on(flags, "ve_exposure"):
        br += 0.08
    if _on(flags, "ve_contrast"):
        ct *= 1.08
    if _on(flags, "ve_saturation"):
        sat *= 1.12
    if _on(flags, "ve_gamma"):
        gm *= 1.06
    if _on(flags, "ve_auto_color") or _on(flags, "ve_color_restore"):
        ct *= 1.05
        sat *= 1.08
        gm *= 0.96

    color: List[str] = []
    if any(
        _on(flags, f)
        for f in (
            "ve_brightness",
            "ve_contrast",
            "ve_saturation",
            "ve_gamma",
            "ve_exposure",
            "ve_auto_color",
            "ve_color_restore",
        )
    ):
        color.append(f"eq=brightness={br:.4f}:contrast={ct:.4f}:saturation={sat:.4f}:gamma={gm:.4f}")
    if _on(flags, "ve_hue"):
        color.append("hue=h=10")
    if any(_on(flags, k) for k in ("ve_wb", "ve_temp", "ve_tint")):
        color.append("colorbalance=rs=0.04:gs=0.02:bs=-0.03")
    lp = (lut_path or "").strip()
    if _on(flags, "ve_lut_enable") and lp and os.path.isfile(lp):
        color.append(f"lut3d=file='{_lut_path_ffmpeg(lp)}'")
    elif _on(flags, "ve_lut_enable") and not (lp and os.path.isfile(lp)):
        warnings.append("LUT: path missing or file not found.")
    if _on(flags, "ve_color_grading"):
        color.append("curves=all='0/0 0.5/0.54 1/1'")

    hdr: List[str] = []
    if _on(flags, "ve_hdr_detect"):
        warnings.append("HDR detect: no filter; use tonemap if source is HDR.")
    if _on(flags, "ve_dolby_vision"):
        warnings.append("Dolby Vision metadata: full pipeline requires external toolchain.")

    if _on(flags, "ve_sdr_to_hdr_tm"):
        hdr.append("eq=contrast=1.1:saturation=1.15:brightness=0.02")
        warnings.append("SDR→HDR: visual simulation only (no HDR10 mastering metadata).")

    if _on(flags, "ve_hdr_to_sdr_tm") or _on(flags, "ve_hdr_convert") or _on(flags, "ve_hdr10") or _on(flags, "ve_hlg"):
        hdr.append("tonemap=hable,format=yuv420p")
        if not any(_on(flags, k) for k in ("ve_hdr_to_sdr_tm", "ve_hdr_convert")):
            warnings.append("HDR10/HLG: tonemap applied; best suited to HDR sources.")

    sharp: List[str] = []
    unsharp_strength = 0.0
    if any(_on(flags, k) for k in ("ve_sharpen", "ve_edge_enhance")):
        unsharp_strength = max(unsharp_strength, 0.85)
    if any(_on(flags, k) for k in ("ve_detail_enhance", "ve_texture_restore")):
        unsharp_strength = max(unsharp_strength, 1.15)
    if any(_on(flags, k) for k in ("ve_adaptive_sharpen", "ve_clarity")):
        unsharp_strength = max(unsharp_strength, 1.0)
    if unsharp_strength > 0:
        sharp.append(f"unsharp=5:5:{unsharp_strength:.2f}:5:5:0.0")

    art: List[str] = []
    if _on(flags, "ve_banding"):
        art.append("deband=r=16:range=8")
    if _on(flags, "ve_comp_artifact") or _on(flags, "ve_block_artifact"):
        art.append("spp=6")
    if _on(flags, "ve_ringing"):
        art.append("hqdn3d=1:1:2:2")

    frame: List[str] = []
    if any(
        _on(flags, k)
        for k in ("ve_frame_interp", "ve_motion_interp", "ve_optical_flow")
    ):
        frame.append("minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:vsbmc=1")
        warnings.append("Frame interpolation to 60 fps: CPU-intensive.")
    elif _on(flags, "ve_fps_increase"):
        frame.append("minterpolate=fps=50:mi_mode=mci")
    if _on(flags, "ve_frame_blend"):
        frame.append("tblend=all_mode=average")

    analog: List[str] = []
    if any(_on(flags, k) for k in ("ve_vhs_restore", "ve_tape_damage", "ve_dropout")):
        analog.append("curves=all='0/0 0.18/0.14 1/1'")
    if _on(flags, "ve_line_flicker"):
        analog.append("deflicker=mode=am")
    if _on(flags, "ve_scan_line"):
        analog.append("noise=alls=0.0002:allf=t")

    ordered = deint + stab + noise + scale + color + hdr + sharp + art + frame + analog
    if not ordered:
        return "", warnings
    return ",".join(ordered), warnings


def collect_ve_flags_from_vars(ve_vars: Dict[str, Any]) -> Dict[str, bool]:
    out: Dict[str, bool] = {}
    for k, v in ve_vars.items():
        try:
            out[k] = bool(v.get())
        except Exception:
            out[k] = False
    return out


def has_any_ve_processing(flags: Dict[str, bool], lut_path: str = "") -> bool:
    """True if the built graph is non-empty (active filters or valid LUT)."""
    vf, _ = build_ve_video_filter(flags, lut_path)
    return bool(vf.strip())
