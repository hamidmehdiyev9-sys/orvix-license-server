"""
Bütün sosial şəbəkə iş pəncərələri üçün vahid kompakt UI: platformaya uyğun 3 preset,
mənbə/çıxış/fon, bitrate/fps, premium progress, Start/Pause/Stop.
"""
from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Dict, List, Tuple

from orvix.file_info import FileInfoExtractor
from orvix.social_export_panel import ensure_social_export_vars
from orvix.social_tab import SOCIAL_PLATFORMS

F = ("Segoe UI", 8)
FB = ("Segoe UI", 8, "bold")

# platform → (mode_id, düymə mətni, export dict üstü yazıları)
PLATFORM_MODE_PRESETS: Dict[str, List[Tuple[str, str, Dict[str, Any]]]] = {
    "Facebook": [
        ("fb_169", "Feed 16:9", {"res": "1920x1080", "vb": "4M", "ab": "192k", "fps": "30"}),
        ("fb_916", "Story 9:16", {"res": "1080x1920", "vb": "4M", "ab": "128k", "fps": "30"}),
        ("fb_11", "Kvadrat 1:1", {"res": "1080x1080", "vb": "4M", "ab": "128k", "fps": "30"}),
    ],
    "WhatsApp": [
        ("wa_st", "Status 9:16", {"res": "1080x1920", "vb": "3M", "ab": "128k", "fps": "30"}),
        ("wa_169", "Landscape", {"res": "1280x720", "vb": "2.5M", "ab": "128k", "fps": "30"}),
        ("wa_11", "Kvadrat", {"res": "1080x1080", "vb": "3M", "ab": "128k", "fps": "30"}),
    ],
    "TikTok": [
        ("tt_fhd", "Tam vertikal", {"res": "1080x1920", "vb": "5M", "ab": "128k", "fps": "30"}),
        ("tt_hd", "HD vertikal", {"res": "720x1280", "vb": "4M", "ab": "128k", "fps": "30"}),
        ("tt_sq", "Kvadrat", {"res": "1080x1080", "vb": "4.5M", "ab": "128k", "fps": "30"}),
    ],
    "Telegram": [
        ("tg_720", "720p", {"res": "1280x720", "vb": "2.5M", "ab": "128k", "fps": "30"}),
        ("tg_1080", "1080p", {"res": "1920x1080", "vb": "4M", "ab": "128k", "fps": "30"}),
        ("tg_vert", "Vertikal", {"res": "720x1280", "vb": "2.5M", "ab": "128k", "fps": "30"}),
    ],
    "YouTube": [
        ("yt_fhd", "Full HD 16:9", {"res": "1920x1080", "vb": "8M", "ab": "192k", "fps": "30"}),
        ("yt_shorts", "Shorts 9:16", {"res": "1080x1920", "vb": "8M", "ab": "192k", "fps": "30"}),
        ("yt_720", "HD 720p", {"res": "1280x720", "vb": "5M", "ab": "192k", "fps": "30"}),
    ],
    "Snapchat": [
        ("sc_full", "Story 9:16", {"res": "1080x1920", "vb": "5M", "ab": "128k", "fps": "30"}),
        ("sc_hd", "HD vertikal", {"res": "720x1280", "vb": "4M", "ab": "128k", "fps": "30"}),
        ("sc_sq", "Kvadrat", {"res": "1080x1080", "vb": "4.5M", "ab": "128k", "fps": "30"}),
    ],
    "Twitter / X": [
        ("tw_720", "720p", {"res": "1280x720", "vb": "2M", "ab": "128k", "fps": "30"}),
        ("tw_1080", "1080p", {"res": "1920x1080", "vb": "3.5M", "ab": "128k", "fps": "30"}),
        ("tw_vert", "Vertikal", {"res": "1080x1920", "vb": "3M", "ab": "128k", "fps": "30"}),
    ],
    "LinkedIn": [
        ("li_169", "Video 16:9", {"res": "1920x1080", "vb": "3.5M", "ab": "128k", "fps": "30"}),
        ("li_11", "Kvadrat", {"res": "1080x1080", "vb": "3.5M", "ab": "128k", "fps": "30"}),
        ("li_45", "4:5", {"res": "1080x1350", "vb": "3.5M", "ab": "128k", "fps": "30"}),
    ],
    "Pinterest": [
        ("pi_pin", "Pin 2:3", {"res": "1000x1500", "vb": "3M", "ab": "128k", "fps": "30"}),
        ("pi_sq", "Kvadrat", {"res": "1080x1080", "vb": "3M", "ab": "128k", "fps": "30"}),
        ("pi_169", "16:9", {"res": "1920x1080", "vb": "3.5M", "ab": "128k", "fps": "30"}),
    ],
    "VKontakte (VK)": [
        ("vk_720", "720p", {"res": "1280x720", "vb": "2.5M", "ab": "128k", "fps": "30"}),
        ("vk_1080", "1080p", {"res": "1920x1080", "vb": "4M", "ab": "128k", "fps": "30"}),
        ("vk_vert", "Vertikal", {"res": "1080x1920", "vb": "3.5M", "ab": "128k", "fps": "30"}),
    ],
    "Reddit": [
        ("rd_169", "16:9", {"res": "1920x1080", "vb": "2.5M", "ab": "128k", "fps": "30"}),
        ("rd_720", "720p", {"res": "1280x720", "vb": "2M", "ab": "128k", "fps": "30"}),
        ("rd_vert", "Vertikal", {"res": "1080x1920", "vb": "2.5M", "ab": "128k", "fps": "30"}),
    ],
    "Triller": [
        ("tr_fhd", "Tam vertikal", {"res": "1080x1920", "vb": "5M", "ab": "128k", "fps": "30"}),
        ("tr_hd", "HD", {"res": "720x1280", "vb": "4M", "ab": "128k", "fps": "30"}),
        ("tr_11", "Kvadrat", {"res": "1080x1080", "vb": "4.5M", "ab": "128k", "fps": "30"}),
    ],
    "Messenger": [
        ("ms_720", "720p", {"res": "1280x720", "vb": "2M", "ab": "128k", "fps": "30"}),
        ("ms_169", "16:9 HD", {"res": "1920x1080", "vb": "2.5M", "ab": "128k", "fps": "30"}),
        ("ms_vert", "Vertikal", {"res": "1080x1920", "vb": "2.5M", "ab": "128k", "fps": "30"}),
    ],
}

# Düymə rəngləri (aktiv / passiv)
PLATFORM_THEME = {
    "Facebook": ("#1877f2", "#1e3a5f"),
    "WhatsApp": ("#25d366", "#14532d"),
    "TikTok": ("#fe2c55", "#5c1a2e"),
    "Telegram": ("#229ed9", "#164e66"),
    "YouTube": ("#ff0000", "#5c1a1a"),
    "Snapchat": ("#ff6b35", "#5c2a12"),
    "Twitter / X": ("#1d9bf0", "#163d52"),
    "LinkedIn": ("#0a66c2", "#143d66"),
    "Pinterest": ("#e60023", "#5c1420"),
    "VKontakte (VK)": ("#0077ff", "#143d66"),
    "Reddit": ("#ff4500", "#5c260d"),
    "Triller": ("#ff0050", "#5c0020"),
    "Messenger": ("#006aff", "#143d66"),
}

PLATFORM_HINT = {
    "Facebook": "Feed, Story, square — export near Meta recommended sizes.",
    "WhatsApp": "Status 9:16, landscape, square — watch output file size.",
    "TikTok": "Mostly 9:16 vertical video.",
    "Telegram": "720p / 1080p for chat and channels.",
    "YouTube": "Regular video 16:9, Shorts 9:16.",
    "Snapchat": "Story format 9:16.",
    "Twitter / X": "720p/1080p for videos up to ~2:20.",
    "LinkedIn": "Business video: 16:9, square, and 4:5.",
    "Pinterest": "Pins often favor 2:3.",
    "VKontakte (VK)": "Standard web and mobile sizes.",
    "Reddit": "Pick a size that fits the subreddit.",
    "Triller": "Vertical music video.",
    "Messenger": "Lighter sizes for Facebook Messenger.",
}


def _try_hook_file_drop(widget, on_paths):
    try:
        import windnd

        def _cb(fs):
            if not fs:
                return
            p = fs[0]
            if isinstance(p, bytes):
                p = p.decode("utf-8", errors="replace")
            on_paths(p)

        windnd.hook_dropfiles(widget, func=_cb)
    except Exception:
        pass


def _btn(parent, text, cmd, bg, ab=None, **kw):
    return tk.Button(
        parent,
        text=text,
        command=cmd,
        bg=bg,
        fg="#fff",
        font=FB,
        relief=tk.FLAT,
        padx=kw.get("padx", 8),
        pady=kw.get("pady", 6),
        cursor="hand2",
        activebackground=ab or bg,
        activeforeground="#fff",
    )


def install_compact_social_workspace(app, parent, plat: str):
    """Instagram-dan başqa platformalar üçün kompakt panel."""
    from orvix.social_workspace import social_workspace_dialog_parent

    ensure_social_export_vars(app)
    dlg_parent = social_workspace_dialog_parent(app)

    if not hasattr(app, "sn_ws_bitrate_var"):
        app.sn_ws_bitrate_var = tk.StringVar(value="4M")
    if not hasattr(app, "sn_ws_fps_var"):
        app.sn_ws_fps_var = tk.StringVar(value="30")

    bg = "#1e293b"
    fg = "#e2e8f0"
    fg2 = "#94a3b8"

    modes = PLATFORM_MODE_PRESETS.get(plat)
    if not modes:
        base = SOCIAL_PLATFORMS.get(plat, {})
        modes = [
            ("def_a", "Variant A", {}),
            ("def_b", "Variant B", dict(base)),
            ("def_c", "Variant C", dict(base)),
        ]

    mode_on, mode_off = PLATFORM_THEME.get(plat, ("#7c3aed", "#334155"))

    if not hasattr(app, "_sn_compact_mode_by_plat"):
        app._sn_compact_mode_by_plat = {}
    if plat not in app._sn_compact_mode_by_plat:
        app._sn_compact_mode_by_plat[plat] = tk.StringVar(value=modes[0][0])

    mode_var = app._sn_compact_mode_by_plat[plat]
    _mode_btns: Dict[str, tk.Button] = {}

    def _merge_platform(mode_id: str):
        base = dict(SOCIAL_PLATFORMS.get(plat, {}))
        for mid, _lbl, ov in modes:
            if mid == mode_id:
                base.update(ov)
                break
        app._sn_platforms[plat] = base
        app.sn_ws_bitrate_var.set(base.get("vb", "4M"))
        app.sn_ws_fps_var.set(base.get("fps", "30"))

    def _sync_ws_to_platform(*_):
        try:
            p = app._sn_platforms.setdefault(plat, dict(SOCIAL_PLATFORMS.get(plat, {})))
            p["vb"] = app.sn_ws_bitrate_var.get()
            p["fps"] = app.sn_ws_fps_var.get()
            p["vc"] = "libx264"
            p["ac"] = "aac"
            if "ab" not in p:
                p["ab"] = "128k"
        except Exception:
            pass

    def _register_global_ws_traces():
        """Bitrate/FPS dəyişəndə cari platformanın _sn_platforms yazılsın (pəncərə dəyişəndə düzgün)."""
        if getattr(app, "_sn_ws_trace_global", False):
            return

        def _sync(*_):
            try:
                if not hasattr(app, "sn_ws_bitrate_var"):
                    return
                pkey = app.sn_platform_var.get()
                p = app._sn_platforms.setdefault(pkey, dict(SOCIAL_PLATFORMS.get(pkey, {})))
                p["vb"] = app.sn_ws_bitrate_var.get()
                p["fps"] = app.sn_ws_fps_var.get()
                p["vc"] = "libx264"
            except Exception:
                pass

        app.sn_ws_bitrate_var.trace_add("write", lambda *_: _sync())
        app.sn_ws_fps_var.trace_add("write", lambda *_: _sync())
        app._sn_ws_trace_global = True

    def _paint_modes():
        cur = mode_var.get()
        for mid, _lbl, _ in modes:
            b = _mode_btns.get(mid)
            if b:
                b.config(bg=mode_on if mid == cur else mode_off, activebackground=mode_on if mid == cur else "#475569")

    def _select_mode(mode_id: str):
        mode_var.set(mode_id)
        _merge_platform(mode_id)
        _paint_modes()
        try:
            app._social_workspace_sync_player()
        except Exception:
            pass

    meta_var = tk.StringVar(value="—")

    def _meta_vals():
        path = (app.sn_input_var.get() or "").strip()
        if not path or not os.path.isfile(path):
            return "—", "—", "—", "—"
        try:
            info = FileInfoExtractor.extract(path)
            v = info.get("video") or {}
            fmt = info.get("format") or {}
            return (
                str(v.get("resolution", "?")),
                str(fmt.get("duration", "?")),
                str(v.get("fps_display", v.get("fps", "?"))),
                str((info.get("file") or {}).get("size", "?")),
            )
        except Exception:
            return "—", "—", "—", "—"

    def _after_input(path: str):
        if not path:
            return
        app.sn_input_var.set(path)
        a, b, c, d = _meta_vals()
        meta_var.set(f"{a}  •  {b}  •  {c}  •  {d}")
        try:
            app._social_workspace_sync_player()
        except Exception:
            pass

    def _browse_in():
        fp = filedialog.askopenfilename(
            parent=dlg_parent,
            filetypes=[("Video", "*.mp4 *.mov *.mkv *.webm"), ("All files", "*.*")],
        )
        if fp:
            _after_input(fp)

    def _refresh_meta():
        a, b, c, d = _meta_vals()
        meta_var.set(f"{a}  •  {b}  •  {c}  •  {d}")

    root = tk.Frame(parent, bg=bg)
    root.pack(fill=tk.X)

    hint = PLATFORM_HINT.get(plat, "Export settings are selected for this platform.")
    tk.Label(root, text=hint, bg=bg, fg=fg2, font=F, wraplength=420, justify=tk.LEFT).pack(anchor="w", pady=(0, 4))

    mode_row = tk.Frame(root, bg=bg)
    mode_row.pack(fill=tk.X, pady=(2, 4))
    for mid, lbl, _ov in modes:
        b = tk.Button(
            mode_row,
            text=lbl,
            font=("Segoe UI", 9, "bold"),
            fg="#fff",
            relief=tk.FLAT,
            padx=8,
            pady=6,
            cursor="hand2",
            command=lambda m=mid: _select_mode(m),
        )
        b.pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        _mode_btns[mid] = b

    r1 = tk.Frame(root, bg=bg)
    r1.pack(fill=tk.X, pady=(0, 3))
    tk.Label(r1, text="Video", bg=bg, fg=fg2, font=F, width=10, anchor="w").pack(side=tk.LEFT)
    ent_in = tk.Entry(r1, textvariable=app.sn_input_var, bg="#0f172a", fg=fg, font=F, relief=tk.FLAT, bd=1)
    ent_in.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
    _try_hook_file_drop(ent_in, _after_input)
    _btn(r1, "…", _browse_in, "#0369a1", "#0284c7", padx=6, pady=4).pack(side=tk.LEFT)

    out_row = tk.Frame(root, bg=bg)
    out_row.pack(fill=tk.X, pady=(2, 3))
    tk.Label(out_row, text="Output", bg=bg, fg=fg2, font=F, width=10, anchor="w").pack(side=tk.LEFT)
    tk.Entry(out_row, textvariable=app.sn_output_var, bg="#0f172a", fg=fg, font=F, relief=tk.FLAT, bd=1).pack(
        side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6)
    )
    _btn(out_row, "…", app._sn_browse_output, "#0369a1", "#0284c7", padx=6, pady=4).pack(side=tk.LEFT)

    bg_row = tk.Frame(root, bg=bg)
    bg_row.pack(fill=tk.X, pady=(2, 3))
    tk.Label(bg_row, text="Background", bg=bg, fg=fg2, font=F, width=10, anchor="w").pack(side=tk.LEFT)
    tk.Entry(bg_row, textvariable=app.sn_bg_img_var, bg="#0f172a", fg=fg, font=F, relief=tk.FLAT, bd=1).pack(
        side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6)
    )

    def _browse_bg():
        fp = filedialog.askopenfilename(
            parent=dlg_parent,
            filetypes=[("Image", "*.png *.jpg *.jpeg *.webp"), ("All files", "*.*")],
        )
        if fp:
            app.sn_bg_img_var.set(fp)

    _btn(bg_row, "…", _browse_bg, "#0f766e", "#059669", padx=6, pady=4).pack(side=tk.LEFT)

    time_row = tk.Frame(root, bg=bg)
    time_row.pack(fill=tk.X, pady=(2, 2))
    tk.Label(time_row, text="Start", bg=bg, fg=fg2, font=F).pack(side=tk.LEFT)
    tk.Entry(time_row, textvariable=app.sn_start_var, width=9, bg="#0f172a", fg=fg, font=F, relief=tk.FLAT, bd=1).pack(
        side=tk.LEFT, padx=4
    )
    tk.Label(time_row, text="End", bg=bg, fg=fg2, font=F).pack(side=tk.LEFT, padx=(4, 0))
    tk.Entry(time_row, textvariable=app.sn_end_var, width=9, bg="#0f172a", fg=fg, font=F, relief=tk.FLAT, bd=1).pack(
        side=tk.LEFT, padx=4
    )
    tk.Label(time_row, text="Max", bg=bg, fg=fg2, font=F).pack(side=tk.LEFT)
    ttk.Combobox(
        time_row,
        textvariable=app.sn_max_duration_var,
        values=["Auto", "15", "30", "60", "90", "300"],
        state="readonly",
        width=7,
        font=F,
    ).pack(side=tk.LEFT, padx=4)

    meta_row = tk.Frame(root, bg=bg)
    meta_row.pack(fill=tk.X, pady=(2, 2))
    tk.Label(meta_row, textvariable=meta_var, bg=bg, fg="#a5b4fc", font=("Consolas", 8), anchor="w").pack(
        side=tk.LEFT, fill=tk.X, expand=True
    )
    _btn(meta_row, "↻", _refresh_meta, "#334155", "#475569", padx=4, pady=2).pack(side=tk.RIGHT)

    opt_row = tk.Frame(root, bg=bg)
    opt_row.pack(fill=tk.X, pady=(2, 4))
    tk.Label(opt_row, text="Bitrate", bg=bg, fg=fg2, font=F).pack(side=tk.LEFT, padx=(0, 4))
    ttk.Combobox(
        opt_row,
        textvariable=app.sn_ws_bitrate_var,
        values=["2M", "2.5M", "3M", "3.5M", "4M", "5M", "5.5M", "6M", "6.5M", "7M", "8M", "10M"],
        state="readonly",
        width=7,
        font=F,
    ).pack(side=tk.LEFT, padx=(0, 10))
    tk.Label(opt_row, text="FPS", bg=bg, fg=fg2, font=F).pack(side=tk.LEFT, padx=(0, 4))
    ttk.Combobox(
        opt_row,
        textvariable=app.sn_ws_fps_var,
        values=["24", "25", "30", "60"],
        state="readonly",
        width=5,
        font=F,
    ).pack(side=tk.LEFT)

    prev_row = tk.Frame(root, bg=bg)
    prev_row.pack(fill=tk.X, pady=(0, 4))
    pst2 = dict(font=("Segoe UI", 8, "bold"), relief=tk.FLAT, cursor="hand2", padx=8, pady=4, bd=0)
    tk.Button(
        prev_row,
        text="Preview",
        bg="#1e40af",
        fg="#fff",
        command=app._start_social_preview,
        activebackground="#2563eb",
        **pst2,
    ).pack(side=tk.LEFT, padx=(0, 6))
    tk.Button(
        prev_row,
        text="Source in player",
        bg="#0f766e",
        fg="#fff",
        command=app._social_open_source_in_player,
        activebackground="#059669",
        **pst2,
    ).pack(side=tk.LEFT)

    proc = tk.Frame(root, bg="#0c1220", padx=8, pady=8)
    proc.pack(fill=tk.X, pady=(6, 0))
    pst = dict(font=("Segoe UI", 9, "bold"), relief=tk.FLAT, cursor="hand2", padx=12, pady=8, bd=0)
    ph = tk.Frame(proc, bg="#0c1220")
    ph.pack(fill=tk.X)
    tk.Button(ph, text="Start", bg="#047857", fg="#ecfdf5", command=app._start_social, activebackground="#059669", **pst).pack(
        side=tk.LEFT, padx=3, expand=True, fill=tk.X
    )
    tk.Button(
        ph,
        text="Pause",
        bg="#b45309",
        fg="#ffedd5",
        command=app._sn_pause_social_encoding,
        activebackground="#d97706",
        **pst,
    ).pack(side=tk.LEFT, padx=3, expand=True, fill=tk.X)
    tk.Button(ph, text="Stop", bg="#7f1d1d", fg="#fecaca", command=app._stop_social, activebackground="#991b1b", **pst).pack(
        side=tk.LEFT, padx=3, expand=True, fill=tk.X
    )
    tk.Label(
        ph,
        textvariable=app.instagram_ws_status_var,
        bg="#0c1220",
        fg="#fde68a",
        font=("Segoe UI", 9, "bold"),
    ).pack(side=tk.RIGHT, padx=4)

    pb_row = tk.Frame(proc, bg="#0c1220")
    pb_row.pack(fill=tk.X, pady=(8, 4))
    try:
        ttk.Progressbar(
            pb_row,
            style="Social.Horizontal.TProgressbar",
            variable=app.sn_pv,
            maximum=100,
            length=400,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)
    except Exception:
        ttk.Progressbar(pb_row, variable=app.sn_pv, maximum=100, length=400).pack(side=tk.LEFT, fill=tk.X, expand=True)

    tk.Label(
        proc,
        textvariable=app.instagram_progress_detail_var,
        bg="#0c1220",
        fg="#94a3b8",
        font=("Consolas", 8),
        anchor="w",
        justify=tk.LEFT,
        wraplength=420,
    ).pack(fill=tk.X, pady=(4, 0))

    _merge_platform(mode_var.get())
    _paint_modes()

    _register_global_ws_traces()
    _sync_ws_to_platform()

    _refresh_meta()
    try:
        app._social_workspace_sync_player()
    except Exception:
        pass
