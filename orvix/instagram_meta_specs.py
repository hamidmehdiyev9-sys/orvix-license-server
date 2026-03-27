"""
Instagram / Meta Graph API — ORVIX export ilə uyğunlaşdırma üçün referans.

Mənbə: Meta «IG User / media» sənədləri (Reels, Story video, şəkil spesifikasiyaları)
https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media

Peşəkar alətlər (Buffer, Later, Meta Business Suite və s.) adətən:
- Instagram Business / Creator + Facebook Səhifəsi
- Meta Developer tətbiqi + App Review ilə icazələr
- Graph API: konteyner yarat → status gözlə → media_publish
- Video: çox vaxt «resumable upload» (rupload.facebook.com) və ya ictimai HTTPS video_url
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Tuple

# Graph API (referans; ORVIX hazırda birbaşa HTTP yükləmə etmir)
META_GRAPH_API_VERSION = "v25.0"
META_GRAPH_BASE = "https://graph.facebook.com"

# App Review-da tələb olunan icazələr (mətnlər Meta sənədlərinə uyğun; köhnə adlar bəzən istinad olunur)
META_PERMISSIONS_PUBLISH = (
    "instagram_basic və ya instagram_business_basic, "
    "instagram_content_publish və ya instagram_business_content_publish, "
    "pages_read_engagement; səhifə üzərində MANAGE / CREATE_CONTENT"
)

# Reels (Meta «Reel Specifications»)
META_REELS_MIN_DURATION_S = 3
META_REELS_MAX_DURATION_S = 15 * 60  # 15 dəq
META_REELS_MAX_FILE_MB = 300
META_REELS_MAX_VIDEO_BITRATE_MBPS = 25
META_REELS_AUDIO_BITRATE_KBPS = 128
META_REELS_AUDIO_SAMPLE_HZ = 48000
META_REELS_FPS_MIN = 23
META_REELS_FPS_MAX = 60
META_REELS_RECOMMENDED_ASPECT = "9:16"
META_REELS_MAX_WIDTH = 1920

# Story video (Meta «Story Video Specifications»)
META_STORY_MAX_DURATION_S = 60
META_STORY_MIN_DURATION_S = 3
META_STORY_MAX_FILE_MB = 100
META_STORY_MAX_VIDEO_BITRATE_MBPS = 25

# Feed şəkil (API) — video feed üçün ORVIX presetləri Instagram tövsiyə ölçülərinə uyğundur
META_FEED_IMAGE_ASPECT_MIN = "4:5"
META_FEED_IMAGE_ASPECT_MAX = "1.91:1"


def meta_publishing_steps_brief() -> str:
    return (
        "1) POST /{ig-user-id}/media — konteyner (REELS / STORIES / VIDEO)\n"
        "2) Konteyner statusu FINISHED olana qədər sorğu\n"
        "3) POST /{ig-user-id}/media_publish — dərc\n"
        "Ətraflı: Content Publishing guide (Meta Developer).\n"
        "Masaüstü faylı birbaşa göndərmək üçün çox vaxt «resumable upload» və ya ictimai video URL lazımdır."
    )


def validate_export_file_for_mode(path: str, preset_key: str) -> Tuple[bool, List[str]]:
    """
    Export olunmuş faylı Meta spesifikasiyası ilə qabaqcadan yoxlayır (xəbərdarlıq siyahısı).
    preset_key: «Feed 1:1», «Feed 4:5», «Reels», «Stories»
    """
    warnings: List[str] = []
    if not path or not os.path.isfile(path):
        return False, ["Fayl tapılmadı."]

    try:
        from orvix.file_info import FileInfoExtractor

        info = FileInfoExtractor.extract(path)
    except Exception as e:
        return True, [f"Metadata oxunmadı: {e}"]

    fmt = info.get("format") or {}
    fi = info.get("file") or {}
    vid = info.get("video") or {}

    dur = float(fmt.get("duration_sec") or 0.0)
    size_b = int(fi.get("size_bytes") or 0)
    size_mb = size_b / (1024.0 * 1024.0)

    fps_s = str(vid.get("fps_display") or vid.get("fps") or "").strip()
    try:
        fps = float(fps_s) if fps_s else None
    except ValueError:
        fps = None

    if preset_key == "Reels":
        if dur > 0 and dur < META_REELS_MIN_DURATION_S:
            warnings.append(f"Müddət Meta Reels minimumundan qısadır (~{META_REELS_MIN_DURATION_S}s).")
        if dur > META_REELS_MAX_DURATION_S:
            warnings.append(f"Müddət Meta Reels API maksimumundan ({META_REELS_MAX_DURATION_S // 60} dəq) çox ola bilər.")
        if size_mb > META_REELS_MAX_FILE_MB:
            warnings.append(f"Fayl ölçüsü (~{size_mb:.0f} MB) Meta Reels API limitindən ({META_REELS_MAX_FILE_MB} MB) böyükdür.")
        if fps is not None and (fps < META_REELS_FPS_MIN - 0.1 or fps > META_REELS_FPS_MAX + 0.1):
            warnings.append(f"FPS ({fps:.1f}) Meta tövsiyə aralığından kənar ({META_REELS_FPS_MIN}–{META_REELS_FPS_MAX}).")

    if preset_key == "Stories":
        if dur > 0 and dur < META_STORY_MIN_DURATION_S:
            warnings.append(f"Müddət Meta Story minimumundan qısadır (~{META_STORY_MIN_DURATION_S}s).")
        if dur > META_STORY_MAX_DURATION_S:
            warnings.append(f"Story üçün müddət adətən max ~{META_STORY_MAX_DURATION_S}s (Meta API).")
        if size_mb > META_STORY_MAX_FILE_MB:
            warnings.append(f"Fayl ölçüsü (~{size_mb:.0f} MB) Meta Story API limitindən ({META_STORY_MAX_FILE_MB} MB) böyükdür.")

    return True, warnings


def mode_hint_meta_aligned(preset_key: str) -> str:
    """UI üçün qısa sətir — Meta rəqəmləri ilə."""
    base = {
        "Feed 1:1": (
            f"MP4 • 1:1 • 1080×1080 • H.264/AAC • şəkil API: en 320–1440, nisbət ~{META_FEED_IMAGE_ASPECT_MIN}–{META_FEED_IMAGE_ASPECT_MAX} • video: ORVIX preset"
        ),
        "Feed 4:5": (
            "MP4 • 4:5 • 1080×1350 • H.264/AAC • Feed video üçün Instagram tövsiyə ölçü"
        ),
        "Reels": (
            f"MP4/MOV • {META_REELS_RECOMMENDED_ASPECT} tövsiyə • max en {META_REELS_MAX_WIDTH}px • "
            f"{META_REELS_FPS_MIN}–{META_REELS_FPS_MAX} fps • VBR ≤{META_REELS_MAX_VIDEO_BITRATE_MBPS} Mbps • "
            f"AAC {META_REELS_AUDIO_BITRATE_KBPS} kbps • {META_REELS_MIN_DURATION_S}s–{META_REELS_MAX_DURATION_S // 60} dəq • API fayl ≤{META_REELS_MAX_FILE_MB} MB"
        ),
        "Stories": (
            f"MP4 • 9:16 • {META_STORY_MIN_DURATION_S}–{META_STORY_MAX_DURATION_S}s • API fayl ≤{META_STORY_MAX_FILE_MB} MB • "
            f"VBR ≤{META_STORY_MAX_VIDEO_BITRATE_MBPS} Mbps • AAC {META_REELS_AUDIO_BITRATE_KBPS} kbps"
        ),
    }
    return base.get(preset_key, base["Feed 1:1"])


def mode_profile_spec_meta(preset_key: str) -> str:
    return {
        "Feed 1:1": "Feed • 1:1 • 1080×1080 • H.264 • AAC 48 kHz • 128 kb/s • yuv420p • +faststart (Graph API uyğun)",
        "Feed 4:5": "Feed • 4:5 • 1080×1350 • H.264 • AAC 48 kHz • 128 kb/s • yuv420p • +faststart",
        "Reels": "Reels • 9:16 • 1080×1920 • H.264 • AAC 48 kHz • 128 kb/s • Meta Reels video spesifikasiyasına uyğun export",
        "Stories": "Stories • 9:16 • 1080×1920 • Meta Story video (max 60s API) uyğun",
    }.get(preset_key, "")


def show_meta_graph_reference_dialog(parent: Any = None) -> None:
    """Peşəkar alətlərin Meta axını ilə ORVIX export-un uyğunluğunu izah edir."""
    try:
        from tkinter import messagebox

        msg = (
            "ORVIX export (FFmpeg): H.264, AAC 128 kb/s, 48 kHz, yuv420p, -movflags +faststart — "
            "Meta «Reels / Story video» konteyner tələblərinə (MP4, moov əvvəldə) uyğundur.\n\n"
            f"Graph API referans: {META_GRAPH_BASE}/{META_GRAPH_API_VERSION}/…\n\n"
            f"İcazələr (App Review): {META_PERMISSIONS_PUBLISH}\n\n"
            "Dərc axını (Buffer / Later kimi alətlər eyni API-dən istifadə edir):\n"
            f"{meta_publishing_steps_brief()}\n"
            "ORVIX hazırda birbaşa yükləmə etmir (OAuth + resumable upload server tələb olunur).\n"
            "Export faylı Instagram tətbiqində və ya Meta Business Suite-də əl ilə əlavə edin."
        )
        messagebox.showinfo("Instagram — Meta Graph API (referans)", msg, parent=parent)
    except Exception:
        pass
