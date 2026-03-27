"""1920×1080 Instagram qat düzəni: siçan ilə sürüşdürmə və ölçü (scroll)."""
from __future__ import annotations

import tkinter as tk
from typing import Any, Dict, List, Optional, Tuple

from orvix.instagram_layer_layout import CANVAS_H, CANVAS_W, default_layout, layout_to_json, parse_layout_json

LayerKey = str
ORDER_TOP_FIRST: Tuple[LayerKey, ...] = ("center", "bottom", "top", "bg")


def open_instagram_layer_editor(
    app: Any,
    *,
    parent: Optional[tk.Misc] = None,
    dlg_parent: Optional[tk.Misc] = None,
) -> None:
    """insta_layer_layout_json_var yenilənir."""
    root = getattr(app, "root", None)
    dlg = dlg_parent or parent or root
    raw = ""
    if hasattr(app, "insta_layer_layout_json_var"):
        raw = app.insta_layer_layout_json_var.get() or ""
    layout = parse_layout_json(raw)

    pw = 960
    ph = 540
    sx = pw / float(CANVAS_W)
    sy = ph / float(CANVAS_H)

    win = tk.Toplevel(parent or root)
    win.title("Instagram layers — 1920×1080")
    win.configure(bg="#1e293b")
    win.transient(root)
    win.geometry(f"{pw + 48}x{ph + 120}")

    hint = tk.Label(
        win,
        text="Select a layer (click), drag to move; mouse wheel resizes. Feed/Reels/Stories export size is applied separately.",
        bg="#1e293b",
        fg="#94a3b8",
        font=("Segoe UI", 8),
        wraplength=pw + 20,
        justify=tk.LEFT,
    )
    hint.pack(pady=(8, 4))

    cv = tk.Canvas(win, width=pw, height=ph, bg="#0f172a", highlightthickness=1, highlightbackground="#334155")
    cv.pack(padx=24, pady=4)

    labels = {"bg": "BG", "top": "TOP", "bottom": "BOTTOM", "center": "CENTER"}
    colors = {"bg": "#64748b", "top": "#38bdf8", "bottom": "#fbbf24", "center": "#a78bfa"}

    state: Dict[str, Any] = {
        "layout": {k: dict(layout[k]) for k in layout},
        "selected": "center",
        "drag": None,
    }

    def to_cx(x: float) -> int:
        return int(x * sx)

    def to_cy(y: float) -> int:
        return int(y * sy)

    def from_cx(v: int) -> float:
        return float(v) / sx

    def from_cy(v: int) -> float:
        return float(v) / sy

    def clamp_rect(k: str) -> None:
        r = state["layout"][k]
        x = max(0, min(int(r["x"]), CANVAS_W - 2))
        y = max(0, min(int(r["y"]), CANVAS_H - 2))
        w = max(32, min(int(r["w"]), CANVAS_W - x))
        h = max(32, min(int(r["h"]), CANVAS_H - y))
        state["layout"][k] = {"x": x, "y": y, "w": w, "h": h}

    def hit_order(mx: int, my: int) -> Optional[str]:
        for k in ORDER_TOP_FIRST:
            r = state["layout"][k]
            x1, y1 = to_cx(r["x"]), to_cy(r["y"])
            x2, y2 = to_cx(r["x"] + r["w"]), to_cy(r["y"] + r["h"])
            if x1 <= mx <= x2 and y1 <= my <= y2:
                return k
        return None

    def redraw() -> None:
        cv.delete("all")
        cv.create_rectangle(0, 0, pw, ph, outline="#1e293b", width=1)

        draw_order: List[str] = ["bg", "top", "bottom", "center"]
        for k in draw_order:
            r = state["layout"][k]
            x1, y1 = to_cx(r["x"]), to_cy(r["y"])
            x2, y2 = to_cx(r["x"] + r["w"]), to_cy(r["y"] + r["h"])
            col = colors[k]
            fill = "#0c1829" if k == "bg" else ""
            sel = state["selected"] == k
            oc = "#f472b6" if sel else col
            cv.create_rectangle(x1, y1, x2, y2, fill=fill, outline=oc, width=3 if sel else 1)
            cv.create_text(
                x1 + 4,
                y1 + 4,
                anchor="nw",
                text=labels[k],
                fill=col if not sel else "#f472b6",
                font=("Segoe UI", 9, "bold"),
            )

    def on_down(ev: tk.Event) -> None:
        k = hit_order(ev.x, ev.y)
        if k:
            state["selected"] = k
            state["drag"] = (k, ev.x, ev.y, dict(state["layout"][k]))
        redraw()

    def on_move(ev: tk.Event) -> None:
        d = state["drag"]
        if not d:
            return
        k, x0, y0, orig = d
        dx = from_cx(ev.x - x0)
        dy = from_cy(ev.y - y0)
        state["layout"][k]["x"] = int(orig["x"] + dx)
        state["layout"][k]["y"] = int(orig["y"] + dy)
        clamp_rect(k)
        redraw()

    def on_up(_: tk.Event) -> None:
        state["drag"] = None

    def on_wheel(ev: tk.Event) -> None:
        k = state["selected"]
        r = state["layout"][k]
        # Windows: delta ±120; Linux: Button-4/5
        delta = getattr(ev, "delta", 0)
        if delta == 0:
            try:
                n = int(ev.num)
            except Exception:
                n = 0
            step = 24 if n == 4 else -24 if n == 5 else 0
        else:
            step = 16 if delta > 0 else -16
        if step == 0:
            return
        cx = r["x"] + r["w"] / 2.0
        cy = r["y"] + r["h"] / 2.0
        nw = max(32, int(r["w"] + step))
        nh = max(32, int(r["h"] + step))
        state["layout"][k]["x"] = int(cx - nw / 2)
        state["layout"][k]["y"] = int(cy - nh / 2)
        state["layout"][k]["w"] = nw
        state["layout"][k]["h"] = nh
        clamp_rect(k)
        redraw()

    cv.bind("<ButtonPress-1>", on_down)
    cv.bind("<B1-Motion>", on_move)
    cv.bind("<ButtonRelease-1>", on_up)
    cv.bind("<MouseWheel>", on_wheel)
    cv.bind("<Button-4>", on_wheel)
    cv.bind("<Button-5>", on_wheel)

    btns = tk.Frame(win, bg="#1e293b")
    btns.pack(pady=8)

    def apply_ok() -> None:
        merged = parse_layout_json(layout_to_json(state["layout"]))
        if hasattr(app, "insta_layer_layout_json_var"):
            app.insta_layer_layout_json_var.set(layout_to_json(merged))
        win.destroy()

    def reset_def() -> None:
        state["layout"] = {k: dict(v) for k, v in default_layout().items()}
        redraw()

    tk.Button(btns, text="Reset", command=reset_def, bg="#334155", fg="#fff", font=("Segoe UI", 9)).pack(
        side=tk.LEFT, padx=4
    )
    tk.Button(btns, text="Apply", command=apply_ok, bg="#059669", fg="#fff", font=("Segoe UI", 9, "bold")).pack(
        side=tk.LEFT, padx=4
    )
    tk.Button(btns, text="Close", command=win.destroy, bg="#475569", fg="#fff", font=("Segoe UI", 9)).pack(
        side=tk.LEFT, padx=4
    )

    redraw()
