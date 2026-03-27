"""Tək Transform + Crop paneli — aktiv qat seçiləndə yalnız ona təsir edir."""
from __future__ import annotations

import tkinter as tk
from typing import Any, Callable, Dict, Tuple

from orvix.instagram_layer_layout import CANVAS_H, CANVAS_W, layout_to_json, parse_layout_json

F = ("Segoe UI", 8)
FB = ("Segoe UI", 8, "bold")
FL = ("Segoe UI", 8)


def _debounce(app: Any, ms: int, fn: Callable[[], None]) -> None:
    attr = "_insta_layer_ui_after"
    aid = getattr(app, attr, None)
    if aid is not None:
        try:
            app.root.after_cancel(aid)
        except Exception:
            pass

    def _run():
        setattr(app, attr, None)
        try:
            fn()
        except Exception:
            pass

    setattr(app, attr, app.root.after(ms, _run))


def install_layer_parameter_panels(app: Any, parent: tk.Misc, _dlg_parent: tk.Misc) -> None:
    if not hasattr(app, "insta_layer_active_var"):
        app.insta_layer_active_var = tk.StringVar(value="center")

    bg = "#1e293b"
    fg = "#e2e8f0"
    fg2 = "#94a3b8"
    ac = "#334155"

    controls: Dict[str, Tuple[tk.Scale, tk.DoubleVar, tk.StringVar]] = {}

    def get_layout():
        return parse_layout_json(app.insta_layer_layout_json_var.get() or "")

    def save_layout(layout):
        app.insta_layer_layout_json_var.set(layout_to_json(layout))

    def active_layer() -> str:
        k = (app.insta_layer_active_var.get() or "center").strip()
        if k not in ("bg", "top", "bottom", "center"):
            return "center"
        return k

    def refresh_preview():
        _debounce(app, 16, lambda: app._instagram_workspace_preview_mode())

    def apply_num(key: str, v: float, is_int: bool):
        lk = active_layer()
        layout = get_layout()
        if lk not in layout:
            return
        layout[lk][key] = int(round(v)) if is_int else float(v)
        save_layout(layout)
        refresh_preview()

    def add_row(
        grid: tk.Frame,
        row: int,
        label: str,
        key: str,
        lo: float,
        hi: float,
        is_int: bool,
    ) -> None:
        tk.Label(grid, text=label, bg=bg, fg=fg2, font=FL, width=9, anchor="w").grid(
            row=row, column=0, sticky="w", padx=2, pady=1
        )
        layout0 = get_layout()
        lk = active_layer()
        init = float(layout0.get(lk, {}).get(key, lo))
        init = max(lo, min(hi, init))
        var = tk.DoubleVar(value=init)
        ev = tk.StringVar(value=str(int(init)) if is_int else f"{init:.4f}".rstrip("0").rstrip("."))

        sc = tk.Scale(
            grid,
            from_=lo,
            to=hi,
            orient=tk.HORIZONTAL,
            variable=var,
            bg=ac,
            fg=fg,
            highlightthickness=0,
            troughcolor="#0f172a",
            length=140,
            showvalue=0,
            resolution=1 if is_int else 0.01,
        )
        sc.grid(row=row, column=1, sticky="ew", padx=2, pady=1)

        def sync_ev(_v=None):
            v = var.get()
            if is_int:
                ev.set(str(int(round(v))))
            else:
                ev.set(f"{v:.4f}".rstrip("0").rstrip("."))
            apply_num(key, v, is_int)

        sc.config(command=lambda _v: sync_ev())

        ent = tk.Entry(grid, textvariable=ev, width=9, bg="#0f172a", fg=fg, font=FL, relief=tk.FLAT)

        def from_ent(_e=None):
            try:
                v = float(ev.get().replace(",", "."))
                v = max(lo, min(hi, v))
                var.set(v)
                sync_ev()
            except Exception:
                pass

        ent.bind("<Return>", from_ent)
        ent.bind("<FocusOut>", from_ent)
        ent.grid(row=row, column=2, padx=2, pady=1)

        def reset():
            var.set(lo)
            ev.set(str(int(lo)) if is_int else str(lo))
            apply_num(key, lo, is_int)

        tk.Button(grid, text="↺", command=reset, bg="#475569", fg="#fff", font=F, width=2, relief=tk.FLAT).grid(
            row=row, column=3, padx=1
        )
        controls[key] = (sc, var, ev)

    lf = tk.LabelFrame(
        parent,
        text="Selected layer — Transform & Crop (press Active on the row first)",
        bg=bg,
        fg="#c4b5fd",
        font=("Segoe UI", 9, "bold"),
    )
    lf.pack(fill=tk.X, pady=8, padx=0)

    title_lbl = tk.Label(lf, text="", bg=bg, fg="#fde68a", font=("Segoe UI", 8))
    title_lbl.pack(anchor="w", padx=8, pady=(4, 0))

    outer = tk.Frame(lf, bg=bg)
    outer.pack(fill=tk.X, padx=6, pady=4)

    left = tk.Frame(outer, bg=bg)
    left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
    right = tk.Frame(outer, bg=bg)
    right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    tk.Label(left, text="Transform", bg=bg, fg=fg2, font=FB).pack(anchor="w")
    tk.Label(right, text="Crop (source px)", bg=bg, fg=fg2, font=FB).pack(anchor="w")

    gl = tk.Frame(left, bg=bg)
    gl.pack(fill=tk.X)
    gr = tk.Frame(right, bg=bg)
    gr.pack(fill=tk.X)
    for g in (gl, gr):
        g.columnconfigure(1, weight=1)

    rr = 0
    for label, key, lo, hi, is_int in [
        ("Zoom", "zoom", 0.25, 4.0, False),
        ("Zoom X", "zoom_x", 0.25, 4.0, False),
        ("Zoom Y", "zoom_y", 0.25, 4.0, False),
        ("Pan X", "pan_x", -900.0, 900.0, False),
        ("Pan Y", "pan_y", -900.0, 900.0, False),
        ("Rotate Z°", "rotate_z", -180.0, 180.0, False),
    ]:
        add_row(gl, rr, label, key, lo, hi, is_int)
        rr += 1

    rot_fr = tk.Frame(gl, bg=bg)
    rot_fr.grid(row=rr, column=0, columnspan=4, sticky="w", pady=4)
    tk.Label(rot_fr, text="Z", bg=bg, fg=fg2, font=FB).pack(side=tk.LEFT, padx=(0, 6))

    def rot_90():
        layout = get_layout()
        lk = active_layer()
        if lk not in layout:
            return
        rz = float(layout[lk].get("rotate_z", 0)) + 90.0
        while rz > 180:
            rz -= 360
        while rz < -180:
            rz += 360
        layout[lk]["rotate_z"] = rz
        save_layout(layout)
        if "rotate_z" in controls:
            _, var, ev = controls["rotate_z"]
            var.set(rz)
            ev.set(f"{rz:.4f}".rstrip("0").rstrip("."))
        refresh_preview()

    tk.Button(
        rot_fr,
        text="⟳ 90°",
        command=rot_90,
        bg="#6366f1",
        fg="#fff",
        font=F,
        relief=tk.FLAT,
        padx=8,
        pady=2,
        cursor="hand2",
    ).pack(side=tk.LEFT)

    rr = 0
    for label, key, lo, hi, is_int in [
        ("Crop X1", "crop_x1", 0, CANVAS_W, True),
        ("Crop Y1", "crop_y1", 0, CANVAS_H, True),
        ("Crop X2", "crop_x2", 0, CANVAS_W, True),
        ("Crop Y2", "crop_y2", 0, CANVAS_H, True),
    ]:
        add_row(gr, rr, label, key, float(lo), float(hi), is_int)
        rr += 1

    names = {"bg": "Fon", "top": "Üst", "bottom": "Alt", "center": "Orta (video)"}

    def sync_sliders_from_active():
        layout = get_layout()
        lk = active_layer()
        title_lbl.config(text=f"Active layer: {names.get(lk, lk)}  •  sliders apply to this layer")
        r = layout.get(lk) or {}
        for key, (sc, var, ev) in controls.items():
            if key not in r:
                continue
            v = float(r[key])
            try:
                lo = float(sc.cget("from"))
                hi = float(sc.cget("to"))
            except (tk.TclError, ValueError, TypeError):
                continue
            v = max(lo, min(hi, v))
            var.set(v)
            if key in ("crop_x1", "crop_y1", "crop_x2", "crop_y2"):
                ev.set(str(int(round(v))))
            else:
                ev.set(f"{v:.4f}".rstrip("0").rstrip("."))

    def reset_all_active():
        layout = get_layout()
        lk = active_layer()
        fresh = parse_layout_json("")
        layout[lk] = fresh[lk]
        save_layout(layout)
        sync_sliders_from_active()
        refresh_preview()

    tk.Button(lf, text="Reset All", command=reset_all_active, bg="#b45309", fg="#fff", font=F, relief=tk.FLAT, padx=12).pack(
        anchor="e", padx=6, pady=(0, 6)
    )

    def on_active_change(*_):
        sync_sliders_from_active()

    try:
        app.insta_layer_active_var.trace_add("write", on_active_change)
    except Exception:
        pass

    app._instagram_sync_layer_params_ui = sync_sliders_from_active
    sync_sliders_from_active()
