"""
Instagram tab — kompakt UI: Feed / Reels / Stories preset-ləri və alətlər (stub + export sinxron).
"""
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from orvix.file_info import FileInfoExtractor
from orvix.instagram_meta_specs import mode_hint_meta_aligned, mode_profile_spec_meta, show_meta_graph_reference_dialog

# Video növü → FFmpeg export preset (pv_main _sn_platforms['Instagram'] yenilənir)
# Meta «IG User / media» Reels & Story video spesifikasiyalarına uyğun (AAC 48 kHz, +faststart pv_main-də)
_INSTA_AR = "48000"  # Hz — Meta tövsiyə (maks. 48 kHz)

INSTAGRAM_MODES = {
    "Feed 1:1": {
        "export": {
            "res": "1080x1080",
            "vc": "libx264",
            "vb": "6.5M",
            "ac": "aac",
            "ab": "128k",
            "ar": _INSTA_AR,
            "fps": "30",
            "fmt": "mp4",
        },
        "hint": mode_hint_meta_aligned("Feed 1:1"),
        "profile_spec": mode_profile_spec_meta("Feed 1:1"),
        "max_dur_suggest": "3600",
    },
    "Feed 4:5": {
        "export": {
            "res": "1080x1350",
            "vc": "libx264",
            "vb": "6.5M",
            "ac": "aac",
            "ab": "128k",
            "ar": _INSTA_AR,
            "fps": "30",
            "fmt": "mp4",
        },
        "hint": mode_hint_meta_aligned("Feed 4:5"),
        "profile_spec": mode_profile_spec_meta("Feed 4:5"),
        "max_dur_suggest": "3600",
    },
    "Reels": {
        "export": {
            "res": "1080x1920",
            "vc": "libx264",
            "vb": "8M",
            "ac": "aac",
            "ab": "128k",
            "ar": _INSTA_AR,
            "fps": "30",
            "fmt": "mp4",
        },
        "hint": mode_hint_meta_aligned("Reels"),
        "profile_spec": mode_profile_spec_meta("Reels"),
        "max_dur_suggest": "900",
    },
    "Stories": {
        "export": {
            "res": "1080x1920",
            "vc": "libx264",
            "vb": "6.5M",
            "ac": "aac",
            "ab": "128k",
            "ar": _INSTA_AR,
            "fps": "30",
            "fmt": "mp4",
        },
        "hint": mode_hint_meta_aligned("Stories"),
        "profile_spec": mode_profile_spec_meta("Stories"),
        "max_dur_suggest": "60",
    },
}


def resolve_instagram_preset_key(app):
    """UI: Feed / Reels / Story (+ Feed üçün 1:1 və ya 4:5) → daxili preset açarı."""
    mode = getattr(app, "insta_mode_var", None)
    m = mode.get() if mode else "Feed"
    if m == "Feed":
        ap = getattr(app, "insta_feed_aspect_var", None)
        a = (ap.get() if ap else "1:1").strip()
        return "Feed 1:1" if a == "1:1" else "Feed 4:5"
    if m == "Reels":
        return "Reels"
    if m in ("Story", "Stories"):
        return "Stories"
    return "Feed 1:1"


def _apply_insta_mode(app):
    key = resolve_instagram_preset_key(app)
    if key not in INSTAGRAM_MODES:
        return
    d = INSTAGRAM_MODES[key]
    app._sn_platforms["Instagram"] = dict(d["export"])
    try:
        app.insta_hint_lbl.config(text=d["hint"])
    except Exception:
        pass
    try:
        if hasattr(app, "insta_profile_spec_lbl"):
            app.insta_profile_spec_lbl.config(text=d.get("profile_spec", ""))
    except Exception:
        pass
    if hasattr(app, "sn_max_duration_var") and d.get("max_dur_suggest"):
        try:
            app.sn_max_duration_var.set(d["max_dur_suggest"])
        except Exception:
            pass
    vb = d["export"].get("vb", "6M")
    if hasattr(app, "insta_bitrate_var"):
        app.insta_bitrate_var.set(vb)
    fp = d["export"].get("fps", "30")
    if hasattr(app, "insta_fps_var"):
        app.insta_fps_var.set(fp)


def _refresh_insta_metadata(app):
    if not hasattr(app, "insta_meta_lbl"):
        return
    path = (app.sn_input_var.get() or "").strip() if hasattr(app, "sn_input_var") else ""
    if not path or not os.path.exists(path):
        try:
            app.insta_meta_lbl.config(
                text="resolution: —\nduration: —\nfps: —\nfile size: —"
            )
        except Exception:
            pass
        return
    try:
        info = FileInfoExtractor.extract(path)
        v = info.get("video") or {}
        fmt = info.get("format") or {}
        dur = fmt.get("duration", "?")
        res = v.get("resolution", "?")
        fps = v.get("fps_display", "?")
        fsz = info.get("file", {}).get("size", "?")
        txt = (
            f"resolution: {res}\n"
            f"duration: {dur}\n"
            f"fps: {fps}\n"
            f"file size: {fsz}"
        )
        app.insta_meta_lbl.config(text=txt[:800])
    except Exception as e:
        app.insta_meta_lbl.config(text=f"Metadata: {e}")


def install_instagram_panel(app, frame, *, bg, fg, fg2, accent):
    """Instagram notebook səhifəsini doldurur."""
    for w in frame.winfo_children():
        w.destroy()

    tk.Label(
        frame,
        text="Instagram video",
        bg=bg,
        fg=accent,
        font=("Segoe UI", 11, "bold"),
    ).pack(anchor="w", padx=10, pady=(8, 2))

    # --- 1) Video növü ---
    mode_fr = tk.Frame(frame, bg=bg)
    mode_fr.pack(fill=tk.X, padx=10, pady=(0, 4))
    tk.Label(mode_fr, text="Type:", bg=bg, fg=fg, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
    if not hasattr(app, "insta_mode_var"):
        app.insta_mode_var = tk.StringVar(value="Feed")
    if not hasattr(app, "insta_feed_aspect_var"):
        app.insta_feed_aspect_var = tk.StringVar(value="1:1")

    for val in ("Feed", "Reels", "Story"):
        tk.Radiobutton(
            mode_fr,
            text=val,
            variable=app.insta_mode_var,
            value=val,
            bg=bg,
            fg=fg,
            selectcolor="#1a2744",
            activebackground=bg,
            activeforeground=fg,
            font=("Segoe UI", 9),
            command=lambda: _apply_insta_mode(app),
        ).pack(side=tk.LEFT, padx=(8, 4))

    feed_aspect_fr = tk.Frame(frame, bg=bg)
    feed_aspect_fr.pack(fill=tk.X, padx=10, pady=(0, 2))
    tk.Label(feed_aspect_fr, text="Feed aspect:", bg=bg, fg=fg2, font=("Segoe UI", 8)).pack(side=tk.LEFT)
    for val in ("1:1", "4:5"):
        tk.Radiobutton(
            feed_aspect_fr,
            text=val,
            variable=app.insta_feed_aspect_var,
            value=val,
            bg=bg,
            fg=fg,
            selectcolor="#1a2744",
            activebackground=bg,
            activeforeground=fg,
            font=("Segoe UI", 8),
            command=lambda: _apply_insta_mode(app),
        ).pack(side=tk.LEFT, padx=(6, 2))

    app.insta_hint_lbl = tk.Label(
        frame,
        text=INSTAGRAM_MODES[resolve_instagram_preset_key(app)]["hint"],
        bg=bg,
        fg=fg2,
        font=("Segoe UI", 8),
        wraplength=780,
        justify=tk.LEFT,
    )
    app.insta_hint_lbl.pack(anchor="w", padx=10, pady=(0, 6))

    # --- A) Import ---
    sec_a = tk.Frame(frame, bg=bg, highlightthickness=1, highlightbackground="#334155")
    sec_a.pack(fill=tk.X, padx=8, pady=3)
    tk.Label(sec_a, text="A — Video file", bg=bg, fg=accent, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=8, pady=(6, 2))
    row_a = tk.Frame(sec_a, bg=bg)
    row_a.pack(fill=tk.X, padx=8, pady=(0, 6))

    def _browse_video():
        fp = filedialog.askopenfilename(
            title="Video seç (MP4 / MOV)",
            filetypes=[
                ("Video", "*.mp4 *.mov *.m4v *.mkv *.webm"),
                ("All files", "*.*"),
            ],
        )
        if fp and hasattr(app, "sn_input_var"):
            app.sn_input_var.set(fp)
            base = os.path.splitext(fp)[0]
            if hasattr(app, "sn_output_var"):
                app.sn_output_var.set(f"{base}_instagram.mp4")
            _refresh_insta_metadata(app)
            if hasattr(app, "_sn_log"):
                app._sn_log(f"Instagram: file selected — {os.path.basename(fp)}")

    tk.Button(
        row_a,
        text="Select video (Import)",
        bg="#5b21b6",
        fg="#fff",
        font=("Segoe UI", 9, "bold"),
        relief=tk.FLAT,
        cursor="hand2",
        padx=10,
        pady=4,
        command=_browse_video,
    ).pack(side=tk.LEFT)
    tk.Button(
        row_a,
        text="Refresh metadata",
        bg="#334155",
        fg="#e2e8f0",
        font=("Segoe UI", 9),
        relief=tk.FLAT,
        cursor="hand2",
        padx=8,
        pady=4,
        command=lambda: _refresh_insta_metadata(app),
    ).pack(side=tk.LEFT, padx=(6, 0))

    app.insta_meta_lbl = tk.Label(
        row_a,
        text="—",
        bg=bg,
        fg=fg2,
        font=("Consolas", 8),
        anchor="w",
        justify=tk.LEFT,
    )
    app.insta_meta_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
    _refresh_insta_metadata(app)

    # --- B) Trim (ümumi export ilə eyni dəyişənlər) ---
    sec_b = tk.Frame(frame, bg=bg, highlightthickness=1, highlightbackground="#334155")
    sec_b.pack(fill=tk.X, padx=8, pady=3)
    tk.Label(sec_b, text="B — Trim", bg=bg, fg=accent, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=8, pady=(6, 2))
    row_b = tk.Frame(sec_b, bg=bg)
    row_b.pack(fill=tk.X, padx=8, pady=(0, 6))
    if hasattr(app, "sn_start_var"):
        tk.Label(row_b, text="Start", bg=bg, fg=fg2, font=("Segoe UI", 8)).pack(side=tk.LEFT)
        tk.Entry(row_b, textvariable=app.sn_start_var, width=10, bg="#0e1e30", fg=fg, insertbackground=accent, relief=tk.FLAT, bd=2).pack(side=tk.LEFT, padx=4)
        tk.Label(row_b, text="End", bg=bg, fg=fg2, font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(8, 0))
        tk.Entry(row_b, textvariable=app.sn_end_var, width=10, bg="#0e1e30", fg=fg, insertbackground=accent, relief=tk.FLAT, bd=2).pack(side=tk.LEFT, padx=4)
    tk.Label(
        row_b,
        text="(empty end = until EOF)",
        bg=bg,
        fg=fg2,
        font=("Segoe UI", 8),
    ).pack(side=tk.LEFT, padx=8)
    tk.Button(
        row_b,
        text="Merge clips (soon)",
        bg="#475569",
        fg="#fff",
        font=("Segoe UI", 8),
        relief=tk.FLAT,
        cursor="hand2",
        padx=6,
        pady=2,
        command=lambda: messagebox.showinfo(
            "ORVIX",
            "Merging multiple clips will be added in a future version (FFmpeg concat).",
        ),
    ).pack(side=tk.RIGHT)

    # --- C) Ölçü / preset ---
    sec_c = tk.Frame(frame, bg=bg, highlightthickness=1, highlightbackground="#334155")
    sec_c.pack(fill=tk.X, padx=8, pady=3)
    tk.Label(sec_c, text="C — Size (auto from type)", bg=bg, fg=accent, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=8, pady=(6, 2))
    tk.Label(
        sec_c,
        text="On export, size and framing follow the selected type (general settings below).",
        bg=bg,
        fg=fg2,
        font=("Segoe UI", 8),
        wraplength=760,
        justify=tk.LEFT,
    ).pack(anchor="w", padx=8, pady=(0, 6))

    # --- D) Audio / altyazı stub ---
    sec_d = tk.Frame(frame, bg=bg, highlightthickness=1, highlightbackground="#334155")
    sec_d.pack(fill=tk.X, padx=8, pady=3)
    tk.Label(sec_d, text="D — Extra audio / subtitles", bg=bg, fg=accent, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=8, pady=(6, 2))
    row_d = tk.Frame(sec_d, bg=bg)
    row_d.pack(fill=tk.X, padx=8, pady=(0, 4))
    if not hasattr(app, "insta_extra_audio_var"):
        app.insta_extra_audio_var = tk.StringVar(value="")
    if not hasattr(app, "insta_srt_var"):
        app.insta_srt_var = tk.StringVar(value="")

    def _browse_audio():
        fp = filedialog.askopenfilename(filetypes=[("Audio", "*.mp3 *.aac *.wav *.m4a"), ("All files", "*.*")])
        if fp:
            app.insta_extra_audio_var.set(fp)

    def _browse_srt():
        fp = filedialog.askopenfilename(filetypes=[("Subtitles", "*.srt"), ("All files", "*.*")])
        if fp:
            app.insta_srt_var.set(fp)

    tk.Button(row_d, text="Extra audio file", bg="#0e7490", fg="#fff", font=("Segoe UI", 8), relief=tk.FLAT, padx=6, pady=2, command=_browse_audio).pack(side=tk.LEFT)
    tk.Entry(row_d, textvariable=app.insta_extra_audio_var, width=28, bg="#0e1e30", fg=fg, relief=tk.FLAT, bd=2).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
    row_d2 = tk.Frame(sec_d, bg=bg)
    row_d2.pack(fill=tk.X, padx=8, pady=(0, 6))
    tk.Button(row_d2, text="SRT subtitles", bg="#0e7490", fg="#fff", font=("Segoe UI", 8), relief=tk.FLAT, padx=6, pady=2, command=_browse_srt).pack(side=tk.LEFT)
    tk.Entry(row_d2, textvariable=app.insta_srt_var, width=40, bg="#0e1e30", fg=fg, relief=tk.FLAT, bd=2).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
    tk.Label(
        row_d2,
        text="(will hook into export pipeline in a later step)",
        bg=bg,
        fg=fg2,
        font=("Segoe UI", 7),
    ).pack(side=tk.LEFT)
    if hasattr(app, "sn_volume_var"):
        tk.Label(row_d2, text="Main volume:", bg=bg, fg=fg2, font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(12, 4))
        tk.Scale(row_d2, variable=app.sn_volume_var, from_=0.0, to=2.0, resolution=0.05, orient=tk.HORIZONTAL, bg=bg, fg=fg, highlightthickness=0, troughcolor="#0e1e30", length=120).pack(side=tk.LEFT)

    # --- E) Mətn / sticker ---
    sec_e = tk.Frame(frame, bg=bg, highlightthickness=1, highlightbackground="#334155")
    sec_e.pack(fill=tk.X, padx=8, pady=3)
    tk.Label(sec_e, text="E — Text / image overlay", bg=bg, fg=accent, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=8, pady=(6, 2))
    tk.Label(
        sec_e,
        text="Set text, image overlay, and second layer in the Export — general settings section below.",
        bg=bg,
        fg=fg2,
        font=("Segoe UI", 8),
        wraplength=760,
        justify=tk.LEFT,
    ).pack(anchor="w", padx=8, pady=(0, 6))

    # --- F) Codec / bitrate ---
    sec_f = tk.Frame(frame, bg=bg, highlightthickness=1, highlightbackground="#334155")
    sec_f.pack(fill=tk.X, padx=8, pady=3)
    tk.Label(sec_f, text="F — Encoding", bg=bg, fg=accent, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=8, pady=(6, 2))
    row_f = tk.Frame(sec_f, bg=bg)
    row_f.pack(fill=tk.X, padx=8, pady=(0, 6))
    tk.Label(row_f, text="Video: H.264 (libx264)  •  Audio: AAC", bg=bg, fg=fg, font=("Segoe UI", 9)).pack(side=tk.LEFT)
    tk.Label(row_f, text="Video bitrate:", bg=bg, fg=fg2, font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(16, 4))
    if not hasattr(app, "insta_bitrate_var"):
        app.insta_bitrate_var = tk.StringVar(value="6M")

    def _on_br_change(*_):
        vb = app.insta_bitrate_var.get()
        if "Instagram" in app._sn_platforms:
            app._sn_platforms["Instagram"]["vb"] = vb

    br = ttk.Combobox(
        row_f,
        textvariable=app.insta_bitrate_var,
        values=["5M", "5.5M", "6M", "6.5M", "7M", "8M"],
        state="readonly",
        width=8,
        font=("Segoe UI", 9),
    )
    br.pack(side=tk.LEFT)
    br.bind("<<ComboboxSelected>>", _on_br_change)
    tk.Label(row_f, text="FPS:", bg=bg, fg=fg2, font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(12, 4))
    if not hasattr(app, "insta_fps_var"):
        app.insta_fps_var = tk.StringVar(value="30")

    def _on_fps_change(*_):
        fp = app.insta_fps_var.get()
        if "Instagram" in app._sn_platforms:
            app._sn_platforms["Instagram"]["fps"] = fp

    fps_cb = ttk.Combobox(
        row_f,
        textvariable=app.insta_fps_var,
        values=["24", "25", "30", "50", "60"],
        state="readonly",
        width=5,
        font=("Segoe UI", 9),
    )
    fps_cb.pack(side=tk.LEFT)
    fps_cb.bind("<<ComboboxSelected>>", _on_fps_change)

    # --- G / H ---
    sec_gh = tk.Frame(frame, bg=bg, highlightthickness=1, highlightbackground="#334155")
    sec_gh.pack(fill=tk.X, padx=8, pady=3)
    tk.Label(sec_gh, text="G — Preview  •  H — Upload", bg=bg, fg=accent, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=8, pady=(6, 2))
    row_g = tk.Frame(sec_gh, bg=bg)
    row_g.pack(fill=tk.X, padx=8, pady=(0, 4))

    def _preview():
        if hasattr(app, "_start_social_preview"):
            app._start_social_preview()

    def _export():
        if hasattr(app, "_start_social"):
            app._start_social()

    tk.Button(row_g, text="Render preview", bg="#1e40af", fg="#fff", font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=10, pady=4, command=_preview).pack(side=tk.LEFT)
    tk.Button(row_g, text="Start export", bg="#7c3aed", fg="#fff", font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=10, pady=4, command=_export).pack(side=tk.LEFT, padx=6)
    if hasattr(app, "_social_open_source_in_player"):
        tk.Button(row_g, text="Open source in player", bg="#0f766e", fg="#fff", font=("Segoe UI", 9), relief=tk.FLAT, padx=8, pady=4, command=app._social_open_source_in_player).pack(side=tk.LEFT, padx=6)

    row_h = tk.Frame(sec_gh, bg=bg)
    row_h.pack(fill=tk.X, padx=8, pady=(0, 8))
    if not hasattr(app, "insta_api_key_var"):
        app.insta_api_key_var = tk.StringVar(value="")

    tk.Label(row_h, text="Access token (Meta Graph API — future OAuth):", bg=bg, fg=fg2, font=("Segoe UI", 8)).pack(side=tk.LEFT)
    tk.Entry(row_h, textvariable=app.insta_api_key_var, width=36, bg="#0e1e30", fg=fg, show="*", relief=tk.FLAT, bd=2).pack(side=tk.LEFT, padx=6, fill=tk.X, expand=True)
    tk.Button(
        row_h,
        text="Meta API — how it works",
        bg="#be185d",
        fg="#fff",
        font=("Segoe UI", 9),
        relief=tk.FLAT,
        padx=8,
        pady=4,
        command=lambda: show_meta_graph_reference_dialog(getattr(app, "root", None)),
    ).pack(side=tk.LEFT, padx=6)

    _apply_insta_mode(app)
    _on_br_change()
    _on_fps_change()
