"""
Instagram — kompakt konverter: Feed / Reels / Stories, mənbə + çıxış, istəyə görə fon şəkli.
"""
import os
import tkinter as tk
from tkinter import filedialog, ttk

from orvix.instagram_video_module import InstagramVideoModule
from orvix import instagram_panel as ig
from orvix.social_export_panel import ensure_social_export_vars
from orvix.social_workspace import social_workspace_dialog_parent

F = ("Segoe UI", 8)
FB = ("Segoe UI", 8, "bold")


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


def install_instagram_workspace(app, parent):
    ensure_social_export_vars(app)
    dlg_parent = social_workspace_dialog_parent(app)
    bg = "#1e293b"
    fg = "#e2e8f0"
    fg2 = "#94a3b8"

    app._instagram_workspace_simple = True
    app.sn_platform_var.set("Instagram")

    # Köhnə qat / çoxlu video yox — sade konverter
    for vn in (
        "insta_layer_bg_var",
        "insta_layer_top_var",
        "insta_layer_bottom_var",
        "insta_layer_center_var",
    ):
        if hasattr(app, vn):
            getattr(app, vn).set("")
    if hasattr(app, "insta_layer_layout_json_var"):
        app.insta_layer_layout_json_var.set("")
    for i in (1, 2, 3):
        if hasattr(app, f"insta_video_slot_{i}_var"):
            getattr(app, f"insta_video_slot_{i}_var").set("")

    mod = InstagramVideoModule(app)
    app._instagram_module = mod

    if not hasattr(app, "insta_mode_var"):
        app.insta_mode_var = tk.StringVar(value="Feed")
    if not hasattr(app, "insta_feed_aspect_var"):
        app.insta_feed_aspect_var = tk.StringVar(value="1:1")
    if not hasattr(app, "insta_bitrate_var"):
        app.insta_bitrate_var = tk.StringVar(value="6.5M")
    if not hasattr(app, "insta_fps_var"):
        app.insta_fps_var = tk.StringVar(value="30")
    if not hasattr(app, "insta_video_codec_var"):
        app.insta_video_codec_var = tk.StringVar(value="H.264")
    if not hasattr(app, "insta_custom_res_var"):
        app.insta_custom_res_var = tk.StringVar(value="")

    app.insta_hint_lbl = tk.Label(parent, text="", bg=bg)
    app.insta_profile_spec_lbl = tk.Label(parent, text="", bg=bg)

    meta_var = tk.StringVar(value="—")

    def _meta_vals():
        m = mod.read_metadata()
        if not m:
            return "—", "—", "—", "—"
        return (
            str(m.get("resolution", "?")),
            str(m.get("duration_display", "?")),
            str(m.get("fps", "?")),
            str(m.get("file_size", "?")),
        )

    def _after_input(path: str):
        if not path:
            return
        app.sn_input_var.set(path)
        mod.import_video(path)
        a, b, c, d = _meta_vals()
        meta_var.set(f"{a}  •  {b}  •  {c}  •  {d}")
        app._instagram_workspace_preview_mode()

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

    # Mənbə
    r1 = tk.Frame(root, bg=bg)
    r1.pack(fill=tk.X, pady=(0, 3))
    tk.Label(r1, text="Video", bg=bg, fg=fg2, font=F, width=10, anchor="w").pack(side=tk.LEFT)
    ent_in = tk.Entry(r1, textvariable=app.sn_input_var, bg="#0f172a", fg=fg, font=F, relief=tk.FLAT, bd=1)
    ent_in.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
    _try_hook_file_drop(ent_in, _after_input)
    _btn(r1, "…", _browse_in, "#0369a1", "#0284c7", padx=6, pady=4).pack(side=tk.LEFT)

    # Feed / Reels / Stories
    mode_row = tk.Frame(root, bg=bg)
    mode_row.pack(fill=tk.X, pady=(4, 2))
    MODE_ON = "#7c3aed"
    MODE_OFF = "#334155"
    _mode_btns = {}

    def _paint_modes():
        m = app.insta_mode_var.get()
        for name, b in _mode_btns.items():
            b.config(bg=MODE_ON if name == m else MODE_OFF, activebackground=MODE_ON if name == m else "#475569")

    def _select_mode(mode):
        app.insta_mode_var.set(mode)
        app.insta_custom_res_var.set("")
        ig._apply_insta_mode(app)
        _paint_modes()
        if mode == "Feed":
            feed_aspect_row.pack(fill=tk.X, pady=(0, 3))
        else:
            feed_aspect_row.pack_forget()
        app._instagram_workspace_preview_mode()

    for label, key in (("Feed", "Feed"), ("Reels", "Reels"), ("Stories", "Stories")):
        b = tk.Button(
            mode_row,
            text=label,
            font=("Segoe UI", 9, "bold"),
            fg="#fff",
            relief=tk.FLAT,
            padx=10,
            pady=6,
            cursor="hand2",
            command=lambda k=key: _select_mode(k),
        )
        b.pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        _mode_btns[key] = b

    feed_aspect_row = tk.Frame(root, bg=bg)
    tk.Label(feed_aspect_row, text="Feed", bg=bg, fg=fg2, font=F).pack(side=tk.LEFT, padx=(0, 6))
    cb_aspect = ttk.Combobox(
        feed_aspect_row,
        textvariable=app.insta_feed_aspect_var,
        values=["1:1", "4:5"],
        state="readonly",
        width=5,
        font=F,
    )
    cb_aspect.pack(side=tk.LEFT)

    def _on_feed_aspect(_e=None):
        app.insta_custom_res_var.set("")
        ig._apply_insta_mode(app)
        app._instagram_workspace_preview_mode()

    cb_aspect.bind("<<ComboboxSelected>>", _on_feed_aspect)

    if app.insta_mode_var.get() == "Feed":
        feed_aspect_row.pack(fill=tk.X, pady=(0, 3))

    # Çıxış
    out_row = tk.Frame(root, bg=bg)
    out_row.pack(fill=tk.X, pady=(3, 3))
    tk.Label(out_row, text="Output", bg=bg, fg=fg2, font=F, width=10, anchor="w").pack(side=tk.LEFT)
    tk.Entry(out_row, textvariable=app.sn_output_var, bg="#0f172a", fg=fg, font=F, relief=tk.FLAT, bd=1).pack(
        side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6)
    )
    _btn(out_row, "…", app._sn_browse_output, "#0369a1", "#0284c7", padx=6, pady=4).pack(side=tk.LEFT)

    # Background image (social export bg_img)
    bg_row = tk.Frame(root, bg=bg)
    bg_row.pack(fill=tk.X, pady=(2, 4))
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

    # Meta + bitrate / fps
    meta_row = tk.Frame(root, bg=bg)
    meta_row.pack(fill=tk.X, pady=(0, 2))
    tk.Label(
        meta_row,
        textvariable=meta_var,
        bg=bg,
        fg="#a5b4fc",
        font=("Consolas", 8),
        anchor="w",
        justify=tk.LEFT,
    ).pack(side=tk.LEFT, fill=tk.X, expand=True)
    _btn(meta_row, "↻", _refresh_meta, "#334155", "#475569", padx=4, pady=2).pack(side=tk.RIGHT)

    opt_row = tk.Frame(root, bg=bg)
    opt_row.pack(fill=tk.X, pady=(0, 4))
    tk.Label(opt_row, text="Bitrate", bg=bg, fg=fg2, font=F).pack(side=tk.LEFT, padx=(0, 4))
    ttk.Combobox(
        opt_row,
        textvariable=app.insta_bitrate_var,
        values=["5M", "5.5M", "6M", "6.5M", "7M", "7.5M", "8M", "8.5M", "9M", "10M"],
        state="readonly",
        width=7,
        font=F,
    ).pack(side=tk.LEFT, padx=(0, 10))
    tk.Label(opt_row, text="FPS", bg=bg, fg=fg2, font=F).pack(side=tk.LEFT, padx=(0, 4))
    ttk.Combobox(
        opt_row,
        textvariable=app.insta_fps_var,
        values=["24", "25", "30", "60"],
        state="readonly",
        width=5,
        font=F,
    ).pack(side=tk.LEFT)

    # Premium progress + Start / Pause / Stop (üslub pv_main._styles()-də)
    proc = tk.Frame(root, bg="#0c1220", padx=8, pady=8)
    proc.pack(fill=tk.X, pady=(8, 0))
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
    tk.Label(ph, textvariable=app.instagram_ws_status_var, bg="#0c1220", fg="#fde68a", font=("Segoe UI", 9, "bold")).pack(
        side=tk.RIGHT, padx=4
    )

    pb_row = tk.Frame(proc, bg="#0c1220")
    pb_row.pack(fill=tk.X, pady=(8, 4))
    try:
        ttk.Progressbar(
            pb_row,
            style="IG.Horizontal.TProgressbar",
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

    def _sync_ig(*_):
        try:
            igd = app._sn_platforms.setdefault("Instagram", {})
            igd["vb"] = app.insta_bitrate_var.get()
            igd["fps"] = app.insta_fps_var.get()
            igd["vc"] = "libx264"
        except Exception:
            pass

    if not getattr(app, "_insta_preset_trace_done", False):
        app._insta_preset_trace_done = True
        for _attr in ("insta_bitrate_var", "insta_fps_var"):
            if hasattr(app, _attr):
                getattr(app, _attr).trace_add("write", lambda *_: _sync_ig())
    _sync_ig()

    if app.insta_mode_var.get() == "Story":
        app.insta_mode_var.set("Stories")
    ig._apply_insta_mode(app)
    _refresh_meta()
    _paint_modes()

    try:
        app._instagram_setup_workspace_player()
    except Exception:
        pass
    app._instagram_workspace_preview_mode()
