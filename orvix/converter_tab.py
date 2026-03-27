# -*- coding: utf-8 -*-
"""Video Converter — compact notebook UI + modern preset strip + fixed bottom dock."""
from tkinter import filedialog, scrolledtext, ttk
import tkinter as tk

def _btn(**extra):
    base = dict(font=("Segoe UI", 9, "bold"), relief=tk.FLAT, cursor="hand2", bd=0)
    base.update(extra)
    return base


def _btn_sm(**extra):
    base = dict(font=("Segoe UI", 8, "bold"), relief=tk.FLAT, cursor="hand2", bd=0, padx=8, pady=3)
    base.update(extra)
    return base


def _section_label(parent, text, bg, fg_accent):
    tk.Label(parent, text=text, bg=bg, fg=fg_accent, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))


def _hint(parent, bg, text, wrap=520):
    tk.Label(
        parent,
        text=text,
        bg=bg,
        fg="#64748b",
        font=("Segoe UI", 8),
        wraplength=wrap,
        justify=tk.LEFT,
    ).pack(anchor="w", pady=(0, 6))


def _scroll_area(parent, bg):
    """Scrollable inner frame; siçan çarxı yalnız bu ağacda (bind_all yox — bütün GUI-ni yavaşlatmır)."""
    wrap = tk.Frame(parent, bg=bg)
    c = tk.Canvas(wrap, bg=bg, highlightthickness=0)
    vsb = ttk.Scrollbar(wrap, orient=tk.VERTICAL, command=c.yview)
    inner = tk.Frame(c, bg=bg)

    def _cfg(_e=None):
        c.configure(scrollregion=c.bbox("all"))

    inner.bind("<Configure>", _cfg)
    win_id = c.create_window((0, 0), window=inner, anchor="nw")

    def _on_canvas_cfg(e):
        c.itemconfigure(win_id, width=e.width)

    c.bind("<Configure>", _on_canvas_cfg)
    c.configure(yscrollcommand=vsb.set)

    def _wheel_win(e):
        d = getattr(e, "delta", 0) or 0
        if d == 0:
            return
        if abs(d) < 120:
            c.yview_scroll(-1 if d > 0 else 1, "units")
        else:
            c.yview_scroll(int(-1 * (d / 120)), "units")

    def _wheel_x11_up(_e=None):
        c.yview_scroll(-1, "units")

    def _wheel_x11_down(_e=None):
        c.yview_scroll(1, "units")

    c.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    vsb.pack(side=tk.RIGHT, fill=tk.Y)
    wrap.pack(fill=tk.BOTH, expand=True)
    return inner


_CHIP_OFF = "#1e293b"
_CHIP_ON = "#0d9488"
_CHIP_FG_OFF = "#cbd5e1"
_CHIP_FG_ON = "#f0fdfa"
_CHIP_FONT = ("Segoe UI", 8, "bold")


def _chip_style(btn, active: bool):
    btn.config(
        bg=_CHIP_ON if active else _CHIP_OFF,
        fg=_CHIP_FG_ON if active else _CHIP_FG_OFF,
        activebackground=_CHIP_ON if active else _CHIP_OFF,
        activeforeground=_CHIP_FG_ON if active else _CHIP_FG_OFF,
    )


def _chip_section(parent, bg, app, var_attr: str, title: str, choices: list, *, trace=True):
    """choices: [(label, value), ...] — compact toggle buttons; value matches StringVar."""
    var = getattr(app, var_attr)
    box = tk.Frame(parent, bg=bg)
    tk.Label(box, text=title, bg=bg, fg="#94a3b8", font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 4))
    row = tk.Frame(box, bg=bg)
    btns = []

    def sync(_a=None, _b=None, _c=None):
        try:
            cur = var.get()
        except Exception:
            return
        for (lbl, val), b in zip(choices, btns):
            _chip_style(b, str(cur) == str(val))

    def pick(val):
        var.set(val)
        sync()

    for lbl, val in choices:
        b = tk.Button(
            row,
            text=lbl,
            font=_CHIP_FONT,
            relief=tk.FLAT,
            cursor="hand2",
            bd=0,
            padx=8,
            pady=5,
            command=lambda v=val: pick(v),
        )
        b.pack(side=tk.LEFT, padx=2, pady=2)
        btns.append(b)
    sync()
    if trace:
        try:
            var.trace_add("write", sync)
        except Exception:
            pass
    row.pack(fill=tk.X, anchor="w")
    box.pack(fill=tk.X, pady=(0, 10))


def _bool_chip_section(parent, bg, app, var_attr: str, title: str, *, on_label="ON", off_label="OFF"):
    var = getattr(app, var_attr)
    box = tk.Frame(parent, bg=bg)
    tk.Label(box, text=title, bg=bg, fg="#94a3b8", font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 4))

    btn = tk.Button(
        box,
        text=off_label,
        font=_CHIP_FONT,
        relief=tk.FLAT,
        cursor="hand2",
        bd=0,
        padx=12,
        pady=5,
    )

    def sync(_a=None, _b=None, _c=None):
        try:
            on = bool(var.get())
        except Exception:
            on = False
        _chip_style(btn, on)
        btn.config(text=on_label if on else off_label)

    def toggle():
        var.set(not bool(var.get()))
        sync()

    btn.config(command=toggle)
    btn.pack(anchor="w", pady=2)
    sync()
    try:
        var.trace_add("write", sync)
    except Exception:
        pass
    box.pack(fill=tk.X, pady=(0, 8))


# One-click workflow presets (FFmpeg-friendly defaults)
_CONV_PRESETS = {
    "match": {
        "conv_container": "mp4",
        "conv_vcodec": "libx264",
        "conv_acodec": "aac",
        "conv_res": "Original",
        "conv_preset": "veryfast",
        "conv_crf": "23",
        "conv_vbitrate": "Auto",
        "conv_abitrate": "192k",
        "hw_encoder": "Software (default)",
    },
    "1080p": {
        "conv_container": "mp4",
        "conv_vcodec": "libx264",
        "conv_acodec": "aac",
        "conv_res": "1920x1080",
        "conv_preset": "veryfast",
        "conv_crf": "20",
        "conv_vbitrate": "Auto",
        "conv_abitrate": "192k",
        "hw_encoder": "Software (default)",
    },
    "720p": {
        "conv_container": "mp4",
        "conv_vcodec": "libx264",
        "conv_acodec": "aac",
        "conv_res": "1280x720",
        "conv_preset": "veryfast",
        "conv_crf": "24",
        "conv_vbitrate": "4M",
        "conv_abitrate": "128k",
        "hw_encoder": "Software (default)",
    },
    "hevc": {
        "conv_container": "mkv",
        "conv_vcodec": "libx265",
        "conv_acodec": "aac",
        "conv_res": "1920x1080",
        "conv_preset": "veryfast",
        "conv_crf": "24",
        "conv_vbitrate": "Auto",
        "conv_abitrate": "192k",
        "hw_encoder": "Software (default)",
    },
    # ~170 MB target total size; mux bitrate is computed from duration at encode time (see pv_main).
    "whatsapp170": {
        "conv_container": "mp4",
        "conv_vcodec": "libx264",
        "conv_acodec": "aac",
        "conv_res": "1280x720",
        "conv_preset": "veryfast",
        "conv_crf": "23",
        "conv_vbitrate": "__TARGET_MB_170__",
        "conv_abitrate": "128k",
        "hw_encoder": "Software (default)",
    },
}


def _apply_conv_preset(app, key: str):
    data = _CONV_PRESETS.get(key)
    if not data:
        return
    for attr, val in data.items():
        v = getattr(app, attr, None)
        if v is None:
            continue
        try:
            v.set(val)
        except Exception:
            pass
    if hasattr(app, "conv_status"):
        try:
            app.conv_status.config(text=f"Preset: {key}")
        except Exception:
            pass


def install_converter_ui(app, parent):
    BG = app.BG
    BG2 = app.BG2
    BG3 = app.BG3
    FG = app.FG
    FG2 = app.FG2
    AC = app.AC

    outer = tk.Frame(parent, bg=BG)
    outer.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # --- Compact header + preset strip ---
    header = tk.Frame(outer, bg="#0a1628", highlightthickness=1, highlightbackground="#1e3a5f")
    header.pack(fill=tk.X)
    htop = tk.Frame(header, bg="#0a1628")
    htop.pack(fill=tk.X, padx=10, pady=(8, 4))
    tk.Label(
        htop,
        text="Video Converter",
        bg="#0a1628",
        fg="#f8fafc",
        font=("Segoe UI", 12, "bold"),
    ).pack(side=tk.LEFT)
    tk.Label(
        htop,
        text="  ·  I/O → encode → start",
        bg="#0a1628",
        fg="#64748b",
        font=("Segoe UI", 9),
    ).pack(side=tk.LEFT)

    preset_row = tk.Frame(header, bg="#0a1628")
    preset_row.pack(fill=tk.X, padx=10, pady=(0, 8))
    tk.Label(
        preset_row,
        text="Quick:",
        bg="#0a1628",
        fg="#94a3b8",
        font=("Segoe UI", 8, "bold"),
    ).pack(side=tk.LEFT, padx=(0, 6))
    chip = _btn_sm(padx=10, pady=4)
    for label, key, bg_c, fg_c in [
        ("Match source", "match", "#334155", "#f1f5f9"),
        ("1080p H.264", "1080p", "#0369a1", "#f0f9ff"),
        ("720p Web", "720p", "#0f766e", "#ccfbf1"),
        ("HEVC / MKV", "hevc", "#6d28d9", "#f5f3ff"),
        ("WhatsApp ~170MB", "whatsapp170", "#128c7e", "#ecfdf5"),
    ]:
        tk.Button(
            preset_row,
            text=label,
            bg=bg_c,
            fg=fg_c,
            activebackground=bg_c,
            activeforeground=fg_c,
            command=lambda k=key: _apply_conv_preset(app, k),
            **chip,
        ).pack(side=tk.LEFT, padx=2)

    # --- Bottom dock (packed first so it stays pinned) ---
    dock = tk.Frame(outer, bg="#050a12", highlightthickness=1, highlightbackground="#1e293b")
    dock.pack(side=tk.BOTTOM, fill=tk.X)

    app.conv_preview_label = tk.Label(
        dock,
        text="Preview: first frame in the player (no autoplay). Load input or Use main file.",
        bg="#050a12",
        fg="#64748b",
        font=("Segoe UI", 8),
        wraplength=720,
        justify=tk.LEFT,
    )
    app.conv_preview_label.pack(anchor="w", padx=10, pady=(6, 2))

    pline = tk.Frame(dock, bg="#050a12", padx=10)
    pline.pack(fill=tk.X)
    tk.Label(pline, text="Player", bg="#050a12", fg="#94a3b8", font=("Segoe UI", 8, "bold")).pack(
        side=tk.LEFT, padx=(0, 6)
    )
    pb = _btn(padx=10, pady=3)
    tk.Button(
        pline,
        text="Play",
        bg="#1e3a5f",
        fg="#e2e8f0",
        activebackground="#2563eb",
        command=app._conv_player_play,
        **pb,
    ).pack(side=tk.LEFT, padx=1)
    tk.Button(
        pline,
        text="Pause",
        bg="#1e3a5f",
        fg="#e2e8f0",
        command=app._conv_player_pause,
        **pb,
    ).pack(side=tk.LEFT, padx=1)
    tk.Button(
        pline,
        text="Stop",
        bg="#1e3a5f",
        fg="#e2e8f0",
        command=app._conv_player_stop,
        **pb,
    ).pack(side=tk.LEFT, padx=1)
    tk.Label(
        pline,
        text="Space · play/pause",
        bg="#050a12",
        fg="#475569",
        font=("Segoe UI", 8),
    ).pack(side=tk.LEFT, padx=(10, 0))

    # --- Encode progress (premium dock card) ---
    # ConvDock.Horizontal.TProgressbar üslubu pv_main._styles() içində qeydiyyatdan keçirilir
    # (ikinci ttk.Style() bəzi sistemlərdə Tcl xətası verirdi → proqram açılmırdı).
    _pb_style_name = "ConvDock.Horizontal.TProgressbar"

    prog = tk.Frame(dock, bg="#0b1220", padx=12, pady=8)
    prog.pack(fill=tk.X, pady=(2, 0))
    tk.Frame(prog, bg="#334155", height=1).pack(fill=tk.X, pady=(0, 8))

    prow = tk.Frame(prog, bg="#0b1220")
    prow.pack(fill=tk.X)
    app.conv_prog_state = tk.Label(
        prow,
        text="READY",
        bg="#0b1220",
        fg="#64748b",
        font=("Segoe UI", 7, "bold"),
    )
    app.conv_prog_state.pack(side=tk.LEFT)
    app.conv_prog_pct_lbl = tk.Label(
        prow,
        text="0%",
        bg="#0b1220",
        fg="#e2e8f0",
        font=("Segoe UI", 22, "bold"),
    )
    app.conv_prog_pct_lbl.pack(side=tk.RIGHT)

    app.conv_pv = tk.DoubleVar(value=0.0)
    try:
        ttk.Progressbar(
            prog,
            variable=app.conv_pv,
            maximum=100,
            mode="determinate",
            style=_pb_style_name,
        ).pack(fill=tk.X, pady=(6, 6))
    except tk.TclError:
        ttk.Progressbar(
            prog,
            variable=app.conv_pv,
            maximum=100,
            mode="determinate",
            style="C.Horizontal.TProgressbar",
        ).pack(fill=tk.X, pady=(6, 6))

    app.conv_prog_metrics = tk.Label(
        prog,
        text="—",
        bg="#0b1220",
        fg="#94a3b8",
        font=("Segoe UI", 9),
        justify=tk.LEFT,
        wraplength=780,
        anchor="w",
    )
    app.conv_prog_metrics.pack(fill=tk.X, anchor="w")
    app.conv_prog_paths = tk.Label(
        prog,
        text="",
        bg="#0b1220",
        fg="#475569",
        font=("Segoe UI", 8),
        justify=tk.LEFT,
        wraplength=780,
        anchor="w",
    )
    app.conv_prog_paths.pack(fill=tk.X, anchor="w", pady=(2, 0))

    app.conv_status = tk.Label(
        prog,
        text="Ready",
        bg="#0b1220",
        fg="#64748b",
        font=("Segoe UI", 8),
        anchor="w",
    )
    app.conv_status.pack(fill=tk.X, anchor="w", pady=(2, 0))

    actions = tk.Frame(dock, bg="#0f172a", padx=6, pady=6)
    actions.pack(fill=tk.X)
    bc_pri = _btn(padx=14, pady=6)
    bc_dan = _btn(padx=12, pady=6)
    bc_sec = _btn_sm()

    row_a = tk.Frame(actions, bg="#0f172a")
    row_a.pack(fill=tk.X)
    tk.Button(
        row_a,
        text="Start",
        bg="#0284c7",
        fg="#ffffff",
        activebackground="#0369a1",
        command=app._conv_start,
        **bc_pri,
    ).pack(side=tk.LEFT, padx=2)
    tk.Button(
        row_a,
        text="Stop",
        bg="#b91c1c",
        fg="#fecaca",
        activebackground="#991b1b",
        command=app._stop_convert,
        **bc_dan,
    ).pack(side=tk.LEFT, padx=2)
    app.conv_pause_btn = tk.Button(
        row_a,
        text="Pause",
        bg="#475569",
        fg="#f1f5f9",
        command=app._conv_pause_encoding,
        state=tk.DISABLED,
        **bc_dan,
    )
    app.conv_pause_btn.pack(side=tk.LEFT, padx=2)
    app.conv_resume_btn = tk.Button(
        row_a,
        text="Resume",
        bg="#15803d",
        fg="#dcfce7",
        command=app._conv_resume_encoding,
        state=tk.DISABLED,
        **bc_dan,
    )
    app.conv_resume_btn.pack(side=tk.LEFT, padx=2)
    tk.Button(
        row_a,
        text="FFplay",
        bg="#4338ca",
        fg="#e0e7ff",
        command=app._conv_preview_ffplay,
        **bc_dan,
    ).pack(side=tk.LEFT, padx=(8, 2))

    row_b = tk.Frame(actions, bg="#0f172a")
    row_b.pack(fill=tk.X, pady=(6, 0))
    tk.Button(
        row_b,
        text="Main file",
        bg="#1e293b",
        fg="#cbd5e1",
        command=app._conv_use_main_file,
        **bc_sec,
    ).pack(side=tk.LEFT, padx=2)
    tk.Button(
        row_b,
        text="Export JSON",
        bg="#1e293b",
        fg="#94a3b8",
        command=app._conv_export_json,
        **bc_sec,
    ).pack(side=tk.LEFT, padx=2)
    tk.Button(
        row_b,
        text="Save log",
        bg="#1e293b",
        fg="#94a3b8",
        command=app._conv_export_log,
        **bc_sec,
    ).pack(side=tk.LEFT, padx=2)

    # --- Notebook: üslub pv_main._styles() ilə qeydiyyatdan keçirilir (ikinci Style() yox)
    try:
        nb = ttk.Notebook(outer, style="Conv.TNotebook")
    except tk.TclError:
        nb = ttk.Notebook(outer)
    nb.pack(fill=tk.BOTH, expand=True, padx=6, pady=(4, 0))

    bc_row = dict(font=("Segoe UI", 8, "bold"), relief=tk.FLAT, cursor="hand2", padx=6, pady=3, bd=0)

    # Tab: I/O
    tab_q = tk.Frame(nb, bg=BG)
    nb.add(tab_q, text=" I/O ")
    q_inner = _scroll_area(tab_q, BG)
    _hint(q_inner, BG, "Paths and naming. Pick input — output updates from the filename template.")

    fio = tk.Frame(q_inner, bg=BG2, padx=8, pady=6)
    fio.pack(fill=tk.X, pady=(0, 4))
    _section_label(fio, "Input / output", BG2, AC)
    app.conv_input_var = tk.StringVar()
    app.conv_output_var = tk.StringVar()
    for lab, var, cmd in [
        ("Input", app.conv_input_var, "_conv_browse_input"),
        ("Output", app.conv_output_var, "_conv_browse_output"),
    ]:
        r = tk.Frame(fio, bg=BG2)
        r.pack(fill=tk.X, pady=2)
        tk.Label(r, text=lab, bg=BG2, fg=FG, width=8, anchor="w", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        tk.Entry(r, textvariable=var, bg="#0e1e30", fg=FG, insertbackground=AC, font=("Segoe UI", 9)).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=4
        )
        tk.Button(r, text="…", bg="#0369a1", fg="#fff", command=getattr(app, cmd), width=2, **bc_row).pack(
            side=tk.RIGHT
        )

    # Output directory: empty = same folder as input (see pv_main _conv_make_output_path)
    app.conv_out_dir = tk.StringVar(value="")
    app.conv_acodec = tk.StringVar(value="aac")
    app.conv_abitrate = tk.StringVar(value="192k")

    app.conv_pattern = tk.StringVar(value="{name}_{res}_{fps}_{codec}_{date}_{time}")
    pf = tk.Frame(q_inner, bg=BG)
    pf.pack(fill=tk.X, pady=2)
    tk.Label(pf, text="Filename template", bg=BG, fg=FG2, font=("Segoe UI", 8)).pack(anchor="w")
    tk.Entry(pf, textvariable=app.conv_pattern, bg="#0e1e30", fg=FG, insertbackground=AC, font=("Segoe UI", 9)).pack(
        fill=tk.X, pady=(2, 0)
    )

    row_od = tk.Frame(q_inner, bg=BG)
    row_od.pack(fill=tk.X, pady=(4, 2))
    tk.Label(row_od, text="Output folder", bg=BG, fg=FG2, font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(0, 6))
    tk.Entry(row_od, textvariable=app.conv_out_dir, bg="#0e1e30", fg=FG, insertbackground=AC).pack(
        side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6)
    )
    tk.Button(row_od, text="…", bg="#0369a1", fg="#fff", command=app._conv_browse_out_dir, **bc_row).pack(side=tk.LEFT)

    # Tab: Video (video-only; audio codec / bitrate → Audio tab)
    tab_v = tk.Frame(nb, bg=BG)
    nb.add(tab_v, text=" Video ")
    v_inner = _scroll_area(tab_v, BG)
    _hint(v_inner, BG, "Video: mux, codec, quality, size, FPS. Audio settings are on the Audio tab.")

    sf = tk.Frame(v_inner, bg=BG3, padx=8, pady=8)
    sf.pack(fill=tk.X, pady=(0, 4))

    app.conv_container = tk.StringVar(value="mp4")
    app.conv_vcodec = tk.StringVar(value="libx264")
    app.hw_encoder = tk.StringVar(value="Software (default)")

    _chip_section(
        sf,
        BG3,
        app,
        "conv_container",
        "Container",
        [
            ("MP4", "mp4"),
            ("MKV", "mkv"),
            ("MOV", "mov"),
            ("AVI", "avi"),
            ("FLV", "flv"),
            ("WMV", "wmv"),
            ("WebM", "webm"),
            ("MPEG", "mpeg"),
            ("MPG", "mpg"),
        ],
    )
    _chip_section(
        sf,
        BG3,
        app,
        "conv_vcodec",
        "Video codec",
        [
            ("H.264", "libx264"),
            ("H.265", "libx265"),
            ("VP8", "libvpx"),
            ("VP9", "libvpx-vp9"),
            ("ProRes", "prores_ks"),
            ("MPEG-2", "mpeg2video"),
        ],
    )
    _chip_section(
        sf,
        BG3,
        app,
        "hw_encoder",
        "Hardware encoder",
        [
            ("Software", "Software (default)"),
            ("QSV H.264", "Intel QSV H.264"),
            ("QSV HEVC", "Intel QSV HEVC"),
        ],
    )

    app.conv_preset = tk.StringVar(value="veryfast")
    app.conv_crf = tk.StringVar(value="23")
    app.conv_vbitrate = tk.StringVar(value="Auto")

    _chip_section(
        sf,
        BG3,
        app,
        "conv_preset",
        "Encoding preset",
        [
            ("ultrafast", "ultrafast"),
            ("superfast", "superfast"),
            ("veryfast", "veryfast"),
            ("fast", "fast"),
            ("medium", "medium"),
            ("slow", "slow"),
        ],
    )

    crf_box = tk.Frame(sf, bg=BG3)
    crf_box.pack(fill=tk.X, pady=(0, 6))
    tk.Label(crf_box, text="CRF (quality)", bg=BG3, fg="#94a3b8", font=("Segoe UI", 8, "bold")).pack(
        anchor="w", pady=(0, 4)
    )
    crf_row = tk.Frame(crf_box, bg=BG3)
    crf_btns = []

    def _crf_sync(_a=None, _b=None, _c=None):
        try:
            cur = app.conv_crf.get().strip()
        except Exception:
            return
        for (lbl, val), b in zip(
            [("18", "18"), ("20", "20"), ("23", "23"), ("26", "26"), ("28", "28")],
            crf_btns,
        ):
            _chip_style(b, cur == val)

    def _crf_pick(val):
        app.conv_crf.set(val)
        _crf_sync()

    for lbl, val in [("18", "18"), ("20", "20"), ("23", "23"), ("26", "26"), ("28", "28")]:
        b = tk.Button(
            crf_row,
            text=lbl,
            font=_CHIP_FONT,
            relief=tk.FLAT,
            cursor="hand2",
            bd=0,
            padx=8,
            pady=5,
            command=lambda v=val: _crf_pick(v),
        )
        b.pack(side=tk.LEFT, padx=2, pady=2)
        crf_btns.append(b)
    _crf_sync()
    try:
        app.conv_crf.trace_add("write", _crf_sync)
    except Exception:
        pass
    tk.Label(crf_row, text="Custom", bg=BG3, fg=FG2, font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(10, 4))
    tk.Entry(crf_row, textvariable=app.conv_crf, width=5, bg="#0e1e30", fg=FG, insertbackground=AC).pack(
        side=tk.LEFT, padx=2
    )
    crf_row.pack(fill=tk.X, anchor="w")

    _chip_section(
        sf,
        BG3,
        app,
        "conv_vbitrate",
        "Video bitrate",
        [
            ("Auto", "Auto"),
            ("WA ~170MB", "__TARGET_MB_170__"),
            ("1M", "1M"),
            ("2M", "2M"),
            ("4M", "4M"),
            ("8M", "8M"),
            ("15M", "15M"),
            ("25M", "25M"),
            ("40M", "40M"),
        ],
    )

    app.conv_res = tk.StringVar(value="Original")
    app.conv_custom_w = tk.StringVar()
    app.conv_custom_h = tk.StringVar()
    app.conv_scale_method = tk.StringVar(value="Bilinear")
    app.conv_scan = tk.StringVar(value="Progressive (p)")
    app.conv_fps = tk.StringVar(value="Original")
    app.conv_custom_fps = tk.StringVar()
    app.conv_fps_mode = tk.StringVar(value="Default")
    app.conv_frame_interpolate = tk.BooleanVar(value=False)

    _chip_section(
        sf,
        BG3,
        app,
        "conv_res",
        "Resolution",
        [
            ("Original", "Original"),
            ("8K", "7680x4320"),
            ("4K", "3840x2160"),
            ("1440p", "2560x1440"),
            ("1080p", "1920x1080"),
            ("720p", "1280x720"),
            ("480p", "854x480"),
            ("360p", "640x360"),
            ("Custom", "Custom"),
        ],
    )
    wh_row = tk.Frame(sf, bg=BG3)
    wh_row.pack(fill=tk.X, pady=(0, 8))
    tk.Label(wh_row, text="Custom W × H", bg=BG3, fg=FG2, font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(0, 8))
    tk.Entry(wh_row, textvariable=app.conv_custom_w, width=6, bg="#0e1e30", fg=FG, insertbackground=AC).pack(
        side=tk.LEFT, padx=2
    )
    tk.Label(wh_row, text="×", bg=BG3, fg=FG2).pack(side=tk.LEFT)
    tk.Entry(wh_row, textvariable=app.conv_custom_h, width=6, bg="#0e1e30", fg=FG, insertbackground=AC).pack(
        side=tk.LEFT, padx=2
    )

    _chip_section(
        sf,
        BG3,
        app,
        "conv_scale_method",
        "Scale filter",
        [("Bilinear", "Bilinear"), ("Bicubic", "Bicubic"), ("Lanczos", "Lanczos")],
    )
    _chip_section(
        sf,
        BG3,
        app,
        "conv_scan",
        "Scan type",
        [("Progressive", "Progressive (p)"), ("Interlaced", "Interlaced (i)")],
    )
    _chip_section(
        sf,
        BG3,
        app,
        "conv_fps",
        "FPS",
        [
            ("Original", "Original"),
            ("24", "24"),
            ("25", "25"),
            ("30", "30"),
            ("50", "50"),
            ("60", "60"),
            ("120", "120"),
            ("Custom", "Custom"),
        ],
    )
    fps_row = tk.Frame(sf, bg=BG3)
    fps_row.pack(fill=tk.X, pady=(0, 6))
    tk.Label(fps_row, text="Custom FPS", bg=BG3, fg=FG2, font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(0, 8))
    tk.Entry(fps_row, textvariable=app.conv_custom_fps, width=8, bg="#0e1e30", fg=FG, insertbackground=AC).pack(
        side=tk.LEFT, padx=2
    )

    _chip_section(
        sf,
        BG3,
        app,
        "conv_fps_mode",
        "FPS mode",
        [
            ("Default", "Default"),
            ("Drop", "Drop (vsync)"),
            ("CFR dup", "Duplicate / CFR"),
        ],
    )
    _bool_chip_section(sf, BG3, app, "conv_frame_interpolate", "Frame interpolate (minterpolate)", on_label="ON", off_label="OFF")

    # Tab: Audio
    tab_a = tk.Frame(nb, bg=BG)
    nb.add(tab_a, text=" Audio ")
    a_inner = _scroll_area(tab_a, BG)
    _hint(a_inner, BG, "Audio codec, bitrate, channels, sample rate, volume — separate from video.")

    af = tk.Frame(a_inner, bg=BG3, padx=10, pady=8)
    af.pack(fill=tk.X)

    app.conv_vol = tk.DoubleVar(value=100.0)
    app.conv_mute = tk.BooleanVar(value=False)
    app.conv_normalize = tk.BooleanVar(value=False)
    app.conv_ach = tk.StringVar(value="stereo")
    app.conv_sr = tk.StringVar(value="Original")
    app.conv_bitdepth = tk.StringVar(value="16-bit")

    _chip_section(
        af,
        BG3,
        app,
        "conv_acodec",
        "Audio codec",
        [
            ("AAC", "aac"),
            ("MP3", "mp3"),
            ("Opus", "libopus"),
            ("PCM 16", "pcm_s16le"),
            ("PCM 24", "pcm_s24le"),
            ("AC3", "ac3"),
        ],
    )
    _chip_section(
        af,
        BG3,
        app,
        "conv_abitrate",
        "Audio bitrate",
        [
            ("Auto", "Auto"),
            ("96k", "96k"),
            ("128k", "128k"),
            ("192k", "192k"),
            ("256k", "256k"),
            ("320k", "320k"),
        ],
    )

    tk.Label(af, text="Volume %", bg=BG3, fg="#94a3b8", font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(4, 4))
    vol_row = tk.Frame(af, bg=BG3)
    vol_row.pack(fill=tk.X, pady=(0, 4))

    def _vol_set(pct):
        app.conv_vol.set(float(pct))

    for lab, pct in [("0%", 0), ("50%", 50), ("100%", 100)]:
        tk.Button(
            vol_row,
            text=lab,
            font=_CHIP_FONT,
            relief=tk.FLAT,
            cursor="hand2",
            bd=0,
            padx=10,
            pady=4,
            bg=_CHIP_OFF,
            fg=_CHIP_FG_OFF,
            command=lambda p=pct: _vol_set(p),
        ).pack(side=tk.LEFT, padx=2)
    tk.Scale(
        af,
        variable=app.conv_vol,
        from_=0,
        to=100,
        orient=tk.HORIZONTAL,
        length=280,
        bg=BG3,
        fg=FG,
        highlightthickness=0,
    ).pack(anchor="w", pady=(0, 6))

    row_mu = tk.Frame(af, bg=BG3)
    row_mu.pack(fill=tk.X, pady=(0, 4))
    left_mu = tk.Frame(row_mu, bg=BG3)
    left_mu.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    right_mu = tk.Frame(row_mu, bg=BG3)
    right_mu.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    _bool_chip_section(left_mu, BG3, app, "conv_mute", "Mute", on_label="Muted", off_label="Unmuted")
    _bool_chip_section(right_mu, BG3, app, "conv_normalize", "Loudnorm (EBU R128)", on_label="ON", off_label="OFF")

    _chip_section(
        af,
        BG3,
        app,
        "conv_ach",
        "Channels",
        [("Stereo", "stereo"), ("Mono", "mono"), ("5.1", "5.1")],
    )
    _chip_section(
        af,
        BG3,
        app,
        "conv_sr",
        "Sample rate",
        [("Original", "Original"), ("44100", "44100"), ("48000", "48000"), ("96000", "96000")],
    )
    _chip_section(
        af,
        BG3,
        app,
        "conv_bitdepth",
        "PCM bit depth",
        [("16-bit", "16-bit"), ("24-bit", "24-bit")],
    )

    # Tab: Overlay
    tab_o = tk.Frame(nb, bg=BG)
    nb.add(tab_o, text=" Overlay ")
    o_inner = _scroll_area(tab_o, BG)
    of = tk.Frame(o_inner, bg=BG2, padx=8, pady=8)
    of.pack(fill=tk.X)
    _section_label(of, "Burn-in text / image", BG2, AC)
    _hint(of, BG2, "Empty = off. Forces re-encode.", wrap=480)

    app.conv_ol_text = tk.StringVar()
    app.conv_ol_font = tk.StringVar(value="Arial")
    app.conv_ol_tsize = tk.StringVar(value="24")
    app.conv_ol_color = tk.StringVar(value="#FFFFFF")
    app.conv_ol_opa = tk.StringVar(value="80")
    app.conv_ol_x = tk.StringVar(value="10")
    app.conv_ol_y = tk.StringVar(value="10")
    app.conv_ol_anim = tk.StringVar(value="None")
    r = tk.Frame(of, bg=BG2)
    r.pack(fill=tk.X, pady=2)
    tk.Label(r, text="Text", bg=BG2, fg=FG, font=("Segoe UI", 8)).pack(side=tk.LEFT)
    tk.Entry(r, textvariable=app.conv_ol_text, bg="#0e1e30", fg=FG, width=32).pack(side=tk.LEFT, padx=4)
    tk.Label(r, text="Font", bg=BG2, fg=FG2, font=("Segoe UI", 8)).pack(side=tk.LEFT)
    ttk.Combobox(r, textvariable=app.conv_ol_font, values=["Arial", "Segoe UI", "Consolas", "Times"], width=9).pack(
        side=tk.LEFT, padx=2
    )
    tk.Label(r, text="Sz", bg=BG2, fg=FG2, font=("Segoe UI", 8)).pack(side=tk.LEFT)
    tk.Entry(r, textvariable=app.conv_ol_tsize, width=3).pack(side=tk.LEFT)
    tk.Label(r, text="#", bg=BG2, fg=FG2, font=("Segoe UI", 8)).pack(side=tk.LEFT)
    tk.Entry(r, textvariable=app.conv_ol_color, width=7).pack(side=tk.LEFT, padx=2)
    tk.Label(r, text="%", bg=BG2, fg=FG2, font=("Segoe UI", 8)).pack(side=tk.LEFT)
    tk.Entry(r, textvariable=app.conv_ol_opa, width=3).pack(side=tk.LEFT)

    r2 = tk.Frame(of, bg=BG2)
    r2.pack(fill=tk.X, pady=2)
    tk.Label(r2, text="x/y", bg=BG2, fg=FG2, font=("Segoe UI", 8)).pack(side=tk.LEFT)
    tk.Entry(r2, textvariable=app.conv_ol_x, width=5).pack(side=tk.LEFT)
    tk.Entry(r2, textvariable=app.conv_ol_y, width=5).pack(side=tk.LEFT, padx=2)
    tk.Label(r2, text="Anim", bg=BG2, fg=FG2, font=("Segoe UI", 8)).pack(side=tk.LEFT)
    ttk.Combobox(r2, textvariable=app.conv_ol_anim, values=["None", "Fade in", "Scroll"], width=9).pack(
        side=tk.LEFT, padx=2
    )

    app.conv_ol_img = tk.StringVar()
    app.conv_ol_ix = tk.StringVar(value="10")
    app.conv_ol_iy = tk.StringVar(value="10")
    app.conv_ol_iw = tk.StringVar(value="-1")
    app.conv_ol_ih = tk.StringVar(value="-1")
    r3 = tk.Frame(of, bg=BG2)
    r3.pack(fill=tk.X, pady=4)
    tk.Label(r3, text="Image", bg=BG2, fg=FG2, font=("Segoe UI", 8)).pack(side=tk.LEFT)
    tk.Entry(r3, textvariable=app.conv_ol_img, bg="#0e1e30", fg=FG, width=42).pack(side=tk.LEFT, padx=4)
    tk.Button(r3, text="…", bg="#0369a1", fg="#fff", command=app._conv_browse_ol_img, **bc_row).pack(side=tk.LEFT)

    r4 = tk.Frame(of, bg=BG2)
    r4.pack(fill=tk.X)
    tk.Label(r4, text="x y w h", bg=BG2, fg=FG2, font=("Segoe UI", 8)).pack(side=tk.LEFT)
    for v in (app.conv_ol_ix, app.conv_ol_iy, app.conv_ol_iw, app.conv_ol_ih):
        tk.Entry(r4, textvariable=v, width=5).pack(side=tk.LEFT, padx=2)

    app.conv_ol_t0 = tk.StringVar(value="0")
    app.conv_ol_t1 = tk.StringVar(value="999999")
    r5 = tk.Frame(of, bg=BG2)
    r5.pack(fill=tk.X, pady=4)
    tk.Label(r5, text="Visible t0–t1 (s)", bg=BG2, fg=FG2, font=("Segoe UI", 8)).pack(side=tk.LEFT)
    tk.Entry(r5, textvariable=app.conv_ol_t0, width=8).pack(side=tk.LEFT, padx=4)
    tk.Entry(r5, textvariable=app.conv_ol_t1, width=8).pack(side=tk.LEFT, padx=4)

    # Tab: Advanced
    tab_x = tk.Frame(nb, bg=BG)
    nb.add(tab_x, text=" Adv ")
    x_inner = _scroll_area(tab_x, BG)
    _hint(x_inner, BG, "HW decode, threads, extra FFmpeg args, temp dir, collision policy.")
    af2 = tk.Frame(x_inner, bg=BG3, padx=8, pady=8)
    af2.pack(fill=tk.X)

    app.conv_hwaccel = tk.StringVar(value="none")
    app.conv_threads = tk.StringVar(value="0")
    app.conv_extra = tk.StringVar()
    app.conv_temp = tk.StringVar(value="")
    app.conv_auto_clean = tk.BooleanVar(value=True)
    app.conv_overwrite = tk.StringVar(value="rename")
    app.conv_retry = tk.BooleanVar(value=False)

    rx = tk.Frame(af2, bg=BG3)
    rx.pack(fill=tk.X, pady=2)
    tk.Label(rx, text="HW dec", bg=BG3, fg=FG2, font=("Segoe UI", 8)).pack(side=tk.LEFT)
    ttk.Combobox(rx, textvariable=app.conv_hwaccel, values=["none", "qsv"], width=7, state="readonly").pack(
        side=tk.LEFT, padx=2
    )
    tk.Label(rx, text="Thr", bg=BG3, fg=FG2, font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(6, 0))
    tk.Entry(rx, textvariable=app.conv_threads, width=4).pack(side=tk.LEFT)
    tk.Label(rx, text="Exists", bg=BG3, fg=FG2, font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(8, 0))
    ttk.Combobox(rx, textvariable=app.conv_overwrite, values=["rename", "ask"], width=7, state="readonly").pack(
        side=tk.LEFT, padx=2
    )
    tk.Checkbutton(
        rx,
        text="Retry",
        variable=app.conv_retry,
        bg=BG3,
        fg=FG,
        selectcolor="#0a1420",
        activebackground=BG3,
        font=("Segoe UI", 8),
    ).pack(side=tk.LEFT, padx=6)
    tk.Checkbutton(
        rx,
        text="Clean temp",
        variable=app.conv_auto_clean,
        bg=BG3,
        fg=FG,
        selectcolor="#0a1420",
        activebackground=BG3,
        font=("Segoe UI", 8),
    ).pack(side=tk.LEFT, padx=4)

    tk.Label(af2, text="Extra FFmpeg args", bg=BG3, fg=FG2, font=("Segoe UI", 8)).pack(anchor="w", pady=(6, 2))
    tk.Entry(af2, textvariable=app.conv_extra, bg="#0e1e30", fg=FG, font=("Consolas", 8)).pack(fill=tk.X, pady=2)
    tk.Label(af2, text="Temp dir (empty = default)", bg=BG3, fg=FG2, font=("Segoe UI", 8)).pack(anchor="w", pady=(4, 2))
    tk.Entry(af2, textvariable=app.conv_temp, bg="#0e1e30", fg=FG).pack(fill=tk.X)

    # Tab: Log
    tab_l = tk.Frame(nb, bg=BG)
    nb.add(tab_l, text=" Log ")
    tk.Label(
        tab_l,
        text="FFmpeg command lines and errors — save when reporting issues.",
        bg=BG,
        fg=FG2,
        font=("Segoe UI", 8),
        wraplength=560,
        justify=tk.LEFT,
    ).pack(anchor="w", padx=8, pady=(6, 0))
    app.conv_log = scrolledtext.ScrolledText(
        tab_l, bg="#04080f", fg=FG2, font=("Consolas", 8), height=12, wrap=tk.WORD, insertbackground=AC
    )
    app.conv_log.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
