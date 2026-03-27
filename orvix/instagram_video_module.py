"""
Instagram Video Module — API siyahısı (Import, Trim, Merge, Export, Layihə, və s.).
UI və pv_main ilə `InstagramVideoModule(app)` vasitəsilə əlaqələndirilir.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional

import tkinter as tk

from orvix.file_info import FileInfoExtractor
from orvix.ffmpeg_core import ffmpeg_mgr


def ffmpeg_escape_subtitle_path(path: str) -> str:
    """FFmpeg subtitles= filter üçün Windows yolu."""
    x = os.path.abspath(path).replace("\\", "/")
    if len(x) >= 2 and x[1] == ":":
        x = x[0] + "\\:" + x[2:]
    return x.replace("'", "\\'")


def _apply_social_dict_to_ui(app, soc: Dict[str, Any]) -> None:
    """_sn_collect_settings_from_ui() ilə uyğun açarları bərpa edir."""
    if not isinstance(soc, dict):
        return

    def set_var(name, val):
        if hasattr(app, name):
            try:
                getattr(app, name).set(val)
            except Exception:
                pass

    set_var("sn_start_var", soc.get("start", "00:00:00"))
    set_var("sn_end_var", soc.get("end", ""))
    set_var("sn_max_duration_var", soc.get("max_duration", "Auto"))
    set_var("sn_fill_mode_var", soc.get("fill_mode", "Blur Fill"))
    if hasattr(app, "sn_y_shift"):
        try:
            app.sn_y_shift.set(int(soc.get("y_shift", 0)))
        except Exception:
            pass
    if hasattr(app, "sn_x_shift"):
        try:
            app.sn_x_shift.set(int(soc.get("x_shift", 0)))
        except Exception:
            pass
    set_var("sn_video_zoom_var", soc.get("video_zoom", "1.00"))
    set_var("sn_bg_img_var", soc.get("bg_img", ""))
    set_var("sn_text_var", soc.get("text", ""))
    set_var("sn_text_color_var", soc.get("text_color", "white"))
    set_var("sn_text_size_var", soc.get("text_size", "46"))
    set_var("sn_text_x_var", soc.get("text_x", "(w-text_w)/2"))
    set_var("sn_text_y_var", soc.get("text_y", "h*0.82"))
    set_var("sn_text_start_var", soc.get("text_start", "0"))
    set_var("sn_text_end_var", soc.get("text_end", ""))
    set_var("sn_overlay_img_var", soc.get("overlay_img", ""))
    set_var("sn_overlay_scale_var", soc.get("overlay_scale", "1.0"))
    set_var("sn_overlay_opacity_var", soc.get("overlay_opacity", "1.0"))
    set_var("sn_overlay_x_var", soc.get("overlay_x", "W-w-36"))
    set_var("sn_overlay_y_var", soc.get("overlay_y", "H-h-36"))
    set_var("sn_overlay_start_var", soc.get("overlay_start", "0"))
    set_var("sn_overlay_end_var", soc.get("overlay_end", ""))
    set_var("sn_overlay2_img_var", soc.get("overlay2_img", ""))
    set_var("sn_overlay2_scale_var", soc.get("overlay2_scale", "1.0"))
    set_var("sn_overlay2_opacity_var", soc.get("overlay2_opacity", "1.0"))
    set_var("sn_overlay2_x_var", soc.get("overlay2_x", "W-w-120"))
    set_var("sn_overlay2_y_var", soc.get("overlay2_y", "H-h-120"))
    if hasattr(app, "sn_volume_var"):
        try:
            app.sn_volume_var.set(float(soc.get("volume", 1.0)))
        except Exception:
            pass
    set_var("sn_fade_in_var", soc.get("fade_in", "0"))
    set_var("sn_fade_out_var", soc.get("fade_out", "0"))


class InstagramVideoModule:
    """Spesifikasiyadakı funksiyaların tək nöqtəli interfeysi."""

    def __init__(self, app):
        self._app = app

    # --- 1) Import / Metadata ---
    def import_video(self, file_path: str) -> bool:
        if not file_path or not os.path.exists(file_path):
            return False
        if hasattr(self._app, "sn_input_var"):
            self._app.sn_input_var.set(file_path)
            base, _ = os.path.splitext(file_path)
            if hasattr(self._app, "sn_output_var"):
                self._app.sn_output_var.set(f"{base}_instagram.mp4")
        if hasattr(self._app, "sn_platform_var"):
            self._app.sn_platform_var.set("Instagram")
        try:
            from orvix import instagram_panel as ig

            ig._refresh_insta_metadata(self._app)
        except Exception:
            pass
        return True

    def read_metadata(self, file_path: Optional[str] = None) -> Dict[str, Any]:
        fp = file_path or (
            (self._app.sn_input_var.get() or "").strip() if hasattr(self._app, "sn_input_var") else ""
        )
        if not fp or not os.path.exists(fp):
            return {}
        info = FileInfoExtractor.extract(fp)
        v = info.get("video") or {}
        fmt = info.get("format") or {}
        fi = info.get("file") or {}
        a = info.get("audio")
        return {
            "duration_sec": fmt.get("duration_sec"),
            "duration_display": fmt.get("duration"),
            "resolution": v.get("resolution"),
            "width": v.get("width"),
            "height": v.get("height"),
            "codec": v.get("codec"),
            "fps": v.get("fps_display") or v.get("fps"),
            "has_audio": a is not None,
            "audio_codec": (a or {}).get("codec"),
            "file_size": fi.get("size"),
            "format_bitrate": fmt.get("bitrate"),
            "video_bitrate": v.get("bitrate"),
        }

    # --- 2) Trim / Merge ---
    def trim_video(self, start: str, end: str = "") -> None:
        if hasattr(self._app, "sn_start_var"):
            self._app.sn_start_var.set(start or "00:00:00")
        if hasattr(self._app, "sn_end_var"):
            self._app.sn_end_var.set(end or "")

    def merge_videos(self, video_list: List[str], output_path: str) -> bool:
        if not video_list or not ffmpeg_mgr.ffmpeg_path:
            return False
        clean = [p for p in video_list if p and os.path.exists(p)]
        if len(clean) < 2:
            return False
        lines = []
        for p in clean:
            ap = os.path.abspath(p).replace("\\", "/").replace("'", "'\\''")
            lines.append(f"file '{ap}'")
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8")
        try:
            tmp.write("\n".join(lines))
            tmp.close()
            cmd = [
                ffmpeg_mgr.ffmpeg_path,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                tmp.name,
                "-c",
                "copy",
                output_path,
            ]
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode != 0:
                return False
            self.import_video(output_path)
            return True
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass

    # --- 3) Resize / Crop / Aspect ---
    def resize_video(self, width: int, height: int) -> None:
        """Instagram presetləri ilə eyni məntiqi — əl ilə ölçü (Custom üçün yalnız qeyd)."""
        if hasattr(self._app, "_sn_platforms"):
            p = self._app._sn_platforms.get("Instagram") or {}
            p["res"] = f"{int(width)}x{int(height)}"
            self._app._sn_platforms["Instagram"] = p

    def crop_video(self, x: int, y: int, width: int, height: int) -> None:
        """Əsas layout: Social ümumi bölmə + Layout Editor; burada yalnız layihə üçün saxlanılır."""
        if not hasattr(self._app, "insta_crop_var"):
            self._app.insta_crop_var = tk.StringVar()
        self._app.insta_crop_var.set(f"{x},{y},{width},{height}")

    def set_aspect_ratio(self, ratio: str) -> None:
        """ratio: '1:1' | '4:5' | '9:16' | '9:16_story' (Feed / Reels / Story)."""
        r = (ratio or "").strip()
        if not hasattr(self._app, "insta_mode_var"):
            return
        if not hasattr(self._app, "insta_feed_aspect_var"):
            self._app.insta_feed_aspect_var = tk.StringVar(value="1:1")
        if r == "1:1":
            self._app.insta_mode_var.set("Feed")
            self._app.insta_feed_aspect_var.set("1:1")
        elif r == "4:5":
            self._app.insta_mode_var.set("Feed")
            self._app.insta_feed_aspect_var.set("4:5")
        elif r in ("9:16", "9:16_reels"):
            self._app.insta_mode_var.set("Reels")
        elif r == "9:16_story":
            self._app.insta_mode_var.set("Stories")
        try:
            from orvix import instagram_panel as ig

            ig._apply_insta_mode(self._app)
        except Exception:
            pass

    # --- 4) Audio / Subtitles ---
    def add_audio_track(self, audio_file: str) -> None:
        if hasattr(self._app, "insta_extra_audio_var"):
            self._app.insta_extra_audio_var.set(audio_file or "")

    def set_audio_volume(self, level: float) -> None:
        if hasattr(self._app, "sn_volume_var"):
            self._app.sn_volume_var.set(float(level))

    def add_subtitles(self, file_srt: str) -> None:
        if hasattr(self._app, "insta_srt_var"):
            self._app.insta_srt_var.set(file_srt or "")

    def remove_audio(self, remove: bool = True) -> None:
        if hasattr(self._app, "insta_remove_audio_var"):
            self._app.insta_remove_audio_var.set(bool(remove))

    # --- 5) Text / Stickers / Overlay ---
    def add_text_overlay(
        self,
        text: str,
        font: str = "Segoe UI",
        color: str = "white",
        position: str = "bottom",
    ) -> str:
        if hasattr(self._app, "sn_text_var"):
            self._app.sn_text_var.set(text)
        if hasattr(self._app, "sn_text_color_var"):
            self._app.sn_text_color_var.set(color)
        if position == "top" and hasattr(self._app, "sn_text_y_var"):
            self._app.sn_text_y_var.set("h*0.10")
        elif position == "bottom" and hasattr(self._app, "sn_text_y_var"):
            self._app.sn_text_y_var.set("h*0.82")
        return "text_1"

    def remove_text_overlay(self, overlay_id: str = "text_1") -> None:
        if overlay_id.startswith("text") and hasattr(self._app, "sn_text_var"):
            self._app.sn_text_var.set("")

    def add_sticker(self, image_file: str, position: str = "corner") -> str:
        if hasattr(self._app, "sn_overlay_img_var"):
            self._app.sn_overlay_img_var.set(image_file or "")
        if position == "center" and hasattr(self._app, "sn_overlay_x_var"):
            self._app.sn_overlay_x_var.set("(W-w)/2")
            self._app.sn_overlay_y_var.set("(H-h)/2")
        return "sticker_1"

    def remove_sticker(self, overlay_id: str = "sticker_1") -> None:
        if overlay_id.startswith("sticker") and hasattr(self._app, "sn_overlay_img_var"):
            self._app.sn_overlay_img_var.set("")

    def set_overlay_opacity(self, level: float) -> None:
        if hasattr(self._app, "sn_overlay_opacity_var"):
            self._app.sn_overlay_opacity_var.set(str(max(0.0, min(1.0, float(level)))))

    # --- 6) Compression / Export ---
    def set_video_codec(self, codec: str) -> None:
        c = (codec or "").upper()
        if hasattr(self._app, "insta_video_codec_var"):
            if "265" in c or c == "HEVC":
                self._app.insta_video_codec_var.set("H.265")
            else:
                self._app.insta_video_codec_var.set("H.264")
        self._sync_instagram_vc()

    def set_audio_codec(self, codec: str) -> None:
        if hasattr(self._app, "_sn_platforms") and "Instagram" in self._app._sn_platforms:
            self._app._sn_platforms["Instagram"]["ac"] = "aac" if "aac" in (codec or "").lower() else "aac"

    def set_bitrate(self, target_bitrate: str) -> None:
        if hasattr(self._app, "insta_bitrate_var"):
            self._app.insta_bitrate_var.set(target_bitrate)
        if hasattr(self._app, "_sn_platforms") and "Instagram" in self._app._sn_platforms:
            self._app._sn_platforms["Instagram"]["vb"] = target_bitrate

    def set_frame_rate(self, fps: str) -> None:
        if hasattr(self._app, "insta_fps_var"):
            self._app.insta_fps_var.set(str(fps))
        if hasattr(self._app, "_sn_platforms") and "Instagram" in self._app._sn_platforms:
            self._app._sn_platforms["Instagram"]["fps"] = str(fps)

    def export_video(self, output_path: str) -> None:
        if hasattr(self._app, "sn_output_var"):
            self._app.sn_output_var.set(output_path)
        if hasattr(self._app, "_start_social"):
            self._app._start_social()

    def optimize_for_instagram(self) -> None:
        try:
            from orvix import instagram_panel as ig

            ig._apply_insta_mode(self._app)
        except Exception:
            pass
        # Yalnız Instagram convert pəncərəsində köhnə "preview/tətbiq" zənciri lazım deyil.
        if getattr(self._app, "_instagram_convert_only", False):
            try:
                self._app._sn_applied_settings = self._app._sn_collect_settings_from_ui()
            except Exception:
                pass
            return
        if hasattr(self._app, "_sn_apply_settings"):
            self._app._sn_apply_settings()

    def _sync_instagram_vc(self) -> None:
        if not hasattr(self._app, "_sn_platforms"):
            return
        vc = "libx264"
        if hasattr(self._app, "insta_video_codec_var"):
            v = self._app.insta_video_codec_var.get()
            vc = "libx265" if v == "H.265" else "libx264"
        self._app._sn_platforms.setdefault("Instagram", {})["vc"] = vc

    def _workspace_or_social_player(self):
        """İş pəncərəsi (Instagram) açıqdırsa sağ pleyer — əks halda əsas Social pleyer."""
        app = self._app
        if hasattr(app, "_active_social_video_player"):
            try:
                return app._active_social_video_player()
            except Exception:
                pass
        return app._social_player() if hasattr(app, "_social_player") else None

    # --- 7) Preview / Player ---
    def preview_video(self, output_path: str) -> None:
        pl = self._workspace_or_social_player()
        if pl and output_path and os.path.exists(output_path):
            pl.load(output_path)
            pl.play_media()

    def play_video(self, path: Optional[str] = None) -> None:
        pl = self._workspace_or_social_player()
        if not pl:
            return
        fp = path or (self._app.sn_output_var.get() if hasattr(self._app, "sn_output_var") else "")
        if fp and os.path.exists(fp):
            pl.load(fp)
        pl.play_media()

    def pause_video(self) -> None:
        pl = self._workspace_or_social_player()
        if pl:
            pl.pause_media()

    def stop_video(self) -> None:
        pl = self._workspace_or_social_player()
        if pl:
            pl.stop()

    # --- 8) Process (export) ---
    def start_process(self) -> None:
        if hasattr(self._app, "_start_social"):
            self._app._start_social()

    def pause_process(self) -> None:
        if hasattr(self._app, "_sn_pause_social_encoding"):
            self._app._sn_pause_social_encoding()

    def resume_process(self) -> None:
        if hasattr(self._app, "_sn_resume_social_encoding"):
            self._app._sn_resume_social_encoding()

    def stop_process(self) -> None:
        if hasattr(self._app, "_stop_social"):
            self._app._stop_social()

    # --- 9) Upload ---
    def upload_to_instagram(
        self,
        api_key: str,
        video_file: str,
        type: str = "Feed",
    ) -> None:
        try:
            from tkinter import messagebox

            from orvix import instagram_panel as ig
            from orvix.instagram_meta_specs import show_meta_graph_reference_dialog, validate_export_file_for_mode

            root = getattr(self._app, "root", None)
            fp = (video_file or "").strip()
            if fp and os.path.isfile(fp):
                key = ig.resolve_instagram_preset_key(self._app)
                _ok, warns = validate_export_file_for_mode(fp, key)
                if warns:
                    messagebox.showwarning("Export — Meta specification", "\n".join(warns[:12]), parent=root)
            show_meta_graph_reference_dialog(root)
        except Exception:
            pass

    def schedule_upload(self, when: datetime, upload_type: str = "Feed") -> None:
        if hasattr(self._app, "insta_schedule_var"):
            self._app.insta_schedule_var.set(when.isoformat())

    def preview_upload(self) -> Dict[str, Any]:
        out = (self._app.sn_output_var.get() if hasattr(self._app, "sn_output_var") else "") or ""
        mode = (
            self._app.insta_mode_var.get() if hasattr(self._app, "insta_mode_var") else ""
        )
        return {
            "ok": bool(out and os.path.exists(out)),
            "output": out,
            "mode": mode,
            "api_configured": bool(
                (self._app.insta_api_key_var.get() if hasattr(self._app, "insta_api_key_var") else "")
            ),
        }

    # --- 10) Project ---
    def _collect_full_project(self) -> Dict[str, Any]:
        app = self._app
        data: Dict[str, Any] = {
            "version": 1,
            "saved_at": datetime.now().isoformat(timespec="seconds"),
        }
        if hasattr(app, "_sn_collect_settings_from_ui"):
            data["social"] = app._sn_collect_settings_from_ui()
        if hasattr(app, "sn_input_var"):
            data["input"] = app.sn_input_var.get()
        if hasattr(app, "sn_output_var"):
            data["output"] = app.sn_output_var.get()
        if hasattr(app, "sn_platform_var"):
            data["platform"] = app.sn_platform_var.get()
        if hasattr(app, "insta_mode_var"):
            data["instagram_mode"] = app.insta_mode_var.get()
        if hasattr(app, "insta_extra_audio_var"):
            data["instagram_extra_audio"] = app.insta_extra_audio_var.get()
        if hasattr(app, "insta_srt_var"):
            data["instagram_srt"] = app.insta_srt_var.get()
        if hasattr(app, "insta_remove_audio_var"):
            data["instagram_remove_audio"] = app.insta_remove_audio_var.get()
        if hasattr(app, "insta_extra_audio_mode_var"):
            data["instagram_audio_mode"] = app.insta_extra_audio_mode_var.get()
        if hasattr(app, "insta_video_codec_var"):
            data["instagram_video_codec"] = app.insta_video_codec_var.get()
        if hasattr(app, "insta_bitrate_var"):
            data["instagram_bitrate"] = app.insta_bitrate_var.get()
        if hasattr(app, "insta_fps_var"):
            data["instagram_fps"] = app.insta_fps_var.get()
        if hasattr(app, "insta_schedule_var"):
            data["schedule_iso"] = app.insta_schedule_var.get()
        if hasattr(app, "insta_extra_mix_vol_var"):
            data["instagram_extra_mix_vol"] = app.insta_extra_mix_vol_var.get()
        return data

    def save_project(self, file_path: str) -> bool:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self._collect_full_project(), f, ensure_ascii=False, indent=2)
            return True
        except OSError:
            return False

    def load_project(self, file_path: str) -> bool:
        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return False
        app = self._app
        soc = data.get("social") or {}
        if hasattr(app, "sn_input_var") and data.get("input"):
            app.sn_input_var.set(data["input"])
        if hasattr(app, "sn_output_var") and data.get("output"):
            app.sn_output_var.set(data["output"])
        if hasattr(app, "sn_platform_var") and data.get("platform"):
            app.sn_platform_var.set(data["platform"])
        _apply_social_dict_to_ui(app, soc)
        # birbaşa adlar
        if hasattr(app, "insta_mode_var") and data.get("instagram_mode"):
            raw = data["instagram_mode"]
            if not hasattr(app, "insta_feed_aspect_var"):
                app.insta_feed_aspect_var = tk.StringVar(value="1:1")
            if raw == "Feed 1:1":
                app.insta_mode_var.set("Feed")
                app.insta_feed_aspect_var.set("1:1")
            elif raw == "Feed 4:5":
                app.insta_mode_var.set("Feed")
                app.insta_feed_aspect_var.set("4:5")
            elif raw == "Reels":
                app.insta_mode_var.set("Reels")
            elif raw in ("Stories", "Story"):
                app.insta_mode_var.set("Stories")
            else:
                app.insta_mode_var.set(raw)
        if hasattr(app, "insta_extra_audio_var"):
            app.insta_extra_audio_var.set(data.get("instagram_extra_audio", ""))
        if hasattr(app, "insta_srt_var"):
            app.insta_srt_var.set(data.get("instagram_srt", ""))
        if hasattr(app, "insta_remove_audio_var"):
            app.insta_remove_audio_var.set(data.get("instagram_remove_audio", False))
        if hasattr(app, "insta_extra_audio_mode_var"):
            app.insta_extra_audio_mode_var.set(data.get("instagram_audio_mode", "Replace"))
        if hasattr(app, "insta_video_codec_var"):
            app.insta_video_codec_var.set(data.get("instagram_video_codec", "H.264"))
        if hasattr(app, "insta_bitrate_var"):
            app.insta_bitrate_var.set(data.get("instagram_bitrate", "6M"))
        if hasattr(app, "insta_fps_var"):
            app.insta_fps_var.set(data.get("instagram_fps", "30"))
        if hasattr(app, "insta_schedule_var"):
            app.insta_schedule_var.set(data.get("schedule_iso", ""))
        if hasattr(app, "insta_extra_mix_vol_var") and data.get("instagram_extra_mix_vol") is not None:
            try:
                app.insta_extra_mix_vol_var.set(float(data["instagram_extra_mix_vol"]))
            except Exception:
                pass
        try:
            from orvix import instagram_panel as ig

            ig._apply_insta_mode(app)
            if hasattr(app, "insta_meta_lbl"):
                ig._refresh_insta_metadata(app)
        except Exception:
            pass
        if hasattr(app, "_sn_apply_settings"):
            app._sn_apply_settings()
        return True

    def export_settings(self, file_path: str) -> bool:
        """Yalnız sıxışdırma / Instagram parametrləri."""
        try:
            subset = {
                "instagram_mode": getattr(self._app, "insta_mode_var", None)
                and self._app.insta_mode_var.get(),
                "video_codec": getattr(self._app, "insta_video_codec_var", None)
                and self._app.insta_video_codec_var.get(),
                "bitrate": getattr(self._app, "insta_bitrate_var", None)
                and self._app.insta_bitrate_var.get(),
                "fps": getattr(self._app, "insta_fps_var", None) and self._app.insta_fps_var.get(),
                "platform_export": self._app._sn_platforms.get("Instagram", {})
                if hasattr(self._app, "_sn_platforms")
                else {},
            }
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(subset, f, ensure_ascii=False, indent=2)
            return True
        except OSError:
            return False
