"""Orvix Lite — application entry point."""
import ctypes
import os
import sys
import tkinter as tk
from tkinter import messagebox

import orvix.deps  # noqa: F401 — Pillow/OpenCV yoxlanışı
from orvix.bootstrap import fix_windows_compatibility
from orvix.deps import PIL_AVAILABLE, _HAS_SD
from orvix.ffmpeg_core import ffmpeg_mgr
from orvix.gpu import gpu_acc
from orvix.license_ui import run_license_gate, start_license_heartbeat
from orvix.pv_main import OrvixApp


def _set_windows_dpi_before_tk():
    """SetProcessDpiAwareness Tk() / HWND yaranmazdan əvvəl olmalıdır; əks halda ghosting, ikiqat çəkilmə."""
    if sys.platform != "win32":
        return
    mode = (os.environ.get("ORVIX_DPI_AWARENESS", "") or "").strip().lower()
    try:
        if mode in ("2", "permonitorv2", "v2"):
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        elif mode in ("0", "unaware"):
            ctypes.windll.shcore.SetProcessDpiAwareness(0)
        else:
            # 1 = per-monitor (Tk ilə ən sabit; 2 bəzi sistemlərdə “qatlanmış” UI)
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def main():
    fix_windows_compatibility()
    _set_windows_dpi_before_tk()
    gpu_info = gpu_acc.get_gpu_info()
    print("=" * 60)
    print("Orvix Lite — Video QC (simple edition)")
    print("=" * 60)
    print(f"GPU: {gpu_info['name']} ({gpu_info['type']})")
    print(f"Pillow: {'OK' if PIL_AVAILABLE else 'NOT FOUND - pip install Pillow'}")
    print(f"FFmpeg: {ffmpeg_mgr.ffmpeg_path or 'NOT FOUND'}")
    print(f"SoundDevice: {'OK' if _HAS_SD else 'NOT FOUND - pip install sounddevice'}")
    print("Player: Aspect-correct fill (no black bars)")
    print("Sync: Wall-clock video+audio, zero lag")
    print("VU Meter: Premium slim horizontal dB, 60fps")
    print("Slogan: See the Unseen — Every Frame Holds a Truth.")
    print("Parameters: Full video+audio metadata with scan type")
    print("Double-click: plays 2s before problem start")
    print("=" * 60)

    if not PIL_AVAILABLE:
        try:
            _root = tk.Tk()
            _root.withdraw()
            messagebox.showerror(
                "Missing Dependency",
                "Pillow (PIL) is not installed!\n\n"
                "Please run:\n    pip install Pillow\n\n"
                "Then restart Orvix Lite.",
            )
            _root.destroy()
        except Exception:
            pass
        sys.exit(1)

    if not run_license_gate():
        sys.exit(0)

    root = tk.Tk()
    OrvixApp(root)
    start_license_heartbeat(root)
    root.mainloop()


if __name__ == "__main__":
    main()
