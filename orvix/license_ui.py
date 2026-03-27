"""Splash + trial / license gate (Tkinter)."""
from __future__ import annotations

import os
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox, simpledialog

from orvix import license_client
from orvix.license_state import get_or_create_install_id, load_state, update_token


def _license_enabled() -> bool:
    if os.environ.get("ORVIX_LICENSE_SKIP", "").strip().lower() in ("1", "true", "yes", "on"):
        return False
    base = os.environ.get("ORVIX_LICENSE_SERVER", "").strip()
    if not base:
        strict = os.environ.get("ORVIX_LICENSE_STRICT", "").strip().lower() in ("1", "true", "yes", "on")
        if strict:
            return True
        print(
            "[Orvix] ORVIX_LICENSE_SERVER not set — license check skipped (dev). "
            "Set ORVIX_LICENSE_STRICT=1 to require server."
        )
        return False
    return True


def _base_url() -> str:
    return os.environ.get("ORVIX_LICENSE_SERVER", "").strip().rstrip("/")


def run_splash_ms(parent: tk.Tk, ms: int = 900) -> None:
    splash = tk.Toplevel(parent)
    splash.overrideredirect(True)
    splash.configure(bg="#0f172a")
    w, h = 420, 140
    splash.geometry(f"{w}x{h}+{parent.winfo_screenwidth() // 2 - w // 2}+{parent.winfo_screenheight() // 2 - h // 2}")
    tk.Label(
        splash,
        text="Orvix Lite",
        fg="#e2e8f0",
        bg="#0f172a",
        font=("Segoe UI", 18, "bold"),
    ).pack(pady=(24, 8))
    tk.Label(splash, text="Loading…", fg="#94a3b8", bg="#0f172a", font=("Segoe UI", 10)).pack()
    splash.update()
    t0 = time.time()
    while (time.time() - t0) * 1000 < ms:
        splash.update_idletasks()
        splash.update()
        time.sleep(0.02)
    try:
        splash.destroy()
    except tk.TclError:
        pass


def _try_ping(base: str, install_id: str, token: str) -> bool:
    try:
        r = license_client.api_session_ping(base, install_id, token)
        if r.get("ok") and r.get("valid"):
            new_tok = r.get("token")
            if new_tok:
                update_token(base, new_tok)
            return True
    except Exception:
        pass
    return False


def run_license_gate() -> bool:
    """
    Returns True if user may open the main app.
    """
    if not _license_enabled():
        return True

    base = _base_url()
    if not base:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Orvix",
            "Set ORVIX_LICENSE_SERVER to your license server HTTPS URL\n"
            "(e.g. https://your-service.onrender.com).",
        )
        root.destroy()
        return False

    install_id = get_or_create_install_id()

    root = tk.Tk()
    root.withdraw()
    root.title("Orvix")
    try:
        run_splash_ms(root, 900)
    except Exception:
        pass

    st = load_state()
    token = (st.get("token") or "").strip()
    cached_server = (st.get("server") or "").strip()
    if cached_server and cached_server != base:
        token = ""

    if token and _try_ping(base, install_id, token):
        root.destroy()
        return True

    try:
        license_client.api_device_register(base, install_id)
    except Exception as e:
        messagebox.showerror(
            "License server",
            f"Cannot reach license server:\n{e}\n\nCheck ORVIX_LICENSE_SERVER and internet.",
            parent=root,
        )
        root.destroy()
        return False

    win = tk.Toplevel(root)
    win.title("Orvix — License")
    win.configure(bg="#1e293b")
    win.resizable(False, False)
    tk.Label(
        win,
        text="Start 7-day trial or enter a license key.",
        fg="#e2e8f0",
        bg="#1e293b",
        font=("Segoe UI", 11),
        wraplength=380,
        justify=tk.LEFT,
    ).pack(padx=20, pady=(16, 8))

    result = {"ok": False}

    def do_trial():
        try:
            r = license_client.api_trial_start(base, install_id)
            if r.get("ok") and r.get("token"):
                update_token(base, r["token"])
                result["ok"] = True
                win.destroy()
        except Exception as e:
            messagebox.showerror("Trial", str(e), parent=win)

    def do_license():
        key = simpledialog.askstring("License key", "Enter your license key:", parent=win)
        if not key:
            return
        try:
            r = license_client.api_license_activate(base, install_id, key)
            if r.get("ok") and r.get("token"):
                update_token(base, r["token"])
                result["ok"] = True
                win.destroy()
        except Exception as e:
            messagebox.showerror("License", str(e), parent=win)

    def do_exit():
        win.destroy()

    bf = tk.Frame(win, bg="#1e293b")
    bf.pack(padx=20, pady=(0, 16))
    tk.Button(bf, text="Start 7-day trial", command=do_trial, width=22, font=("Segoe UI", 10)).pack(pady=4)
    tk.Button(bf, text="Enter license key…", command=do_license, width=22, font=("Segoe UI", 10)).pack(pady=4)
    tk.Button(bf, text="Exit", command=do_exit, width=22, font=("Segoe UI", 10)).pack(pady=4)

    win.transient(root)
    win.grab_set()
    root.wait_window(win)
    ok = result["ok"]
    try:
        root.destroy()
    except tk.TclError:
        pass
    return ok


_heartbeat_stop = threading.Event()
_main_root: tk.Tk | None = None


def start_license_heartbeat(root: tk.Tk) -> None:
    """Background ping every 15 minutes; exits process if license invalid."""
    global _main_root
    if not _license_enabled():
        return
    _main_root = root

    def fail():
        messagebox.showerror(
            "License",
            "License check failed or expired. The application will close.",
        )
        sys.exit(1)

    def loop():
        while not _heartbeat_stop.wait(900):
            base = _base_url()
            if not base:
                continue
            st = load_state()
            token = (st.get("token") or "").strip()
            iid = (st.get("install_id") or get_or_create_install_id()).strip()
            if not token:
                continue
            try:
                r = license_client.api_session_ping(base, iid, token)
                if r.get("ok") and r.get("valid") and r.get("token"):
                    update_token(base, r["token"])
                else:
                    raise RuntimeError("invalid")
            except Exception:
                mr = _main_root
                if mr:
                    mr.after(0, fail)
                else:
                    sys.exit(1)

    threading.Thread(target=loop, daemon=True).start()
