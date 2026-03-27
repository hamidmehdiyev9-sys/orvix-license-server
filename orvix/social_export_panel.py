"""
Social export — dəyişənlər və UI (tək platform pəncərəsində istifadə üçün).
"""
import tkinter as tk
from tkinter import ttk


def ensure_social_export_vars(app):
    """sn_* dəyişənlərini bir dəfə yaradır (UI olmadan)."""
    if not hasattr(app, "sn_input_var"):
        app.sn_input_var = tk.StringVar()
    if not hasattr(app, "sn_output_var"):
        app.sn_output_var = tk.StringVar()
    if not hasattr(app, "sn_start_var"):
        app.sn_start_var = tk.StringVar(value="00:00:00")
    if not hasattr(app, "sn_end_var"):
        app.sn_end_var = tk.StringVar(value="")
    if not hasattr(app, "sn_max_duration_var"):
        app.sn_max_duration_var = tk.StringVar(value="90")
    if not hasattr(app, "sn_fill_mode_var"):
        app.sn_fill_mode_var = tk.StringVar(value="Blur Fill")
    if not hasattr(app, "sn_y_shift"):
        app.sn_y_shift = tk.IntVar(value=0)
    if not hasattr(app, "sn_x_shift"):
        app.sn_x_shift = tk.IntVar(value=0)
    if not hasattr(app, "sn_video_zoom_var"):
        app.sn_video_zoom_var = tk.StringVar(value="1.00")
    if not hasattr(app, "sn_bg_img_var"):
        app.sn_bg_img_var = tk.StringVar(value="")
    if not hasattr(app, "sn_preset_var"):
        app.sn_preset_var = tk.StringVar(value="Custom")
    if not hasattr(app, "sn_text_var"):
        app.sn_text_var = tk.StringVar(value="")
    if not hasattr(app, "sn_text_color_var"):
        app.sn_text_color_var = tk.StringVar(value="white")
    if not hasattr(app, "sn_text_size_var"):
        app.sn_text_size_var = tk.StringVar(value="46")
    if not hasattr(app, "sn_text_x_var"):
        app.sn_text_x_var = tk.StringVar(value="(w-text_w)/2")
    if not hasattr(app, "sn_text_y_var"):
        app.sn_text_y_var = tk.StringVar(value="h*0.82")
    if not hasattr(app, "sn_text_start_var"):
        app.sn_text_start_var = tk.StringVar(value="0")
    if not hasattr(app, "sn_text_end_var"):
        app.sn_text_end_var = tk.StringVar(value="")
    if not hasattr(app, "sn_overlay_img_var"):
        app.sn_overlay_img_var = tk.StringVar(value="")
    if not hasattr(app, "sn_overlay_scale_var"):
        app.sn_overlay_scale_var = tk.StringVar(value="1.0")
    if not hasattr(app, "sn_overlay_opacity_var"):
        app.sn_overlay_opacity_var = tk.StringVar(value="1.0")
    if not hasattr(app, "sn_overlay_x_var"):
        app.sn_overlay_x_var = tk.StringVar(value="W-w-36")
    if not hasattr(app, "sn_overlay_y_var"):
        app.sn_overlay_y_var = tk.StringVar(value="H-h-36")
    if not hasattr(app, "sn_overlay_start_var"):
        app.sn_overlay_start_var = tk.StringVar(value="0")
    if not hasattr(app, "sn_overlay_end_var"):
        app.sn_overlay_end_var = tk.StringVar(value="")
    if not hasattr(app, "sn_overlay2_img_var"):
        app.sn_overlay2_img_var = tk.StringVar(value="")
    if not hasattr(app, "sn_overlay2_scale_var"):
        app.sn_overlay2_scale_var = tk.StringVar(value="1.0")
    if not hasattr(app, "sn_overlay2_opacity_var"):
        app.sn_overlay2_opacity_var = tk.StringVar(value="1.0")
    if not hasattr(app, "sn_overlay2_x_var"):
        app.sn_overlay2_x_var = tk.StringVar(value="W-w-120")
    if not hasattr(app, "sn_overlay2_y_var"):
        app.sn_overlay2_y_var = tk.StringVar(value="H-h-120")
    if not hasattr(app, "sn_volume_var"):
        app.sn_volume_var = tk.DoubleVar(value=1.0)
    if not hasattr(app, "sn_fade_in_var"):
        app.sn_fade_in_var = tk.StringVar(value="0")
    if not hasattr(app, "sn_fade_out_var"):
        app.sn_fade_out_var = tk.StringVar(value="0")
    if not hasattr(app, "sn_preview_len_var"):
        app.sn_preview_len_var = tk.StringVar(value="8")
    if not hasattr(app, "sn_auto_preview_var"):
        app.sn_auto_preview_var = tk.BooleanVar(value=True)
    if not hasattr(app, "instagram_ws_status_var"):
        app.instagram_ws_status_var = tk.StringVar(value="Ready")
    if not hasattr(app, "sn_pv"):
        app.sn_pv = tk.DoubleVar(value=0.0)
    if not hasattr(app, "instagram_progress_detail_var"):
        app.instagram_progress_detail_var = tk.StringVar(value="")
    if not hasattr(app, "insta_layer_bg_var"):
        app.insta_layer_bg_var = tk.StringVar(value="")
    if not hasattr(app, "insta_layer_top_var"):
        app.insta_layer_top_var = tk.StringVar(value="")
    if not hasattr(app, "insta_layer_bottom_var"):
        app.insta_layer_bottom_var = tk.StringVar(value="")
    if not hasattr(app, "insta_layer_center_var"):
        app.insta_layer_center_var = tk.StringVar(value="")
    if not hasattr(app, "insta_layer_layout_json_var"):
        app.insta_layer_layout_json_var = tk.StringVar(value="")
    if not hasattr(app, "insta_layer_active_var"):
        app.insta_layer_active_var = tk.StringVar(value="center")
    # Instagram iş pəncərəsi: 3 ardıcıl mənbə yuvası (önizləmə üçün aktiv seçim)
    if not hasattr(app, "insta_video_slot_1_var"):
        app.insta_video_slot_1_var = tk.StringVar(value="")
    if not hasattr(app, "insta_video_slot_2_var"):
        app.insta_video_slot_2_var = tk.StringVar(value="")
    if not hasattr(app, "insta_video_slot_3_var"):
        app.insta_video_slot_3_var = tk.StringVar(value="")
    if not hasattr(app, "insta_active_video_slot_var"):
        app.insta_active_video_slot_var = tk.IntVar(value=1)


def install_social_export_form(app, parent, *, bg3, show_file_rows=True, form_heading=None):
    """Mənbə/çıxış və export parametrləri (kompakt). show_file_rows=False — mənbə/çıxış başqa blokdadır."""
    FG = app.FG
    AC = app.AC
    FG2 = app.FG2

    heading = form_heading or "Fayl və export"
    tk.Label(
        parent,
        text=heading,
        bg=bg3,
        fg="#caa3ff",
        font=("Segoe UI", 10, "bold"),
    ).pack(anchor="w", pady=(0, 4))

    if show_file_rows:
        for label, var_name, browse_cmd in [
            ("Source:", "sn_input_var", "_sn_browse_input"),
            ("Output:", "sn_output_var", "_sn_browse_output"),
        ]:
            row = tk.Frame(parent, bg=bg3)
            row.pack(fill=tk.X, pady=1)
            tk.Label(row, text=label, bg=bg3, fg=FG, font=("Segoe UI", 9, "bold"), width=10, anchor="w").pack(
                side=tk.LEFT
            )
            tk.Entry(
                row,
                textvariable=getattr(app, var_name),
                bg="#0e1e30",
                fg=FG,
                font=("Segoe UI", 9),
                insertbackground=AC,
                relief=tk.FLAT,
                bd=2,
            ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
            tk.Button(
                row,
                text="…",
                bg="#004a7a",
                fg="#fff",
                font=("Segoe UI", 9, "bold"),
                relief=tk.FLAT,
                padx=8,
                pady=2,
                cursor="hand2",
                command=getattr(app, browse_cmd),
            ).pack(side=tk.RIGHT)

    row1 = tk.Frame(parent, bg=bg3)
    row1.pack(fill=tk.X, pady=2)
    tk.Label(row1, text="Start", bg=bg3, fg=FG2, width=8, anchor="w").pack(side=tk.LEFT)
    tk.Entry(row1, textvariable=app.sn_start_var, width=11, bg="#0e1e30", fg=FG, insertbackground=AC, relief=tk.FLAT, bd=2).pack(
        side=tk.LEFT, padx=2
    )
    tk.Label(row1, text="End", bg=bg3, fg=FG2).pack(side=tk.LEFT, padx=(6, 0))
    tk.Entry(row1, textvariable=app.sn_end_var, width=11, bg="#0e1e30", fg=FG, insertbackground=AC, relief=tk.FLAT, bd=2).pack(
        side=tk.LEFT, padx=2
    )
    tk.Label(row1, text="Max(s)", bg=bg3, fg=FG2).pack(side=tk.LEFT, padx=(6, 0))
    ttk.Combobox(
        row1,
        textvariable=app.sn_max_duration_var,
        values=["Auto", "15", "30", "60", "90"],
        state="readonly",
        width=7,
        font=("Segoe UI", 9),
    ).pack(side=tk.LEFT, padx=2)

    row2 = tk.Frame(parent, bg=bg3)
    row2.pack(fill=tk.X, pady=1)
    tk.Label(row2, text="Fill mode", bg=bg3, fg=FG2, width=8, anchor="w").pack(side=tk.LEFT)
    ttk.Combobox(
        row2,
        textvariable=app.sn_fill_mode_var,
        values=["Blur Fill", "Solid Black", "Solid White"],
        state="readonly",
        width=14,
        font=("Segoe UI", 9),
    ).pack(side=tk.LEFT, padx=2)
    tk.Label(row2, text="Y/X", bg=bg3, fg=FG2).pack(side=tk.LEFT, padx=(4, 0))
    tk.Scale(
        row2,
        variable=app.sn_y_shift,
        from_=-700,
        to=700,
        orient=tk.HORIZONTAL,
        length=100,
        bg=bg3,
        fg=FG,
        highlightthickness=0,
        troughcolor="#0e1e30",
    ).pack(side=tk.LEFT)
    tk.Scale(
        row2,
        variable=app.sn_x_shift,
        from_=-700,
        to=700,
        orient=tk.HORIZONTAL,
        length=100,
        bg=bg3,
        fg=FG,
        highlightthickness=0,
        troughcolor="#0e1e30",
    ).pack(side=tk.LEFT, padx=4)
    tk.Label(row2, text="Zoom", bg=bg3, fg=FG2).pack(side=tk.LEFT)
    tk.Entry(row2, textvariable=app.sn_video_zoom_var, width=5, bg="#0e1e30", fg=FG, insertbackground=AC, relief=tk.FLAT, bd=2).pack(
        side=tk.LEFT, padx=2
    )

    bg_row = tk.Frame(parent, bg=bg3)
    bg_row.pack(fill=tk.X, pady=1)
    tk.Label(bg_row, text="Background", bg=bg3, fg=FG2, width=8, anchor="w").pack(side=tk.LEFT)
    tk.Entry(bg_row, textvariable=app.sn_bg_img_var, bg="#0e1e30", fg=FG, insertbackground=AC, relief=tk.FLAT, bd=2).pack(
        side=tk.LEFT, fill=tk.X, expand=True, padx=4
    )
    tk.Button(
        bg_row,
        text="…",
        bg="#004a7a",
        fg="#fff",
        font=("Segoe UI", 9, "bold"),
        relief=tk.FLAT,
        padx=8,
        command=app._sn_browse_background_image,
    ).pack(side=tk.RIGHT)

    row3 = tk.Frame(parent, bg=bg3)
    row3.pack(fill=tk.X, pady=2)
    tk.Label(row3, text="Preset", bg=bg3, fg=FG2, width=8, anchor="w").pack(side=tk.LEFT)
    ttk.Combobox(
        row3,
        textvariable=app.sn_preset_var,
        values=["Custom", "Headline Bottom", "Top CTA", "Watermark Corner"],
        state="readonly",
        width=16,
        font=("Segoe UI", 9),
    ).pack(side=tk.LEFT, padx=2)
    tk.Button(
        row3,
        text="Apply",
        bg="#4b2d7f",
        fg="#f0e8ff",
        font=("Segoe UI", 9, "bold"),
        relief=tk.FLAT,
        padx=6,
        command=app._sn_apply_preset,
    ).pack(side=tk.LEFT, padx=4)
    tk.Label(row3, text="Text", bg=bg3, fg=FG2).pack(side=tk.LEFT, padx=(4, 0))
    tk.Entry(row3, textvariable=app.sn_text_var, bg="#0e1e30", fg=FG, insertbackground=AC, relief=tk.FLAT, bd=2).pack(
        side=tk.LEFT, fill=tk.X, expand=True, padx=4
    )
    ttk.Combobox(
        row3,
        textvariable=app.sn_text_color_var,
        values=["white", "yellow", "black", "red", "cyan", "lime"],
        state="readonly",
        width=7,
        font=("Segoe UI", 9),
    ).pack(side=tk.LEFT, padx=2)
    tk.Entry(row3, textvariable=app.sn_text_size_var, width=4, bg="#0e1e30", fg=FG, insertbackground=AC, relief=tk.FLAT, bd=2).pack(
        side=tk.LEFT
    )

    row4 = tk.Frame(parent, bg=bg3)
    row4.pack(fill=tk.X, pady=1)
    tk.Label(row4, text="Text X/Y", bg=bg3, fg=FG2, width=8, anchor="w").pack(side=tk.LEFT)
    tk.Entry(row4, textvariable=app.sn_text_x_var, width=14, bg="#0e1e30", fg=FG, insertbackground=AC, relief=tk.FLAT, bd=2).pack(
        side=tk.LEFT, padx=2
    )
    tk.Entry(row4, textvariable=app.sn_text_y_var, width=12, bg="#0e1e30", fg=FG, insertbackground=AC, relief=tk.FLAT, bd=2).pack(
        side=tk.LEFT, padx=2
    )
    tk.Label(row4, text="Duration [s]", bg=bg3, fg=FG2).pack(side=tk.LEFT)
    tk.Entry(row4, textvariable=app.sn_text_start_var, width=4, bg="#0e1e30", fg=FG, insertbackground=AC, relief=tk.FLAT, bd=2).pack(
        side=tk.LEFT, padx=2
    )
    tk.Entry(row4, textvariable=app.sn_text_end_var, width=4, bg="#0e1e30", fg=FG, insertbackground=AC, relief=tk.FLAT, bd=2).pack(
        side=tk.LEFT
    )

    row5 = tk.Frame(parent, bg=bg3)
    row5.pack(fill=tk.X, pady=1)
    tk.Label(row5, text="Overlay image", bg=bg3, fg=FG2, width=8, anchor="w").pack(side=tk.LEFT)
    tk.Entry(row5, textvariable=app.sn_overlay_img_var, bg="#0e1e30", fg=FG, insertbackground=AC, relief=tk.FLAT, bd=2).pack(
        side=tk.LEFT, fill=tk.X, expand=True, padx=4
    )
    tk.Button(row5, text="…", bg="#004a7a", fg="#fff", font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=8, command=app._sn_browse_overlay_image).pack(
        side=tk.RIGHT
    )
    tk.Label(row5, text="Size", bg=bg3, fg=FG2).pack(side=tk.LEFT)
    tk.Entry(row5, textvariable=app.sn_overlay_scale_var, width=4, bg="#0e1e30", fg=FG, insertbackground=AC, relief=tk.FLAT, bd=2).pack(
        side=tk.LEFT, padx=2
    )
    tk.Label(row5, text="α", bg=bg3, fg=FG2).pack(side=tk.LEFT)
    tk.Entry(row5, textvariable=app.sn_overlay_opacity_var, width=4, bg="#0e1e30", fg=FG, insertbackground=AC, relief=tk.FLAT, bd=2).pack(
        side=tk.LEFT
    )

    row6 = tk.Frame(parent, bg=bg3)
    row6.pack(fill=tk.X, pady=1)
    tk.Label(row6, text="Ovrl X/Y", bg=bg3, fg=FG2, width=8, anchor="w").pack(side=tk.LEFT)
    tk.Entry(row6, textvariable=app.sn_overlay_x_var, width=12, bg="#0e1e30", fg=FG, insertbackground=AC, relief=tk.FLAT, bd=2).pack(
        side=tk.LEFT, padx=2
    )
    tk.Entry(row6, textvariable=app.sn_overlay_y_var, width=12, bg="#0e1e30", fg=FG, insertbackground=AC, relief=tk.FLAT, bd=2).pack(
        side=tk.LEFT, padx=2
    )
    tk.Entry(row6, textvariable=app.sn_overlay_start_var, width=4, bg="#0e1e30", fg=FG, insertbackground=AC, relief=tk.FLAT, bd=2).pack(
        side=tk.LEFT, padx=2
    )
    tk.Entry(row6, textvariable=app.sn_overlay_end_var, width=4, bg="#0e1e30", fg=FG, insertbackground=AC, relief=tk.FLAT, bd=2).pack(
        side=tk.LEFT
    )

    tk.Label(parent, text="Overlay 2 (video/image)", bg=bg3, fg=FG2, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(4, 0))
    row8 = tk.Frame(parent, bg=bg3)
    row8.pack(fill=tk.X, pady=1)
    tk.Entry(row8, textvariable=app.sn_overlay2_img_var, bg="#0e1e30", fg=FG, insertbackground=AC, relief=tk.FLAT, bd=2).pack(
        side=tk.LEFT, fill=tk.X, expand=True, padx=2
    )
    tk.Button(row8, text="…", bg="#004a7a", fg="#fff", relief=tk.FLAT, padx=8, command=app._sn_browse_overlay2_media).pack(side=tk.RIGHT)
    row9 = tk.Frame(parent, bg=bg3)
    row9.pack(fill=tk.X, pady=1)
    tk.Label(row9, text="Size/α", bg=bg3, fg=FG2).pack(side=tk.LEFT)
    tk.Entry(row9, textvariable=app.sn_overlay2_scale_var, width=5, bg="#0e1e30", fg=FG, insertbackground=AC, relief=tk.FLAT, bd=2).pack(
        side=tk.LEFT, padx=2
    )
    tk.Entry(row9, textvariable=app.sn_overlay2_opacity_var, width=5, bg="#0e1e30", fg=FG, insertbackground=AC, relief=tk.FLAT, bd=2).pack(
        side=tk.LEFT, padx=2
    )
    tk.Entry(row9, textvariable=app.sn_overlay2_x_var, width=10, bg="#0e1e30", fg=FG, insertbackground=AC, relief=tk.FLAT, bd=2).pack(
        side=tk.LEFT, padx=2
    )
    tk.Entry(row9, textvariable=app.sn_overlay2_y_var, width=10, bg="#0e1e30", fg=FG, insertbackground=AC, relief=tk.FLAT, bd=2).pack(
        side=tk.LEFT, padx=2
    )

    row7 = tk.Frame(parent, bg=bg3)
    row7.pack(fill=tk.X, pady=2)
    tk.Label(row7, text="Audio", bg=bg3, fg=FG2, width=8, anchor="w").pack(side=tk.LEFT)
    tk.Scale(
        row7,
        variable=app.sn_volume_var,
        from_=0.0,
        to=2.0,
        resolution=0.05,
        orient=tk.HORIZONTAL,
        bg=bg3,
        fg=FG,
        highlightthickness=0,
        troughcolor="#0e1e30",
        length=120,
    ).pack(side=tk.LEFT, padx=2)
    tk.Label(row7, text="Fade in/out", bg=bg3, fg=FG2).pack(side=tk.LEFT, padx=(6, 0))
    tk.Entry(row7, textvariable=app.sn_fade_in_var, width=4, bg="#0e1e30", fg=FG, insertbackground=AC, relief=tk.FLAT, bd=2).pack(
        side=tk.LEFT, padx=2
    )
    tk.Entry(row7, textvariable=app.sn_fade_out_var, width=4, bg="#0e1e30", fg=FG, insertbackground=AC, relief=tk.FLAT, bd=2).pack(
        side=tk.LEFT, padx=2
    )

    row_ed = tk.Frame(parent, bg=bg3)
    row_ed.pack(fill=tk.X, pady=4)
    tk.Button(
        row_ed,
        text="Layout Editor",
        bg="#1f3650",
        fg="#e7f1ff",
        font=("Segoe UI", 9, "bold"),
        relief=tk.FLAT,
        padx=8,
        pady=4,
        command=app._sn_open_layout_editor,
    ).pack(side=tk.LEFT, padx=2)
    tk.Button(
        row_ed,
        text="Use main file",
        bg="#121e34",
        fg="#7a9ab8",
        font=("Segoe UI", 9, "bold"),
        relief=tk.FLAT,
        padx=8,
        pady=4,
        command=app._sn_use_main_file,
    ).pack(side=tk.LEFT, padx=2)


def install_social_instagram_toolbar(app, parent, *, bg):
    """Instagram: Start / Pause / Stop, progress, status (player ilə sinxron)."""
    FG2 = app.FG2
    ensure_social_export_vars(app)
    fnt = ("Segoe UI", 9, "bold")
    bbc = dict(font=fnt, relief=tk.FLAT, cursor="hand2", padx=10, pady=6, bd=0)
    f1 = tk.Frame(parent, bg=bg, pady=4, padx=4)
    f1.pack(fill=tk.X)
    tk.Label(f1, text="Convert:", bg=bg, fg=FG2, font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(2, 8))
    tk.Button(
        f1,
        text="Start",
        bg="#047857",
        fg="#ecfdf5",
        command=app._start_social,
        activebackground="#059669",
        **bbc,
    ).pack(side=tk.LEFT, padx=2)
    tk.Button(
        f1,
        text="Pause",
        bg="#92400e",
        fg="#ffedd5",
        command=app._sn_pause_social_encoding,
        activebackground="#b45309",
        **bbc,
    ).pack(side=tk.LEFT, padx=2)
    tk.Button(
        f1,
        text="Stop",
        bg="#6a1515",
        fg="#ffaaaa",
        command=app._stop_social,
        activebackground="#8a2020",
        **bbc,
    ).pack(side=tk.LEFT, padx=2)
    tk.Label(f1, text="0–100%", bg=bg, fg=FG2, font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(8, 4))
    ttk.Progressbar(f1, variable=app.sn_pv, maximum=100, length=140).pack(side=tk.LEFT, padx=2)
    tk.Label(
        f1,
        textvariable=app.instagram_ws_status_var,
        bg=bg,
        fg="#e2e8f0",
        font=("Segoe UI", 9),
    ).pack(side=tk.LEFT, padx=(10, 4), fill=tk.X, expand=True)


def install_social_export_toolbar(app, parent, *, bg):
    """Export və önizləmə düymələri — pəncərənin altında sabit (ümumi platformalar)."""
    FG2 = app.FG2
    bbc = dict(font=("Segoe UI", 9, "bold"), relief=tk.FLAT, cursor="hand2", padx=10, pady=5, bd=0)
    f = tk.Frame(parent, bg=bg, pady=6)
    f.pack(fill=tk.X)
    tk.Button(f, text="Export", bg="#5a0080", fg="#ffffff", command=app._start_social, activebackground="#7800a0", **bbc).pack(
        side=tk.LEFT, padx=2
    )
    tk.Button(f, text="Apply", bg="#0f4a2a", fg="#dfffe9", command=app._sn_apply_settings, activebackground="#15653b", **bbc).pack(
        side=tk.LEFT, padx=2
    )
    tk.Button(f, text="Reset", bg="#3a1f1f", fg="#ffd8d8", command=app._sn_reset_settings, activebackground="#5a2b2b", **bbc).pack(
        side=tk.LEFT, padx=2
    )
    ttk.Combobox(
        f,
        textvariable=app.sn_preview_len_var,
        values=["5", "8", "10", "12"],
        state="readonly",
        width=4,
        font=("Segoe UI", 9),
    ).pack(side=tk.LEFT, padx=4)
    tk.Button(f, text="Preview", bg="#1b3a66", fg="#d8ecff", command=app._start_social_preview, activebackground="#245189", **bbc).pack(
        side=tk.LEFT, padx=2
    )
    tk.Button(
        f,
        text="Source in player",
        bg="#12324a",
        fg="#d8f0ff",
        command=app._social_open_source_in_player,
        activebackground="#1a4767",
        **bbc,
    ).pack(side=tk.LEFT, padx=2)
    tk.Button(f, text="Stop", bg="#6a1515", fg="#ffaaaa", command=app._stop_social, activebackground="#8a2020", **bbc).pack(
        side=tk.LEFT, padx=2
    )
    tk.Checkbutton(
        f,
        text="Auto preview",
        variable=app.sn_auto_preview_var,
        bg=bg,
        fg=FG2,
        activebackground=bg,
        activeforeground=FG2,
        selectcolor="#0f4a2a",
        cursor="hand2",
    ).pack(side=tk.LEFT, padx=6)
