"""
Seçilmiş platform üçün tək iş pəncərəsi — Social Network Converter (export / convert parametrləri).
"""
import tkinter as tk
from tkinter import ttk

from orvix.social_export_panel import ensure_social_export_vars
from orvix.social_compact_workspace import install_compact_social_workspace
from orvix.social_tab import PLATFORM_ORDER
from orvix.video_player import EmbeddedVideoPlayer


def social_workspace_dialog_parent(app):
    """Fayl dialoqları bu pəncərəyə bağlansın — əsas pəncərəyə keçməsin."""
    win = getattr(app, "_social_workspace_win", None)
    if win is not None:
        try:
            if win.winfo_exists():
                return win
        except tk.TclError:
            pass
    return app.root


def open_social_workspace(app, platform_name=None):
    """platform_name verilərsə, əvvəl seçimi təyin edir."""
    from tkinter import messagebox

    if not getattr(app, "_orvix_pro_mode", False):
        try:
            messagebox.showinfo(
                "Full Orvix",
                "Social network converter and workspace are only available in the full Orvix build.\n\n"
                "Enable ORVIX_PRO=1 or use a full license to unlock.",
                parent=getattr(app, "root", None),
            )
        except Exception:
            pass
        return

    ensure_social_export_vars(app)
    if platform_name:
        app.sn_platform_var.set(platform_name)
    elif not hasattr(app, "sn_platform_var"):
        app.sn_platform_var = tk.StringVar(value=PLATFORM_ORDER[0])

    plat = app.sn_platform_var.get()

    old = getattr(app, "_social_workspace_win", None)
    if old is not None:
        try:
            if "social_workspace" in getattr(app, "_players", {}):
                del app._players["social_workspace"]
            app._social_workspace_player = None
            old.destroy()
        except tk.TclError:
            pass

    win = tk.Toplevel(app.root)
    app._social_workspace_win = win
    app._instagram_convert_only = plat == "Instagram"
    win.title(f"{plat} — Video Convert — ORVIX" if plat == "Instagram" else f"{plat} — ORVIX")
    win.configure(bg="#0f172a")
    try:
        win.transient(app.root)
    except tk.TclError:
        pass
    try:
        win.state("zoomed")
    except tk.TclError:
        sw, sh = app.root.winfo_screenwidth(), app.root.winfo_screenheight()
        win.geometry(f"{min(1180, sw - 48)}x{min(800, sh - 48)}+24+24")

    def _on_close():
        app._social_workspace_player = None
        app._instagram_convert_only = False
        app._instagram_workspace_simple = False
        try:
            if "social_workspace" in getattr(app, "_players", {}):
                del app._players["social_workspace"]
        except Exception:
            pass
        app._social_workspace_win = None
        win.destroy()
        try:
            app.root.lift()
            app.root.focus_force()
        except Exception:
            pass

    header = tk.Frame(win, bg="#1e293b", padx=12, pady=6)
    hdr_txt = f"{plat} — video convert" if plat == "Instagram" else plat
    tk.Label(header, text=hdr_txt, bg="#1e293b", fg="#f5f3ff", font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT)
    tk.Button(
        header,
        text="Close",
        bg="#475569",
        fg="#fff",
        font=("Segoe UI", 9, "bold"),
        relief=tk.FLAT,
        padx=12,
        pady=4,
        cursor="hand2",
        command=_on_close,
    ).pack(side=tk.RIGHT)
    # Start/Pause/Stop + progress — kompakt paneldə (alt toolbar yox)
    header.pack(side=tk.TOP, fill=tk.X)

    mid = tk.Frame(win, bg="#0f172a")
    mid.pack(fill=tk.BOTH, expand=True)

    left_wrap = tk.Frame(mid, bg="#0f172a")
    left_wrap.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    canvas = tk.Canvas(left_wrap, bg="#0f172a", highlightthickness=0)
    scroll = ttk.Scrollbar(left_wrap, orient=tk.VERTICAL, command=canvas.yview)
    _pad = (12, 8)
    inner = tk.Frame(canvas, bg="#1e293b", padx=_pad[0], pady=_pad[1])

    win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

    def _on_inner_configure(_event=None):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _on_canvas_configure(e):
        # Instagram: kompakt converter paneli
        _min_inner = 340
        canvas.itemconfig(win_id, width=max(_min_inner, e.width - 10))

    inner.bind("<Configure>", _on_inner_configure)
    canvas.bind("<Configure>", _on_canvas_configure)
    canvas.configure(yscrollcommand=scroll.set)

    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scroll.pack(side=tk.RIGHT, fill=tk.Y)

    # Siçan çarxı: əsas pəncərədə _install_global_mousewheel (pv_main)

    # İş pəncərəsi: geniş pleyer
    _ws_player_w = 660 if plat == "Instagram" else 620
    _ws_canvas_h = 340 if plat == "Instagram" else 320
    _player_w = _ws_player_w
    player_host = tk.Frame(mid, bg="#0f172a", width=_player_w)
    player_host.pack(side=tk.RIGHT, fill=tk.Y)
    player_host.pack_propagate(False)
    ws_pl = EmbeddedVideoPlayer(
        player_host,
        on_play_start=app._on_player_play_start,
        on_pfl=app._on_player_pfl,
        panel_width=_ws_player_w,
        video_canvas_height=_ws_canvas_h,
    )
    app._social_workspace_player = ws_pl
    app._players["social_workspace"] = ws_pl

    if plat == "Instagram":
        from orvix.instagram_workspace import install_instagram_workspace

        install_instagram_workspace(app, inner)
    else:
        install_compact_social_workspace(app, inner, plat)

    try:
        win.protocol("WM_DELETE_WINDOW", _on_close)
    except tk.TclError:
        pass
    try:
        app._social_workspace_sync_player()
    except Exception:
        pass
