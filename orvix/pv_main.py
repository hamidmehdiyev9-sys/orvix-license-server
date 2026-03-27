"""Main GUI: Orvix Lite.

Legacy: this codebase was originally developed under the name *pvaq_analyzer*;
the main window class was previously referred to as PVAQ23.
"""
import colorsys
import ctypes
import datetime
import getpass
import hashlib
import json
import math
import os
import platform
import random
import re
import shutil
import socket
import ssl
import subprocess
import queue
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid
import zipfile
from datetime import timedelta
from tkinter import filedialog, messagebox, scrolledtext, ttk
import tkinter as tk
import tkinter.font as tkfont

import cv2
import numpy as np
from PIL import Image, ImageTk

import orvix.deps  # noqa: F401 — cv2/PIL yoxlanışı
from orvix.analyzers import ProfessionalAudioAnalyzer, ProfessionalVideoAnalyzer
from orvix.deps import PIL_AVAILABLE, SCIPY_AVAILABLE, _HAS_SD
from orvix.ffmpeg_core import ffmpeg_mgr
from orvix.ffmpeg_cuda import (
    edit_export_video_args,
    hwaccel_cuda_prefix,
    instagram_simple_video_args,
    map_lib_codec_to_nvenc,
    social_main_export_video_args,
    ve_export_video_audio_args,
    ve_preview_video_args,
)
from orvix.file_info import FileInfoExtractor
from orvix.gpu import gpu_acc
from orvix.utils import (
    PROBLEM_DICTIONARY,
    format_time,
    fmt_dur,
    fmt_size,
    get_english_time,
    run_ffprobe,
)
from orvix.video_player import EmbeddedVideoPlayer
from orvix.video_enhancement_ffmpeg import (
    build_ve_video_filter,
    collect_ve_flags_from_vars,
    has_any_ve_processing,
)
from orvix.instagram_video_module import ffmpeg_escape_subtitle_path
from orvix.widgets_brand import AnimatedLogo, AnimatedSlogan

try:
    from orvix.converter_ffmpeg import (
        build_ffmpeg_command,
        pattern_to_filename,
        probe_input_health,
        unique_output_path,
        validate_settings,
    )
except ImportError:
    build_ffmpeg_command = None  # type: ignore

    def probe_input_health(_ffprobe, _path, _si=None):  # type: ignore
        return True, ""


def _os_suspend_process(pid: int) -> bool:
    """Suspend a child process (pause FFmpeg). Windows: NtSuspendProcess; Unix: SIGSTOP."""
    if not pid:
        return False
    if os.name == "nt":
        try:
            PROCESS_SUSPEND_RESUME = 0x0800
            k32 = ctypes.windll.kernel32
            ntdll = ctypes.windll.ntdll
            h = k32.OpenProcess(PROCESS_SUSPEND_RESUME, False, int(pid))
            if not h:
                return False
            try:
                st = ntdll.NtSuspendProcess(h)
                return int(st) == 0
            finally:
                k32.CloseHandle(h)
        except Exception:
            return False
    try:
        import signal

        os.kill(int(pid), signal.SIGSTOP)
        return True
    except Exception:
        return False


def _os_resume_process(pid: int) -> bool:
    if not pid:
        return False
    if os.name == "nt":
        try:
            PROCESS_SUSPEND_RESUME = 0x0800
            k32 = ctypes.windll.kernel32
            ntdll = ctypes.windll.ntdll
            h = k32.OpenProcess(PROCESS_SUSPEND_RESUME, False, int(pid))
            if not h:
                return False
            try:
                st = ntdll.NtResumeProcess(h)
                return int(st) == 0
            finally:
                k32.CloseHandle(h)
        except Exception:
            return False
    try:
        import signal

        os.kill(int(pid), signal.SIGCONT)
        return True
    except Exception:
        return False


class OrvixApp:  # Orvix Lite (formerly PVAQ23 / pvaq_analyzer lineage)
    # Notebook tab order must match nb.add(...) sequence — used for active player lookup
    TAB_PLAYER_KEYS = (
        "file_params",
        "all_problems",
        "critical",
        "dict",
        "log",
        "broadcast",
        "converter",
        "social",
        "editing",
        "video_enhancement",
    )

    # VIDEO ENHANCEMENT — preset profiles (AUTO / Broadcast / Film / Sport / Social)
    VE_PRESET_PROFILES = {
        "auto": (
            "ve_auto_color",
            "ve_vid_denoise",
            "ve_sharpen",
            "ve_aspect_fix",
            "ve_lanczos",
        ),
        "broadcast": (
            "ve_auto_deint",
            "ve_vid_denoise",
            "ve_banding",
            "ve_aspect_fix",
            "ve_auto_color",
            "ve_comp_artifact",
            "ve_ringing",
        ),
        "film": (
            "ve_color_grading",
            "ve_contrast",
            "ve_saturation",
            "ve_gamma",
            "ve_brightness",
            "ve_texture_restore",
        ),
        "sport": (
            "ve_sharpen",
            "ve_clarity",
            "ve_motion_interp",
            "ve_vid_denoise",
            "ve_fps_increase",
            "ve_adaptive_sharpen",
        ),
        "social": (
            "ve_aspect_fix",
            "ve_lanczos",
            "ve_sharpen",
            "ve_auto_color",
            "ve_saturation",
            "ve_brightness",
        ),
    }

    # Critical tab — yalnız efirdə açıq görünən / bariz eşidilən (qısa donma·keçid·cüzi pozuntu All Problems-də)
    CRITICAL_TAB_FROZEN_MIN_S = 10.0
    CRITICAL_TAB_BLACK_MIN_S = 3.0
    CRITICAL_TAB_SILENCE_MIN_S = 12.0
    CRITICAL_TAB_CLIPPING_MIN_S = 0.15

    # ── PREMIUM PLUS PALETTE (ana panel) ───────────────────────────────────
    BG = '#080d14'       # Dərin mərmər tünd
    BG2 = '#0c121c'      # Panel
    BG3 = '#121a2a'      # Kart
    BG4 = '#182238'      # Qaldırılmış səth
    FG = '#eef6ff'       # Əsas mətn (daha açıq)
    FG2 = '#8fa3bc'      # İkinci dərəcə
    AC = '#3de8ff'       # Cyan vurğu
    AC2 = '#0a7ea8'      # Tünd mavi-cyan
    GN = '#00e699'       # Uğur
    GN2 = '#00b86b'
    RD = '#ff4d5c'       # Xəta
    OR = '#ff9f40'       # Xəbərdarlıq
    YL = '#ffd24d'       # Məlumat
    PR = '#b388ff'       # Bənövşəyi
    BORDER = '#1a2d4a'   # Çərçivə
    SEP = '#0f1828'      # Ayırıcı
    GOLD = '#d4af37'     # Premium nazik xətt
    HDR_BG = '#0a111f'   # Başlıq fonu
    HDR_LINE = '#1e3a5c' # Başlıq alt işıq
    FILE_BAR = '#0c1526'
    ZONE_PROG = '#070d18'
    ZONE_STAT = '#0a101c'

    def __init__(self, root):
        self.root = root
        self.root.title("Orvix Lite — Video QC")
        self.root.geometry("1680x1000")
        self.root.minsize(1280, 800)
        self.root.configure(bg=self.BG)
        # DPI: yalnız entry.py-də Tk() əvvəl (SetProcessDpiAwareness Tk sonra ghosting verir)
        try:
            self.root.attributes("-alpha", 1.0)
        except Exception:
            pass
        self._apply_typography()
        self.va = ProfessionalVideoAnalyzer()
        self.aa = ProfessionalAudioAnalyzer()
        self.file = None
        self.probs = []
        self.pcnt = 0
        self._prob_q_lock = threading.Lock()
        self._prob_q_pending = []
        self._prob_q_flush_id = None
        self._stat_err = 0
        self._stat_warn = 0
        self._stat_info = 0
        self._stat_vid = 0
        self._stat_aud = 0
        self.t0 = 0.0
        self.file_info = None
        self._running = False
        self.current_problem_index = -1
        self._conv_running = False
        self._conv_proc = None
        self._conv_cancel = False
        self._conv_pause = False
        self._conv_last_ct = 0.0
        self._conv_resume_settings_override = None
        self._conv_report = []
        self._sn_running = False
        self._sn_proc = None
        self._sn_cancel = False
        self._sn_pause = False
        self._sn_preview_running = False
        self._sn_preview_proc = None
        self._sn_preview_file = None
        self._sn_applied_settings = None
        self._sn_live_preview_after_id = None
        self._sn_preview_dirty = False
        self._sn_traces_ready = False
        self._sn_traces_set = False
        self._edit_running = False
        self._edit_proc = None
        self._edit_cancel = False
        self._ve_running = False
        self._ve_proc = None
        self._ve_cancel = False
        self._ve_total_dur = 0.0
        self._ve_preview_after_id = None
        self._ve_preview_busy = False
        self._ve_last_sync_ts = 0.0
        self._ve_preview_ss = 0.0
        self._ve_preview_seg_dur = 15.0
        self._ve_preview_temp = None
        self._timeline_canvas = None
        self._timeline_status_var = None
        self._timeline_drag_mode = None
        self._timeline_drag_clip_idx = None
        self._timeline_total_duration = 1.0
        self._timeline_playhead = 0.0
        self._timeline_clips = []
        self._timeline_active_idx = 0
        self._timeline_sync_guard = False

        # Social + Video Editing: True only with ORVIX_PRO=1 or manual override
        self._orvix_pro_mode = os.environ.get("ORVIX_PRO", "").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        # self._orvix_pro_mode = True  # yerli Pro testi üçün

        # One player per tab; only one active at a time globally
        self._players = {}
        self._active_player = None

        self._styles()
        self._build()
        self._update_display()
        self._install_global_mousewheel()
        self.root.after(400, self._startup_log)

        # Keyboard bindings
        self.root.bind('<Left>', self._on_left_arrow)
        self.root.bind('<Right>', self._on_right_arrow)
        self.root.bind('<Up>', self._on_up_arrow)
        self.root.bind('<Down>', self._on_down_arrow)
        self.root.bind('<space>', self._on_space)
        self.root.bind('<Control-Left>', self._on_ctrl_left)
        self.root.bind('<Control-Right>', self._on_ctrl_right)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Tab change: auto-stop old players
        self.nb.bind('<<NotebookTabChanged>>', self._on_tab_changed)

    def _apply_typography(self):
        """Windows üçün Segoe UI + Consolas — daha səlist və oxunaqlı default şriftlər."""
        try:
            tkfont.nametofont('TkDefaultFont').configure(family='Segoe UI', size=10)
            tkfont.nametofont('TkTextFont').configure(family='Segoe UI', size=10)
            tkfont.nametofont('TkHeadingFont').configure(family='Segoe UI', size=10, weight='bold')
            tkfont.nametofont('TkMenuFont').configure(family='Segoe UI', size=10)
            tkfont.nametofont('TkFixedFont').configure(family='Consolas', size=10)
        except Exception:
            pass

    def _on_close(self):
        for p in self._players.values():
            try:
                p.stop()
            except Exception:
                pass
        self.root.destroy()

    def _on_tab_changed(self, event=None):
        """When switching tabs, gracefully stop non-active players.
        Deferred by 60ms to avoid GUI stutter/flash during tab draw.
        Yalnız həqiqətən oynayan pleyerlər dayandırılır (boş tab keçidlərində join/CPU yükü olmasın)."""
        def _deferred_stop():
            try:
                current_tab_idx = self.nb.index(self.nb.select())
                tab_keys = list(self._players.keys())
                active_key = tab_keys[current_tab_idx] if current_tab_idx < len(tab_keys) else None
                for key, player in self._players.items():
                    if key != active_key:
                        try:
                            if getattr(player, "_playing", False):
                                player.stop()
                        except Exception:
                            pass
            except Exception:
                pass
        self.root.after(25, _deferred_stop)

    def _install_global_mousewheel(self):
        """Bütün pəncərələrdə siçan çarxı — yuxarıya qədər ilk scrollable tapılır (Canvas/Text/Treeview/Listbox)."""

        def _on_wheel(event):
            try:
                w = event.widget
            except Exception:
                return
            delta = getattr(event, "delta", 0) or 0
            if delta == 0:
                num = getattr(event, "num", 0)
                if num == 4:
                    delta = 120
                elif num == 5:
                    delta = -120
                else:
                    return
            if abs(delta) < 120:
                units = -1 if delta > 0 else 1
            else:
                units = int(-1 * (delta / 120))

            cur = w
            for _ in range(64):
                if cur is None:
                    break
                try:
                    cls = cur.winfo_class()
                except Exception:
                    break
                if cls in ("TScale", "Scale", "TCombobox", "TSpinbox"):
                    return
                if cls == "Canvas":
                    try:
                        yc = cur.cget("yscrollcommand")
                        if yc and str(yc).strip():
                            cur.yview_scroll(units, "units")
                            return "break"
                    except Exception:
                        pass
                if cls == "Text":
                    try:
                        cur.yview_scroll(units, "units")
                        return "break"
                    except Exception:
                        pass
                if cls == "Treeview":
                    try:
                        cur.yview_scroll(units, "units")
                        return "break"
                    except Exception:
                        pass
                if cls == "Listbox":
                    try:
                        cur.yview_scroll(units, "units")
                        return "break"
                    except Exception:
                        pass
                try:
                    cur = cur.master
                except Exception:
                    break
            return

        try:
            self.root.bind_all("<MouseWheel>", _on_wheel, add="+")
            self.root.bind_all("<Button-4>", _on_wheel, add="+")
            self.root.bind_all("<Button-5>", _on_wheel, add="+")
        except Exception:
            pass

    def _styles(self):
        s = ttk.Style()
        s.theme_use('clam')
        # Progress bars — daha qalın, “studio” görünüşü
        s.configure('P.Horizontal.TProgressbar', troughcolor='#050a10', background=self.GN2, thickness=20, borderwidth=0)
        s.configure('R.Horizontal.TProgressbar', troughcolor='#120808', background='#ff7733', thickness=18, borderwidth=0)
        s.configure('C.Horizontal.TProgressbar', troughcolor='#060c14', background=self.AC2, thickness=18, borderwidth=0)
        s.configure('S.Horizontal.TProgressbar', troughcolor='#0a0614', background='#8b5cf6', thickness=18, borderwidth=0)
        s.configure('E.Horizontal.TProgressbar', troughcolor='#05100c', background='#00cc77', thickness=18, borderwidth=0)
        # Video Converter dock — tək üslub (ikinci ttk.Style() Tcl xətası verməsin deyə burada)
        s.configure(
            'ConvDock.Horizontal.TProgressbar',
            troughcolor='#1e293b',
            background='#0ea5e9',
            thickness=22,
            borderwidth=0,
        )
        # Social / Instagram kompakt pəncərələr — tək Style() (video_player / workspace ikinci Style atır)
        try:
            _soc_pb = dict(
                troughcolor="#0a0f18",
                background="#22c55e",
                thickness=16,
                borderwidth=0,
                lightcolor="#4ade80",
                darkcolor="#15803d",
            )
            s.configure("Social.Horizontal.TProgressbar", **_soc_pb)
            s.configure("IG.Horizontal.TProgressbar", **_soc_pb)
        except (tk.TclError, Exception):
            pass
        # Video Converter daxili notebook — ikinci ttk.Style() yaratmadan (Tcl xətası riski)
        try:
            s.configure("Conv.TNotebook", background=self.BG, borderwidth=0)
            s.configure(
                "Conv.TNotebook.Tab",
                background="#0f172a",
                foreground="#94a3b8",
                padding=[10, 5],
                font=("Segoe UI", 9, "bold"),
            )
            s.map(
                "Conv.TNotebook.Tab",
                background=[("selected", "#1e293b"), ("active", "#172033")],
                foreground=[("selected", self.AC), ("active", "#e2e8f0")],
            )
        except (tk.TclError, Exception):
            pass
        # Treeview
        s.configure('T.Treeview',
                     background='#0a101c',
                     foreground=self.FG,
                     fieldbackground='#0a101c',
                     font=('Segoe UI', 11),
                     rowheight=32,
                     borderwidth=0)
        s.configure('T.Treeview.Heading',
                     background='#122038',
                     foreground=self.AC,
                     font=('Segoe UI', 11, 'bold'),
                     relief='flat',
                     padding=[10, 8])
        s.map('T.Treeview',
              background=[('selected', '#153560')],
              foreground=[('selected', '#ffffff')])
        # Notebook — tab “kart” görünüşü
        s.configure('TNotebook', background=self.BG2, borderwidth=0, tabmargins=[2, 4, 0, 0])
        s.configure('TNotebook.Tab',
                     background='#101828',
                     foreground='#5a7a9a',
                     font=('Segoe UI', 11, 'bold'),
                     padding=[20, 10])
        s.map('TNotebook.Tab',
              background=[('selected', '#162440'), ('active', '#142035')],
              foreground=[('selected', self.AC), ('active', '#a8c8e8')])
        # Scrollbars
        s.configure('Vertical.TScrollbar',
                     background='#152838',
                     troughcolor='#060a10',
                     borderwidth=0,
                     arrowsize=11)
        # Scales — EmbeddedVideoPlayer ilə eyni (video_player-da ikinci Style() olmasın)
        s.configure('TScale', background=self.BG, troughcolor='#0f1a2c', sliderlength=14)
        s.configure(
            'Player.Horizontal.TScale',
            background='#070a10',
            troughcolor='#0c1324',
            sliderthickness=12,
            sliderlength=10,
        )

    def _add_player_to_tab(self, frame, tab_name):
        player = EmbeddedVideoPlayer(
            frame,
            on_play_start=self._on_player_play_start,
            on_pfl=self._on_player_pfl,
        )
        self._players[tab_name] = player
        if tab_name == 'social':
            # Quick interaction: click social player (only when not playing) to open layout editor.
            def _maybe_open_editor(_e=None):
                try:
                    if getattr(player, '_playing', False):
                        return
                except Exception:
                    pass
                try:
                    self._sn_open_layout_editor()
                except Exception:
                    pass
            try:
                player.canvas.bind('<Button-1>', _maybe_open_editor)
            except Exception:
                pass
        return player

    def _on_player_play_start(self, active_player):
        """Stop all other players when one starts playing."""
        self._active_player = active_player
        for name, player in self._players.items():
            if player is not active_player:
                try:
                    player.stop()
                except Exception:
                    pass

    def _on_player_pfl(self, active_player, active: bool):
        """Only one PFL across all players; turning one on clears the others."""
        if not active:
            return
        for player in self._players.values():
            if player is not active_player:
                try:
                    player.clear_pfl()
                except Exception:
                    pass

    def _get_active_player(self):
        try:
            idx = self.nb.index(self.nb.select())
            if 0 <= idx < len(self.TAB_PLAYER_KEYS):
                key = self.TAB_PLAYER_KEYS[idx]
                return self._players.get(key)
        except Exception:
            pass
        return None

    def _notify_all_players(self, filepath):
        if not filepath or not os.path.exists(filepath):
            return
        try:
            cap = cv2.VideoCapture(filepath)
            if cap.isOpened():
                fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
                total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                dur = total / fps if fps > 0 else 0
                cap.release()
            else:
                cap.release()
                fps, total, dur = 25.0, 0, 0
        except Exception:
            fps, total, dur = 25.0, 0, 0
        for name, player in self._players.items():
            try:
                if hasattr(player, "preview_file"):
                    player.preview_file(filepath)
                else:
                    player.set_file_info(filepath, fps, total, dur)
            except Exception:
                pass
        try:
            if filepath and hasattr(self, "_ve_schedule_preview_refresh"):
                self.root.after(450, self._ve_schedule_preview_refresh)
        except Exception:
            pass

    def _play_problem_in_active_tab(self, start_time):
        """Load and play file from start_time in the active tab's player."""
        if not self.file:
            return
        player = self._get_active_player()
        if not player:
            return
        player.load(self.file, start_time)
        try:
            if hasattr(player, "apply_problem_playback_mode"):
                player.apply_problem_playback_mode()
        except Exception:
            pass

    def _on_up_arrow(self, event=None):
        player = self._get_active_player()
        if player:
            player.vol_up()
        return "break"

    def _on_down_arrow(self, event=None):
        player = self._get_active_player()
        if player:
            player.vol_down()
        return "break"

    def _on_space(self, event=None):
        fw = self.root.focus_get()
        if fw and fw.winfo_class() in ("Entry", "Text"):
            return
        player = self._get_active_player()
        if player:
            player.toggle_play()
        return "break"

    def _build(self):
        BG = self.BG; BG2 = self.BG2; BG3 = self.BG3; BG4 = self.BG4
        FG = self.FG; FG2 = self.FG2; AC = self.AC; GN = self.GN; RD = self.RD

        # Üst “premium” zolaq: qızılı xətt + cyan
        accent = tk.Frame(self.root, bg=self.BG, height=0)
        accent.pack(fill=tk.X)
        tk.Frame(accent, bg=self.GOLD, height=1).pack(fill=tk.X)
        tk.Frame(accent, bg=self.AC, height=2).pack(fill=tk.X)
        tk.Frame(accent, bg=self.BG, height=1).pack(fill=tk.X)

        # ── HEADER ──────────────────────────────────────────────────────────
        hdr = tk.Frame(self.root, bg=self.HDR_BG, height=88)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Frame(hdr, bg=self.HDR_LINE, height=1).pack(side=tk.BOTTOM, fill=tk.X)

        # Logo
        logo_frame = tk.Frame(hdr, bg=self.HDR_BG)
        logo_frame.pack(side=tk.LEFT, padx=20, pady=8)
        AnimatedLogo(logo_frame, width=300, height=72, bg=self.HDR_BG).pack()

        # Status badge + animated slogan
        mid_frame = tk.Frame(hdr, bg=self.HDR_BG)
        mid_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=12)
        AnimatedSlogan(mid_frame, width=520, height=22, bg=self.HDR_BG).pack(anchor='w', pady=(16, 0))
        self.status_badge = tk.Label(
            mid_frame,
            text="Orvix Lite  |  Ready",
            bg=self.HDR_BG,
            fg='#4a6a8a',
            font=('Segoe UI', 10),
        )
        self.status_badge.pack(anchor='sw', pady=(6, 6))

        # Clock
        clk_frame = tk.Frame(hdr, bg=self.HDR_BG)
        clk_frame.place(relx=1.0, x=-22, y=12, anchor='ne')
        self.time_lbl = tk.Label(
            clk_frame, text="", bg=self.HDR_BG, fg=self.AC,
            font=('Segoe UI', 24, 'bold'),
        )
        self.time_lbl.pack(anchor='e')
        self.date_lbl = tk.Label(
            clk_frame, text="", bg=self.HDR_BG, fg=self.FG2,
            font=('Segoe UI', 10),
        )
        self.date_lbl.pack(anchor='e')
        self._tick()

        # ── FILE BAR ──────────────────────────────────────────────────────
        fb = tk.Frame(
            self.root,
            bg=self.FILE_BAR,
            padx=14,
            pady=8,
            highlightthickness=1,
            highlightbackground=self.BORDER,
        )
        fb.pack(fill=tk.X)

        tk.Label(
            fb,
            text="VIDEO FILE",
            bg=self.FILE_BAR,
            fg=self.AC2,
            font=('Segoe UI', 9, 'bold'),
        ).pack(side=tk.LEFT)
        tk.Frame(fb, bg=self.BORDER, width=1).pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=3)

        self.file_lbl = tk.Label(
            fb,
            text="  No file selected — use Open File",
            bg=self.FILE_BAR,
            fg=self.FG2,
            font=('Segoe UI', 11),
            anchor='w',
        )
        self.file_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

        bc = dict(
            font=('Segoe UI', 10, 'bold'),
            relief=tk.FLAT,
            cursor='hand2',
            padx=14,
            pady=6,
            bd=0,
        )

        self.exp_btn = tk.Button(
            fb,
            text="  Export",
            bg='#152a45',
            fg=FG2,
            command=self._export,
            state=tk.DISABLED,
            activebackground='#1c3550',
            activeforeground=FG,
            **bc,
        )
        self.exp_btn.pack(side=tk.RIGHT, padx=3)

        self.stop_btn = tk.Button(
            fb,
            text="  Stop",
            bg='#7a1c24',
            fg='#ffd0d0',
            command=self._stop,
            state=tk.DISABLED,
            activebackground='#9a2525',
            activeforeground='#ffffff',
            **bc,
        )
        self.stop_btn.pack(side=tk.RIGHT, padx=3)

        self.go_btn = tk.Button(
            fb,
            text="  ANALYZE",
            bg='#0a6b52',
            fg='#ffffff',
            command=self._start_analysis,
            state=tk.DISABLED,
            activebackground='#0a8558',
            activeforeground='#ffffff',
            **bc,
        )
        self.go_btn.pack(side=tk.RIGHT, padx=3)

        tk.Frame(fb, bg=self.BORDER, width=1).pack(side=tk.RIGHT, fill=tk.Y, pady=3, padx=4)

        self.open_btn = tk.Button(
            fb,
            text="  Open File",
            bg='#0a5a8c',
            fg='#ffffff',
            command=self._open_file,
            activebackground='#0a7ab8',
            activeforeground='#ffffff',
            **bc,
        )
        self.open_btn.pack(side=tk.RIGHT, padx=(4, 0))

        # ── PROGRESS BAR ────────────────────────────────────────────────
        pf = tk.Frame(self.root, bg=self.ZONE_PROG)
        pf.pack(fill=tk.X)
        tk.Frame(pf, bg=self.HDR_LINE, height=1).pack(fill=tk.X)
        self.pv = tk.DoubleVar()
        pb_frame = tk.Frame(pf, bg=self.ZONE_PROG, pady=5, padx=12)
        pb_frame.pack(fill=tk.X, side=tk.TOP)
        ttk.Progressbar(
            pb_frame,
            variable=self.pv,
            maximum=100,
            style='P.Horizontal.TProgressbar',
        ).pack(fill=tk.X, side=tk.LEFT, expand=True)
        self.pl = tk.Label(
            pb_frame,
            text="  Ready — load a video file to begin",
            bg=self.ZONE_PROG,
            fg='#5a7a9a',
            font=('Consolas', 10),
            width=58,
            anchor='w',
        )
        self.pl.pack(side=tk.RIGHT, padx=(8, 0))

        # ── STATS BAR ───────────────────────────────────────────────────
        sf = tk.Frame(
            self.root,
            bg=self.ZONE_STAT,
            padx=0,
            pady=0,
            highlightthickness=1,
            highlightbackground=self.BORDER,
        )
        sf.pack(fill=tk.X)
        self.st = {}
        stat_data = [
            ('n', '  0 Problems', '#9aa8b8', self.ZONE_STAT),
            ('c', '  0 Errors', self.RD, '#140a0a'),
            ('h', '  0 Warnings', self.OR, '#140c06'),
            ('m', '  0 Info', self.YL, '#141006'),
            ('v', '  0 Video', self.PR, '#100818'),
            ('a', '  0 Audio', self.AC, '#0a1020'),
            ('t', '  --', self.GN, '#0a140e'),
            ('r', '  --', FG2, '#0a0c12'),
        ]
        for i, (k, t, fg_c, bg_c) in enumerate(stat_data):
            cell = tk.Frame(sf, bg=bg_c, padx=12, pady=5)
            cell.pack(side=tk.LEFT, fill=tk.Y)
            if i > 0:
                tk.Frame(sf, bg=self.SEP, width=1).pack(side=tk.LEFT, fill=tk.Y)
            lbl = tk.Label(cell, text=t, bg=bg_c, fg=fg_c, font=('Segoe UI', 10, 'bold'))
            lbl.pack()
            self.st[k] = lbl

        # ── NOTEBOOK (çərçivəli “kart”) ───────────────────────────────────
        nb_outer = tk.Frame(self.root, bg=self.BORDER, padx=1, pady=1)
        nb_outer.pack(fill=tk.BOTH, expand=True, padx=14, pady=(6, 12))
        nb_host = tk.Frame(nb_outer, bg=self.BG2)
        nb_host.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        nb = ttk.Notebook(nb_host)
        nb.pack(fill=tk.BOTH, expand=True)
        self.nb = nb

        # ========== TAB 1: File Parameters ==========
        t1 = tk.Frame(nb, bg=BG)
        nb.add(t1, text="  File Parameters  ")
        self._add_player_to_tab(t1, 'file_params')
        self.info_text = scrolledtext.ScrolledText(
            t1, bg='#050a12', fg='#80b8d8',
            font=('Consolas', 12), wrap=tk.WORD, padx=18, pady=12)
        self.info_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        for tag, cfg in [
            ('title', {'foreground': '#00cc88', 'font': ('Consolas', 14, 'bold')}),
            ('section', {'foreground': '#009acc', 'font': ('Consolas', 13, 'bold')}),
            ('label', {'foreground': '#2a4050'}),
            ('value', {'foreground': '#c8dcea', 'font': ('Consolas', 12, 'bold')}),
            ('highlight', {'foreground': '#ffd040', 'font': ('Consolas', 12, 'bold')}),
            ('sep', {'foreground': '#0d1a28'}),
            ('path', {'foreground': '#4a7080'}),
            ('video_param', {'foreground': '#00ee99', 'font': ('Consolas', 12, 'bold')}),
            ('audio_param', {'foreground': '#ff9900', 'font': ('Consolas', 12, 'bold')}),
            ('container_param', {'foreground': '#9966ff', 'font': ('Consolas', 12, 'bold')}),
        ]:
            self.info_text.tag_configure(tag, **cfg)
        self.info_text.insert('1.0', '  Load a video file to see detailed parameters.\n', 'label')
        self.info_text.config(state=tk.DISABLED)

        # ========== TAB 2: All Problems ==========
        t2 = tk.Frame(nb, bg=BG)
        nb.add(t2, text="  All Problems  ")
        self._add_player_to_tab(t2, 'all_problems')
        tf = tk.Frame(t2, bg=BG)
        tf.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        cols = ('no', 'sev', 'cat', 'problem', 'start_end', 'dur', 'desc')
        self.tr = ttk.Treeview(tf, columns=cols, show='headings', style='T.Treeview')
        col_cfg = [
            ('no', '#', 44, 'center'), ('sev', 'SEVERITY', 96, 'center'),
            ('cat', 'CATEGORY', 86, 'center'), ('problem', 'PROBLEM', 156, 'w'),
            ('start_end', 'START -> END', 210, 'center'), ('dur', 'DURATION', 86, 'center'),
            ('desc', 'DESCRIPTION', 510, 'w'),
        ]
        for cl, tx, w, a in col_cfg:
            self.tr.heading(cl, text=tx)
            self.tr.column(cl, width=w, minwidth=38, anchor=a)
        sy = ttk.Scrollbar(tf, orient=tk.VERTICAL, command=self.tr.yview)
        sx = ttk.Scrollbar(tf, orient=tk.HORIZONTAL, command=self.tr.xview)
        self.tr.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        sy.pack(side=tk.RIGHT, fill=tk.Y)
        sx.pack(side=tk.BOTTOM, fill=tk.X)
        self.tr.pack(fill=tk.BOTH, expand=True)
        self.tr.tag_configure('error_frozen', background='#004aaa', foreground='#ffffff')
        self.tr.tag_configure('error', background='#aa0000', foreground='#ffffff')
        self.tr.tag_configure('warning', background='#994400', foreground='#ffffff')
        self.tr.tag_configure('info', background='#886600', foreground='#ffffff')
        self.tr.bind('<Double-1>', self._on_problem_dbl_click)
        self.tr.bind('<Left>', lambda e: self._navigate_problems('prev'))
        self.tr.bind('<Right>', lambda e: self._navigate_problems('next'))
        hint = tk.Label(t2,
                        text="Double-click \u2192 play 2s before problem | Left/Right=prev/next | Up/Down=volume | Space=play/pause",
                        bg=self.ZONE_STAT, fg='#6a8aaa', font=('Segoe UI', 10))
        hint.pack(side=tk.BOTTOM, fill=tk.X, padx=4, pady=2)

        # ========== TAB 3: Critical Problems ==========
        t3 = tk.Frame(nb, bg=BG)
        nb.add(t3, text="  Critical Problems  ")
        self._add_player_to_tab(t3, 'critical')
        critical_frame = tk.Frame(t3, bg=BG)
        critical_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        critical_cols = ('no', 'time_range', 'problem', 'desc')
        self.critical_tr = ttk.Treeview(critical_frame, columns=critical_cols, show='headings', style='T.Treeview')
        critical_col_cfg = [
            ('no', '#', 44, 'center'), ('time_range', 'START -> END', 210, 'center'),
            ('problem', 'PROBLEM', 196, 'w'), ('desc', 'DESCRIPTION', 510, 'w'),
        ]
        for cl, tx, w, a in critical_col_cfg:
            self.critical_tr.heading(cl, text=tx)
            self.critical_tr.column(cl, width=w, minwidth=38, anchor=a)
        critical_sy = ttk.Scrollbar(critical_frame, orient=tk.VERTICAL, command=self.critical_tr.yview)
        critical_sx = ttk.Scrollbar(critical_frame, orient=tk.HORIZONTAL, command=self.critical_tr.xview)
        self.critical_tr.configure(yscrollcommand=critical_sy.set, xscrollcommand=critical_sx.set)
        critical_sy.pack(side=tk.RIGHT, fill=tk.Y)
        critical_sx.pack(side=tk.BOTTOM, fill=tk.X)
        self.critical_tr.pack(fill=tk.BOTH, expand=True)
        self.critical_tr.tag_configure('critical', background='#aa0000', foreground='#ffffff')
        self.critical_tr.bind('<Double-1>', self._on_critical_problem_dbl_click)
        # Left/Right navigation in critical problems too
        self.critical_tr.bind('<Left>', lambda e: self._navigate_critical_problems('prev'))
        self.critical_tr.bind('<Right>', lambda e: self._navigate_critical_problems('next'))
        hint3 = tk.Label(
            t3,
            text="Severe issues: freeze >=10 s, black >=3 s, silence >=12 s, audio cut >=0.15 s. "
            "Short glitches/transitions — All Problems. Double-click: 2 s before | Left/Right | Space",
            bg=self.ZONE_STAT,
            fg='#6a8aaa',
            font=('Segoe UI', 10),
            wraplength=920,
            justify=tk.LEFT,
        )
        hint3.pack(side=tk.BOTTOM, fill=tk.X, padx=4, pady=2)
        self._critical_problem_index = -1

        # ========== TAB 4: Problem Dictionary ==========
        t4 = tk.Frame(nb, bg=BG)
        nb.add(t4, text="  Problem Dictionary  ")
        self._add_player_to_tab(t4, 'dict')
        search_frame = tk.Frame(t4, bg=BG2, height=48)
        search_frame.pack(fill=tk.X, padx=10, pady=8)
        search_frame.pack_propagate(False)
        tk.Label(search_frame, text="Search:", bg=BG2, fg=FG,
                 font=('Segoe UI', 10)).pack(side=tk.LEFT, padx=10)
        self.dict_search_var = tk.StringVar()
        self.dict_search_var.trace('w', self._update_dictionary)
        search_entry = tk.Entry(search_frame, textvariable=self.dict_search_var,
                                bg='#0e1e30', fg=FG,
                                font=('Segoe UI', 10), insertbackground=AC,
                                relief=tk.FLAT, bd=5)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10, pady=8)
        dict_frame = tk.Frame(t4, bg=BG)
        dict_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)
        self.dict_listbox = tk.Listbox(dict_frame, bg='#0a1620', fg=FG,
                                       font=('Segoe UI', 11),
                                       selectbackground='#0e3060',
                                       relief=tk.FLAT, bd=4)
        dict_scroll = tk.Scrollbar(dict_frame, orient=tk.VERTICAL, command=self.dict_listbox.yview)
        self.dict_listbox.configure(yscrollcommand=dict_scroll.set)
        dict_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.dict_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        detail_frame = tk.Frame(t4, bg=BG2, height=140)
        detail_frame.pack(fill=tk.X, padx=10, pady=4)
        detail_frame.pack_propagate(False)
        self.dict_detail_text = scrolledtext.ScrolledText(
            detail_frame, bg='#0e1e2e', fg=FG,
            font=('Segoe UI', 10), wrap=tk.WORD,
            padx=10, pady=10, relief=tk.FLAT, bd=4)
        self.dict_detail_text.pack(fill=tk.BOTH, expand=True)
        self.dict_detail_text.tag_configure('title', foreground='#00ee99', font=('Segoe UI', 12, 'bold'))
        self.dict_detail_text.tag_configure('label', foreground='#4a6070')
        self.dict_detail_text.tag_configure('content', foreground='#c8dcea')
        self._update_dictionary()
        self.dict_listbox.bind('<<ListboxSelect>>', self._show_problem_detail)

        # ========== TAB 5: Analysis Log ==========
        t5 = tk.Frame(nb, bg=BG)
        nb.add(t5, text="  Analysis Log  ")
        self._add_player_to_tab(t5, 'log')
        self.lg = scrolledtext.ScrolledText(
            t5, bg='#050a12', fg='#506070',
            font=('Consolas', 10), wrap=tk.WORD, padx=10, pady=8)
        self.lg.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        for tag, clr, bold in [
            ('i', '#009acc', False), ('ok', '#00cc77', False),
            ('w', '#ffcc00', False), ('e', '#ff4444', False),
            ('h', '#7755cc', True), ('ts', '#336655', False),
        ]:
            f = ('Consolas', 10, 'bold') if bold else ('Consolas', 10)
            self.lg.tag_configure(tag, foreground=clr, font=f)

        # ========== TAB 6: Broadcast QC ==========
        t6 = tk.Frame(nb, bg=BG)
        nb.add(t6, text="  Broadcast QC  ")
        self._add_player_to_tab(t6, 'broadcast')
        bcast_canvas_frame = tk.Frame(t6, bg=BG)
        bcast_canvas_frame.pack(fill=tk.BOTH, expand=True)
        bcast_canvas = tk.Canvas(bcast_canvas_frame, bg=BG, highlightthickness=0)
        bcast_vsb = ttk.Scrollbar(bcast_canvas_frame, orient=tk.VERTICAL, command=bcast_canvas.yview)
        bcast_canvas.configure(yscrollcommand=bcast_vsb.set)
        bcast_vsb.pack(side=tk.RIGHT, fill=tk.Y)
        bcast_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        broadcast_frame = tk.Frame(bcast_canvas, bg=BG2, padx=10, pady=10)
        bcast_canvas.create_window((0, 0), window=broadcast_frame, anchor='nw')
        broadcast_frame.bind('<Configure>', lambda e: bcast_canvas.configure(scrollregion=bcast_canvas.bbox('all')))
        tk.Label(broadcast_frame, text="BROADCAST COMPLIANCE REPORT",
                 fg=AC, bg=BG2, font=('Segoe UI', 14, 'bold')).pack(pady=10)
        for sec_title, attr_name, height in [
            ("FILE INFORMATION", 'file_info_text', 8),
            ("VIDEO STREAM", 'video_info_text', 12),
            ("AUDIO STREAM", 'audio_info_text', 10),
            ("CONTAINER & OTHER STREAMS", 'container_info_text', 8),
        ]:
            frm = tk.Frame(broadcast_frame, bg=BG3, padx=15, pady=14)
            frm.pack(fill=tk.X, pady=4)
            tk.Label(frm, text=sec_title, fg=AC, bg=BG3,
                     font=('Segoe UI', 11, 'bold')).pack(anchor='w')
            txt = tk.Text(frm, bg=BG3, fg=FG,
                          font=('Consolas', 10), height=height, relief=tk.FLAT, bd=0)
            txt.pack(fill=tk.X, pady=4)
            setattr(self, attr_name, txt)

        # ========== TAB 7: VIDEO CONVERTER ==========
        t8 = tk.Frame(nb, bg=BG)
        nb.add(t8, text="  Video Converter  ")
        self._add_player_to_tab(t8, 'converter')
        self._build_converter_tab(t8)

        # ========== TAB 8: SOCIAL NETWORK CONVERTER ==========
        t9 = tk.Frame(nb, bg=BG)
        nb.add(t9, text="  Social Network Converter  ")
        self._add_player_to_tab(t9, 'social')
        self._build_social_tab(t9)

        # ========== TAB 9: VIDEO EDITING ==========
        t10 = tk.Frame(nb, bg=BG)
        nb.add(t10, text="  Video Editing  ")
        edit_player = self._add_player_to_tab(t10, 'editing')
        edit_player.set_time_observer(self._on_edit_player_time)
        self._build_editing_tab(t10)

        # ========== TAB 10: VIDEO ENHANCEMENT ==========
        t11 = tk.Frame(nb, bg=BG)
        nb.add(t11, text="  VIDEO ENHANCEMENT  ")
        self._build_video_enhancement_tab(t11)

        self._tab_social_root = t9
        self._tab_editing_root = t10
        self._tab_video_enhancement_root = t11
        self._apply_orvix_pro_tab_locks()

    def _is_orvix_pro_mode(self):
        return bool(getattr(self, "_orvix_pro_mode", False))

    def _apply_orvix_pro_tab_locks(self):
        """When full-feature mode is off, lock Social, Video Editing, and Video Enhancement tabs."""
        if self._is_orvix_pro_mode():
            return
        self._add_orvix_pro_lock_overlay(self._tab_social_root, "Social Network Converter")
        self._add_orvix_pro_lock_overlay(self._tab_editing_root, "Video Editing")
        self._add_orvix_pro_lock_overlay(self._tab_video_enhancement_root, "VIDEO ENHANCEMENT")

    def _add_orvix_pro_lock_overlay(self, parent, title: str):
        overlay = tk.Frame(parent, bg="#070b12", cursor="hand2")
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)

        inner = tk.Frame(overlay, bg="#121a2a", highlightthickness=1, highlightbackground="#4c1d95")
        inner.place(relx=0.5, rely=0.4, anchor="center")
        tk.Label(
            inner,
            text="Full Orvix",
            bg="#121a2a",
            fg="#c4b5fd",
            font=("Segoe UI", 13, "bold"),
        ).pack(pady=(14, 6))
        tk.Label(
            inner,
            text="This section is available only in the full Orvix build.\n\nClick for details.",
            bg="#121a2a",
            fg="#94a3b8",
            font=("Segoe UI", 10),
            justify=tk.CENTER,
            wraplength=380,
        ).pack(padx=22, pady=(0, 14))

        def _on_click(_event=None):
            messagebox.showinfo(
                "Full Orvix",
                f'The "{title}" section and related tools are available only in the full Orvix build.\n\n'
                "Enable ORVIX_PRO=1 or use a full license to unlock.",
                parent=self.root,
            )

        overlay.bind("<Button-1>", _on_click)
        inner.bind("<Button-1>", _on_click)
        for ch in inner.winfo_children():
            ch.bind("<Button-1>", _on_click)

        def _lift(_event=None):
            try:
                overlay.tkraise()
            except Exception:
                pass

        parent.bind("<Configure>", _lift, add="+")
        self.root.after_idle(_lift)

    # ==================== CONVERTER TAB ====================
    def _build_converter_tab(self, parent):
        from orvix.converter_tab import install_converter_ui

        try:
            install_converter_ui(self, parent)
            self._conv_setup_input_trace()
        except Exception as e:
            import traceback

            err = traceback.format_exc()
            try:
                tk.Label(
                    parent,
                    text=f"Video Converter UI failed to load:\n{e}\n\nSee console / log.",
                    bg=self.BG,
                    fg="#f87171",
                    font=("Segoe UI", 10),
                    justify=tk.LEFT,
                    wraplength=560,
                ).pack(anchor="w", padx=12, pady=12)
            except Exception:
                pass
            try:
                print("ORVIX converter_tab error:\n", err)
            except Exception:
                pass

    # ==================== SOCIAL NETWORK TAB ====================
    def _build_social_tab(self, parent):
        from orvix.social_export_panel import ensure_social_export_vars
        from orvix.social_tab import install_social_platform_notebook

        BG = self.BG; BG2 = self.BG2; BG3 = self.BG3; FG = self.FG; AC = self.AC
        ensure_social_export_vars(self)

        tk.Label(
            parent,
            text="SOCIAL NETWORK CONVERTER — pick a platform; convert options are in that workspace window",
            bg=BG,
            fg="#aa66ff",
            font=("Segoe UI", 11, "bold"),
        ).pack(pady=(6, 2))
        tk.Label(
            parent,
            text="Player and log below. Video file and profile — use the platform button to open the workspace (Instagram: Video Convert module).",
            bg=BG,
            fg=self.FG2,
            font=("Segoe UI", 9),
            wraplength=720,
            justify=tk.CENTER,
        ).pack(pady=(0, 4))
        install_social_platform_notebook(
            self,
            parent,
            bg=BG,
            bg3=BG3,
            fg=FG,
            fg2=self.FG2,
            accent="#caa3ff",
        )
        prog_frame = tk.Frame(parent, bg=BG2, padx=10, pady=6)
        prog_frame.pack(fill=tk.X, padx=10, pady=4)
        self.sn_pv = tk.DoubleVar()
        ttk.Progressbar(prog_frame, variable=self.sn_pv, maximum=100,
                         style='S.Horizontal.TProgressbar').pack(fill=tk.X)
        self.sn_status = tk.Label(prog_frame, text="Ready",
                                   bg=BG2, fg=self.FG2, font=('Consolas', 10))
        self.sn_status.pack(fill=tk.X, pady=(3, 0))
        self.sn_log = scrolledtext.ScrolledText(parent, bg='#050a12', fg=self.FG2,
                                                 font=('Consolas', 10), height=4, wrap=tk.WORD)
        self.sn_log.pack(fill=tk.X, padx=10, pady=4)

        # Enable live preview on draft changes.
        self._sn_setup_live_preview_traces()

    # ==================== VIDEO EDITING TAB ====================
    def _build_editing_tab(self, parent):
        BG = self.BG; BG2 = self.BG2; BG3 = self.BG3; FG = self.FG; AC = self.AC

        def entry_row(frame, label, var_name, default=''):
            row = tk.Frame(frame, bg=BG3)
            row.pack(fill=tk.X, pady=1)
            tk.Label(row, text=label, bg=BG3, fg=self.FG2,
                     font=('Segoe UI', 9), width=16, anchor='w').pack(side=tk.LEFT)
            v = tk.StringVar(value=default)
            tk.Entry(row, textvariable=v, bg='#0e1e30', fg=FG,
                     font=('Segoe UI', 9), insertbackground=AC,
                     relief=tk.FLAT, bd=3, width=14).pack(side=tk.LEFT, padx=4)
            setattr(self, var_name, v)

        tk.Label(parent, text="VIDEO EDITING — Trim, Color, Audio, Filters",
                 bg=BG, fg='#00cc88', font=('Segoe UI', 12, 'bold')).pack(pady=(8, 4))
        file_frame = tk.Frame(parent, bg=BG2, padx=15, pady=8)
        file_frame.pack(fill=tk.X, padx=10, pady=4)
        for label, var_name, browse_cmd in [
            ("Input File:", 'edit_input_var', '_edit_browse_input'),
            ("Output File:", 'edit_output_var', '_edit_browse_output'),
        ]:
            row = tk.Frame(file_frame, bg=BG2)
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=label, bg=BG2, fg=FG,
                     font=('Segoe UI', 10, 'bold'), width=12, anchor='w').pack(side=tk.LEFT)
            v = tk.StringVar()
            setattr(self, var_name, v)
            tk.Entry(row, textvariable=v, bg='#0e1e30', fg=FG,
                     font=('Segoe UI', 10), insertbackground=AC,
                     relief=tk.FLAT, bd=3).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            tk.Button(row, text="Browse", bg='#004a7a', fg='#fff',
                      font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, cursor='hand2',
                      padx=10, pady=3,
                      command=getattr(self, browse_cmd)).pack(side=tk.RIGHT)
        tk.Label(parent, text="Output Format:", bg=BG2, fg=self.FG2,
                 font=('Segoe UI', 9)).pack(anchor='w', padx=10)
        self.edit_format = tk.StringVar(value='mp4')
        ttk.Combobox(parent, textvariable=self.edit_format,
                     values=['mp4', 'mkv', 'mov', 'avi'], state='readonly',
                     width=10, font=('Segoe UI', 9)).pack(anchor='w', padx=10, pady=2)

        edit_main = tk.Frame(parent, bg=BG2)
        edit_main.pack(fill=tk.X, padx=10, pady=4)
        left_col = tk.Frame(edit_main, bg=BG3, padx=10, pady=10)
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Label(left_col, text="TIMELINE TRIM", bg=BG3, fg=AC,
                 font=('Segoe UI', 11, 'bold')).pack(anchor='w', pady=(0, 4))
        for lbl, vn, dflt in [
            ("Start Time:", 'edit_start_time', '00:00:00'),
            ("End Time:", 'edit_end_time', ''),
            ("Duration:", 'edit_duration', ''),
        ]:
            entry_row(left_col, lbl, vn, dflt)
        tk.Label(left_col, text="Rotate:", bg=BG3, fg=self.FG2,
                 font=('Segoe UI', 9)).pack(anchor='w', pady=(4, 2))
        self.edit_rotate = tk.StringVar(value='No rotation')
        ttk.Combobox(left_col, textvariable=self.edit_rotate,
                     values=['No rotation', 'Rotate 90 CW', 'Rotate 90 CCW',
                             'Rotate 180', 'Flip Horizontal', 'Flip Vertical', 'Flip Both'],
                     state='readonly', width=16, font=('Segoe UI', 9)).pack(anchor='w', pady=1)
        tk.Label(left_col, text="Speed:", bg=BG3, fg=self.FG2,
                 font=('Segoe UI', 9)).pack(anchor='w', pady=(4, 2))
        self.edit_speed = tk.StringVar(value='1.0 (Normal)')
        ttk.Combobox(left_col, textvariable=self.edit_speed,
                     values=['0.25', '0.5', '0.75', '1.0 (Normal)', '1.25', '1.5', '2.0', '4.0'],
                     state='readonly', width=14, font=('Segoe UI', 9)).pack(anchor='w', pady=1)

        mid_col = tk.Frame(edit_main, bg=BG3, padx=10, pady=10)
        mid_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 0))
        tk.Label(mid_col, text="CROP & SCALE", bg=BG3, fg=AC,
                 font=('Segoe UI', 11, 'bold')).pack(anchor='w', pady=(0, 4))
        for lbl_txt, var_nm, dflt in [
            ("Crop W:", 'edit_crop_w', ''),
            ("Crop H:", 'edit_crop_h', ''),
            ("Crop X offset:", 'edit_crop_x', '0'),
            ("Crop Y offset:", 'edit_crop_y', '0'),
        ]:
            entry_row(mid_col, lbl_txt, var_nm, dflt)
        tk.Label(mid_col, text="Scale/Resize:", bg=BG3, fg=self.FG2,
                 font=('Segoe UI', 9)).pack(anchor='w', pady=(4, 2))
        self.edit_scale = tk.StringVar(value='Original')
        ttk.Combobox(mid_col, textvariable=self.edit_scale,
                     values=['Original', '3840x2160', '1920x1080', '1280x720', '854x480', '640x360'],
                     state='readonly', width=14, font=('Segoe UI', 9)).pack(anchor='w', pady=1)
        tk.Label(mid_col, text="COLOR CORRECTION", bg=BG3, fg='#ffaa00',
                 font=('Segoe UI', 11, 'bold')).pack(anchor='w', pady=(6, 4))
        for lbl_txt, var_nm, fr, to, dflt in [
            ("Brightness:", 'edit_brightness', -2.0, 2.0, 1.0),
            ("Contrast:", 'edit_contrast', -2.0, 2.0, 1.0),
            ("Saturation:", 'edit_saturation', 0.0, 3.0, 1.0),
            ("Gamma:", 'edit_gamma', 0.1, 3.0, 1.0),
        ]:
            row = tk.Frame(mid_col, bg=BG3)
            row.pack(fill=tk.X, pady=1)
            tk.Label(row, text=lbl_txt, bg=BG3, fg=self.FG2,
                     font=('Segoe UI', 9), width=12, anchor='w').pack(side=tk.LEFT)
            v = tk.DoubleVar(value=dflt)
            tk.Scale(row, variable=v, from_=fr, to=to, resolution=0.1,
                     orient=tk.HORIZONTAL, bg=BG3, fg=FG,
                     highlightthickness=0, troughcolor='#0e1e30', length=100).pack(side=tk.LEFT)
            tk.Label(row, textvariable=v, bg=BG3, fg=AC,
                     font=('Segoe UI', 9), width=4).pack(side=tk.LEFT)
            setattr(self, var_nm, v)

        right_col = tk.Frame(edit_main, bg=BG3, padx=10, pady=10)
        right_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 0))
        tk.Label(right_col, text="AUDIO EDITING", bg=BG3, fg='#00aaff',
                 font=('Segoe UI', 11, 'bold')).pack(anchor='w', pady=(0, 4))
        row_v = tk.Frame(right_col, bg=BG3)
        row_v.pack(fill=tk.X, pady=2)
        tk.Label(row_v, text="Volume:", bg=BG3, fg=self.FG2,
                 font=('Segoe UI', 9), width=12, anchor='w').pack(side=tk.LEFT)
        self.edit_volume = tk.DoubleVar(value=1.0)
        tk.Scale(row_v, variable=self.edit_volume, from_=0.0, to=4.0, resolution=0.05,
                 orient=tk.HORIZONTAL, bg=BG3, fg=FG,
                 highlightthickness=0, troughcolor='#0e1e30', length=100).pack(side=tk.LEFT)
        tk.Label(row_v, textvariable=self.edit_volume, bg=BG3, fg=AC,
                 font=('Segoe UI', 9), width=4).pack(side=tk.LEFT)
        tk.Label(right_col, text="Audio Filter:", bg=BG3, fg=self.FG2,
                 font=('Segoe UI', 9)).pack(anchor='w', pady=(4, 1))
        self.edit_audio_filter = tk.StringVar(value='None')
        ttk.Combobox(right_col, textvariable=self.edit_audio_filter,
                     values=['None', 'loudnorm', 'dynaudnorm', 'highpass f=200', 'lowpass f=8000'],
                     state='readonly', width=22, font=('Segoe UI', 9)).pack(anchor='w', pady=1)
        tk.Label(right_col, text="VIDEO FILTERS", bg=BG3, fg='#00aaff',
                 font=('Segoe UI', 11, 'bold')).pack(anchor='w', pady=(6, 4))
        for txt, var_nm in [
            ("Deinterlace (yadif)", 'edit_deinterlace'),
            ("Denoise (hqdn3d)", 'edit_denoise'),
            ("Sharpen (unsharp)", 'edit_sharpen'),
            ("Grayscale", 'edit_grayscale'),
            ("Vertical Flip", 'edit_vflip'),
            ("Horizontal Flip", 'edit_hflip'),
        ]:
            v = tk.BooleanVar(value=False)
            tk.Checkbutton(right_col, text=txt, variable=v,
                           bg=BG3, fg=FG, selectcolor='#0a1420',
                           activebackground=BG3,
                           font=('Segoe UI', 9)).pack(anchor='w')
            setattr(self, var_nm, v)

        tl_wrap = tk.Frame(parent, bg=BG3, padx=10, pady=8)
        tl_wrap.pack(fill=tk.X, padx=10, pady=(2, 3))
        tl_hdr = tk.Frame(tl_wrap, bg=BG3)
        tl_hdr.pack(fill=tk.X)
        tk.Label(tl_hdr, text="TIMELINE (LIVE LINKED WITH RIGHT PLAYER)",
                 bg=BG3, fg='#66d0ff', font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT)
        self._timeline_status_var = tk.StringVar(value="No clip loaded.")
        tk.Label(tl_hdr, textvariable=self._timeline_status_var,
                 bg=BG3, fg=self.FG2, font=('Consolas', 10)).pack(side=tk.RIGHT)

        tl_btns = tk.Frame(tl_wrap, bg=BG3)
        tl_btns.pack(fill=tk.X, pady=(4, 4))
        tbc = dict(font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, cursor='hand2', padx=8, pady=3, bd=0)
        tk.Button(tl_btns, text="Set In @ Playhead", bg='#12324a', fg='#d8f0ff',
                  command=self._timeline_set_in_at_playhead, activebackground='#1a4767', **tbc).pack(side=tk.LEFT, padx=(0, 3))
        tk.Button(tl_btns, text="Set Out @ Playhead", bg='#12324a', fg='#d8f0ff',
                  command=self._timeline_set_out_at_playhead, activebackground='#1a4767', **tbc).pack(side=tk.LEFT, padx=3)
        tk.Button(tl_btns, text="Duplicate Clip", bg='#2f235c', fg='#e7deff',
                  command=self._timeline_duplicate_clip, activebackground='#45338a', **tbc).pack(side=tk.LEFT, padx=3)
        tk.Button(tl_btns, text="Reset Timeline", bg='#3a1f1f', fg='#ffd8d8',
                  command=self._timeline_reset_from_input, activebackground='#5a2b2b', **tbc).pack(side=tk.LEFT, padx=3)
        tk.Label(tl_btns, text="Transition:", bg=BG3, fg=self.FG2, font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=(10, 3))
        self.edit_transition = tk.StringVar(value='None')
        ttk.Combobox(tl_btns, textvariable=self.edit_transition,
                     values=['None', 'Cross Dissolve'], state='readonly',
                     width=14, font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=2)
        tk.Label(tl_btns, text="Dur(s):", bg=BG3, fg=self.FG2, font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=(6, 2))
        self.edit_transition_dur = tk.StringVar(value='0.5')
        tk.Entry(tl_btns, textvariable=self.edit_transition_dur, width=5,
                 bg='#0e1e30', fg=FG, insertbackground=AC, relief=tk.FLAT, bd=2).pack(side=tk.LEFT, padx=(0, 3))

        self._timeline_canvas = tk.Canvas(
            tl_wrap, bg='#071322', height=124, highlightthickness=1, highlightbackground='#18304d'
        )
        self._timeline_canvas.pack(fill=tk.X)
        self._timeline_canvas.bind('<Button-1>', self._timeline_on_press)
        self._timeline_canvas.bind('<B1-Motion>', self._timeline_on_drag)
        self._timeline_canvas.bind('<ButtonRelease-1>', self._timeline_on_release)
        self._timeline_canvas.bind('<Configure>', lambda e: self._timeline_redraw())

        prog_frame = tk.Frame(parent, bg=BG2, padx=10, pady=5)
        prog_frame.pack(fill=tk.X, padx=10, pady=3)
        self.edit_pv = tk.DoubleVar()
        ttk.Progressbar(prog_frame, variable=self.edit_pv, maximum=100,
                         style='E.Horizontal.TProgressbar').pack(fill=tk.X)
        self.edit_status = tk.Label(prog_frame, text="Ready",
                                     bg=BG2, fg=self.FG2, font=('Consolas', 10))
        self.edit_status.pack(fill=tk.X, pady=(2, 0))
        self.edit_log = scrolledtext.ScrolledText(parent, bg='#050a12', fg=self.FG2,
                                                   font=('Consolas', 10), height=4, wrap=tk.WORD)
        self.edit_log.pack(fill=tk.X, padx=10, pady=3)
        btn_frame = tk.Frame(parent, bg=BG, pady=5)
        btn_frame.pack(fill=tk.X, padx=10)
        bbc = dict(font=('Segoe UI', 9, 'bold'), relief=tk.FLAT,
                   cursor='hand2', padx=12, pady=5, bd=0)
        tk.Button(btn_frame, text="  Apply Edit", bg='#004a28', fg='#ffffff',
                  command=self._start_edit,
                  activebackground='#006636', **bbc).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="  Stop", bg='#6a1515', fg='#ffaaaa',
                  command=self._stop_edit,
                  activebackground='#8a2020', **bbc).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="  Save As", bg='#004a7a', fg='#ffffff',
                  command=self._edit_save_output,
                  activebackground='#006096', **bbc).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="  Export Log", bg='#0e1e30', fg=self.FG2,
                  command=self._edit_export_log,
                  activebackground='#162840', **bbc).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="  Use Main File", bg='#121e34', fg='#7a9ab8',
                  command=self._edit_use_main_file,
                  activebackground='#1a2a44', **bbc).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="  Reset All", bg='#101820', fg=self.FG2,
                  command=self._edit_reset,
                  activebackground='#182030', **bbc).pack(side=tk.LEFT, padx=2)
        self._timeline_reset_from_input()

    def _build_video_enhancement_tab(self, parent):
        """VIDEO ENHANCEMENT / RESTORATION — FFmpeg filter chain + export."""
        BG = self.BG
        BG2 = self.BG2
        BG3 = self.BG3
        FG = self.FG
        self._ve_vars = {}
        self._ve_buttons = {}
        ve_font = ("Segoe UI", 8)
        hdr_font = ("Segoe UI", 9, "bold")

        tk.Label(
            parent,
            text="VIDEO ENHANCEMENT / RESTORATION",
            bg=BG,
            fg="#7dd3fc",
            font=("Segoe UI", 12, "bold"),
        ).pack(pady=(6, 2))
        tk.Label(
            parent,
            text="Use a preset or toggle individual processing options. Below: SOURCE (MAIN) | FILTERED preview (FFmpeg pipeline).",
            bg=BG,
            fg=self.FG2,
            font=("Segoe UI", 8),
            wraplength=920,
            justify=tk.CENTER,
        ).pack(pady=(0, 4))

        preset_fr = tk.Frame(parent, bg=BG2, padx=10, pady=8)
        preset_fr.pack(fill=tk.X, padx=8, pady=(0, 4))
        tk.Label(
            preset_fr,
            text="Preset:",
            bg=BG2,
            fg=FG,
            font=("Segoe UI", 9, "bold"),
        ).pack(side=tk.LEFT, padx=(0, 8))
        pbc = dict(
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            cursor="hand2",
            padx=12,
            pady=6,
            bd=0,
        )
        for txt, pid, bg_c, fg_c in [
            ("AUTO", "auto", "#0369a1", "#f0f9ff"),
            ("Broadcast", "broadcast", "#14532d", "#dcfce7"),
            ("Film", "film", "#713f12", "#fef3c7"),
            ("Sport", "sport", "#991b1b", "#fee2e2"),
            ("Social", "social", "#5b21b6", "#ede9fe"),
        ]:
            tk.Button(
                preset_fr,
                text=txt,
                bg=bg_c,
                fg=fg_c,
                activebackground=bg_c,
                activeforeground=fg_c,
                command=lambda p=pid: self._ve_apply_preset(p),
                **pbc,
            ).pack(side=tk.LEFT, padx=3)

        io_fr = tk.Frame(parent, bg=BG2, padx=8, pady=6)
        io_fr.pack(fill=tk.X, padx=8, pady=2)
        self.ve_input_var = tk.StringVar(value="")
        self.ve_output_var = tk.StringVar(value="")
        r1 = tk.Frame(io_fr, bg=BG2)
        r1.pack(fill=tk.X, pady=1)
        tk.Label(r1, text="Input:", bg=BG2, fg=FG, font=("Segoe UI", 9), width=8, anchor="w").pack(side=tk.LEFT)
        tk.Entry(
            r1,
            textvariable=self.ve_input_var,
            bg="#0e1e30",
            fg=FG,
            font=("Segoe UI", 9),
            insertbackground=self.AC,
            relief=tk.FLAT,
            bd=2,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        tk.Button(
            r1,
            text="Browse",
            bg="#004a7a",
            fg="#fff",
            font=("Segoe UI", 8),
            relief=tk.FLAT,
            cursor="hand2",
            padx=8,
            pady=2,
            command=self._ve_browse_input,
        ).pack(side=tk.LEFT)
        r2 = tk.Frame(io_fr, bg=BG2)
        r2.pack(fill=tk.X, pady=1)
        tk.Label(r2, text="Output:", bg=BG2, fg=FG, font=("Segoe UI", 9), width=8, anchor="w").pack(side=tk.LEFT)
        tk.Entry(
            r2,
            textvariable=self.ve_output_var,
            bg="#0e1e30",
            fg=FG,
            font=("Segoe UI", 9),
            insertbackground=self.AC,
            relief=tk.FLAT,
            bd=2,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        tk.Button(
            r2,
            text="Browse",
            bg="#004a7a",
            fg="#fff",
            font=("Segoe UI", 8),
            relief=tk.FLAT,
            cursor="hand2",
            padx=8,
            pady=2,
            command=self._ve_browse_output,
        ).pack(side=tk.LEFT)

        ve_prog = tk.Frame(parent, bg=BG2, padx=10, pady=4)
        ve_prog.pack(fill=tk.X, padx=8, pady=2)
        self.ve_pv = tk.DoubleVar(value=0.0)
        ttk.Progressbar(ve_prog, variable=self.ve_pv, maximum=100, style="E.Horizontal.TProgressbar").pack(
            fill=tk.X
        )
        self.ve_status = tk.Label(
            ve_prog, text="Ready", bg=BG2, fg=self.FG2, font=("Consolas", 9)
        )
        self.ve_status.pack(fill=tk.X, pady=(3, 0))

        # Fixed height so scroll does not collapse the dual-player area
        dual_outer = tk.Frame(parent, bg=BG, height=640)
        dual_outer.pack(fill=tk.X, padx=6, pady=(4, 2))
        dual_outer.pack_propagate(False)
        pw = tk.PanedWindow(
            dual_outer,
            orient=tk.HORIZONTAL,
            sashwidth=6,
            bg=BG,
            sashrelief=tk.RAISED,
        )
        pw.pack(fill=tk.BOTH, expand=True)
        left_col = tk.Frame(pw, bg=BG)
        right_col = tk.Frame(pw, bg=BG)
        try:
            pw.add(left_col, minsize=320, stretch="always")
            pw.add(right_col, minsize=320, stretch="always")
        except tk.TclError:
            pw.add(left_col, minsize=320)
            pw.add(right_col, minsize=320)

        tk.Label(
            left_col,
            text="MAIN — source (reference)",
            bg=BG,
            fg="#6ee7ff",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", padx=2, pady=(0, 2))
        wrap_m = tk.Frame(left_col, bg=BG)
        wrap_m.pack(fill=tk.BOTH, expand=True)
        self._ve_player_main = EmbeddedVideoPlayer(
            wrap_m,
            on_play_start=self._on_player_play_start,
            on_pfl=self._on_player_pfl,
            panel_width=410,
            video_canvas_height=200,
        )
        self._players["video_enhancement"] = self._ve_player_main
        try:
            self._ve_player_main.set_preview_badge(" MAIN")
        except Exception:
            pass
        self._ve_player_main.set_time_observer(self._ve_main_time_observer)

        tk.Label(
            right_col,
            text="FILTER — processed (FFmpeg preview)",
            bg=BG,
            fg="#c4b5fd",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", padx=2, pady=(0, 2))
        wrap_p = tk.Frame(right_col, bg=BG)
        wrap_p.pack(fill=tk.BOTH, expand=True)
        self._ve_player_preview = EmbeddedVideoPlayer(
            wrap_p,
            on_play_start=self._on_player_play_start,
            on_pfl=self._on_player_pfl,
            panel_width=410,
            video_canvas_height=200,
        )
        try:
            self._ve_player_preview.set_preview_badge(" FILTER")
        except Exception:
            pass

        ve_sync_row = tk.Frame(right_col, bg=BG)
        ve_sync_row.pack(fill=tk.X, pady=(2, 0))
        self._ve_preview_sync_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            ve_sync_row,
            text="Sync seek (FILTER follows MAIN timeline)",
            variable=self._ve_preview_sync_var,
            bg=BG,
            fg=self.FG2,
            selectcolor="#0a1420",
            activebackground=BG,
            font=("Segoe UI", 8),
        ).pack(side=tk.LEFT)
        tk.Button(
            ve_sync_row,
            text="Refresh preview",
            bg="#3730a3",
            fg="#e0e7ff",
            font=("Segoe UI", 8, "bold"),
            relief=tk.FLAT,
            cursor="hand2",
            padx=8,
            pady=2,
            command=self._ve_force_preview_refresh,
        ).pack(side=tk.RIGHT, padx=4)

        scroll_host = tk.Frame(parent, bg=BG)
        scroll_host.pack(fill=tk.BOTH, expand=True, padx=4, pady=2)
        ve_canvas = tk.Canvas(scroll_host, bg=BG, highlightthickness=0)
        ve_vsb = ttk.Scrollbar(scroll_host, orient=tk.VERTICAL, command=ve_canvas.yview)
        ve_canvas.configure(yscrollcommand=ve_vsb.set)
        ve_vsb.pack(side=tk.RIGHT, fill=tk.Y)
        ve_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        inner = tk.Frame(ve_canvas, bg=BG)

        def _ve_inner_width(event):
            ve_canvas.itemconfigure(ve_win, width=event.width)

        ve_win = ve_canvas.create_window((0, 0), window=inner, anchor="nw")

        def _ve_scrollregion(_event=None):
            ve_canvas.configure(scrollregion=ve_canvas.bbox("all"))

        inner.bind("<Configure>", lambda e: (_ve_scrollregion(),))

        ve_canvas.bind("<Configure>", _ve_inner_width)

        def _ve_add_section(title, pairs, extra_after=None):
            sec = tk.Frame(inner, bg=BG3, padx=8, pady=5)
            sec.pack(fill=tk.X, padx=4, pady=3)
            tk.Label(sec, text=title, bg=BG3, fg="#a5f3fc", font=hdr_font).pack(anchor="w", pady=(0, 3))
            g = tk.Frame(sec, bg=BG3)
            g.pack(fill=tk.X)
            col, row = 0, 0
            for label, key in pairs:
                v = tk.BooleanVar(value=False)
                self._ve_vars[key] = v
                btn = tk.Button(
                    g,
                    text=label,
                    command=lambda k=key: self._ve_toggle_key(k),
                    font=ve_font,
                    relief=tk.FLAT,
                    cursor="hand2",
                    padx=6,
                    pady=3,
                    bd=0,
                    anchor="w",
                    wraplength=118,
                    justify=tk.LEFT,
                )
                btn.grid(row=row, column=col, sticky="ew", padx=3, pady=2)
                self._ve_buttons[key] = btn
                self._ve_style_ve_button(key)
                col += 1
                if col >= 3:
                    col = 0
                    row += 1
            for c in range(3):
                g.grid_columnconfigure(c, weight=1)
            if extra_after:
                extra_after(sec)

        _ve_add_section(
            "Resolution & Upscale",
            [
                ("Resolution change", "ve_res_change"),
                ("AI Upscale", "ve_ai_upscale"),
                ("Lanczos Upscale", "ve_lanczos"),
                ("Bicubic Upscale", "ve_bicubic"),
                ("Super Resolution", "ve_super_res"),
                ("Aspect ratio correction", "ve_aspect_fix"),
                ("Pixel resize", "ve_pixel_resize"),
            ],
        )
        _ve_add_section(
            "Color Correction",
            [
                ("Brightness", "ve_brightness"),
                ("Contrast", "ve_contrast"),
                ("Saturation", "ve_saturation"),
                ("Gamma", "ve_gamma"),
                ("Exposure", "ve_exposure"),
                ("Hue", "ve_hue"),
                ("White balance", "ve_wb"),
                ("Temperature", "ve_temp"),
                ("Tint", "ve_tint"),
                ("Auto color correction", "ve_auto_color"),
                ("Color restore", "ve_color_restore"),
                ("LUT (.cube)", "ve_lut_enable"),
                ("Color grading", "ve_color_grading"),
            ],
            extra_after=lambda sec: (
                self._ve_lut_row(sec, BG3, FG, ve_font),
            ),
        )
        _ve_add_section(
            "HDR Processing",
            [
                ("HDR detect", "ve_hdr_detect"),
                ("HDR convert", "ve_hdr_convert"),
                ("SDR → HDR tone mapping", "ve_sdr_to_hdr_tm"),
                ("HDR → SDR tone mapping", "ve_hdr_to_sdr_tm"),
                ("HDR10 support", "ve_hdr10"),
                ("HLG support", "ve_hlg"),
                ("Dolby Vision metadata detect", "ve_dolby_vision"),
            ],
        )
        _ve_add_section(
            "Noise Reduction",
            [
                ("Video denoise", "ve_vid_denoise"),
                ("Temporal denoise", "ve_temporal_denoise"),
                ("Spatial denoise", "ve_spatial_denoise"),
                ("3D denoise", "ve_denoise_3d"),
                ("Film grain removal", "ve_film_grain"),
                ("Analog noise reduction", "ve_analog_noise"),
                ("VHS noise removal", "ve_vhs_noise"),
            ],
        )
        _ve_add_section(
            "Sharpen & Detail",
            [
                ("Sharpen", "ve_sharpen"),
                ("Edge enhance", "ve_edge_enhance"),
                ("Detail enhance", "ve_detail_enhance"),
                ("Adaptive sharpen", "ve_adaptive_sharpen"),
                ("Clarity boost", "ve_clarity"),
                ("Texture restore", "ve_texture_restore"),
            ],
        )
        _ve_add_section(
            "Frame Processing",
            [
                ("Frame interpolation", "ve_frame_interp"),
                ("FPS increase", "ve_fps_increase"),
                ("Motion interpolation", "ve_motion_interp"),
                ("Optical flow interpolation", "ve_optical_flow"),
                ("Frame blending", "ve_frame_blend"),
            ],
        )
        _ve_add_section(
            "Deinterlace",
            [
                ("Auto deinterlace", "ve_auto_deint"),
                ("Yadif", "ve_yadif"),
                ("BWDIF", "ve_bwdif"),
                ("QTGMC", "ve_qtgmc"),
            ],
        )
        _ve_add_section(
            "Stabilization",
            [
                ("Video stabilization", "ve_vid_stab"),
                ("Motion stabilization", "ve_motion_stab"),
                ("Camera shake reduction", "ve_shake_reduce"),
                ("Warp stabilization", "ve_warp_stab"),
            ],
        )
        _ve_add_section(
            "Artifact Removal",
            [
                ("Compression artifact removal", "ve_comp_artifact"),
                ("Block artifact reduction", "ve_block_artifact"),
                ("Ringing artifact removal", "ve_ringing"),
                ("Banding reduction", "ve_banding"),
            ],
        )
        _ve_add_section(
            "Analog Video Restore",
            [
                ("VHS restore", "ve_vhs_restore"),
                ("Tape damage correction", "ve_tape_damage"),
                ("Line flicker removal", "ve_line_flicker"),
                ("Dropout repair", "ve_dropout"),
                ("Scan line correction", "ve_scan_line"),
            ],
        )
        _ve_add_section(
            "Advanced Enhancement",
            [
                ("AI video enhancement", "ve_ai_video"),
                ("AI detail reconstruction", "ve_ai_detail"),
                ("AI face enhancement", "ve_ai_face"),
                ("AI object sharpening", "ve_ai_object"),
            ],
        )

        btn_row = tk.Frame(parent, bg=BG, pady=4)
        btn_row.pack(fill=tk.X, padx=8)
        bkw = dict(font=("Segoe UI", 9, "bold"), relief=tk.FLAT, cursor="hand2", padx=10, pady=4, bd=0)
        tk.Button(
            btn_row,
            text="Process & export",
            bg="#0e7490",
            fg="#ecfeff",
            command=self._ve_start_encode,
            activebackground="#155e75",
            **bkw,
        ).pack(side=tk.LEFT, padx=2)
        tk.Button(
            btn_row,
            text="Stop",
            bg="#6a1515",
            fg="#ffaaaa",
            command=self._ve_stop_encode,
            activebackground="#8a2020",
            **bkw,
        ).pack(side=tk.LEFT, padx=2)
        tk.Button(
            btn_row,
            text="Reset all",
            bg="#1e293b",
            fg=self.FG2,
            command=self._ve_reset_all,
            activebackground="#334155",
            **bkw,
        ).pack(side=tk.LEFT, padx=2)
        tk.Button(
            btn_row,
            text="Use main file",
            bg="#121e34",
            fg="#7a9ab8",
            command=self._ve_use_main_file,
            activebackground="#1a2a44",
            **bkw,
        ).pack(side=tk.LEFT, padx=2)

        self.ve_log = scrolledtext.ScrolledText(
            parent, bg="#050a12", fg=self.FG2, font=("Consolas", 9), height=4, wrap=tk.WORD
        )
        self.ve_log.pack(fill=tk.X, padx=8, pady=(0, 6))
        self.ve_log.insert(
            "1.0",
            "VIDEO ENHANCEMENT — FFmpeg ready. Select processing options and set output path.\n",
        )
        self.ve_log.config(state=tk.DISABLED)

    def _ve_lut_row(self, sec, BG3, FG, ve_font):
        row = tk.Frame(sec, bg=BG3)
        row.pack(fill=tk.X, pady=(4, 0))
        tk.Label(row, text="LUT path:", bg=BG3, fg=self.FG2, font=ve_font).pack(side=tk.LEFT)
        self.ve_lut_path = tk.StringVar(value="")
        tk.Entry(
            row,
            textvariable=self.ve_lut_path,
            bg="#0e1e30",
            fg=FG,
            font=ve_font,
            insertbackground=self.AC,
            relief=tk.FLAT,
            bd=2,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        tk.Button(
            row,
            text="Browse",
            bg="#004a7a",
            fg="#fff",
            font=ve_font,
            relief=tk.FLAT,
            cursor="hand2",
            padx=8,
            pady=2,
            command=self._ve_browse_lut,
        ).pack(side=tk.LEFT)

    def _ve_browse_lut(self):
        p = filedialog.askopenfilename(
            title="Select .cube LUT",
            filetypes=[("Cube LUT", "*.cube"), ("All files", "*.*")],
            parent=self.root,
        )
        if p and hasattr(self, "ve_lut_path"):
            self.ve_lut_path.set(p)
            self._ve_schedule_preview_refresh()

    def _ve_style_ve_button(self, key):
        btn = self._ve_buttons.get(key)
        if not btn or not self._ve_vars.get(key):
            return
        on = bool(self._ve_vars[key].get())
        if on:
            btn.config(
                bg="#0e7490",
                fg="#ecfeff",
                activebackground="#155e75",
                activeforeground="#ecfeff",
            )
        else:
            btn.config(
                bg="#1e293b",
                fg="#94a3b8",
                activebackground="#334155",
                activeforeground="#e2e8f0",
            )

    def _ve_toggle_key(self, key):
        if not self._ve_vars.get(key):
            return
        self._ve_vars[key].set(not self._ve_vars[key].get())
        self._ve_style_ve_button(key)
        self._ve_schedule_preview_refresh()

    def _ve_apply_preset(self, preset_key: str):
        """Apply a named preset: clear all flags, then enable the preset's filter keys."""
        prof = getattr(type(self), "VE_PRESET_PROFILES", None) or {}
        keys = prof.get(preset_key)
        if not keys or not getattr(self, "_ve_vars", None):
            return
        for k in self._ve_vars:
            try:
                self._ve_vars[k].set(False)
            except Exception:
                pass
        for k in keys:
            if k in self._ve_vars:
                self._ve_vars[k].set(True)
        for k in list(self._ve_buttons.keys()):
            self._ve_style_ve_button(k)
        self._ve_log_line(f'Preset "{preset_key}": {len(keys)} options enabled.')
        self._ve_schedule_preview_refresh()

    def _ve_schedule_preview_refresh(self):
        if not hasattr(self, "root"):
            return
        if self._ve_preview_after_id:
            try:
                self.root.after_cancel(self._ve_preview_after_id)
            except Exception:
                pass
            self._ve_preview_after_id = None
        self._ve_preview_after_id = self.root.after(450, self._ve_run_preview_job)

    def _ve_force_preview_refresh(self):
        if self._ve_preview_after_id:
            try:
                self.root.after_cancel(self._ve_preview_after_id)
            except Exception:
                pass
            self._ve_preview_after_id = None
        self._ve_run_preview_job()

    def _ve_main_time_observer(self, cur_t, dur_t):
        if not getattr(self, "_ve_preview_sync_var", None) or not self._ve_preview_sync_var.get():
            return
        pv = getattr(self, "_ve_player_preview", None)
        if not pv or not getattr(pv, "_filepath", None):
            return
        try:
            ss = float(getattr(self, "_ve_preview_ss", 0) or 0)
            seg = float(getattr(self, "_ve_preview_seg_dur", 15) or 15)
        except Exception:
            return
        now = time.time()
        if now - getattr(self, "_ve_last_sync_ts", 0) < 0.18:
            return
        self._ve_last_sync_ts = now
        local = float(cur_t) - ss
        if local < -0.05 or local > seg + 0.2:
            return
        try:
            d = float(getattr(pv, "_duration", 0) or 0)
            pv.seek(max(0.0, min(local, d)))
        except Exception:
            pass

    def _ve_run_preview_job(self):
        self._ve_preview_after_id = None
        if self._ve_preview_busy:
            return
        inp = (self.ve_input_var.get().strip() if hasattr(self, "ve_input_var") else "") or (
            getattr(self, "file", None) or ""
        )
        if not inp or not os.path.isfile(inp):
            return
        if not ffmpeg_mgr.ffmpeg_path:
            self._ve_log_line("Preview: FFmpeg not found.")
            return
        lut = (self.ve_lut_path.get() or "").strip() if hasattr(self, "ve_lut_path") else ""
        flags = collect_ve_flags_from_vars(self._ve_vars)
        vf, warns = build_ve_video_filter(flags, lut)
        if not vf.strip():
            self.root.after(0, lambda p=inp: self._ve_load_preview_same_as_main(p))
            return
        self._ve_preview_busy = True
        try:
            self.ve_status.config(text="Building preview…")
        except Exception:
            pass
        main = getattr(self, "_ve_player_main", None)
        try:
            ss = float(getattr(main, "_current_time", 0) or 0)
        except Exception:
            ss = 0.0
        seg = 14.0
        warn_copy = list(warns) if warns else []

        def work():
            out = None
            try:
                if self._ve_preview_temp and os.path.isfile(self._ve_preview_temp):
                    try:
                        os.remove(self._ve_preview_temp)
                    except Exception:
                        pass
                fd, out = tempfile.mkstemp(suffix=".mp4", prefix="orvix_ve_prev_")
                os.close(fd)
                _caps = getattr(ffmpeg_mgr, "cuda_caps", None)
                cmd = (
                    [ffmpeg_mgr.ffmpeg_path, "-y"]
                    + hwaccel_cuda_prefix(_caps)
                    + [
                        "-ss",
                        f"{max(0.0, ss):.3f}",
                        "-i",
                        inp,
                        "-vf",
                        vf,
                        "-t",
                        f"{seg:.2f}",
                    ]
                    + ve_preview_video_args(_caps)
                    + [
                        "-movflags",
                        "+faststart",
                        out,
                    ]
                )
                si = ffmpeg_mgr._get_startupinfo()
                r = subprocess.run(cmd, capture_output=True, text=True, startupinfo=si)
                if r.returncode != 0:
                    err = (r.stderr or r.stdout or "")[-900:]
                    self.root.after(
                        0,
                        lambda e=err: self._ve_log_line(f"Preview FFmpeg error: {e}"),
                    )
                    return
                self._ve_preview_temp = out
                self.root.after(
                    0,
                    lambda p=out, s=ss, g=seg, w=warn_copy: self._ve_on_preview_ready(p, s, g, w),
                )
            except Exception as e:
                self.root.after(0, lambda: self._ve_log_line(f"Preview: {e}"))
            finally:
                self._ve_preview_busy = False

        threading.Thread(target=work, daemon=True).start()

    def _ve_on_preview_ready(self, path, ss, seg, warns):
        self._ve_preview_ss = ss
        self._ve_preview_seg_dur = seg
        pv = getattr(self, "_ve_player_preview", None)
        if pv:
            try:
                pv.load(path, 0.0)
                pv.set_preview_badge(" FILTER")
            except Exception:
                try:
                    pv.preview_file(path)
                except Exception:
                    pass
        for w in warns or []:
            self._ve_log_line(f"[preview] {w}")
        try:
            self.ve_status.config(text="Preview ready — compare with MAIN")
        except Exception:
            pass

    def _ve_load_preview_same_as_main(self, inp):
        pv = getattr(self, "_ve_player_preview", None)
        if not pv:
            return
        try:
            pv.preview_file(inp)
            pv.set_preview_badge(" passthrough")
        except Exception:
            pass
        try:
            self.ve_status.config(text="No filter chain — right panel shows source preview")
        except Exception:
            pass

    def _ve_reset_all(self):
        if not getattr(self, "_ve_vars", None):
            return
        for v in self._ve_vars.values():
            try:
                v.set(False)
            except Exception:
                pass
        if hasattr(self, "ve_lut_path"):
            self.ve_lut_path.set("")
        for key in list(self._ve_buttons.keys()):
            self._ve_style_ve_button(key)
        self._ve_schedule_preview_refresh()

    def _ve_use_main_file(self):
        fp = getattr(self, "file", None) or ""
        if not fp or not os.path.isfile(fp):
            messagebox.showinfo(
                "VIDEO ENHANCEMENT",
                "No main file loaded.",
                parent=self.root,
            )
            return
        if hasattr(self, "ve_input_var"):
            self.ve_input_var.set(fp)
        pl = self._players.get("video_enhancement")
        if pl:
            try:
                pl.load(fp, 0)
            except Exception:
                try:
                    pl.preview_file(fp)
                except Exception:
                    pass
        self._ve_log_line(f"Main file → MAIN player: {fp}")
        self._ve_schedule_preview_refresh()

    def _ve_browse_input(self):
        p = filedialog.askopenfilename(
            title="VIDEO ENHANCEMENT — input",
            filetypes=[
                ("Video", "*.mp4 *.mkv *.mov *.avi *.mxf *.ts *.m2ts"),
                ("All files", "*.*"),
            ],
            parent=self.root,
        )
        if p and hasattr(self, "ve_input_var"):
            self.ve_input_var.set(p)
            self._ve_schedule_preview_refresh()

    def _ve_browse_output(self):
        p = filedialog.asksaveasfilename(
            title="VIDEO ENHANCEMENT — output",
            defaultextension=".mp4",
            filetypes=[("MP4", "*.mp4"), ("Matroska", "*.mkv"), ("All files", "*.*")],
            parent=self.root,
        )
        if p and hasattr(self, "ve_output_var"):
            self.ve_output_var.set(p)

    def _ve_log_line(self, text):
        if not hasattr(self, "ve_log"):
            return
        self.ve_log.config(state=tk.NORMAL)
        self.ve_log.insert(tk.END, text + "\n")
        self.ve_log.see(tk.END)
        self.ve_log.config(state=tk.DISABLED)

    def _ve_start_encode(self):
        if getattr(self, "_ve_running", False):
            return
        if not getattr(self, "_ve_vars", None):
            return
        inp = (self.ve_input_var.get().strip() if hasattr(self, "ve_input_var") else "") or (
            getattr(self, "file", None) or ""
        )
        if not inp or not os.path.isfile(inp):
            messagebox.showerror(
                "VIDEO ENHANCEMENT",
                'No valid input file. Use "Use main file" or Browse.',
                parent=self.root,
            )
            return
        out = self.ve_output_var.get().strip() if hasattr(self, "ve_output_var") else ""
        if not out:
            out = filedialog.asksaveasfilename(
                title="Output video",
                defaultextension=".mp4",
                filetypes=[("MP4", "*.mp4"), ("Matroska", "*.mkv"), ("All files", "*.*")],
                parent=self.root,
            )
            if not out:
                return
            self.ve_output_var.set(out)
        lut = (self.ve_lut_path.get() or "").strip() if hasattr(self, "ve_lut_path") else ""
        flags = collect_ve_flags_from_vars(self._ve_vars)
        if not has_any_ve_processing(flags, lut):
            messagebox.showwarning(
                "VIDEO ENHANCEMENT",
                "Enable at least one processing option or a valid .cube LUT.",
                parent=self.root,
            )
            return
        vf, warnings = build_ve_video_filter(flags, lut)
        if not vf.strip():
            messagebox.showwarning(
                "VIDEO ENHANCEMENT",
                "No active video filter (e.g. metadata-only options selected).",
                parent=self.root,
            )
            return
        if not ffmpeg_mgr.ffmpeg_path:
            messagebox.showerror("FFmpeg", "FFmpeg not found.", parent=self.root)
            return
        self._ve_cancel = False
        self._ve_running = True
        self.ve_pv.set(0)
        self.ve_status.config(text="Starting…")
        try:
            fi = FileInfoExtractor.extract(inp)
            self._ve_total_dur = float(fi.get("format", {}).get("duration_sec", 0) or 0)
        except Exception:
            self._ve_total_dur = 0.0
        _caps = getattr(ffmpeg_mgr, "cuda_caps", None)
        cmd = (
            [ffmpeg_mgr.ffmpeg_path, "-y"]
            + hwaccel_cuda_prefix(_caps)
            + ["-i", inp, "-vf", vf]
            + ve_export_video_audio_args(_caps)
            + [
                "-movflags",
                "+faststart",
                "-progress",
                "pipe:1",
                "-nostats",
                out,
            ]
        )
        self.ve_log.config(state=tk.NORMAL)
        self.ve_log.insert(tk.END, "\n--- VE EXPORT ---\n" + " ".join(cmd[:12]) + " ... " + out + "\n")
        for w in warnings:
            self.ve_log.insert(tk.END, f"[NOTE] {w}\n")
        self.ve_log.see(tk.END)
        self.ve_log.config(state=tk.DISABLED)
        threading.Thread(target=self._run_ve_thread, args=(cmd, out), daemon=True).start()

    def _run_ve_thread(self, cmd, out_path):
        try:
            si = ffmpeg_mgr._get_startupinfo()
            self._ve_proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                startupinfo=si,
            )
            for line in self._ve_proc.stdout:
                if self._ve_cancel:
                    self._ve_proc.terminate()
                    self.root.after(0, lambda: self.ve_status.config(text="Stopped"))
                    break
                line = line.strip()
                if line.startswith("out_time_ms="):
                    try:
                        ms = int(line.split("=", 1)[1])
                        ct = ms / 1_000_000.0
                        td = self._ve_total_dur
                        if td > 0.05:
                            pct = min(99.0, (ct / td) * 100.0)
                            msg = f"VE: {ct:.1f}s / {td:.1f}s ({pct:.0f}%)"
                            self.root.after(
                                0,
                                lambda p=pct, m=msg: (self.ve_pv.set(p), self.ve_status.config(text=m)),
                            )
                    except Exception:
                        pass
                elif line.startswith("progress=end"):
                    self.root.after(
                        0,
                        lambda: (self.ve_pv.set(100), self.ve_status.config(text="Done")),
                    )
            self._ve_proc.wait()
            rc = self._ve_proc.returncode
            if rc == 0 and not self._ve_cancel:
                sz = fmt_size(out_path) if os.path.isfile(out_path) else "N/A"
                self.root.after(
                    0,
                    lambda: (
                        self._ve_log_line(f"OK: {out_path} ({sz})"),
                        messagebox.showinfo(
                            "VIDEO ENHANCEMENT",
                            f"Export finished.\n{out_path}\n{sz}",
                            parent=self.root,
                        ),
                    ),
                )
            elif not self._ve_cancel:
                self.root.after(
                    0,
                    lambda: messagebox.showerror(
                        "VIDEO ENHANCEMENT",
                        f"FFmpeg exited with code {rc}.\nSome filters may be unavailable in this FFmpeg build.",
                        parent=self.root,
                    ),
                )
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("VIDEO ENHANCEMENT", str(e), parent=self.root))
        finally:
            self._ve_running = False
            self._ve_proc = None

    def _ve_stop_encode(self):
        if self._ve_running and self._ve_proc:
            self._ve_cancel = True
            try:
                self._ve_proc.terminate()
            except Exception:
                pass

    # ==================== CONVERTER FUNCTIONS ====================
    def _conv_collect_settings(self):
        return {
            "resolution": self.conv_res.get(),
            "custom_w": self.conv_custom_w.get(),
            "custom_h": self.conv_custom_h.get(),
            "scale_method": self.conv_scale_method.get(),
            "scan_type": self.conv_scan.get(),
            "fps": self.conv_fps.get(),
            "custom_fps": self.conv_custom_fps.get(),
            "fps_mode": self.conv_fps_mode.get(),
            "frame_interpolate": self.conv_frame_interpolate.get(),
            "volume": self.conv_vol.get(),
            "mute_audio": self.conv_mute.get(),
            "normalize_audio": self.conv_normalize.get(),
            "audio_channels": self.conv_ach.get(),
            "sample_rate": self.conv_sr.get(),
            "bit_depth": self.conv_bitdepth.get(),
            "overlay_text": self.conv_ol_text.get(),
            "overlay_font": self.conv_ol_font.get(),
            "overlay_text_size": self.conv_ol_tsize.get(),
            "overlay_text_color": self.conv_ol_color.get(),
            "overlay_opacity": self.conv_ol_opa.get(),
            "overlay_x": self.conv_ol_x.get(),
            "overlay_y": self.conv_ol_y.get(),
            "overlay_anim": self.conv_ol_anim.get(),
            "overlay_image": self.conv_ol_img.get(),
            "overlay_img_x": self.conv_ol_ix.get(),
            "overlay_img_y": self.conv_ol_iy.get(),
            "overlay_img_w": self.conv_ol_iw.get(),
            "overlay_img_h": self.conv_ol_ih.get(),
            "vcodec": self.conv_vcodec.get(),
            "acodec": self.conv_acodec.get(),
            "preset": self.conv_preset.get(),
            "crf": self.conv_crf.get(),
            "video_bitrate": self.conv_vbitrate.get(),
            "audio_bitrate": self.conv_abitrate.get(),
            "hw_encoder": self.hw_encoder.get(),
            "hwaccel": self.conv_hwaccel.get(),
            "threads": self.conv_threads.get(),
            "extra_ffmpeg": self.conv_extra.get(),
        }

    @staticmethod
    def _conv_parse_bitrate_to_bps(s: str) -> float:
        """AAC-style '128k' / '1.5M' → bits per second."""
        t = (s or "").strip().lower()
        if not t or t == "auto":
            return 128_000.0
        try:
            if t.endswith("k"):
                return float(t[:-1]) * 1000.0
            if t.endswith("m"):
                return float(t[:-1]) * 1_000_000.0
            return float(t)
        except (TypeError, ValueError):
            return 128_000.0

    def _conv_expand_target_mb_bitrate(self, st: dict, duration_sec: float) -> dict:
        """
        Replace __TARGET_MB_N__ video_bitrate with a concrete -b:v from duration and target file size (MB).
        Uses average bitrate (no CRF) + yuv420p + faststart for phone-friendly MP4.
        """
        st = dict(st)
        vb = (st.get("video_bitrate") or "Auto").strip()
        import re

        m = re.match(r"__TARGET_MB_([\d.]+)__\s*$", vb)
        if not m:
            return st
        mb = float(m.group(1))
        dur = float(duration_sec or 0.0)
        if dur <= 0:
            dur = 120.0
        ab_str = st.get("audio_bitrate") or "128k"
        audio_bps = self._conv_parse_bitrate_to_bps(ab_str)
        target_bits = mb * 1024 * 1024 * 8
        total_bps = target_bits / dur
        video_bps = (total_bps - audio_bps) * 0.96
        video_bps = max(80_000.0, min(video_bps, 45_000_000.0))
        kbps = int(video_bps / 1000)
        st["video_bitrate"] = f"{kbps}k"
        st["abr_no_crf"] = True
        st["pix_fmt"] = "yuv420p"
        st["movflags"] = "+faststart"
        return st

    def _conv_make_output_path(self, inp: str) -> str:
        ext = "." + self.conv_container.get().strip().lstrip(".")
        st = self._conv_collect_settings()
        dir_ = self.conv_out_dir.get().strip()
        if not dir_:
            dir_ = os.path.dirname(os.path.abspath(inp))
        os.makedirs(dir_, exist_ok=True)
        fn = pattern_to_filename(self.conv_pattern.get(), inp, st, ext)
        path = os.path.join(dir_, os.path.basename(fn))
        if self.conv_overwrite.get() == "rename":
            path = unique_output_path(path)
        return path

    def _conv_browse_input(self):
        fp = filedialog.askopenfilename(
            title="Select Input",
            filetypes=[
                (
                    "Media",
                    "*.mp4 *.mkv *.mov *.avi *.flv *.wmv *.webm *.mpeg *.mpg *.m2v *.ts *.m2ts *.ogv *.gif *.hevc *.m4v",
                ),
                ("All files", "*.*"),
            ],
        )
        if fp:
            self.conv_input_var.set(fp)
            self.conv_output_var.set(self._conv_make_output_path(fp))
            self._conv_sync_player(fp)

    def _conv_browse_output(self):
        ext = "." + self.conv_container.get().strip().lstrip(".")
        fp = filedialog.asksaveasfilename(
            title="Save Converted File",
            defaultextension=ext,
            filetypes=[("Output", f"*{ext}"), ("All files", "*.*")],
        )
        if fp:
            self.conv_output_var.set(fp)

    def _conv_browse_out_dir(self):
        d = filedialog.askdirectory(title="Output folder")
        if d:
            self.conv_out_dir.set(d)

    def _conv_browse_ol_img(self):
        fp = filedialog.askopenfilename(
            title="Overlay image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.gif *.webp"), ("All files", "*.*")],
        )
        if fp:
            self.conv_ol_img.set(fp)

    def _conv_use_main_file(self):
        if self.file:
            self.conv_input_var.set(self.file)
            self.conv_output_var.set(self._conv_make_output_path(self.file))
            self._conv_sync_player(self.file)
        else:
            messagebox.showwarning("No File", "Use Open File first.")

    def _conv_setup_input_trace(self):
        """When the input path changes, sync the right-hand player (preview only, no autoplay)."""
        if getattr(self, "_conv_trace_ok", False):
            return
        self._conv_sync_pending = None

        def _debounced(*_a):
            if self._conv_sync_pending:
                try:
                    self.root.after_cancel(self._conv_sync_pending)
                except Exception:
                    pass
            self._conv_sync_pending = self.root.after(350, self._conv_input_sync_job)

        v = getattr(self, "conv_input_var", None)
        if not v:
            return
        try:
            v.trace_add("write", lambda *_: _debounced())
        except Exception:
            v.trace("w", lambda *_: _debounced())
        self._conv_trace_ok = True

    def _conv_input_sync_job(self):
        self._conv_sync_pending = None
        try:
            fp = self.conv_input_var.get().strip()
        except Exception:
            return
        if fp and os.path.isfile(fp):
            self._conv_sync_player(fp)

    def _conv_sync_player(self, fp):
        try:
            pl = self._players.get("converter")
            if not pl or not fp or not os.path.isfile(fp):
                return
            ok_m, msg_m = probe_input_health(
                getattr(ffmpeg_mgr, "ffprobe_path", None), fp, ffmpeg_mgr._get_startupinfo()
            )
            if not ok_m:
                self.conv_preview_label.config(text=f"Cannot read file: {msg_m[:70]}…")
                messagebox.showwarning("Preview", msg_m)
                return
            pl.preview_file(fp)
            self.conv_preview_label.config(
                text=f"Preview: {os.path.basename(fp)}  ·  press Play in the player"
            )
        except Exception:
            pass

    def _conv_log(self, msg):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.conv_log.insert(tk.END, f"[{ts}] {msg}\n")
        self.conv_log.see(tk.END)

    def _conv_state_path(self) -> str:
        return os.path.join(tempfile.gettempdir(), "orvix_pro_converter_state.json")

    def _conv_clear_state_file(self):
        try:
            p = self._conv_state_path()
            if os.path.isfile(p):
                os.remove(p)
        except OSError:
            pass

    def _conv_read_state_file(self):
        try:
            p = self._conv_state_path()
            if not os.path.isfile(p):
                return None
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def _conv_save_state_file(self, payload: dict):
        try:
            payload = dict(payload)
            payload["version"] = 2
            payload["status"] = "encoding"
            payload["saved_at"] = datetime.datetime.now().isoformat(timespec="seconds")
            with open(self._conv_state_path(), "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
        except Exception as e:
            try:
                self._conv_log(f"[state] save failed: {e}")
            except Exception:
                pass

    def _conv_flush_state_snapshot(self):
        """Persist last progress so crash / kill can resume from -ss (partial output is discarded)."""
        st = self._conv_collect_settings()
        ct = float(getattr(self, "_conv_last_ct", 0.0) or 0.0)
        inp = self.conv_input_var.get().strip() if getattr(self, "conv_input_var", None) else ""
        out = self.conv_output_var.get().strip() if getattr(self, "conv_output_var", None) else ""
        base = {
            "settings": st,
            "last_time_sec": ct,
            "paused": bool(self._conv_pause),
            "mode": "single",
            "single": {"inp": inp, "out": out},
        }
        try:
            fi = FileInfoExtractor.extract(inp)
            base["duration_sec"] = float(fi.get("format", {}).get("duration_sec") or 0)
        except Exception:
            base["duration_sec"] = 0.0
        self._conv_save_state_file(base)

    def _conv_update_pause_buttons(self):
        try:
            run = getattr(self, "_conv_running", False)
            p = getattr(self, "_conv_pause", False)
            if hasattr(self, "conv_pause_btn"):
                self.conv_pause_btn.config(state=tk.NORMAL if (run and not p) else tk.DISABLED)
            if hasattr(self, "conv_resume_btn"):
                self.conv_resume_btn.config(state=tk.NORMAL if (run and p) else tk.DISABLED)
        except Exception:
            pass

    def _conv_pause_encoding(self):
        if not self._conv_running or self._conv_pause or not self._conv_proc:
            return
        self._conv_pause = True
        pid = self._conv_proc.pid
        if pid:
            _os_suspend_process(pid)
        self._conv_flush_state_snapshot()
        try:
            self.conv_status.config(text="Paused — FFmpeg suspended; press Resume")
            if hasattr(self, "conv_prog_state"):
                try:
                    self.conv_prog_state.config(text="PAUSED")
                except Exception:
                    pass
        except Exception:
            pass
        self.root.after(0, self._conv_update_pause_buttons)

    def _conv_resume_encoding(self):
        if not self._conv_running or not self._conv_pause:
            return
        self._conv_pause = False
        pid = self._conv_proc.pid if self._conv_proc else None
        if pid:
            _os_resume_process(pid)
        try:
            self.conv_status.config(text="Encoding resumed — progress will update shortly")
            if hasattr(self, "conv_prog_state"):
                try:
                    self.conv_prog_state.config(text="ENCODING")
                except Exception:
                    pass
        except Exception:
            pass
        self.root.after(0, self._conv_update_pause_buttons)

    def _conv_start_from_resume_state(self, state: dict):
        """Resume after crash: re-encode from last_time_sec; partial output removed."""
        if state.get("mode") == "batch":
            messagebox.showinfo(
                "Converter",
                "Saved state is from the old multi-file queue, which was removed. Clear it and start a new conversion.",
            )
            self._conv_clear_state_file()
            return
        seek = float(state.get("last_time_sec", 0.0) or 0.0)
        if seek < 0.5:
            messagebox.showinfo("Converter", "No valid resume position in saved state.")
            self._conv_clear_state_file()
            return
        stg = state.get("settings") if isinstance(state.get("settings"), dict) else None
        self._conv_resume_settings_override = stg
        sg = state.get("single") or {}
        inp, out = sg.get("inp", "").strip(), sg.get("out", "").strip()
        if not inp or not os.path.isfile(inp):
            messagebox.showerror("Converter", "Resume failed: input file missing.")
            self._conv_clear_state_file()
            return
        self.conv_input_var.set(inp)
        self.conv_output_var.set(out)
        if out and os.path.isfile(out):
            try:
                os.remove(out)
            except OSError as e:
                messagebox.showerror("Converter", f"Could not remove partial output:\n{e}")
                return
        self._conv_cancel = False
        self._conv_report = []
        self.conv_log.delete("1.0", tk.END)
        self._conv_running = True
        self.conv_pv.set(0)
        self.root.after(0, self._conv_encode_start_ui)
        self.root.after(0, self._conv_update_pause_buttons)
        threading.Thread(
            target=lambda: self._run_one_job(
                inp, out, True, seek_sec=seek, settings_override=stg
            ),
            daemon=True,
        ).start()

    def _build_conv_cmd(self, inp, out, seek_sec: float = 0.0, settings=None):
        st = settings if isinstance(settings, dict) else self._conv_collect_settings()
        cmd, _ = build_ffmpeg_command(
            ffmpeg_mgr.ffmpeg_path,
            inp,
            out,
            st,
            progress_pipe=True,
            seek_seconds=float(seek_sec or 0.0),
        )
        return cmd

    def _conv_start(self):
        if not ffmpeg_mgr.ffmpeg_path:
            messagebox.showerror("FFmpeg", "FFmpeg was not found.")
            return
        if self._conv_running:
            return
        saved = self._conv_read_state_file()
        if (
            saved
            and saved.get("status") == "encoding"
            and saved.get("mode") != "batch"
            and float(saved.get("last_time_sec", 0) or 0) > 0.5
        ):
            lt = float(saved.get("last_time_sec", 0))
            mm = int(lt // 60)
            ss = int(lt % 60)
            if messagebox.askyesno(
                "Resume encoding",
                f"An interrupted conversion was found (last position ~{mm:02d}:{ss:02d}).\n\n"
                "Resume from that point? The incomplete output file will be removed and "
                "replaced with a clean encode from the saved position.",
            ):
                self._conv_start_from_resume_state(saved)
                return
            self._conv_clear_state_file()
        else:
            self._conv_clear_state_file()
        self._conv_cancel = False
        self._conv_report = []
        self.conv_log.delete("1.0", tk.END)
        inp = self.conv_input_var.get().strip()
        out = self.conv_output_var.get().strip()
        ok, err = validate_settings(self._conv_collect_settings(), inp, out)
        if not ok:
            messagebox.showerror("Converter", err)
            return
        if not os.path.isfile(inp):
            messagebox.showerror("Converter", "Input file does not exist.")
            return
        ok_m, msg_m = probe_input_health(
            getattr(ffmpeg_mgr, "ffprobe_path", None), inp, ffmpeg_mgr._get_startupinfo()
        )
        if not ok_m:
            messagebox.showerror("Converter", msg_m)
            return
        if not out:
            out = self._conv_make_output_path(inp)
            self.conv_output_var.set(out)
        self._conv_running = True
        self.conv_pv.set(0)
        self.root.after(0, self._conv_encode_start_ui)
        self.root.after(0, self._conv_update_pause_buttons)
        threading.Thread(target=lambda: self._run_one_job(inp, out, True, seek_sec=0.0), daemon=True).start()

    def _conv_fmt_hms(self, sec: float) -> str:
        if sec is None or sec < 0 or sec > 3600 * 200:
            return "—"
        s = int(sec)
        h, m, r = s // 3600, (s % 3600) // 60, s % 60
        if h > 0:
            return f"{h}:{m:02d}:{r:02d}"
        return f"{m}:{r:02d}"

    def _conv_fmt_size_mb(self, n_mb: float) -> str:
        if n_mb >= 1024:
            return f"{n_mb / 1024:.2f} GB"
        if n_mb < 0.005:
            return "0 MB"
        return f"{n_mb:.1f} MB"

    def _conv_apply_progress_ui(
        self,
        pct: float,
        eta: float,
        mb_s: str,
        inp: str,
        out: str,
        *,
        elapsed: float = 0.0,
        in_mb: float = 0.0,
        out_mb: float = 0.0,
        phase: str = "encode",
    ):
        """Progress bar + premium status: ETA, speed, sizes, elapsed."""
        try:
            self.conv_pv.set(min(100.0, pct))
            try:
                self.root.update_idletasks()
            except Exception:
                pass
            bn_in = os.path.basename(inp)
            bn_out = os.path.basename(out)
            ph = {"encode": "ENCODING", "ready": "READY", "done": "DONE", "fail": "FAILED"}.get(phase, phase.upper())
            if hasattr(self, "conv_prog_pct_lbl"):
                self.conv_prog_pct_lbl.config(text=f"{min(100.0, pct):.1f}%")
            if hasattr(self, "conv_prog_state"):
                self.conv_prog_state.config(text=ph)
            if hasattr(self, "conv_prog_metrics"):
                self.conv_prog_metrics.config(
                    text=(
                        f"ETA {self._conv_fmt_hms(eta)}  ·  speed {mb_s} MB/s  ·  "
                        f"written {self._conv_fmt_size_mb(out_mb)}  ·  elapsed {self._conv_fmt_hms(elapsed)}  ·  "
                        f"source {self._conv_fmt_size_mb(in_mb)}"
                    )
                )
            if hasattr(self, "conv_prog_paths"):
                self.conv_prog_paths.config(text=f"{bn_in}  →  {bn_out}")
        except Exception:
            pass

    def _conv_idle_progress_ui(self):
        try:
            self.conv_pv.set(0.0)
            if hasattr(self, "conv_prog_pct_lbl"):
                self.conv_prog_pct_lbl.config(text="0%")
            if hasattr(self, "conv_prog_state"):
                self.conv_prog_state.config(text="READY")
            if hasattr(self, "conv_prog_metrics"):
                self.conv_prog_metrics.config(text="—")
            if hasattr(self, "conv_prog_paths"):
                self.conv_prog_paths.config(text="")
            if hasattr(self, "conv_status"):
                self.conv_status.config(text="Ready")
        except Exception:
            pass

    def _conv_encode_start_ui(self):
        try:
            if hasattr(self, "conv_prog_state"):
                self.conv_prog_state.config(text="ENCODING")
            if hasattr(self, "conv_prog_pct_lbl"):
                self.conv_prog_pct_lbl.config(text="0%")
            if hasattr(self, "conv_prog_metrics"):
                self.conv_prog_metrics.config(text="Preparing encoder…")
            if hasattr(self, "conv_status"):
                self.conv_status.config(text="Encoding…")
        except Exception:
            pass

    def _run_one_job(self, inp, out, clear_running, seek_sec=0.0, settings_override=None):
        try:
            st = settings_override if isinstance(settings_override, dict) else self._conv_collect_settings()
            ok, err = validate_settings(st, inp, out)
            if not ok:
                self.root.after(0, lambda: self._conv_log(f"ERROR {inp}: {err}"))
                return
            fi = FileInfoExtractor.extract(inp)
            dur = float(fi.get("format", {}).get("duration_sec") or 0)
            if dur <= 0:
                pr = run_ffprobe(inp)
                if pr and pr.get("format"):
                    try:
                        dur = float(pr["format"].get("duration") or 0)
                    except (TypeError, ValueError):
                        dur = 0.0
            seek_sec = float(seek_sec or 0.0)
            eff_dur = max(0.01, dur - seek_sec) if dur > 0 else 0.0

            st = dict(st)
            raw_vb = str(st.get("video_bitrate") or "")
            d_for_target = eff_dur if eff_dur > 0 else (max(0.01, dur) if dur > 0 else 120.0)
            st = self._conv_expand_target_mb_bitrate(st, d_for_target)
            if raw_vb.strip().startswith("__TARGET_MB_"):
                vb_final = st.get("video_bitrate", "?")
                self.root.after(
                    0,
                    lambda: self._conv_log(
                        f"Target file size mode: average video bitrate {vb_final} for ~{d_for_target:.0f}s "
                        f"(aim ~170 MB total; actual size depends on content)."
                    ),
                )

            def _kick_start():
                self.conv_pv.set(0.0)
                self._conv_encode_start_ui()

            self.root.after(0, _kick_start)

            cmd = self._build_conv_cmd(inp, out, seek_sec=seek_sec, settings=st)
            self.root.after(0, lambda: self._conv_log("CMD: " + " ".join(cmd)))
            si = ffmpeg_mgr._get_startupinfo()
            self._conv_proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                encoding="utf-8",
                errors="replace",
                startupinfo=si,
            )
            t0 = time.time()
            self._conv_ui_last_ts = 0.0
            last_state_save = 0.0
            time_re = re.compile(r"time=(\d+):(\d+):(\d+(?:\.\d+)?)")
            out_ms_re = re.compile(r"out_time_ms=(\d+)")
            frame_re = re.compile(r"frame=\s*(\d+)")
            nb_frames = int(fi.get("video", {}).get("total_frames") or 0)
            q = queue.Queue()

            def _reader():
                try:
                    for line in iter(self._conv_proc.stderr.readline, ""):
                        q.put(line)
                finally:
                    q.put(None)

            threading.Thread(target=_reader, daemon=True).start()
            while True:
                try:
                    line = q.get(timeout=0.35)
                except queue.Empty:
                    if self._conv_proc and self._conv_proc.poll() is not None:
                        break
                    if self._conv_cancel and self._conv_proc:
                        try:
                            self._conv_proc.terminate()
                        except Exception:
                            pass
                    continue
                if line is None:
                    break
                if self._conv_cancel:
                    try:
                        self._conv_proc.terminate()
                    except Exception:
                        pass
                    break
                line = line.strip()
                ct = None
                otm = out_ms_re.search(line)
                if otm:
                    try:
                        ct = int(otm.group(1)) / 1_000_000.0
                    except ValueError:
                        pass
                if ct is None:
                    tm = time_re.search(line)
                    if tm:
                        try:
                            h, m_, s = int(tm.group(1)), int(tm.group(2)), float(tm.group(3))
                            ct = h * 3600 + m_ * 60 + s
                        except ValueError:
                            pass
                if ct is not None:
                    self._conv_last_ct = ct
                pct = None
                eta = 0.0
                if dur > 0 and ct is not None and eff_dur > 0:
                    try:
                        pct = min(99.0, max(0.0, (ct - seek_sec) / eff_dur) * 100)
                        eta = max(0.0, eff_dur - max(0.0, ct - seek_sec))
                    except Exception:
                        pct = None
                if pct is None and seek_sec <= 0.001:
                    fm = frame_re.search(line)
                    if fm and nb_frames > 0:
                        try:
                            fn = int(fm.group(1))
                            pct = min(99.0, (fn / float(nb_frames)) * 100)
                            eta = max(0.0, dur - dur * (pct / 100.0)) if dur > 0 else 0.0
                        except Exception:
                            pct = None
                if pct is not None:
                    now = time.time()
                    if (now - getattr(self, "_conv_ui_last_ts", 0)) < 0.15 and pct < 99.0:
                        pass
                    else:
                        self._conv_ui_last_ts = now
                        try:
                            elapsed = now - t0
                            in_mb = os.path.getsize(inp) / (1024 * 1024) if os.path.isfile(inp) else 0.0
                            out_mb = 0.0
                            mb_s = "-"
                            if os.path.isfile(out):
                                sz = os.path.getsize(out)
                                out_mb = sz / (1024 * 1024)
                                dt = max(0.001, elapsed)
                                mb_s = f"{out_mb / dt:.2f}"
                            done_src = max(0.0, (ct or 0.0) - seek_sec)
                            eta_u = 0.0
                            if eff_dur > 0 and done_src > 0.05 and elapsed > 0.25:
                                eta_u = max(0.0, (eff_dur - done_src) * (elapsed / done_src))
                            elif eff_dur > 0:
                                eta_u = max(0.0, eff_dur - done_src)
                            self.root.after(
                                0,
                                lambda p=pct,
                                e=eta_u,
                                m=mb_s,
                                i=inp,
                                o=out,
                                el=elapsed,
                                im=in_mb,
                                om=out_mb: self._conv_apply_progress_ui(
                                    p, e, m, i, o, elapsed=el, in_mb=im, out_mb=om, phase="encode"
                                ),
                            )
                        except Exception:
                            pass
                now = time.time()
                if now - last_state_save > 1.4:
                    last_state_save = now
                    try:
                        self._conv_flush_state_snapshot()
                    except Exception:
                        pass
            try:
                self._conv_proc.wait()
            except Exception:
                pass
            rc = self._conv_proc.returncode if self._conv_proc else -1
            rec = {"input": inp, "output": out, "rc": rc}
            self._conv_report.append(rec)
            if rc == 0:
                self._conv_clear_state_file()
                sz = fmt_size(out) if os.path.isfile(out) else "?"
                self.root.after(0, lambda: self._conv_log(f"OK {out} ({sz})"))

                def _done_ok():
                    self.conv_pv.set(100.0)
                    if hasattr(self, "conv_prog_pct_lbl"):
                        self.conv_prog_pct_lbl.config(text="100%")
                    if hasattr(self, "conv_prog_state"):
                        self.conv_prog_state.config(text="DONE")
                    if hasattr(self, "conv_prog_metrics"):
                        sz = fmt_size(out) if os.path.isfile(out) else "?"
                        self.conv_prog_metrics.config(
                            text=f"Complete  ·  output {sz}  ·  {os.path.basename(out)}"
                        )
                    if hasattr(self, "conv_status"):
                        self.conv_status.config(text="Complete")
                    try:
                        self.root.update_idletasks()
                    except Exception:
                        pass

                self.root.after(0, _done_ok)
            else:
                self.root.after(0, lambda: self._conv_log(f"FAIL rc={rc} {inp}"))

                def _done_fail():
                    if hasattr(self, "conv_prog_state"):
                        self.conv_prog_state.config(text="FAILED")
                    if hasattr(self, "conv_prog_metrics"):
                        self.conv_prog_metrics.config(text=f"FFmpeg exit code {rc} — see Log tab")
                    if hasattr(self, "conv_status"):
                        self.conv_status.config(text=f"Failed (exit {rc})")

                self.root.after(0, _done_fail)
                if self.conv_retry.get():
                    self._run_one_job(inp, out, clear_running, seek_sec=seek_sec, settings_override=settings_override)
        except Exception as e:
            self.root.after(0, lambda: self._conv_log(f"EXC: {e}"))
        finally:
            self._conv_proc = None
            if clear_running:
                self._conv_running = False
                self._conv_pause = False
                self._conv_resume_settings_override = None
            self.root.after(0, self._conv_update_pause_buttons)

    def _stop_convert(self):
        self._conv_cancel = True
        self._conv_pause = False
        if self._conv_proc:
            try:
                pid = self._conv_proc.pid
                if pid:
                    _os_resume_process(pid)
            except Exception:
                pass
            try:
                self._conv_proc.terminate()
            except Exception:
                pass

    def _conv_export_log(self):
        fp = filedialog.asksaveasfilename(title="Export log", defaultextension=".txt", filetypes=[("Text", "*.txt")])
        if fp:
            with open(fp, "w", encoding="utf-8") as f:
                f.write(self.conv_log.get("1.0", tk.END))
            messagebox.showinfo("Log saved", fp)

    def _conv_export_json(self):
        fp = filedialog.asksaveasfilename(title="Export JSON report", defaultextension=".json", filetypes=[("JSON", "*.json")])
        if fp:
            with open(fp, "w", encoding="utf-8") as f:
                json.dump(
                    {"settings": self._conv_collect_settings(), "jobs": self._conv_report},
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
            messagebox.showinfo("Report saved", fp)

    def _conv_player_play(self):
        pl = self._players.get("converter")
        if pl:
            try:
                pl.play_media()
            except Exception:
                pass

    def _conv_player_pause(self):
        pl = self._players.get("converter")
        if pl:
            try:
                pl.pause_media()
            except Exception:
                pass

    def _conv_player_stop(self):
        pl = self._players.get("converter")
        if pl:
            try:
                pl.stop()
            except Exception:
                pass

    def _conv_preview_ffplay(self):
        inp = self.conv_input_var.get().strip()
        if not inp or not os.path.isfile(inp):
            messagebox.showwarning("Preview", "Select an input file.")
            return
        ffplay = getattr(ffmpeg_mgr, "ffplay_path", None) or "ffplay"
        try:
            subprocess.Popen([ffplay, "-autoexit", inp], startupinfo=ffmpeg_mgr._get_startupinfo())
        except Exception as e:
            messagebox.showerror("FFplay preview", str(e))

    # ==================== SOCIAL FUNCTIONS ====================
    def _sn_browse_input(self):
        fp = filedialog.askopenfilename(
            parent=self._social_workspace_dialog_parent(),
            title="Select Input Video",
            filetypes=[("Video files", "*.mp4 *.mov *.avi *.mkv *.webm *.wmv *.flv *.ts *.mpg"), ("All files", "*.*")],
        )
        if fp:
            self.sn_input_var.set(fp)
            base, ext = os.path.splitext(fp)
            plat = self.sn_platform_var.get()
            fmt = self._sn_platforms.get(plat, {}).get('fmt', 'mp4')
            self.sn_output_var.set(f"{base}_social.{fmt}")
            self._social_workspace_sync_player()

    def _sn_browse_output(self):
        fp = filedialog.asksaveasfilename(
            parent=self._social_workspace_dialog_parent(),
            title="Save Output",
            defaultextension=".mp4",
            filetypes=[("MP4", "*.mp4"), ("All files", "*.*")],
        )
        if fp:
            self.sn_output_var.set(fp)
            self._social_workspace_sync_player()

    def _sn_use_main_file(self):
        if self.file:
            self.sn_input_var.set(self.file)
            base, ext = os.path.splitext(self.file)
            plat = self.sn_platform_var.get()
            fmt = self._sn_platforms.get(plat, {}).get('fmt', 'mp4')
            self.sn_output_var.set(f"{base}_social.{fmt}")
            self._social_workspace_sync_player()
        else:
            messagebox.showwarning("No File", "Use Open File first.")

    def _sn_browse_overlay_image(self):
        fp = filedialog.askopenfilename(
            parent=self._social_workspace_dialog_parent(),
            title="Select Overlay Image",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.webp"), ("All files", "*.*")],
        )
        if fp:
            self.sn_overlay_img_var.set(fp)

    def _sn_browse_overlay2_media(self):
        fp = filedialog.askopenfilename(
            parent=self._social_workspace_dialog_parent(),
            title="Select Overlay2 Media (Video/Image)",
            filetypes=[("Media files", "*.png *.jpg *.jpeg *.webp *.mp4 *.mov *.mkv *.avi"), ("All files", "*.*")],
        )
        if fp:
            self.sn_overlay2_img_var.set(fp)

    def _sn_browse_background_image(self):
        fp = filedialog.askopenfilename(
            parent=self._social_workspace_dialog_parent(),
            title="Select Background Image",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.webp"), ("All files", "*.*")],
        )
        if fp:
            self.sn_bg_img_var.set(fp)

    def _sn_safe_float(self, value, default=0.0, min_v=None, max_v=None):
        try:
            out = float(value)
        except Exception:
            out = float(default)
        if min_v is not None:
            out = max(min_v, out)
        if max_v is not None:
            out = min(max_v, out)
        return out

    def _sn_escape_drawtext(self, txt):
        # Escape critical chars used by FFmpeg drawtext parser.
        out = (txt or '')
        out = out.replace('\\', '\\\\')
        out = out.replace(':', '\\:')
        out = out.replace("'", "\\'")
        out = out.replace(',', '\\,')
        out = out.replace('%', '\\%')
        return out

    def _sn_apply_preset(self):
        preset = (self.sn_preset_var.get() if hasattr(self, 'sn_preset_var') else 'Custom').strip()
        if preset == 'Headline Bottom':
            if not (self.sn_text_var.get() or '').strip():
                self.sn_text_var.set('YOUR HEADLINE')
            self.sn_text_color_var.set('white')
            self.sn_text_size_var.set('52')
            self.sn_text_x_var.set('(w-text_w)/2')
            self.sn_text_y_var.set('h*0.82')
            self.sn_text_start_var.set('0')
            self.sn_text_end_var.set('')
            self.sn_overlay_x_var.set('W-w-36')
            self.sn_overlay_y_var.set('H-h-36')
            self.sn_overlay_scale_var.set('1.0')
            self.sn_overlay_opacity_var.set('1.0')
            self.sn_fill_mode_var.set('Blur Fill')
            self.sn_y_shift.set(0)
            if hasattr(self, 'sn_x_shift'):
                self.sn_x_shift.set(0)
            self._sn_log("Preset applied: Headline Bottom")
            return
        if preset == 'Top CTA':
            if not (self.sn_text_var.get() or '').strip():
                self.sn_text_var.set('FOLLOW FOR MORE')
            self.sn_text_color_var.set('yellow')
            self.sn_text_size_var.set('46')
            self.sn_text_x_var.set('(w-text_w)/2')
            self.sn_text_y_var.set('h*0.10')
            self.sn_text_start_var.set('0')
            self.sn_text_end_var.set('6')
            self.sn_overlay_x_var.set('W-w-36')
            self.sn_overlay_y_var.set('H-h-36')
            self.sn_overlay_scale_var.set('0.9')
            self.sn_overlay_opacity_var.set('0.92')
            self.sn_fill_mode_var.set('Blur Fill')
            self.sn_y_shift.set(0)
            if hasattr(self, 'sn_x_shift'):
                self.sn_x_shift.set(0)
            self._sn_log("Preset applied: Top CTA")
            return
        if preset == 'Watermark Corner':
            if not (self.sn_text_var.get() or '').strip():
                self.sn_text_var.set('@yourbrand')
            self.sn_text_color_var.set('white')
            self.sn_text_size_var.set('30')
            self.sn_text_x_var.set('36')
            self.sn_text_y_var.set('H-text_h-36')
            self.sn_text_start_var.set('0')
            self.sn_text_end_var.set('')
            self.sn_overlay_x_var.set('W-w-28')
            self.sn_overlay_y_var.set('28')
            self.sn_overlay_scale_var.set('0.45')
            self.sn_overlay_opacity_var.set('0.72')
            self.sn_fill_mode_var.set('Blur Fill')
            self.sn_y_shift.set(0)
            if hasattr(self, 'sn_x_shift'):
                self.sn_x_shift.set(0)
            self._sn_log("Preset applied: Watermark Corner")
            return
        self._sn_log("Preset: Custom (no auto changes).")

    def _sn_nudge_y(self, delta):
        try:
            cur = int(self.sn_y_shift.get())
        except Exception:
            cur = 0
        nxt = max(-700, min(700, cur + int(delta)))
        self.sn_y_shift.set(nxt)

    def _sn_nudge_x(self, delta):
        try:
            cur = int(self.sn_x_shift.get())
        except Exception:
            cur = 0
        nxt = max(-700, min(700, cur + int(delta)))
        self.sn_x_shift.set(nxt)

    def _sn_center_y(self):
        self.sn_y_shift.set(0)

    def _sn_center_x(self):
        if hasattr(self, 'sn_x_shift'):
            self.sn_x_shift.set(0)

    def _sn_expr_to_float(self, expr, default=0.0):
        s = str(expr or '').strip()
        if not s:
            return float(default)
        try:
            return float(s)
        except Exception:
            return float(default)

    def _sn_open_layout_editor(self):
        inp = (self.sn_input_var.get() or '').strip()
        if not inp or not os.path.exists(inp):
            messagebox.showwarning("No Input", "Select input video first.")
            return
        plat = self.sn_platform_var.get()
        p = self._sn_platforms.get(plat, {})
        res = p.get('res', '1080x1920')
        try:
            tw, th = [int(x) for x in res.split('x')]
        except Exception:
            tw, th = 1080, 1920
        s = self._sn_applied_settings or self._sn_collect_settings_from_ui()
        zoom = self._sn_safe_float(s.get('video_zoom', 1.0), default=1.0, min_v=0.3, max_v=3.0)
        x_shift = int(self._sn_safe_float(s.get('x_shift', 0), default=0, min_v=-2000, max_v=2000))
        y_shift = int(self._sn_safe_float(s.get('y_shift', 0), default=0, min_v=-2000, max_v=2000))
        txt = str(s.get('text', '')).strip()
        txt_size = int(self._sn_safe_float(s.get('text_size', 46), default=46, min_v=12, max_v=220))
        bg_path = str(s.get('bg_img', '')).strip()
        ov_path = str(s.get('overlay_img', '')).strip()
        ov_scale = self._sn_safe_float(s.get('overlay_scale', 1.0), default=1.0, min_v=0.05, max_v=8.0)
        ov2_path = str(s.get('overlay2_img', '')).strip()
        ov2_scale = self._sn_safe_float(s.get('overlay2_scale', 1.0), default=1.0, min_v=0.05, max_v=8.0)

        preview_max_h = 760
        ratio = tw / max(1.0, th)
        ph = preview_max_h
        pw = int(ph * ratio)
        if pw > 520:
            pw = 520
            ph = int(pw / max(0.0001, ratio))
        sx = pw / max(1.0, tw)
        sy = ph / max(1.0, th)

        win = tk.Toplevel(self.root)
        win.title("Social Layout Editor")
        win.configure(bg=self.BG2)
        win.geometry(f"{pw+40}x{ph+130}")
        win.transient(self.root)

        cv = tk.Canvas(win, width=pw, height=ph, bg='#111111', highlightthickness=1, highlightbackground='#24425f')
        cv.pack(padx=20, pady=(14, 8))

        # Optional background image shown in the editor only.
        bg_tk = None
        if bg_path and os.path.exists(bg_path) and PIL_AVAILABLE:
            try:
                bg_pil = Image.open(bg_path).convert('RGB')
                bg_tk = ImageTk.PhotoImage(bg_pil.resize((pw, ph), Image.LANCZOS))
            except Exception:
                bg_tk = None

        # Source frame (single still) for reference in editor.
        base_frame = None
        try:
            st = self._parse_hms_to_seconds(str(s.get('start', '00:00:00'))) or 0.0
            cap = cv2.VideoCapture(inp)
            if cap.isOpened():
                if st > 0:
                    cap.set(cv2.CAP_PROP_POS_MSEC, st * 1000.0)
                ok, fr = cap.read()
                cap.release()
                if ok and PIL_AVAILABLE:
                    fr = cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)
                    base_frame = Image.fromarray(fr)
        except Exception:
            base_frame = None

        info = FileInfoExtractor.extract(inp)
        sw = int(info.get('video', {}).get('width', 1920) or 1920)
        sh = int(info.get('video', {}).get('height', 1080) or 1080)
        fit = min(tw / max(1, sw), th / max(1, sh))
        vw = max(8, int(sw * fit * zoom))
        vh = max(8, int(sh * fit * zoom))
        vx = int((tw - vw) / 2 + x_shift)
        vy = int((th - vh) / 2 + y_shift)
        txt_x = self._sn_expr_to_float(s.get('text_x', ''), default=(tw / 2))
        txt_y = self._sn_expr_to_float(s.get('text_y', ''), default=(th * 0.82))
        ov_x = self._sn_expr_to_float(s.get('overlay_x', ''), default=(tw - 140))
        ov_y = self._sn_expr_to_float(s.get('overlay_y', ''), default=(th - 140))
        ov2_x = self._sn_expr_to_float(s.get('overlay2_x', ''), default=(tw - 220))
        ov2_y = self._sn_expr_to_float(s.get('overlay2_y', ''), default=(th - 220))

        state = {
            'vw': vw, 'vh': vh, 'vx': vx, 'vy': vy,
            'zoom': zoom, 'txt_x': txt_x, 'txt_y': txt_y, 'txt_size': txt_size,
            'ov_x': ov_x, 'ov_y': ov_y, 'ov_scale': ov_scale,
            'ov2_x': ov2_x, 'ov2_y': ov2_y, 'ov2_scale': ov2_scale,
            'selected': 'video', 'drag_start': None
        }

        ov_img = None
        ov_orig_w = 0
        ov_orig_h = 0
        if ov_path and os.path.exists(ov_path) and PIL_AVAILABLE:
            try:
                ov_img = Image.open(ov_path).convert('RGBA')
                ov_orig_w, ov_orig_h = ov_img.size
            except Exception:
                ov_img = None

        ov2_img = None
        ov2_orig_w = 0
        ov2_orig_h = 0
        if ov2_path and os.path.exists(ov2_path) and PIL_AVAILABLE:
            try:
                ext = os.path.splitext(ov2_path)[1].lower()
                video_exts = {'.mp4', '.mov', '.mkv', '.avi', '.webm', '.wmv', '.flv', '.ts', '.mpg'}
                if ext in video_exts:
                    st2 = self._parse_hms_to_seconds(str(s.get('start', '00:00:00'))) or 0.0
                    cap2 = cv2.VideoCapture(ov2_path)
                    if cap2.isOpened() and st2 > 0:
                        cap2.set(cv2.CAP_PROP_POS_MSEC, float(st2) * 1000.0)
                    ok2, fr2 = cap2.read() if cap2.isOpened() else (False, None)
                    cap2.release()
                    if ok2 and fr2 is not None:
                        fr2 = cv2.cvtColor(fr2, cv2.COLOR_BGR2RGB)
                        ov2_img = Image.fromarray(fr2).convert('RGBA')
                        ov2_orig_w, ov2_orig_h = ov2_img.size
                else:
                    ov2_img = Image.open(ov2_path).convert('RGBA')
                    ov2_orig_w, ov2_orig_h = ov2_img.size
            except Exception:
                ov2_img = None

        def to_canvas_x(v): return int(v * sx)
        def to_canvas_y(v): return int(v * sy)
        def to_target_x(v): return float(v) / max(0.0001, sx)
        def to_target_y(v): return float(v) / max(0.0001, sy)

        def redraw():
            cv.delete('all')
            if bg_tk is not None:
                cv.create_image(0, 0, image=bg_tk, anchor='nw')
            else:
                cv.create_rectangle(0, 0, pw, ph, fill='#141414', outline='')
            vx1 = to_canvas_x(state['vx']); vy1 = to_canvas_y(state['vy'])
            vx2 = to_canvas_x(state['vx'] + state['vw']); vy2 = to_canvas_y(state['vy'] + state['vh'])
            if base_frame is not None and PIL_AVAILABLE:
                try:
                    fr = base_frame.resize((max(4, vx2 - vx1), max(4, vy2 - vy1)), Image.LANCZOS)
                    p = ImageTk.PhotoImage(fr)
                    cv.create_image(vx1, vy1, image=p, anchor='nw')
                    cv._frame_img = p
                except Exception:
                    cv.create_rectangle(vx1, vy1, vx2, vy2, fill='#2a5a88', outline='')
            else:
                cv.create_rectangle(vx1, vy1, vx2, vy2, fill='#2a5a88', outline='')
            vcol = '#ffda66' if state['selected'] == 'video' else '#88d0ff'
            cv.create_rectangle(vx1, vy1, vx2, vy2, outline=vcol, width=2)
            cv.create_text(vx1 + 6, vy1 + 6, anchor='nw', text='VIDEO', fill=vcol, font=('Segoe UI', 9, 'bold'))

            if txt:
                tx = to_canvas_x(state['txt_x']); ty = to_canvas_y(state['txt_y'])
                tcol = '#ffe070' if state['selected'] == 'text' else '#e8e8e8'
                cv.create_text(tx, ty, text=txt, fill=tcol, anchor='nw', font=('Segoe UI', max(8, int(state['txt_size'] * sx)), 'bold'))
                cv.create_rectangle(tx - 3, ty - 3, tx + 120, ty + 24, outline=tcol, width=1)
                cv.create_text(tx + 4, ty - 12, anchor='nw', text='TEXT', fill=tcol, font=('Segoe UI', 8, 'bold'))

            if ov_img is not None:
                ow = max(8, int(ov_orig_w * state['ov_scale'] * sx))
                oh = max(8, int(ov_orig_h * state['ov_scale'] * sy))
                ox = to_canvas_x(state['ov_x']); oy = to_canvas_y(state['ov_y'])
                try:
                    oi = ov_img.resize((ow, oh), Image.LANCZOS)
                    op = ImageTk.PhotoImage(oi)
                    cv.create_image(ox, oy, image=op, anchor='nw')
                    cv._ov_img = op
                except Exception:
                    cv.create_rectangle(ox, oy, ox + ow, oy + oh, fill='#8899aa', outline='')
                ocol = '#8aff8a' if state['selected'] == 'logo' else '#a6f0a6'
                cv.create_rectangle(ox, oy, ox + ow, oy + oh, outline=ocol, width=2)
                cv.create_text(ox + 4, oy - 12, anchor='nw', text='LOGO', fill=ocol, font=('Segoe UI', 8, 'bold'))

            if ov2_img is not None:
                ow2 = max(8, int(ov2_orig_w * state['ov2_scale'] * sx))
                oh2 = max(8, int(ov2_orig_h * state['ov2_scale'] * sy))
                ox2 = to_canvas_x(state['ov2_x']); oy2 = to_canvas_y(state['ov2_y'])
                try:
                    oi2 = ov2_img.resize((ow2, oh2), Image.LANCZOS)
                    op2 = ImageTk.PhotoImage(oi2)
                    cv.create_image(ox2, oy2, image=op2, anchor='nw')
                    cv._ov2_img = op2
                except Exception:
                    cv.create_rectangle(ox2, oy2, ox2 + ow2, oy2 + oh2, fill='#7aa0aa', outline='')
                ocol2 = '#ff8aff' if state['selected'] == 'logo2' else '#cdb0ff'
                cv.create_rectangle(ox2, oy2, ox2 + ow2, oy2 + oh2, outline=ocol2, width=2)
                cv.create_text(ox2 + 4, oy2 - 12, anchor='nw', text='LAYER2', fill=ocol2, font=('Segoe UI', 8, 'bold'))

            help_txt = "Click object to select  •  Drag to move  •  MouseWheel to resize  •  Apply To Social"
            cv.create_text(8, ph - 10, anchor='sw', text=help_txt, fill='#95aac0', font=('Segoe UI', 9))

        def on_press(e):
            # Auto-select by hit-test to keep editor UI simple.
            vx1 = to_canvas_x(state['vx']); vy1 = to_canvas_y(state['vy'])
            vx2 = to_canvas_x(state['vx'] + state['vw']); vy2 = to_canvas_y(state['vy'] + state['vh'])
            tx = to_canvas_x(state['txt_x']); ty = to_canvas_y(state['txt_y'])
            # Text rect matches redraw() constants: (tx-3 .. tx+120, ty-3 .. ty+24)
            tx1, ty1, tx2, ty2 = tx - 3, ty - 3, tx + 120, ty + 24
            logo_hit = False
            if ov_img is not None:
                ow = max(8, int(ov_orig_w * state['ov_scale'] * sx))
                oh = max(8, int(ov_orig_h * state['ov_scale'] * sy))
                ox = to_canvas_x(state['ov_x']); oy = to_canvas_y(state['ov_y'])
                logo_hit = (ox <= e.x <= ox + ow and oy <= e.y <= oy + oh)
            logo2_hit = False
            if ov2_img is not None:
                ow2 = max(8, int(ov2_orig_w * state['ov2_scale'] * sx))
                oh2 = max(8, int(ov2_orig_h * state['ov2_scale'] * sy))
                ox2 = to_canvas_x(state['ov2_x']); oy2 = to_canvas_y(state['ov2_y'])
                logo2_hit = (ox2 <= e.x <= ox2 + ow2 and oy2 <= e.y <= oy2 + oh2)
            video_hit = (vx1 <= e.x <= vx2 and vy1 <= e.y <= vy2)
            text_hit = (tx1 <= e.x <= tx2 and ty1 <= e.y <= ty2)
            if logo2_hit:
                state['selected'] = 'logo2'
            elif logo_hit:
                state['selected'] = 'logo'
            elif text_hit:
                state['selected'] = 'text'
            elif video_hit:
                state['selected'] = 'video'
            else:
                state['selected'] = 'video'
            state['drag_start'] = (e.x, e.y)

        def on_drag(e):
            if not state.get('drag_start'):
                return
            px, py = state['drag_start']
            dx = to_target_x(e.x - px)
            dy = to_target_y(e.y - py)
            state['drag_start'] = (e.x, e.y)
            if state['selected'] == 'video':
                state['vx'] += dx
                state['vy'] += dy
            elif state['selected'] == 'text':
                state['txt_x'] += dx
                state['txt_y'] += dy
            elif state['selected'] == 'logo':
                state['ov_x'] += dx
                state['ov_y'] += dy
            elif state['selected'] == 'logo2':
                state['ov2_x'] += dx
                state['ov2_y'] += dy
            redraw()
            # Sync current editor state into Social "draft" variables
            # so live preview updates automatically (debounced).
            try:
                if state['selected'] == 'video':
                    self.sn_video_zoom_var.set(f"{state['zoom']:.3f}")
                    self.sn_y_shift.set(int(round((state['vy'] + state['vh'] / 2.0) - (th / 2.0))))
                    if hasattr(self, 'sn_x_shift'):
                        self.sn_x_shift.set(int(round((state['vx'] + state['vw'] / 2.0) - (tw / 2.0))))
                elif state['selected'] == 'text':
                    self.sn_text_x_var.set(str(int(round(state['txt_x']))))
                    self.sn_text_y_var.set(str(int(round(state['txt_y']))))
                elif state['selected'] == 'logo':
                    self.sn_overlay_x_var.set(str(int(round(state['ov_x']))))
                    self.sn_overlay_y_var.set(str(int(round(state['ov_y']))))
                elif state['selected'] == 'logo2':
                    self.sn_overlay2_x_var.set(str(int(round(state['ov2_x']))))
                    self.sn_overlay2_y_var.set(str(int(round(state['ov2_y']))))
            except Exception:
                pass

        def on_release(_e):
            state['drag_start'] = None

        def resize_selected(mult):
            if state['selected'] == 'video':
                state['zoom'] = max(0.3, min(3.0, state['zoom'] * mult))
                fit2 = min(tw / max(1, sw), th / max(1, sh))
                old_cx = state['vx'] + state['vw'] / 2.0
                old_cy = state['vy'] + state['vh'] / 2.0
                state['vw'] = max(8, int(sw * fit2 * state['zoom']))
                state['vh'] = max(8, int(sh * fit2 * state['zoom']))
                state['vx'] = old_cx - state['vw'] / 2.0
                state['vy'] = old_cy - state['vh'] / 2.0
            elif state['selected'] == 'text':
                state['txt_size'] = int(max(12, min(220, state['txt_size'] * mult)))
            elif state['selected'] == 'logo':
                state['ov_scale'] = max(0.05, min(8.0, state['ov_scale'] * mult))
            elif state['selected'] == 'logo2':
                state['ov2_scale'] = max(0.05, min(8.0, state['ov2_scale'] * mult))
            redraw()
            # Keep draft in sync during wheel resize.
            try:
                if state['selected'] == 'video':
                    self.sn_video_zoom_var.set(f"{state['zoom']:.3f}")
                    self.sn_y_shift.set(int(round((state['vy'] + state['vh'] / 2.0) - (th / 2.0))))
                    if hasattr(self, 'sn_x_shift'):
                        self.sn_x_shift.set(int(round((state['vx'] + state['vw'] / 2.0) - (tw / 2.0))))
                elif state['selected'] == 'text':
                    self.sn_text_size_var.set(str(int(round(state['txt_size']))))
                elif state['selected'] == 'logo':
                    self.sn_overlay_scale_var.set(f"{state['ov_scale']:.3f}")
                elif state['selected'] == 'logo2':
                    self.sn_overlay2_scale_var.set(f"{state['ov2_scale']:.3f}")
            except Exception:
                pass

        def on_wheel(e):
            # Windows: e.delta is typically +/-120
            delta = getattr(e, 'delta', 0) or 0
            mult = 1.10 if delta > 0 else 0.90
            resize_selected(mult)

        def apply_editor():
            self.sn_video_zoom_var.set(f"{state['zoom']:.3f}")
            self.sn_y_shift.set(int(round((state['vy'] + state['vh'] / 2.0) - (th / 2.0))))
            if hasattr(self, 'sn_x_shift'):
                self.sn_x_shift.set(int(round((state['vx'] + state['vw'] / 2.0) - (tw / 2.0))))
            self.sn_text_x_var.set(str(int(round(state['txt_x']))))
            self.sn_text_y_var.set(str(int(round(state['txt_y']))))
            self.sn_text_size_var.set(str(int(round(state['txt_size']))))
            self.sn_overlay_x_var.set(str(int(round(state['ov_x']))))
            self.sn_overlay_y_var.set(str(int(round(state['ov_y']))))
            self.sn_overlay_scale_var.set(f"{state['ov_scale']:.3f}")
            if hasattr(self, 'sn_overlay2_x_var'):
                self.sn_overlay2_x_var.set(str(int(round(state['ov2_x']))))
            if hasattr(self, 'sn_overlay2_y_var'):
                self.sn_overlay2_y_var.set(str(int(round(state['ov2_y']))))
            if hasattr(self, 'sn_overlay2_scale_var'):
                self.sn_overlay2_scale_var.set(f"{state['ov2_scale']:.3f}")
            self._sn_apply_settings()
            self._sn_log("Layout Editor applied: video + overlays + text updated.")
            win.destroy()

        foot = tk.Frame(win, bg=self.BG2)
        foot.pack(fill=tk.X, padx=20, pady=(0, 10))
        bopt = dict(relief=tk.FLAT, bd=0, cursor='hand2', font=('Segoe UI', 9, 'bold'), padx=10, pady=4)
        tk.Button(foot, text='Apply To Social', bg='#0f4a2a', fg='#dfffe9', command=apply_editor, **bopt).pack(side=tk.LEFT, padx=2)
        tk.Button(foot, text='Cancel', bg='#3a1f1f', fg='#ffd8d8', command=win.destroy, **bopt).pack(side=tk.LEFT, padx=2)

        cv.bind('<Button-1>', on_press)
        cv.bind('<B1-Motion>', on_drag)
        cv.bind('<ButtonRelease-1>', on_release)
        cv.bind('<MouseWheel>', on_wheel)
        redraw()

    def _sn_collect_settings_from_ui(self):
        return {
            'start': self.sn_start_var.get() if hasattr(self, 'sn_start_var') else '00:00:00',
            'end': self.sn_end_var.get() if hasattr(self, 'sn_end_var') else '',
            'max_duration': self.sn_max_duration_var.get() if hasattr(self, 'sn_max_duration_var') else 'Auto',
            'fill_mode': self.sn_fill_mode_var.get() if hasattr(self, 'sn_fill_mode_var') else 'Blur Fill',
            'y_shift': int(self.sn_y_shift.get()) if hasattr(self, 'sn_y_shift') else 0,
            'x_shift': int(self.sn_x_shift.get()) if hasattr(self, 'sn_x_shift') else 0,
            'video_zoom': self.sn_video_zoom_var.get() if hasattr(self, 'sn_video_zoom_var') else '1.00',
            'bg_img': self.sn_bg_img_var.get() if hasattr(self, 'sn_bg_img_var') else '',
            'text': self.sn_text_var.get() if hasattr(self, 'sn_text_var') else '',
            'text_color': self.sn_text_color_var.get() if hasattr(self, 'sn_text_color_var') else 'white',
            'text_size': self.sn_text_size_var.get() if hasattr(self, 'sn_text_size_var') else '46',
            'text_x': self.sn_text_x_var.get() if hasattr(self, 'sn_text_x_var') else '(w-text_w)/2',
            'text_y': self.sn_text_y_var.get() if hasattr(self, 'sn_text_y_var') else 'h*0.82',
            'text_start': self.sn_text_start_var.get() if hasattr(self, 'sn_text_start_var') else '0',
            'text_end': self.sn_text_end_var.get() if hasattr(self, 'sn_text_end_var') else '',
            'overlay_img': self.sn_overlay_img_var.get() if hasattr(self, 'sn_overlay_img_var') else '',
            'overlay_scale': self.sn_overlay_scale_var.get() if hasattr(self, 'sn_overlay_scale_var') else '1.0',
            'overlay_opacity': self.sn_overlay_opacity_var.get() if hasattr(self, 'sn_overlay_opacity_var') else '1.0',
            'overlay_x': self.sn_overlay_x_var.get() if hasattr(self, 'sn_overlay_x_var') else 'W-w-36',
            'overlay_y': self.sn_overlay_y_var.get() if hasattr(self, 'sn_overlay_y_var') else 'H-h-36',
            'overlay_start': self.sn_overlay_start_var.get() if hasattr(self, 'sn_overlay_start_var') else '0',
            'overlay_end': self.sn_overlay_end_var.get() if hasattr(self, 'sn_overlay_end_var') else '',
            'overlay2_img': self.sn_overlay2_img_var.get() if hasattr(self, 'sn_overlay2_img_var') else '',
            'overlay2_scale': self.sn_overlay2_scale_var.get() if hasattr(self, 'sn_overlay2_scale_var') else '1.0',
            'overlay2_opacity': self.sn_overlay2_opacity_var.get() if hasattr(self, 'sn_overlay2_opacity_var') else '1.0',
            'overlay2_x': self.sn_overlay2_x_var.get() if hasattr(self, 'sn_overlay2_x_var') else 'W-w-120',
            'overlay2_y': self.sn_overlay2_y_var.get() if hasattr(self, 'sn_overlay2_y_var') else 'H-h-120',
            'volume': float(self.sn_volume_var.get()) if hasattr(self, 'sn_volume_var') else 1.0,
            'fade_in': self.sn_fade_in_var.get() if hasattr(self, 'sn_fade_in_var') else '0',
            'fade_out': self.sn_fade_out_var.get() if hasattr(self, 'sn_fade_out_var') else '0',
            'remove_audio': bool(self.insta_remove_audio_var.get()) if hasattr(self, 'insta_remove_audio_var') else False,
            'extra_audio': (self.insta_extra_audio_var.get() or '').strip() if hasattr(self, 'insta_extra_audio_var') else '',
            'extra_audio_mode': (self.insta_extra_audio_mode_var.get() or 'Replace').strip() if hasattr(self, 'insta_extra_audio_mode_var') else 'Replace',
            'extra_mix_vol': float(self.insta_extra_mix_vol_var.get()) if hasattr(self, 'insta_extra_mix_vol_var') else 0.35,
            'srt_path': (self.insta_srt_var.get() or '').strip() if hasattr(self, 'insta_srt_var') else '',
            'insta_video_codec': (self.insta_video_codec_var.get() or '').strip() if hasattr(self, 'insta_video_codec_var') else '',
            'insta_custom_res': (self.insta_custom_res_var.get() or '').strip() if hasattr(self, 'insta_custom_res_var') else '',
            'insta_zoom': (self.insta_zoom_var.get() or '1.0').strip() if hasattr(self, 'insta_zoom_var') else '1.0',
            'insta_crop': (self.insta_crop_var.get() or '').strip() if hasattr(self, 'insta_crop_var') else '',
            'insta_audio_bitrate': (self.insta_audio_bitrate_var.get() or '128k').strip() if hasattr(self, 'insta_audio_bitrate_var') else '128k',
            'insta_compress': bool(self.insta_compress_var.get()) if hasattr(self, 'insta_compress_var') else False,
            'insta_audio_codec': (self.insta_audio_codec_var.get() or 'aac').strip().lower() if hasattr(self, 'insta_audio_codec_var') else 'aac',
            'insta_layer_bg': (self.insta_layer_bg_var.get() or '').strip() if hasattr(self, 'insta_layer_bg_var') else '',
            'insta_layer_top': (self.insta_layer_top_var.get() or '').strip() if hasattr(self, 'insta_layer_top_var') else '',
            'insta_layer_bottom': (self.insta_layer_bottom_var.get() or '').strip() if hasattr(self, 'insta_layer_bottom_var') else '',
            'insta_layer_center': (self.insta_layer_center_var.get() or '').strip() if hasattr(self, 'insta_layer_center_var') else '',
            'insta_layer_layout_json': (self.insta_layer_layout_json_var.get() or '').strip() if hasattr(self, 'insta_layer_layout_json_var') else '',
        }

    def _sn_apply_settings(self):
        self._sn_applied_settings = self._sn_collect_settings_from_ui()
        self._sn_log("Applied current social export settings.")
        self.sn_status.config(text="Settings applied. Preview/Export uses these values.")
        # After "Apply" we also refresh the live preview quickly (debounced).
        self._sn_schedule_live_preview(delay_ms=150)
        try:
            self._social_workspace_sync_player()
        except Exception:
            pass

    def _sn_reset_settings(self):
        self.sn_start_var.set('00:00:00')
        self.sn_end_var.set('')
        self.sn_max_duration_var.set('90')
        self.sn_fill_mode_var.set('Blur Fill')
        self.sn_y_shift.set(0)
        if hasattr(self, 'sn_x_shift'):
            self.sn_x_shift.set(0)
        self.sn_video_zoom_var.set('1.00')
        self.sn_text_var.set('')
        self.sn_text_color_var.set('white')
        self.sn_text_size_var.set('46')
        self.sn_text_x_var.set('(w-text_w)/2')
        self.sn_text_y_var.set('h*0.82')
        self.sn_text_start_var.set('0')
        self.sn_text_end_var.set('')
        self.sn_overlay_img_var.set('')
        if hasattr(self, 'sn_overlay2_img_var'):
            self.sn_overlay2_img_var.set('')
        if hasattr(self, 'sn_bg_img_var'):
            self.sn_bg_img_var.set('')
        self.sn_overlay_scale_var.set('1.0')
        self.sn_overlay_opacity_var.set('1.0')
        self.sn_overlay_x_var.set('W-w-36')
        self.sn_overlay_y_var.set('H-h-36')
        self.sn_overlay_start_var.set('0')
        self.sn_overlay_end_var.set('')
        if hasattr(self, 'sn_overlay2_scale_var'):
            self.sn_overlay2_scale_var.set('1.0')
        if hasattr(self, 'sn_overlay2_opacity_var'):
            self.sn_overlay2_opacity_var.set('1.0')
        if hasattr(self, 'sn_overlay2_x_var'):
            self.sn_overlay2_x_var.set('W-w-120')
        if hasattr(self, 'sn_overlay2_y_var'):
            self.sn_overlay2_y_var.set('H-h-120')
        self.sn_volume_var.set(1.0)
        self.sn_fade_in_var.set('0')
        self.sn_fade_out_var.set('0')
        self.sn_preset_var.set('Custom')
        if hasattr(self, 'insta_remove_audio_var'):
            self.insta_remove_audio_var.set(False)
        if hasattr(self, 'insta_extra_audio_var'):
            self.insta_extra_audio_var.set('')
        if hasattr(self, 'insta_srt_var'):
            self.insta_srt_var.set('')
        if hasattr(self, 'insta_extra_audio_mode_var'):
            self.insta_extra_audio_mode_var.set('Replace')
        if hasattr(self, 'insta_extra_mix_vol_var'):
            self.insta_extra_mix_vol_var.set(0.35)
        if hasattr(self, 'insta_video_codec_var'):
            self.insta_video_codec_var.set('H.264')
        self._sn_apply_settings()
        self._sn_log("Reset social settings to defaults.")

    def _sn_schedule_live_preview(self, delay_ms=650):
        if not getattr(self, 'sn_auto_preview_var', None):
            return
        if not bool(self.sn_auto_preview_var.get()):
            return
        if not getattr(self, '_sn_traces_ready', False):
            return
        try:
            pl = self._social_player()
            if pl and getattr(pl, '_playing', False):
                # Don't fight user playback with continuous auto renders.
                return
        except Exception:
            pass
        # Avoid piling up preview renders: if one is running, mark dirty.
        if self._sn_preview_running:
            self._sn_preview_dirty = True
            if self._sn_live_preview_after_id:
                try:
                    self.root.after_cancel(self._sn_live_preview_after_id)
                except Exception:
                    pass
                self._sn_live_preview_after_id = None
            return
        if self._sn_live_preview_after_id:
            try:
                self.root.after_cancel(self._sn_live_preview_after_id)
            except Exception:
                pass
            self._sn_live_preview_after_id = None
        self._sn_live_preview_after_id = self.root.after(int(delay_ms), self._sn_start_live_preview_from_draft)

    def _sn_start_live_preview_from_draft(self):
        # Scheduled callback runs on UI thread.
        self._sn_live_preview_after_id = None
        inp = (self.sn_input_var.get() or '').strip() if hasattr(self, 'sn_input_var') else ''
        if not inp or not os.path.exists(inp):
            return
        if not ffmpeg_mgr.ffmpeg_path:
            return
        # Use current draft UI values (not applied settings).
        self._start_social_preview()

    def _sn_setup_live_preview_traces(self):
        if getattr(self, '_sn_traces_set', False):
            return
        self._sn_traces_ready = False
        # Live preview triggers only on visual parameters.
        watch_vars = [
            self.sn_platform_var,
            self.sn_fill_mode_var,
            self.sn_y_shift,
            self.sn_x_shift,
            self.sn_video_zoom_var,
            self.sn_text_var,
            self.sn_text_color_var,
            self.sn_text_size_var,
            self.sn_text_x_var,
            self.sn_text_y_var,
            self.sn_overlay_img_var,
            self.sn_overlay_scale_var,
            self.sn_overlay_opacity_var,
            self.sn_overlay_x_var,
            self.sn_overlay_y_var,
            self.sn_bg_img_var,
            self.sn_overlay2_img_var,
            self.sn_overlay2_scale_var,
            self.sn_overlay2_opacity_var,
            self.sn_overlay2_x_var,
            self.sn_overlay2_y_var,
            self.sn_volume_var,
            self.sn_fade_in_var,
            self.sn_fade_out_var,
        ]
        # trace_add("write", ...) çağırışında Tcl 3 arqument ötürür — *args qəbul etməlidir.
        def mk_cb(*_args):
            self._sn_schedule_live_preview(delay_ms=650)

        for v in watch_vars:
            try:
                v.trace_add('write', mk_cb)
            except Exception:
                pass

        # Instagram iş pəncərəsi: qat yolu / layout dəyişəndə sağ pleyeri sinxron saxla (debounce).
        self._ig_ws_layer_preview_after = None

        def _schedule_ig_workspace_layer_preview(*_args):
            win = getattr(self, "_social_workspace_win", None)
            if not win:
                return
            try:
                if not win.winfo_exists():
                    return
            except tk.TclError:
                return
            if self._ig_ws_layer_preview_after is not None:
                try:
                    self.root.after_cancel(self._ig_ws_layer_preview_after)
                except Exception:
                    pass
                self._ig_ws_layer_preview_after = None

            def _go():
                self._ig_ws_layer_preview_after = None
                try:
                    self._instagram_workspace_preview_mode()
                except Exception:
                    pass

            self._ig_ws_layer_preview_after = self.root.after_idle(_go)

        for _name in (
            "insta_layer_bg_var",
            "insta_layer_top_var",
            "insta_layer_bottom_var",
            "insta_layer_center_var",
            "insta_layer_layout_json_var",
        ):
            if hasattr(self, _name):
                try:
                    getattr(self, _name).trace_add("write", _schedule_ig_workspace_layer_preview)
                except Exception:
                    pass

        self._sn_traces_set = True
        self._sn_traces_ready = True


    def _social_player(self):
        return self._players.get('social')

    def _active_social_video_player(self):
        """Instagram / iş pəncərəsi açıqdırsa sağdakı pleyer, əks halda Social tab pleyeri."""
        try:
            win = getattr(self, '_social_workspace_win', None)
            if win is not None and win.winfo_exists():
                pl = getattr(self, '_social_workspace_player', None)
                if pl is not None:
                    return pl
        except Exception:
            pass
        return self._social_player()

    def _social_workspace_dialog_parent(self):
        from orvix.social_workspace import social_workspace_dialog_parent
        return social_workspace_dialog_parent(self)

    def _social_workspace_raise(self):
        win = getattr(self, '_social_workspace_win', None)
        if not win:
            return
        try:
            if not win.winfo_exists():
                return
            win.lift()
            win.attributes('-topmost', True)
            win.after(120, lambda w=win: w.attributes('-topmost', False))
            win.focus_force()
        except Exception:
            pass

    def _social_workspace_show_in_player(self, filepath):
        """Konkret faylı iş pəncərəsi pleyerində dərhal göstər (önizləmə / export çıxışı)."""
        pl = getattr(self, '_social_workspace_player', None)
        if not pl or not filepath or not os.path.exists(filepath):
            return
        try:
            pl.preview_file(filepath)
            self._social_workspace_raise()
        except Exception as ex:
            print(f"workspace show in player: {ex}")

    def _social_workspace_sync_player(self, prefer_output=False):
        """İş pəncərəsi sağındakı pleyerdə mənbə və ya çıxışı göstər."""
        pl = getattr(self, '_social_workspace_player', None)
        win = getattr(self, '_social_workspace_win', None)
        if not pl:
            return
        if win:
            try:
                if not win.winfo_exists():
                    return
            except tk.TclError:
                return
        inp = (self.sn_input_var.get() or '').strip()
        out = (self.sn_output_var.get() or '').strip()
        try:
            if prefer_output and out and os.path.exists(out):
                pl.preview_file(out)
            elif inp and os.path.exists(inp):
                pl.preview_file(inp)
                start_t = self._parse_hms_to_seconds(self.sn_start_var.get()) if hasattr(self, 'sn_start_var') else 0.0
                if start_t is None:
                    start_t = 0.0
                if start_t > 0.01:
                    pl.seek(start_t)
            elif out and os.path.exists(out):
                pl.preview_file(out)
        except Exception as ex:
            print(f"workspace player sync: {ex}")
        self._social_workspace_raise()

    def _social_open_source_in_player(self):
        inp = (self.sn_input_var.get() or '').strip()
        if not inp or not os.path.exists(inp):
            messagebox.showwarning("No Input", "Select a valid input file first.")
            return
        start_t = self._parse_hms_to_seconds(self.sn_start_var.get()) if hasattr(self, 'sn_start_var') else 0.0
        if start_t is None:
            start_t = 0.0
        wpl = getattr(self, '_social_workspace_player', None)
        wwin = getattr(self, '_social_workspace_win', None)
        if wpl and wwin:
            try:
                if wwin.winfo_exists():
                    try:
                        wpl.preview_file(inp)
                        if start_t > 0.01:
                            wpl.seek(start_t)
                        self._social_workspace_sync_player()
                        self.sn_status.config(text="Source: playing in workspace player.")
                        self._sn_log(f"Source in workspace player: {os.path.basename(inp)} @ {format_time(start_t)}")
                        return
                    except Exception as e:
                        messagebox.showerror("Player Error", str(e))
                        return
            except tk.TclError:
                pass
        pl = self._social_player()
        if not pl:
            messagebox.showwarning("Player", "Social tab player is not ready.")
            return
        try:
            pl.preview_file(inp)
            if start_t > 0.01:
                pl.seek(start_t)
            self.sn_status.config(text="Source: preview on the right player (press Play).")
            self._sn_log(f"Source loaded in player: {os.path.basename(inp)} @ {format_time(start_t)}")
        except Exception as e:
            messagebox.showerror("Player Error", str(e))

    def _sn_log(self, msg):
        ts = datetime.datetime.now().strftime('%H:%M:%S')
        self.sn_log.insert(tk.END, f"[{ts}] {msg}\n")
        self.sn_log.see(tk.END)

    def _sn_mirror_status(self, text):
        try:
            if hasattr(self, "instagram_ws_status_var"):
                self.instagram_ws_status_var.set(text)
        except Exception:
            pass
        try:
            self.sn_status.config(text=text)
        except Exception:
            pass

    def _sn_mirror_progress_detail(self, text):
        try:
            if hasattr(self, "instagram_progress_detail_var"):
                self.instagram_progress_detail_var.set(text)
        except Exception:
            pass

    def _instagram_workspace_preview_mode(self):
        """Seçilmiş Feed / Reels / Stories preset-inə görə pleyerdə real vaxt kəsmə önizləməsi."""
        import os

        def _same_video_path(a: str, b: str) -> bool:
            if not a or not b:
                return False
            try:
                return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))
            except Exception:
                return a == b

        # StringVar/Entry sinxronu — "Video file seçmək" ilə eyni anda UI oxunur.
        try:
            self.root.update_idletasks()
        except Exception:
            pass

        try:
            self._instagram_setup_workspace_player()
        except Exception:
            pass
        try:
            from orvix.instagram_layer_preview import clear_preview_caches

            clear_preview_caches()
        except Exception:
            pass
        try:
            from orvix import instagram_panel as ig

            pl = getattr(self, "_social_workspace_player", None)
            if not pl:
                return
            key = ig.resolve_instagram_preset_key(self)
            d = ig.INSTAGRAM_MODES.get(key, {})
            res = (d.get("export") or {}).get("res", "1080x1080")
            try:
                tw, th = res.split("x", 1)
                tw, th = int(tw), int(th)
            except Exception:
                tw, th = 1080, 1080
            pl.set_preview_target_size(tw, th)
            pl.set_preview_badge(f"  •  {key}  {tw}×{th}")
            inp = (self.sn_input_var.get() or "").strip()
            # Əsas video yox, amma qatlar var — boş kadr + kompozit (əvvəl yalnız «Video seç» ilə görünürdü).
            if not inp or not os.path.exists(inp):
                if self._instagram_any_layer_path_set():
                    try:
                        dummy = np.full((720, 1280, 3), 32, dtype=np.uint8)
                        pl.preview_rgb_frame(dummy, 0.0)
                    except Exception:
                        pass
                return
            cur = getattr(pl, "_filepath", None)
            # Eyni videodasan: preview_file(stop) çağırma — yalnız kompoziti dərhal yenilə.
            if cur and _same_video_path(cur, inp):
                try:
                    pl.refresh_composite_at_current_time()
                except Exception:
                    pl.preview_file(inp)
            else:
                pl.preview_file(inp)
        except Exception:
            pass

    def _instagram_parse_vb_mbps(self, vb):
        s = str(vb).strip().upper().replace(" ", "")
        try:
            if s.endswith("M"):
                return float(s[:-1])
            if s.endswith("K"):
                return float(s[:-1]) / 1000.0
            return float(s) / 1e6
        except Exception:
            return 6.5

    def _instagram_workspace_play_sync(self):
        self._instagram_workspace_preview_mode()
        pl = getattr(self, "_social_workspace_player", None)
        inp = (self.sn_input_var.get() or "").strip()
        if not pl or not inp or not os.path.exists(inp):
            return
        try:
            pl.play_media()
        except Exception:
            pass

    def _instagram_layer_paths_active(self, s):
        for k in ("insta_layer_bg", "insta_layer_top", "insta_layer_bottom", "insta_layer_center"):
            p = (s.get(k) or "").strip()
            if p:
                return True
        return False

    def _instagram_any_layer_path_set(self):
        """UI-da qat yolu varmı (əsas video olmadan da önizləmə üçün)."""
        for vn in (
            "insta_layer_bg_var",
            "insta_layer_top_var",
            "insta_layer_bottom_var",
            "insta_layer_center_var",
        ):
            if hasattr(self, vn):
                try:
                    if (getattr(self, vn).get() or "").strip():
                        return True
                except Exception:
                    pass
        return False

    def _instagram_layer_preview_frame(self, frame_rgb):
        """Pleyer: 1920×1080 qat + video kompoziti (numpy RGB)."""
        # Həmişə cari UI — StringVar birbaşa (collect ilə birləşik) ki, yol dərhal pleyerə düşsün.
        s = self._sn_collect_settings_from_ui()

        def _pick(sk, vn):
            a = (s.get(sk) or "").strip()
            if hasattr(self, vn):
                b = (getattr(self, vn).get() or "").strip()
                return b or a
            return a

        paths = {
            "bg": _pick("insta_layer_bg", "insta_layer_bg_var"),
            "top": _pick("insta_layer_top", "insta_layer_top_var"),
            "bottom": _pick("insta_layer_bottom", "insta_layer_bottom_var"),
            "center": _pick("insta_layer_center", "insta_layer_center_var"),
        }
        if not any((paths["bg"], paths["top"], paths["bottom"], paths["center"])):
            return frame_rgb
        try:
            from orvix.instagram_layer_layout import parse_layout_json
            from orvix.instagram_layer_preview import composite_1920_frame

            lj = (s.get("insta_layer_layout_json") or "").strip()
            if hasattr(self, "insta_layer_layout_json_var"):
                lj = (self.insta_layer_layout_json_var.get() or "").strip() or lj
            layout = parse_layout_json(lj)
            return composite_1920_frame(np.ascontiguousarray(frame_rgb), layout, paths)
        except Exception:
            return frame_rgb

    def _instagram_setup_workspace_player(self):
        pl = getattr(self, "_social_workspace_player", None)
        if not pl:
            return
        try:
            if getattr(self, "_instagram_workspace_simple", False):
                pl.set_instagram_composite_preview(None)
                pl.set_instagram_layer_interaction(None)
            else:
                pl.set_instagram_composite_preview(self._instagram_layer_preview_frame)
                pl.set_instagram_layer_interaction(self)
        except Exception:
            pass

    def _instagram_try_compose_layers(self, inp0, s, start_t, target_dur):
        """1920×1080 ara fayl yaradır; uğursuzluqda (None, True), əks halda (path, False)."""
        from orvix.instagram_layer_layout import parse_layout_json
        from orvix.instagram_layers_ffmpeg import run_compose

        if not self._instagram_layer_paths_active(s):
            return inp0, False
        layers = {
            "bg": (s.get("insta_layer_bg") or "").strip(),
            "top": (s.get("insta_layer_top") or "").strip(),
            "bottom": (s.get("insta_layer_bottom") or "").strip(),
            "center": (s.get("insta_layer_center") or "").strip(),
        }
        for k, p in layers.items():
            if not p:
                continue
            if not os.path.isfile(p):
                messagebox.showerror("Instagram layers", f"File not found ({k}): {p}")
                return None, True
        layout = parse_layout_json(s.get("insta_layer_layout_json") or "")
        fi_probe = FileInfoExtractor.extract(inp0)
        has_main_audio = fi_probe.get("audio") is not None
        fd, path = tempfile.mkstemp(suffix=".mp4")
        os.close(fd)
        ok, err = run_compose(
            ffmpeg_mgr.ffmpeg_path,
            inp0,
            layers,
            layout,
            start_t=float(start_t or 0),
            target_dur=target_dur,
            out_path=path,
            has_audio=has_main_audio,
            log_fn=self._sn_log,
        )
        if not ok:
            try:
                os.remove(path)
            except Exception:
                pass
            messagebox.showerror("Instagram layers", (err or "FFmpeg")[:2000])
            return None, True
        self._sn_temp_input_cleanup = path
        return path, False

    def _start_instagram_convert_simple(self):
        """Instagram iş pəncərəsi: mətn/overlay olmadan yalnız scale/crop + encode."""
        inp = self.sn_input_var.get().strip()
        out = self.sn_output_var.get().strip()
        if not inp or not os.path.exists(inp):
            messagebox.showerror("Error", "Invalid input file!")
            return
        if not out:
            messagebox.showwarning("No Output", "Set output file path.")
            return
        if not ffmpeg_mgr.ffmpeg_path:
            messagebox.showerror("FFmpeg", "FFmpeg not found!")
            return
        if self._sn_running:
            return
        s = self._sn_applied_settings or self._sn_collect_settings_from_ui()
        p = dict(self._sn_platforms.get("Instagram", {}))
        if hasattr(self, "insta_bitrate_var"):
            p["vb"] = str(self.insta_bitrate_var.get()).strip() or p.get("vb", "6.5M")
        if hasattr(self, "insta_fps_var"):
            p["fps"] = str(self.insta_fps_var.get()).strip() or p.get("fps", "30")

        res_raw = (s.get("insta_custom_res") or "").strip().replace(" ", "").lower()
        if res_raw and re.match(r"^\d+x\d+$", res_raw):
            res = res_raw
        else:
            res = p.get("res", "1080x1080")
        w, h = res.split("x", 1)
        w, h = int(w), int(h)

        _cuda_caps = getattr(ffmpeg_mgr, "cuda_caps", None)
        vc_used = map_lib_codec_to_nvenc("libx264", _cuda_caps)
        vb = p.get("vb", "6.5M")
        fps = str(p.get("fps", "30"))
        ab = str(s.get("insta_audio_bitrate", "128k")).strip() or "128k"
        remove_audio = bool(s.get("remove_audio", False))
        compress = bool(s.get("insta_compress", False))
        zoom = self._sn_safe_float(str(s.get("insta_zoom", "1.0")), default=1.0, min_v=0.25, max_v=4.0)
        crop_str = str(s.get("insta_crop", "")).strip().replace(" ", "")

        start_t = self._parse_hms_to_seconds(s.get("start", "00:00:00"))
        if start_t is None:
            messagebox.showerror("Error", "Invalid Start time format.")
            return
        end_t = self._parse_hms_to_seconds(s.get("end", ""))
        if end_t is not None and end_t <= start_t:
            messagebox.showerror("Error", "End time must be greater than Start.")
            return
        max_dur = None
        max_dur_str = str(s.get("max_duration", "Auto")).strip()
        if max_dur_str and max_dur_str.lower() != "auto":
            max_dur = self._sn_safe_float(max_dur_str, default=90.0, min_v=1.0, max_v=36000.0)
        target_dur = None
        if end_t is not None:
            target_dur = max(0.05, end_t - start_t)
        if max_dur is not None:
            target_dur = min(target_dur, max_dur) if target_dur is not None else max_dur

        inp_orig = inp
        enc_start_t = start_t
        enc_target_dur = target_dur
        if self._instagram_layer_paths_active(s) and not getattr(self, "_instagram_workspace_simple", False):
            self._sn_mirror_status("Merging layers…")
            try:
                self.root.update_idletasks()
            except Exception:
                pass
            new_inp, layer_err = self._instagram_try_compose_layers(inp_orig, s, start_t, target_dur)
            if layer_err:
                return
            if new_inp != inp_orig:
                inp = new_inp
                enc_start_t = 0.0
                enc_target_dur = None

        if crop_str and re.match(r"^\d+:\d+:\d+:\d+$", crop_str):
            if abs(zoom - 1.0) > 0.001:
                vf = (
                    f"scale=iw*{zoom:.6f}:ih*{zoom:.6f}:flags=lanczos,"
                    f"crop={crop_str},scale={w}:{h}:flags=lanczos,format=yuv420p"
                )
            else:
                vf = f"crop={crop_str},scale={w}:{h}:flags=lanczos,format=yuv420p"
        else:
            if abs(zoom - 1.0) > 0.001:
                vf = (
                    f"scale=iw*{zoom:.6f}:ih*{zoom:.6f}:flags=lanczos,"
                    f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},format=yuv420p"
                )
            else:
                vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},format=yuv420p"

        fi_probe = FileInfoExtractor.extract(inp)
        has_main_audio = fi_probe.get("audio") is not None

        bg_img = str(s.get("bg_img", "")).strip()
        bg_is_image = False
        if bg_img:
            bg_ext = os.path.splitext(bg_img)[1].lower()
            bg_is_image = bg_ext in {".png", ".jpg", ".jpeg", ".webp"}
        use_bg_img = bool(bg_img and os.path.exists(bg_img) and bg_is_image)

        fill_mode = s.get("fill_mode", "Blur Fill")
        video_zoom_bg = self._sn_safe_float(s.get("video_zoom", 1.0), default=1.0, min_v=0.3, max_v=3.0)
        x_shift = int(s.get("x_shift", 0) or 0)
        y_shift = int(s.get("y_shift", 0) or 0)
        blur_bg = fill_mode == "Blur Fill"
        bg_blur_part = ",boxblur=18:2" if blur_bg else ""

        td_bg = enc_target_dur
        if use_bg_img and td_bg is None:
            total_dur_v = float(fi_probe.get("format", {}).get("duration_sec", 0) or 0.0)
            td_bg = max(0.1, total_dur_v - enc_start_t)

        if use_bg_img:
            # Əsas Social export ilə eyni: fon tam kadr, video mərkəzdə (sn_video_zoom_var)
            fc = (
                f"[1:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}{bg_blur_part}[bg];"
                f"[0:v]scale={w}:{h}:force_original_aspect_ratio=decrease,scale=iw*{video_zoom_bg:.4f}:ih*{video_zoom_bg:.4f}[fg];"
                f"[bg][fg]overlay=((W-w)/2+{x_shift}):((H-h)/2+{y_shift})[vout]"
            )
            cmd = [ffmpeg_mgr.ffmpeg_path, "-y"] + hwaccel_cuda_prefix(_cuda_caps)
            if enc_start_t > 0:
                cmd += ["-ss", f"{enc_start_t:.3f}"]
            cmd += ["-i", inp]
            cmd += ["-loop", "1", "-t", f"{td_bg:.3f}", "-i", bg_img]
            cmd += ["-filter_complex", fc, "-map", "[vout]"]
            if remove_audio:
                cmd += ["-an"]
            else:
                cmd += ["-map", "0:a?"]
            cmd += ["-t", f"{td_bg:.3f}"]
            cmd += instagram_simple_video_args(vc_used, compress, vb, fps, _cuda_caps)
            if not remove_audio and has_main_audio:
                cmd += ["-c:a", "aac", "-b:a", ab, "-ar", "48000"]
            cmd += ["-movflags", "+faststart", "-progress", "pipe:1", "-nostats", out]
        else:
            cmd = [ffmpeg_mgr.ffmpeg_path, "-y"] + hwaccel_cuda_prefix(_cuda_caps)
            if enc_start_t > 0:
                cmd += ["-ss", f"{enc_start_t:.3f}"]
            cmd += ["-i", inp, "-vf", vf]
            if enc_target_dur is not None:
                cmd += ["-t", f"{enc_target_dur:.3f}"]
            cmd += instagram_simple_video_args(vc_used, compress, vb, fps, _cuda_caps)
            if remove_audio:
                cmd += ["-an"]
            elif has_main_audio:
                cmd += ["-c:a", "aac", "-b:a", ab, "-ar", "48000"]
            cmd += ["-movflags", "+faststart", "-progress", "pipe:1", "-nostats", out]

        self._sn_running = True
        self._sn_cancel = False
        self.sn_pv.set(0)
        self._sn_mirror_status("Preparing…")
        self._sn_mirror_progress_detail("")
        self.sn_log.delete("1.0", tk.END)
        self._sn_log("INSTAGRAM CONVERT (simple): " + " ".join(cmd))
        fi = FileInfoExtractor.extract(inp)
        total_dur = float(fi.get("format", {}).get("duration_sec", 0) or 0.0)
        if inp == inp_orig:
            if end_t is not None:
                total_dur = max(0.0, min(total_dur, end_t) - start_t)
            elif start_t > 0:
                total_dur = max(0.0, total_dur - start_t)
            if target_dur is not None and target_dur > 0:
                total_dur = min(total_dur, target_dur) if total_dur > 0 else target_dur
        if use_bg_img and td_bg is not None:
            total_dur = td_bg
        self._sn_total_dur = total_dur
        threading.Thread(target=self._run_social_thread, args=(cmd,), daemon=True).start()
        self.root.after(0, self._instagram_workspace_play_sync)

    def _start_social(self):
        inp = self.sn_input_var.get().strip()
        out = self.sn_output_var.get().strip()
        if not inp or not os.path.exists(inp):
            messagebox.showerror("Error", "Invalid input file!")
            return
        if not out:
            messagebox.showwarning("No Output", "Set output file path.")
            return
        if not ffmpeg_mgr.ffmpeg_path:
            messagebox.showerror("FFmpeg", "FFmpeg not found!")
            return
        if self._sn_running:
            if getattr(self, "_sn_pause", False):
                self._sn_resume_social_encoding()
            return
        plat = self.sn_platform_var.get()
        if getattr(self, "_instagram_convert_only", False) and plat == "Instagram":
            self._start_instagram_convert_simple()
            return
        p = self._sn_platforms.get(plat, {})
        res = p.get('res', '1920x1080')
        w, h = res.split('x')
        s = self._sn_applied_settings or self._sn_collect_settings_from_ui()
        start_t = self._parse_hms_to_seconds(s.get('start', '00:00:00'))
        if start_t is None:
            messagebox.showerror("Error", "Invalid Start time format.")
            return
        end_t = self._parse_hms_to_seconds(s.get('end', ''))
        if end_t is not None and end_t <= start_t:
            messagebox.showerror("Error", "End time must be greater than Start.")
            return
        max_dur = None
        max_dur_str = str(s.get('max_duration', 'Auto')).strip()
        if max_dur_str and max_dur_str.lower() != 'auto':
            max_dur = self._sn_safe_float(max_dur_str, default=90.0, min_v=1.0, max_v=300.0)
        target_dur = None
        if end_t is not None:
            target_dur = max(0.05, end_t - start_t)
        if max_dur is not None:
            target_dur = min(target_dur, max_dur) if target_dur is not None else max_dur
        if plat in ("TikTok", "Triller", "Snapchat", "WhatsApp"):
            # Qısa vertikal format üçün müddət aralığı (köhnə Instagram Reels məntiqi).
            if target_dur is None:
                target_dur = 90.0
            target_dur = min(90.0, max(15.0, target_dur))
        y_shift = int(s.get('y_shift', 0) or 0)
        x_shift = int(s.get('x_shift', 0) or 0)
        video_zoom = self._sn_safe_float(s.get('video_zoom', 1.0), default=1.0, min_v=0.3, max_v=3.0)
        fill_mode = s.get('fill_mode', 'Solid Black')

        bg_img = str(s.get('bg_img', '')).strip()
        bg_is_image = False
        if bg_img:
            bg_ext = os.path.splitext(bg_img)[1].lower()
            bg_is_image = bg_ext in {'.png', '.jpg', '.jpeg', '.webp'}
        use_bg_img = bool(bg_img and os.path.exists(bg_img) and bg_is_image)
        if bg_img and not use_bg_img:
            messagebox.showerror("Background", "Only background images (.png/.jpg/.jpeg/.webp) are supported.")
            return

        ov_img = str(s.get('overlay_img', '')).strip()
        ov1_is_image = False
        if ov_img:
            ov1_ext = os.path.splitext(ov_img)[1].lower()
            ov1_is_image = ov1_ext in {'.png', '.jpg', '.jpeg', '.webp'}
        use_overlay_img = bool(ov_img and os.path.exists(ov_img))
        if ov_img and not use_overlay_img:
            messagebox.showerror("Error", "Overlay image path is invalid.")
            return

        ov2_img = str(s.get('overlay2_img', '')).strip()
        ov2_is_image = False
        if ov2_img:
            ov2_ext = os.path.splitext(ov2_img)[1].lower()
            ov2_is_image = ov2_ext in {'.png', '.jpg', '.jpeg', '.webp'}
        use_overlay2 = bool(ov2_img and os.path.exists(ov2_img))
        if ov2_img and not use_overlay2:
            messagebox.showerror("Error", "Overlay2 path is invalid.")
            return

        # Input indices (in the order we will add -i)
        next_in = 1
        bg_idx = next_in if use_bg_img else None
        if bg_idx is not None:
            next_in += 1
        ov1_idx = next_in if use_overlay_img else None
        if ov1_idx is not None:
            next_in += 1
        ov2_idx = next_in if use_overlay2 else None
        if ov2_idx is not None:
            next_in += 1

        extra_audio_path = str(s.get('extra_audio', '')).strip()
        remove_audio = bool(s.get('remove_audio', False))
        extra_mode = str(s.get('extra_audio_mode', 'Replace')).strip()
        use_extra_audio = bool(extra_audio_path and os.path.exists(extra_audio_path) and not remove_audio)
        extra_audio_idx = None
        if use_extra_audio:
            extra_audio_idx = next_in
            next_in += 1
        fi_probe = FileInfoExtractor.extract(inp)
        has_main_audio = fi_probe.get('audio') is not None

        # Build filter graph
        vf_chain = []
        if use_bg_img:
            blur_bg = (fill_mode == 'Blur Fill')
            bg_blur_part = ',boxblur=18:2' if blur_bg else ''
            vf_chain.append(
                f"[{bg_idx}:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}{bg_blur_part}[bg]"
            )
            vf_chain.append(
                f"[0:v]scale={w}:{h}:force_original_aspect_ratio=decrease,scale=iw*{video_zoom:.4f}:ih*{video_zoom:.4f}[fg]"
            )
            vf_chain.append(f"[bg][fg]overlay=((W-w)/2+{x_shift}):((H-h)/2+{y_shift})[v0]")
        else:
            if fill_mode == 'Blur Fill':
                vf_chain.append(
                    f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},boxblur=18:2[bg]"
                )
            else:
                bg_color = 'white' if fill_mode == 'Solid White' else 'black'
                vf_chain.append(f"color=c={bg_color}:size={w}x{h}:d=99999[bg]")
            vf_chain.append(
                f"[0:v]scale={w}:{h}:force_original_aspect_ratio=decrease,scale=iw*{video_zoom:.4f}:ih*{video_zoom:.4f}[fg]"
            )
            vf_chain.append(f"[bg][fg]overlay=((W-w)/2+{x_shift}):((H-h)/2+{y_shift})[v0]")

        last_v = "v0"
        txt = str(s.get('text', '')).strip()
        if txt:
            txt_esc = self._sn_escape_drawtext(txt)
            txt_color = str(s.get('text_color', 'white')).strip() or 'white'
            txt_size = int(self._sn_safe_float(s.get('text_size', 46), default=46, min_v=12, max_v=160))
            txt_x = str(s.get('text_x', '(w-text_w)/2')).strip() or '(w-text_w)/2'
            txt_y = str(s.get('text_y', 'h*0.82')).strip() or 'h*0.82'
            txt_s = self._sn_safe_float(s.get('text_start', 0), default=0.0, min_v=0.0)
            txt_e_raw = str(s.get('text_end', '')).strip()
            txt_e = self._sn_safe_float(txt_e_raw, default=(target_dur if target_dur else 99999), min_v=txt_s) if txt_e_raw else (target_dur if target_dur else 99999)
            vf_chain.append(
                f"[{last_v}]drawtext=text='{txt_esc}':fontsize={txt_size}:fontcolor={txt_color}:x={txt_x}:y={txt_y}:enable='between(t,{txt_s:.3f},{txt_e:.3f})'[v1]"
            )
            last_v = "v1"

        # Overlay2 first (optional)
        if use_overlay2:
            ov2_scale = self._sn_safe_float(s.get('overlay2_scale', 1.0), default=1.0, min_v=0.05, max_v=8.0)
            ov2_opacity = self._sn_safe_float(s.get('overlay2_opacity', 1.0), default=1.0, min_v=0.0, max_v=1.0)
            ov2_x = str(s.get('overlay2_x', 'W-w-120')).strip() or 'W-w-120'
            ov2_y = str(s.get('overlay2_y', 'H-h-120')).strip() or 'H-h-120'
            ov2_s = 0.0
            ov2_e = (target_dur if target_dur else 99999)
            vf_chain.append(
                f"[{ov2_idx}:v]scale=iw*{ov2_scale:.4f}:ih*{ov2_scale:.4f},format=rgba,colorchannelmixer=aa={ov2_opacity:.3f}[ov20]"
            )
            vf_chain.append(f"[{last_v}][ov20]overlay={ov2_x}:{ov2_y}:enable='between(t,{ov2_s:.3f},{ov2_e:.3f})'[v2]")
            last_v = "v2"

        # Overlay1 (logo) on top
        if use_overlay_img:
            ov_scale = self._sn_safe_float(s.get('overlay_scale', 1.0), default=1.0, min_v=0.05, max_v=8.0)
            ov_opacity = self._sn_safe_float(s.get('overlay_opacity', 1.0), default=1.0, min_v=0.0, max_v=1.0)
            ov_x = str(s.get('overlay_x', 'W-w-36')).strip() or 'W-w-36'
            ov_y = str(s.get('overlay_y', 'H-h-36')).strip() or 'H-h-36'
            ov_s = self._sn_safe_float(s.get('overlay_start', 0), default=0.0, min_v=0.0)
            ov_e_raw = str(s.get('overlay_end', '')).strip()
            ov_e = self._sn_safe_float(ov_e_raw, default=(target_dur if target_dur else 99999), min_v=ov_s) if ov_e_raw else (target_dur if target_dur else 99999)
            out_label = "v3" if use_overlay2 else "v2"
            vf_chain.append(
                f"[{ov1_idx}:v]scale=iw*{ov_scale:.4f}:ih*{ov_scale:.4f},format=rgba,colorchannelmixer=aa={ov_opacity:.3f}[ov0]"
            )
            vf_chain.append(f"[{last_v}][ov0]overlay={ov_x}:{ov_y}:enable='between(t,{ov_s:.3f},{ov_e:.3f})'[{out_label}]")
            last_v = out_label

        srt_path = str(s.get('srt_path', '')).strip()
        if srt_path and os.path.exists(srt_path):
            esc = ffmpeg_escape_subtitle_path(srt_path)
            vf_chain.append(f"[{last_v}]subtitles='{esc}'[vsubs]")
            last_v = "vsubs"

        fc_video = ';'.join(vf_chain)
        vc_used = p.get('vc', 'libx264')
        if plat == 'Instagram':
            ic = str(s.get('insta_video_codec', '')).strip()
            if ic == 'H.265':
                vc_used = 'libx265'
            elif ic == 'H.264':
                vc_used = 'libx264'

        _hw = hwaccel_cuda_prefix(getattr(ffmpeg_mgr, "cuda_caps", None))
        cmd = [ffmpeg_mgr.ffmpeg_path, '-y'] + _hw
        cmd += ['-i', inp]  # main first; -ss handled below per-video inputs
        if start_t > 0:
            # Restart main input seek without touching other indices
            cmd = [ffmpeg_mgr.ffmpeg_path, '-y'] + _hw + ['-ss', f'{start_t:.3f}', '-i', inp]

        if use_bg_img:
            if target_dur is None:
                messagebox.showerror("Background", "Background image requires Max(s) or End time (finite preview duration).")
                return
            if bg_is_image:
                cmd += ['-loop', '1', '-t', f'{target_dur:.3f}', '-i', bg_img]
            else:
                cmd += ['-i', bg_img]

        if use_overlay_img:
            if ov1_is_image:
                if target_dur is None:
                    messagebox.showerror("Overlay1", "Overlay1 image requires finite duration (Max(s) or End).")
                    return
                cmd += ['-loop', '1', '-t', f'{target_dur:.3f}', '-i', ov_img]
            else:
                if start_t > 0:
                    cmd += ['-ss', f'{start_t:.3f}']
                cmd += ['-i', ov_img]

        if use_overlay2:
            if ov2_is_image:
                if target_dur is None:
                    messagebox.showerror("Overlay2", "Overlay2 image requires finite duration (Max(s) or End).")
                    return
                cmd += ['-loop', '1', '-t', f'{target_dur:.3f}', '-i', ov2_img]
            else:
                if start_t > 0:
                    cmd += ['-ss', f'{start_t:.3f}']
                cmd += ['-i', ov2_img]

        if use_extra_audio:
            cmd += ['-i', extra_audio_path]

        if remove_audio:
            cmd += ['-filter_complex', fc_video, '-map', f'[{last_v}]', '-an']
        elif use_extra_audio and extra_mode == 'Mix' and has_main_audio:
            vol = self._sn_safe_float(s.get('volume', 1.0), default=1.0, min_v=0.0, max_v=4.0)
            exv = self._sn_safe_float(s.get('extra_mix_vol', 0.35), default=0.35, min_v=0.0, max_v=2.0)
            fc_audio = (
                f"[0:a]volume={vol:.4f}[a0];[{extra_audio_idx}:a]volume={exv:.4f}[a1];"
                f"[a0][a1]amix=inputs=2:duration=first:dropout_transition=2[aout]"
            )
            cmd += ['-filter_complex', fc_video + ';' + fc_audio, '-map', f'[{last_v}]', '-map', '[aout]']
        elif use_extra_audio and extra_mode == 'Mix' and not has_main_audio:
            cmd += ['-filter_complex', fc_video, '-map', f'[{last_v}]', '-map', f'{extra_audio_idx}:a']
        elif use_extra_audio:
            cmd += ['-filter_complex', fc_video, '-map', f'[{last_v}]', '-map', f'{extra_audio_idx}:a']
        else:
            cmd += ['-filter_complex', fc_video, '-map', f'[{last_v}]', '-map', '0:a?']

        if target_dur is not None:
            cmd += ['-t', f'{target_dur:.3f}']
        _caps = getattr(ffmpeg_mgr, "cuda_caps", None)
        cmd += social_main_export_video_args(vc_used, p.get('vb', '4M'), p.get('fps', '30'), _caps)
        _vc_out = map_lib_codec_to_nvenc(vc_used, _caps)
        if _vc_out in ('libx265', 'hevc_nvenc'):
            cmd += ['-tag:v', 'hvc1']
        if not remove_audio:
            cmd += ['-c:a', p.get('ac', 'aac'), '-b:a', p.get('ab', '128k')]
            if plat == 'Instagram' and str(p.get('ac', 'aac')).lower() == 'aac':
                cmd += ['-ar', str(p.get('ar', '48000'))]
        afs = []
        volume = self._sn_safe_float(s.get('volume', 1.0), default=1.0, min_v=0.0, max_v=4.0)
        use_af = (
            not remove_audio
            and not (use_extra_audio and extra_mode == 'Mix' and has_main_audio)
        )
        if use_af:
            if abs(volume - 1.0) > 0.001:
                afs.append(f"volume={volume:.3f}")
            fade_in = self._sn_safe_float(s.get('fade_in', 0), default=0.0, min_v=0.0, max_v=30.0)
            fade_out = self._sn_safe_float(s.get('fade_out', 0), default=0.0, min_v=0.0, max_v=30.0)
            if fade_in > 0:
                afs.append(f"afade=t=in:st=0:d={fade_in:.3f}")
            if fade_out > 0 and target_dur and target_dur > fade_out:
                afs.append(f"afade=t=out:st={max(0.0, target_dur - fade_out):.3f}:d={fade_out:.3f}")
        if afs:
            cmd += ['-af', ','.join(afs)]
        cmd += ['-movflags', '+faststart', '-progress', 'pipe:1', '-nostats', out]
        self._sn_running = True
        self._sn_cancel = False
        self.sn_pv.set(0)
        self.sn_status.config(text="Starting...")
        self.sn_log.delete('1.0', tk.END)
        self._sn_log("SOCIAL CONVERT STARTED: " + ' '.join(cmd))
        fi = FileInfoExtractor.extract(inp)
        total_dur = float(fi.get('format', {}).get('duration_sec', 0) or 0.0)
        if end_t is not None:
            total_dur = max(0.0, min(total_dur, end_t) - start_t)
        elif start_t > 0:
            total_dur = max(0.0, total_dur - start_t)
        if target_dur is not None and target_dur > 0:
            total_dur = min(total_dur, target_dur) if total_dur > 0 else target_dur
        self._sn_total_dur = total_dur
        threading.Thread(target=self._run_social_thread, args=(cmd,), daemon=True).start()

    def _start_social_preview(self):
        inp = self.sn_input_var.get().strip()
        if not inp or not os.path.exists(inp):
            messagebox.showerror("Error", "Invalid input file!")
            return
        if not ffmpeg_mgr.ffmpeg_path:
            messagebox.showerror("FFmpeg", "FFmpeg not found!")
            return
        if self._sn_preview_running:
            return
        try:
            prev_len = int(float((self.sn_preview_len_var.get() or '8').strip()))
        except Exception:
            prev_len = 8
        prev_len = max(3, min(20, prev_len))
        prev_out = os.path.join(tempfile.gettempdir(), f"orvix_social_preview_{uuid.uuid4().hex[:10]}.mp4")

        # Reuse current social settings by temporarily forcing preview duration.
        old_max = self.sn_max_duration_var.get() if hasattr(self, 'sn_max_duration_var') else 'Auto'
        try:
            if hasattr(self, 'sn_max_duration_var'):
                self.sn_max_duration_var.set(str(prev_len))
            plat = self.sn_platform_var.get()
            p = self._sn_platforms.get(plat, {})
            res = p.get('res', '1920x1080')
            w, h = res.split('x')
            s = self._sn_collect_settings_from_ui()
            start_t = self._parse_hms_to_seconds(s.get('start', '00:00:00'))
            if start_t is None:
                messagebox.showerror("Error", "Invalid Start time format.")
                return
            end_t = self._parse_hms_to_seconds(s.get('end', ''))
            if end_t is not None and end_t <= start_t:
                messagebox.showerror("Error", "End time must be greater than Start.")
                return
            max_dur = float(prev_len)
            target_dur = max_dur if end_t is None else min(max_dur, max(0.05, end_t - start_t))
            y_shift = int(s.get('y_shift', 0) or 0)
            x_shift = int(s.get('x_shift', 0) or 0)
            video_zoom = self._sn_safe_float(s.get('video_zoom', 1.0), default=1.0, min_v=0.3, max_v=3.0)
            fill_mode = s.get('fill_mode', 'Solid Black')

            bg_img = str(s.get('bg_img', '')).strip()
            bg_is_image = False
            if bg_img:
                bg_ext = os.path.splitext(bg_img)[1].lower()
                bg_is_image = bg_ext in {'.png', '.jpg', '.jpeg', '.webp'}
            use_bg_img = bool(bg_img and os.path.exists(bg_img) and bg_is_image)
            if bg_img and not use_bg_img:
                messagebox.showerror("Background", "Only background images (.png/.jpg/.jpeg/.webp) are supported.")
                return

            ov_img = str(s.get('overlay_img', '')).strip()
            ov1_is_image = False
            if ov_img:
                ov1_ext = os.path.splitext(ov_img)[1].lower()
                ov1_is_image = ov1_ext in {'.png', '.jpg', '.jpeg', '.webp'}
            use_overlay_img = bool(ov_img and os.path.exists(ov_img))
            if ov_img and not use_overlay_img:
                messagebox.showerror("Error", "Overlay image path is invalid.")
                return

            ov2_img = str(s.get('overlay2_img', '')).strip()
            ov2_is_image = False
            if ov2_img:
                ov2_ext = os.path.splitext(ov2_img)[1].lower()
                ov2_is_image = ov2_ext in {'.png', '.jpg', '.jpeg', '.webp'}
            use_overlay2 = bool(ov2_img and os.path.exists(ov2_img))
            if ov2_img and not use_overlay2:
                messagebox.showerror("Error", "Overlay2 path is invalid.")
                return

            # Input indices
            next_in = 1
            bg_idx = next_in if use_bg_img else None
            if bg_idx is not None:
                next_in += 1
            ov1_idx = next_in if use_overlay_img else None
            if ov1_idx is not None:
                next_in += 1
            ov2_idx = next_in if use_overlay2 else None
            if ov2_idx is not None:
                next_in += 1

            vf_chain = []
            if use_bg_img:
                blur_bg = (fill_mode == 'Blur Fill')
                bg_blur_part = ',boxblur=18:2' if blur_bg else ''
                vf_chain.append(
                    f"[{bg_idx}:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}{bg_blur_part}[bg]"
                )
                vf_chain.append(
                    f"[0:v]scale={w}:{h}:force_original_aspect_ratio=decrease,scale=iw*{video_zoom:.4f}:ih*{video_zoom:.4f}[fg]"
                )
                vf_chain.append(f"[bg][fg]overlay=((W-w)/2+{x_shift}):((H-h)/2+{y_shift})[v0]")
            else:
                if fill_mode == 'Blur Fill':
                    vf_chain.append(
                        f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},boxblur=18:2[bg]"
                    )
                else:
                    bg_color = 'white' if fill_mode == 'Solid White' else 'black'
                    vf_chain.append(f"color=c={bg_color}:size={w}x{h}:d=99999[bg]")
                vf_chain.append(
                    f"[0:v]scale={w}:{h}:force_original_aspect_ratio=decrease,scale=iw*{video_zoom:.4f}:ih*{video_zoom:.4f}[fg]"
                )
                vf_chain.append(f"[bg][fg]overlay=((W-w)/2+{x_shift}):((H-h)/2+{y_shift})[v0]")

            last_v = "v0"
            txt = str(s.get('text', '')).strip()
            if txt:
                txt_esc = self._sn_escape_drawtext(txt)
                txt_color = str(s.get('text_color', 'white')).strip() or 'white'
                txt_size = int(self._sn_safe_float(s.get('text_size', 46), default=46, min_v=12, max_v=160))
                txt_x = str(s.get('text_x', '(w-text_w)/2')).strip() or '(w-text_w)/2'
                txt_y = str(s.get('text_y', 'h*0.82')).strip() or 'h*0.82'
                txt_s = self._sn_safe_float(s.get('text_start', 0), default=0.0, min_v=0.0)
                txt_e = target_dur
                vf_chain.append(
                    f"[{last_v}]drawtext=text='{txt_esc}':fontsize={txt_size}:fontcolor={txt_color}:x={txt_x}:y={txt_y}:enable='between(t,{txt_s:.3f},{txt_e:.3f})'[v1]"
                )
                last_v = "v1"

            # Overlay2 first
            if use_overlay2:
                ov2_scale = self._sn_safe_float(s.get('overlay2_scale', 1.0), default=1.0, min_v=0.05, max_v=8.0)
                ov2_opacity = self._sn_safe_float(s.get('overlay2_opacity', 1.0), default=1.0, min_v=0.0, max_v=1.0)
                ov2_x = str(s.get('overlay2_x', 'W-w-120')).strip() or 'W-w-120'
                ov2_y = str(s.get('overlay2_y', 'H-h-120')).strip() or 'H-h-120'
                vf_chain.append(
                    f"[{ov2_idx}:v]scale=iw*{ov2_scale:.4f}:ih*{ov2_scale:.4f},format=rgba,colorchannelmixer=aa={ov2_opacity:.3f}[ov20]"
                )
                vf_chain.append(
                    f"[{last_v}][ov20]overlay={ov2_x}:{ov2_y}:enable='between(t,0.000,{target_dur:.3f})'[v2]"
                )
                last_v = "v2"

            # Overlay1 (logo) on top
            if use_overlay_img:
                ov_scale = self._sn_safe_float(s.get('overlay_scale', 1.0), default=1.0, min_v=0.05, max_v=8.0)
                ov_opacity = self._sn_safe_float(s.get('overlay_opacity', 1.0), default=1.0, min_v=0.0, max_v=1.0)
                ov_x = str(s.get('overlay_x', 'W-w-36')).strip() or 'W-w-36'
                ov_y = str(s.get('overlay_y', 'H-h-36')).strip() or 'H-h-36'
                out_label = "v3" if use_overlay2 else "v2"
                vf_chain.append(
                    f"[{ov1_idx}:v]scale=iw*{ov_scale:.4f}:ih*{ov_scale:.4f},format=rgba,colorchannelmixer=aa={ov_opacity:.3f}[ov0]"
                )
                vf_chain.append(
                    f"[{last_v}][ov0]overlay={ov_x}:{ov_y}:enable='between(t,0.000,{target_dur:.3f})'[{out_label}]"
                )
                last_v = out_label

            # Inputs
            _caps_pv = getattr(ffmpeg_mgr, "cuda_caps", None)
            cmd = [ffmpeg_mgr.ffmpeg_path, '-y'] + hwaccel_cuda_prefix(_caps_pv)
            if start_t > 0:
                cmd += ['-ss', f'{start_t:.3f}', '-i', inp]
            else:
                cmd += ['-i', inp]

            if use_bg_img:
                cmd += ['-loop', '1', '-t', f'{target_dur:.3f}', '-i', bg_img]

            if use_overlay_img:
                if ov1_is_image:
                    cmd += ['-loop', '1', '-t', f'{target_dur:.3f}', '-i', ov_img]
                else:
                    if start_t > 0:
                        cmd += ['-ss', f'{start_t:.3f}']
                    cmd += ['-i', ov_img]

            if use_overlay2:
                if ov2_is_image:
                    cmd += ['-loop', '1', '-t', f'{target_dur:.3f}', '-i', ov2_img]
                else:
                    if start_t > 0:
                        cmd += ['-ss', f'{start_t:.3f}']
                    cmd += ['-i', ov2_img]

            cmd += ['-filter_complex', ';'.join(vf_chain), '-map', f'[{last_v}]', '-map', '0:a?']
            cmd += ['-t', f'{target_dur:.3f}']
            _aud = ['-c:a', p.get('ac', 'aac'), '-b:a', p.get('ab', '128k')]
            if plat == 'Instagram' and str(p.get('ac', 'aac')).lower() == 'aac':
                _aud += ['-ar', str(p.get('ar', '48000'))]
            cmd += social_main_export_video_args(
                p.get('vc', 'libx264'), p.get('vb', '4M'), p.get('fps', '30'), _caps_pv
            ) + _aud + [
                '-movflags', '+faststart', '-progress', 'pipe:1', '-nostats', prev_out]
        finally:
            if hasattr(self, 'sn_max_duration_var'):
                self.sn_max_duration_var.set(old_max)

        self._sn_preview_running = True
        self._sn_preview_file = prev_out
        self.sn_status.config(text=f"Building preview ({prev_len}s)...")
        self._sn_log("SOCIAL PREVIEW STARTED: " + ' '.join(cmd))
        threading.Thread(target=self._run_social_preview_thread, args=(cmd, prev_out), daemon=True).start()

    def _run_social_preview_thread(self, cmd, out_fp):
        try:
            si = ffmpeg_mgr._get_startupinfo()
            self._sn_preview_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                                     text=True, bufsize=1, startupinfo=si)
            last_lines = []
            for raw in self._sn_preview_proc.stdout:
                line = (raw or '').strip()
                if not line:
                    continue
                if line.startswith('out_time_ms='):
                    try:
                        ms = int(line.split('=')[1])
                        ct = ms / 1_000_000.0
                        self.root.after(0, lambda t=ct: self.sn_status.config(text=f"Preview render: {t:.1f}s"))
                    except Exception:
                        pass
                    continue
                if line.startswith('progress='):
                    continue
                last_lines.append(line)
                if len(last_lines) > 20:
                    last_lines = last_lines[-20:]
                if line.startswith('[error]') or 'Error' in line or 'Invalid' in line:
                    self.root.after(0, lambda m=line: self._sn_log("FFMPEG: " + m))
            self._sn_preview_proc.wait()
            rc = self._sn_preview_proc.returncode
            if rc == 0 and os.path.exists(out_fp):
                def _ok():
                    self.sn_status.config(text="Preview ready — in workspace player.")
                    self._sn_log(f"Preview ready: {out_fp}")
                    wpl = getattr(self, '_social_workspace_player', None)
                    wwin = getattr(self, '_social_workspace_win', None)
                    if wpl and wwin:
                        try:
                            if wwin.winfo_exists():
                                self._social_workspace_show_in_player(out_fp)
                                return
                        except tk.TclError:
                            pass
                    pl = self._social_player()
                    if pl:
                        pl.preview_file(out_fp)
                self.root.after(0, _ok)
            else:
                def _fail():
                    self.sn_status.config(text=f"Preview failed (rc={rc}).")
                    self._sn_log(f"Preview failed with return code: {rc}")
                    if last_lines:
                        self._sn_log("FFmpeg tail:")
                        for ln in last_lines[-8:]:
                            self._sn_log("  " + ln)
                self.root.after(0, _fail)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Preview Error", str(e)))
        finally:
            self._sn_preview_running = False
            self._sn_preview_proc = None
            if getattr(self, '_sn_preview_dirty', False):
                self._sn_preview_dirty = False
                # Render latest draft changes.
                try:
                    self._sn_schedule_live_preview(delay_ms=120)
                except Exception:
                    pass

    def _run_social_thread(self, cmd):
        try:
            si = ffmpeg_mgr._get_startupinfo()
            self._sn_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                              text=True, bufsize=1, startupinfo=si)
            for line in self._sn_proc.stdout:
                if self._sn_cancel:
                    self._sn_proc.terminate()
                    self.root.after(
                        0,
                        lambda: (self._sn_mirror_status("Stopped"), self._sn_mirror_progress_detail("")),
                    )
                    break
                line = line.strip()
                if line.startswith('out_time_ms='):
                    try:
                        ms = int(line.split('=')[1])
                        ct = ms / 1_000_000
                        if self._sn_total_dur > 0:
                            pct = min(99.0, (ct / self._sn_total_dur) * 100)
                            msg = f"Encoding {pct:.0f}%"
                            eta = max(0.0, self._sn_total_dur - ct)
                            vb = "6.5M"
                            if hasattr(self, "insta_bitrate_var"):
                                vb = self.insta_bitrate_var.get() or vb
                            mbps = self._instagram_parse_vb_mbps(vb)
                            approx_mb = (mbps * self._sn_total_dur) / 8.0 if self._sn_total_dur > 0 else 0.0
                            detail = (
                                f"{format_time(ct)} / {format_time(self._sn_total_dur)}  •  "
                                f"ETA {format_time(eta)}  •  ≈{approx_mb:.0f} MB output"
                            )
                            self.root.after(
                                0,
                                lambda p=pct, m=msg, d=detail: (
                                    self.sn_pv.set(p),
                                    self._sn_mirror_status(m),
                                    self._sn_mirror_progress_detail(d),
                                ),
                            )
                    except Exception:
                        pass
                elif line.startswith('progress=end'):
                    self.root.after(
                        0,
                        lambda: (
                            self.sn_pv.set(100),
                            self._sn_mirror_status("Finalizing…"),
                            self._sn_mirror_progress_detail(""),
                        ),
                    )
            self._sn_proc.wait()
            rc = self._sn_proc.returncode
            if rc == 0 and not self._sn_cancel:
                out = self.sn_output_var.get()
                sz = fmt_size(out) if os.path.exists(out) else 'N/A'

                def _export_done():
                    self._sn_mirror_status("Completed")
                    try:
                        self._sn_mirror_progress_detail(f"Output: {sz}" if sz and sz != "N/A" else "")
                    except Exception:
                        pass
                    self._sn_log(f"SUCCESS! {out} ({sz})")
                    try:
                        self._social_workspace_show_in_player(out)
                    except Exception:
                        pass
                    messagebox.showinfo("Done", f"Export complete!\n{out}\n{sz}")

                self.root.after(0, _export_done)
            elif not self._sn_cancel:
                self.root.after(0, lambda: self._sn_mirror_status("Failed"))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Export Error", str(e)))
        finally:
            self._sn_running = False
            self._sn_proc = None
            tp = getattr(self, "_sn_temp_input_cleanup", None)
            if tp:
                try:
                    os.remove(tp)
                except Exception:
                    pass
                self._sn_temp_input_cleanup = None

    def _stop_social(self):
        had_encode = bool(self._sn_running and self._sn_proc)
        had_preview = bool(self._sn_preview_running and self._sn_preview_proc)
        self._sn_pause = False
        if had_encode:
            self._sn_cancel = True
            try:
                self._sn_proc.terminate()
            except Exception:
                pass
        if had_preview:
            try:
                self._sn_preview_proc.terminate()
            except Exception:
                pass
        wpl = getattr(self, "_social_workspace_player", None)
        if wpl and (had_encode or had_preview):
            try:
                wpl.stop()
            except Exception:
                pass
        if had_encode or had_preview:
            try:
                self._sn_mirror_status("Stopped")
            except Exception:
                pass

    def _sn_pause_social_encoding(self):
        if not self._sn_running or self._sn_pause or not self._sn_proc:
            return
        self._sn_pause = True
        try:
            _os_suspend_process(self._sn_proc.pid)
        except Exception:
            pass
        self._sn_log("Social export PAUSE")
        wpl = getattr(self, "_social_workspace_player", None)
        if wpl:
            try:
                wpl.pause_media()
            except Exception:
                pass
        try:
            self._sn_mirror_status("Paused")
        except Exception:
            pass

    def _sn_resume_social_encoding(self):
        if not self._sn_running or not self._sn_pause or not self._sn_proc:
            return
        self._sn_pause = False
        try:
            _os_resume_process(self._sn_proc.pid)
        except Exception:
            pass
        self._sn_log("Social export RESUME")
        wpl = getattr(self, "_social_workspace_player", None)
        if wpl:
            try:
                wpl.play_media()
            except Exception:
                pass
        try:
            self._sn_mirror_status("Encoding…")
        except Exception:
            pass

    # ==================== EDIT FUNCTIONS ====================
    def _edit_browse_input(self):
        fp = filedialog.askopenfilename(title="Select Input Video",
            filetypes=[("Video files", "*.mp4 *.mov *.avi *.mkv *.webm *.wmv *.flv *.ts *.mpg *.mxf *.m4v *.3gp"), ("All files", "*.*")])
        if fp:
            self.edit_input_var.set(fp)
            base, ext = os.path.splitext(fp)
            self.edit_output_var.set(f"{base}_edited.{self.edit_format.get()}")
            self._timeline_reset_from_input()

    def _edit_browse_output(self):
        fmt = self.edit_format.get()
        fp = filedialog.asksaveasfilename(title="Save Edited File",
            defaultextension=f".{fmt}", filetypes=[(f"{fmt.upper()}", f"*.{fmt}"), ("All files", "*.*")])
        if fp:
            self.edit_output_var.set(fp)

    def _edit_use_main_file(self):
        if self.file:
            self.edit_input_var.set(self.file)
            base, ext = os.path.splitext(self.file)
            self.edit_output_var.set(f"{base}_edited.{self.edit_format.get()}")
            self._timeline_reset_from_input()
        else:
            messagebox.showwarning("No File", "Use Open File first.")

    def _edit_log(self, msg):
        ts = datetime.datetime.now().strftime('%H:%M:%S')
        self.edit_log.insert(tk.END, f"[{ts}] {msg}\n")
        self.edit_log.see(tk.END)

    def _edit_reset(self):
        self.edit_start_time.set('00:00:00')
        self.edit_end_time.set('')
        self.edit_duration.set('')
        self.edit_rotate.set('No rotation')
        self.edit_crop_w.set('')
        self.edit_crop_h.set('')
        self.edit_crop_x.set('0')
        self.edit_crop_y.set('0')
        self.edit_scale.set('Original')
        self.edit_brightness.set(1.0)
        self.edit_contrast.set(1.0)
        self.edit_saturation.set(1.0)
        self.edit_gamma.set(1.0)
        self.edit_volume.set(1.0)
        self.edit_audio_filter.set('None')
        self.edit_deinterlace.set(False)
        self.edit_denoise.set(False)
        self.edit_sharpen.set(False)
        self.edit_grayscale.set(False)
        self.edit_vflip.set(False)
        self.edit_hflip.set(False)
        self.edit_speed.set('1.0 (Normal)')
        self.edit_transition.set('None')
        self.edit_transition_dur.set('0.5')
        self._edit_log("Reset to defaults.")
        self._timeline_reset_from_input()

    def _editing_player(self):
        return self._players.get('editing')

    def _parse_hms_to_seconds(self, txt):
        s = (txt or "").strip()
        if not s:
            return None
        try:
            if ':' in s:
                parts = [float(p) for p in s.split(':')]
                if len(parts) == 3:
                    return max(0.0, parts[0] * 3600 + parts[1] * 60 + parts[2])
                if len(parts) == 2:
                    return max(0.0, parts[0] * 60 + parts[1])
            return max(0.0, float(s))
        except Exception:
            return None

    def _timeline_set_trim_vars(self, clip):
        if not clip:
            return
        self.edit_start_time.set(format_time(clip['src_start']))
        self.edit_end_time.set(format_time(clip['src_end']))
        self.edit_duration.set(format_time(max(0.0, clip['src_end'] - clip['src_start'])))

    def _timeline_reset_from_input(self):
        fp = (self.edit_input_var.get() or "").strip()
        if not fp or not os.path.exists(fp):
            self._timeline_clips = []
            self._timeline_playhead = 0.0
            self._timeline_total_duration = 1.0
            if self._timeline_status_var:
                self._timeline_status_var.set("No clip loaded.")
            self._timeline_redraw()
            return
        info = FileInfoExtractor.extract(fp)
        dur = float(info.get('format', {}).get('duration_sec', 0) or 0.0)
        if dur <= 0.01:
            dur = 1.0
        base = os.path.basename(fp)
        self._timeline_clips = [{
            'src': fp,
            'name': base[:28],
            'src_start': 0.0,
            'src_end': dur,
            'offset': 0.0,
        }]
        self._timeline_active_idx = 0
        self._timeline_playhead = 0.0
        self._timeline_total_duration = dur
        self._timeline_set_trim_vars(self._timeline_clips[0])
        if self._timeline_status_var:
            self._timeline_status_var.set(f"Clip: {base}  |  Dur: {format_time(dur)}")
        pl = self._editing_player()
        if pl:
            try:
                pl.preview_file(fp)
            except Exception:
                pass
        self._timeline_redraw()

    def _timeline_duration(self):
        if not self._timeline_clips:
            return max(1.0, self._timeline_total_duration)
        end_t = 0.0
        for c in self._timeline_clips:
            ln = max(0.05, c['src_end'] - c['src_start'])
            end_t = max(end_t, c['offset'] + ln)
        return max(1.0, end_t)

    def _timeline_x_to_time(self, x):
        cv = self._timeline_canvas
        if not cv:
            return 0.0
        w = max(100, cv.winfo_width())
        left = 14
        right = w - 14
        span = max(1.0, right - left)
        dur = self._timeline_duration()
        t = ((x - left) / span) * dur
        return max(0.0, min(dur, t))

    def _timeline_time_to_x(self, t):
        cv = self._timeline_canvas
        if not cv:
            return 14
        w = max(100, cv.winfo_width())
        left = 14
        right = w - 14
        dur = self._timeline_duration()
        return left + (max(0.0, min(dur, t)) / dur) * max(1.0, right - left)

    def _timeline_clip_at_x(self, x):
        if not self._timeline_clips:
            return None, None
        t = self._timeline_x_to_time(x)
        for i, c in enumerate(self._timeline_clips):
            cs = c['offset']
            ce = c['offset'] + max(0.05, c['src_end'] - c['src_start'])
            if cs <= t <= ce:
                return i, c
        return None, None

    def _timeline_redraw(self):
        cv = self._timeline_canvas
        if not cv:
            return
        cv.delete('all')
        w = max(200, cv.winfo_width())
        h = max(100, cv.winfo_height())
        left = 14
        right = w - 14
        track_top = 36
        track_h = 44
        dur = self._timeline_duration()
        cv.create_rectangle(left, track_top, right, track_top + track_h, fill='#0b1a2b', outline='#18344f')
        for i in range(0, 11):
            t = dur * (i / 10.0)
            x = self._timeline_time_to_x(t)
            cv.create_line(x, 16, x, track_top + track_h + 22, fill='#17314b')
            cv.create_text(x + 1, 10, text=format_time(t), fill='#6f8faa', anchor='n', font=('Consolas', 9))
        for i, c in enumerate(self._timeline_clips):
            ln = max(0.05, c['src_end'] - c['src_start'])
            x1 = self._timeline_time_to_x(c['offset'])
            x2 = self._timeline_time_to_x(c['offset'] + ln)
            color = '#1f7acc' if i == self._timeline_active_idx else '#245a8a'
            cv.create_rectangle(x1, track_top + 6, x2, track_top + track_h - 6, fill=color, outline='#a8d8ff', width=1)
            cv.create_text((x1 + x2) / 2.0, track_top + track_h / 2.0, text=c['name'], fill='#eef8ff', font=('Segoe UI', 9, 'bold'))
            cv.create_line(x1, track_top + 4, x1, track_top + track_h - 4, fill='#ffe28a', width=2)
            cv.create_line(x2, track_top + 4, x2, track_top + track_h - 4, fill='#ffe28a', width=2)
        px = self._timeline_time_to_x(self._timeline_playhead)
        cv.create_line(px, 20, px, h - 6, fill='#ff5050', width=2)
        cv.create_polygon(px - 6, 20, px + 6, 20, px, 28, fill='#ff5050', outline='')
        cv.create_text(left, h - 7, anchor='w',
                       text=f"Playhead: {format_time(self._timeline_playhead)}", fill='#9fc7e8', font=('Consolas', 10))

    def _timeline_seek_player(self, t):
        pl = self._editing_player()
        if not pl:
            return
        try:
            if self._timeline_clips:
                c = self._timeline_clips[self._timeline_active_idx]
                clip_len = max(0.05, c['src_end'] - c['src_start'])
                rel = max(0.0, min(clip_len, t - c['offset']))
                src_t = c['src_start'] + rel
            else:
                src_t = t
            pl.seek(src_t)
        except Exception:
            pass

    def _timeline_on_press(self, event):
        if not self._timeline_clips:
            return
        idx, clip = self._timeline_clip_at_x(event.x)
        self._timeline_drag_mode = 'playhead'
        self._timeline_drag_clip_idx = idx
        if idx is not None and clip:
            self._timeline_active_idx = idx
            x1 = self._timeline_time_to_x(clip['offset'])
            x2 = self._timeline_time_to_x(clip['offset'] + max(0.05, clip['src_end'] - clip['src_start']))
            if abs(event.x - x1) <= 7:
                self._timeline_drag_mode = 'trim_in'
            elif abs(event.x - x2) <= 7:
                self._timeline_drag_mode = 'trim_out'
            else:
                self._timeline_drag_mode = 'clip_move'
        self._timeline_playhead = self._timeline_x_to_time(event.x)
        self._timeline_seek_player(self._timeline_playhead)
        self._timeline_redraw()

    def _timeline_on_drag(self, event):
        if not self._timeline_clips:
            return
        t = self._timeline_x_to_time(event.x)
        idx = self._timeline_drag_clip_idx
        if idx is None or idx >= len(self._timeline_clips):
            self._timeline_playhead = t
            self._timeline_seek_player(t)
            self._timeline_redraw()
            return
        c = self._timeline_clips[idx]
        clip_len = max(0.05, c['src_end'] - c['src_start'])
        if self._timeline_drag_mode == 'trim_in':
            src_pos = c['src_start'] + max(0.0, min(clip_len, t - c['offset']))
            c['src_start'] = min(c['src_end'] - 0.04, max(0.0, src_pos))
            self._timeline_set_trim_vars(c)
        elif self._timeline_drag_mode == 'trim_out':
            src_pos = c['src_start'] + max(0.0, min(clip_len, t - c['offset']))
            c['src_end'] = max(c['src_start'] + 0.04, src_pos)
            self._timeline_set_trim_vars(c)
        elif self._timeline_drag_mode == 'clip_move':
            c['offset'] = max(0.0, t - (max(0.05, c['src_end'] - c['src_start']) / 2.0))
        self._timeline_playhead = t
        self._timeline_seek_player(t)
        self._timeline_redraw()

    def _timeline_on_release(self, event):
        self._timeline_drag_mode = None
        self._timeline_drag_clip_idx = None

    def _timeline_set_in_at_playhead(self):
        if not self._timeline_clips:
            return
        c = self._timeline_clips[self._timeline_active_idx]
        local_t = c['src_start'] + max(0.0, self._timeline_playhead - c['offset'])
        c['src_start'] = min(c['src_end'] - 0.04, max(0.0, local_t))
        self._timeline_set_trim_vars(c)
        self._timeline_redraw()

    def _timeline_set_out_at_playhead(self):
        if not self._timeline_clips:
            return
        c = self._timeline_clips[self._timeline_active_idx]
        local_t = c['src_start'] + max(0.0, self._timeline_playhead - c['offset'])
        c['src_end'] = max(c['src_start'] + 0.04, local_t)
        self._timeline_set_trim_vars(c)
        self._timeline_redraw()

    def _timeline_duplicate_clip(self):
        if not self._timeline_clips:
            return
        src = dict(self._timeline_clips[self._timeline_active_idx])
        src_len = max(0.05, src['src_end'] - src['src_start'])
        src['offset'] = self._timeline_duration() + 0.2
        src['name'] = (src.get('name') or 'clip') + " *"
        self._timeline_clips.append(src)
        self._timeline_active_idx = len(self._timeline_clips) - 1
        self._timeline_playhead = src['offset']
        self._timeline_set_trim_vars(src)
        self._timeline_redraw()

    def _on_edit_player_time(self, cur_t, dur_t):
        if self._timeline_sync_guard:
            return
        # Video Editing tab indeksi (notebook sırası ilə uyğun)
        if self.nb.index(self.nb.select()) != 8:
            return
        if not self._timeline_clips:
            return
        c = self._timeline_clips[self._timeline_active_idx]
        timeline_t = c['offset'] + max(0.0, cur_t - c['src_start'])
        self._timeline_playhead = max(0.0, timeline_t)
        self._timeline_redraw()

    def _build_edit_cmd(self, inp, out):
        # Multi-clip timeline path with optional cross dissolve transitions.
        if self._timeline_clips and len(self._timeline_clips) > 1:
            clips = sorted(self._timeline_clips, key=lambda c: float(c.get('offset', 0.0)))
            cmd = [ffmpeg_mgr.ffmpeg_path, '-y']
            clip_durs = []
            for c in clips:
                src = c.get('src') or inp
                src_start = max(0.0, float(c.get('src_start', 0.0) or 0.0))
                src_end = max(src_start + 0.05, float(c.get('src_end', src_start + 0.05) or (src_start + 0.05)))
                clip_dur = max(0.05, src_end - src_start)
                clip_durs.append(clip_dur)
                cmd += ['-ss', f'{src_start:.3f}', '-t', f'{clip_dur:.3f}', '-i', src]

            vparts = []
            aparts = []
            rot = self.edit_rotate.get()
            rot_map = {
                'Rotate 90 CW': 'transpose=1',
                'Rotate 90 CCW': 'transpose=2',
                'Rotate 180': 'transpose=2,transpose=2',
                'Flip Horizontal': 'hflip',
                'Flip Vertical': 'vflip',
                'Flip Both': 'hflip,vflip'
            }
            cw = self.edit_crop_w.get().strip()
            ch = self.edit_crop_h.get().strip()
            cx = self.edit_crop_x.get().strip() or '0'
            cy = self.edit_crop_y.get().strip() or '0'
            sc = self.edit_scale.get()
            br = self.edit_brightness.get()
            ct = self.edit_contrast.get()
            sat = self.edit_saturation.get()
            gm = self.edit_gamma.get()
            speed_str = self.edit_speed.get()
            speed_val = float(speed_str.split()[0])
            for i in range(len(clips)):
                vfs = []
                if cw and ch:
                    vfs.append(f'crop={cw}:{ch}:{cx}:{cy}')
                if sc != 'Original':
                    w, h = sc.split('x')
                    vfs.append(f'scale={w}:{h}')
                if rot in rot_map:
                    vfs.append(rot_map[rot])
                if self.edit_hflip.get():
                    vfs.append('hflip')
                if self.edit_vflip.get():
                    vfs.append('vflip')
                if self.edit_deinterlace.get():
                    vfs.append('yadif')
                if self.edit_denoise.get():
                    vfs.append('hqdn3d')
                if self.edit_sharpen.get():
                    vfs.append('unsharp=5:5:1.0:5:5:0.0')
                if self.edit_grayscale.get():
                    vfs.append('hue=s=0')
                if br != 1.0 or ct != 1.0 or sat != 1.0 or gm != 1.0:
                    vfs.append(f'eq=brightness={br-1:.2f}:contrast={ct:.2f}:saturation={sat:.2f}:gamma={gm:.2f}')
                if speed_val != 1.0:
                    vfs.append(f'setpts={1/speed_val:.4f}*PTS')
                v_chain = ','.join(vfs) if vfs else 'null'
                vparts.append(f'[{i}:v]{v_chain},setpts=PTS-STARTPTS[v{i}]')

                afs = []
                vol = self.edit_volume.get()
                if vol != 1.0:
                    afs.append(f'volume={vol:.2f}')
                af = self.edit_audio_filter.get()
                if af != 'None':
                    afs.append(af)
                if speed_val != 1.0:
                    if 0.5 <= speed_val <= 2.0:
                        afs.append(f'atempo={speed_val:.2f}')
                    elif speed_val > 2.0:
                        afs.append('atempo=2.0')
                        afs.append(f'atempo={speed_val/2.0:.2f}')
                    elif speed_val < 0.5:
                        afs.append('atempo=0.5')
                        afs.append(f'atempo={speed_val/0.5:.2f}')
                a_chain = ','.join(afs) if afs else 'anull'
                aparts.append(f'[{i}:a]{a_chain},asetpts=PTS-STARTPTS[a{i}]')

            transition = (self.edit_transition.get() if hasattr(self, 'edit_transition') else 'None').strip()
            trans_dur = 0.5
            try:
                trans_dur = float((self.edit_transition_dur.get() if hasattr(self, 'edit_transition_dur') else '0.5').strip())
            except Exception:
                trans_dur = 0.5
            trans_dur = max(0.05, min(2.0, trans_dur))
            min_d = min(clip_durs) if clip_durs else 0.1
            trans_dur = min(trans_dur, max(0.05, min_d - 0.02))
            if transition == 'Cross Dissolve':
                v_prev = 'v0'
                offset = max(0.0, clip_durs[0] - trans_dur)
                xparts = []
                for i in range(1, len(clips)):
                    v_out = f'vx{i}'
                    xparts.append(
                        f'[{v_prev}][v{i}]xfade=transition=fade:duration={trans_dur:.3f}:offset={offset:.3f}[{v_out}]'
                    )
                    v_prev = v_out
                    offset += max(0.05, clip_durs[i] - trans_dur)
                a_prev = 'a0'
                for i in range(1, len(clips)):
                    a_out = f'ax{i}'
                    xparts.append(f'[{a_prev}][a{i}]acrossfade=d={trans_dur:.3f}:c1=tri:c2=tri[{a_out}]')
                    a_prev = a_out
                filter_complex = ';'.join(vparts + aparts + xparts)
                cmd += ['-filter_complex', filter_complex, '-map', f'[{v_prev}]', '-map', f'[{a_prev}]']
            else:
                v_in = ''.join([f'[v{i}]' for i in range(len(clips))])
                a_in = ''.join([f'[a{i}]' for i in range(len(clips))])
                filter_complex = ';'.join(vparts + aparts + [f'{v_in}{a_in}concat=n={len(clips)}:v=1:a=1[vout][aout]'])
                cmd += ['-filter_complex', filter_complex, '-map', '[vout]', '-map', '[aout]']
            cmd += (
                edit_export_video_args(getattr(ffmpeg_mgr, "cuda_caps", None), "20")
                + ['-c:a', 'aac', '-b:a', '192k']
            )
            cmd += ['-progress', 'pipe:1', '-nostats', out]
            return cmd

        cmd = [ffmpeg_mgr.ffmpeg_path, '-y'] + hwaccel_cuda_prefix(getattr(ffmpeg_mgr, "cuda_caps", None))
        start = self.edit_start_time.get().strip()
        if start and start != '00:00:00':
            cmd += ['-ss', start]
        cmd += ['-i', inp]
        end = self.edit_end_time.get().strip()
        dur = self.edit_duration.get().strip()
        if end:
            cmd += ['-to', end]
        elif dur:
            cmd += ['-t', dur]
        vfilters = []
        cw = self.edit_crop_w.get().strip()
        ch = self.edit_crop_h.get().strip()
        cx = self.edit_crop_x.get().strip() or '0'
        cy = self.edit_crop_y.get().strip() or '0'
        if cw and ch:
            vfilters.append(f'crop={cw}:{ch}:{cx}:{cy}')
        sc = self.edit_scale.get()
        if sc != 'Original':
            w, h = sc.split('x')
            vfilters.append(f'scale={w}:{h}')
        rot = self.edit_rotate.get()
        rot_map = {
            'Rotate 90 CW': 'transpose=1',
            'Rotate 90 CCW': 'transpose=2',
            'Rotate 180': 'transpose=2,transpose=2',
            'Flip Horizontal': 'hflip',
            'Flip Vertical': 'vflip',
            'Flip Both': 'hflip,vflip'
        }
        if rot in rot_map:
            vfilters.append(rot_map[rot])
        if self.edit_hflip.get():
            vfilters.append('hflip')
        if self.edit_vflip.get():
            vfilters.append('vflip')
        if self.edit_deinterlace.get():
            vfilters.append('yadif')
        if self.edit_denoise.get():
            vfilters.append('hqdn3d')
        if self.edit_sharpen.get():
            vfilters.append('unsharp=5:5:1.0:5:5:0.0')
        if self.edit_grayscale.get():
            vfilters.append('hue=s=0')
        br = self.edit_brightness.get()
        ct = self.edit_contrast.get()
        sat = self.edit_saturation.get()
        gm = self.edit_gamma.get()
        if br != 1.0 or ct != 1.0 or sat != 1.0 or gm != 1.0:
            vfilters.append(f'eq=brightness={br-1:.2f}:contrast={ct:.2f}:saturation={sat:.2f}:gamma={gm:.2f}')
        speed_str = self.edit_speed.get()
        speed_val = float(speed_str.split()[0])
        if speed_val != 1.0:
            vfilters.append(f'setpts={1/speed_val:.4f}*PTS')
        if vfilters:
            cmd += ['-vf', ','.join(vfilters)]
        afilters = []
        vol = self.edit_volume.get()
        if vol != 1.0:
            afilters.append(f'volume={vol:.2f}')
        af = self.edit_audio_filter.get()
        if af != 'None':
            afilters.append(af)
        if speed_val != 1.0:
            if 0.5 <= speed_val <= 2.0:
                afilters.append(f'atempo={speed_val:.2f}')
            elif speed_val > 2.0:
                afilters.append('atempo=2.0')
                afilters.append(f'atempo={speed_val/2.0:.2f}')
            elif speed_val < 0.5:
                afilters.append('atempo=0.5')
                afilters.append(f'atempo={speed_val/0.5:.2f}')
        if afilters:
            cmd += ['-af', ','.join(afilters)]
        cmd += edit_export_video_args(getattr(ffmpeg_mgr, "cuda_caps", None), "20")
        cmd += ['-c:a', 'aac', '-b:a', '192k']
        cmd += ['-progress', 'pipe:1', '-nostats']
        cmd.append(out)
        return cmd

    def _start_edit(self):
        inp = self.edit_input_var.get().strip()
        out = self.edit_output_var.get().strip()
        if not inp or not os.path.exists(inp):
            messagebox.showerror("Error", "Invalid input file!")
            return
        if not out:
            messagebox.showwarning("No Output", "Set output file path.")
            return
        if not ffmpeg_mgr.ffmpeg_path:
            messagebox.showerror("FFmpeg", "FFmpeg not found!")
            return
        if self._edit_running:
            return
        self._edit_running = True
        self._edit_cancel = False
        self.edit_pv.set(0)
        self.edit_status.config(text="Starting edit...")
        self.edit_log.delete('1.0', tk.END)
        cmd = self._build_edit_cmd(inp, out)
        self._edit_log("EDIT STARTED: " + ' '.join(cmd))
        if self._timeline_clips and len(self._timeline_clips) > 1:
            clips = sorted(self._timeline_clips, key=lambda c: float(c.get('offset', 0.0)))
            total = sum(max(0.05, float(c.get('src_end', 0.0) or 0.0) - float(c.get('src_start', 0.0) or 0.0)) for c in clips)
            transition = (self.edit_transition.get() if hasattr(self, 'edit_transition') else 'None').strip()
            if transition == 'Cross Dissolve':
                try:
                    td = float((self.edit_transition_dur.get() if hasattr(self, 'edit_transition_dur') else '0.5').strip())
                except Exception:
                    td = 0.5
                td = max(0.05, min(2.0, td))
                total -= max(0, len(clips) - 1) * td
            self._edit_total_dur = max(0.1, total)
        else:
            fi = FileInfoExtractor.extract(inp)
            self._edit_total_dur = fi.get('format', {}).get('duration_sec', 0)
        threading.Thread(target=self._run_edit_thread, args=(cmd,), daemon=True).start()

    def _run_edit_thread(self, cmd):
        try:
            si = ffmpeg_mgr._get_startupinfo()
            self._edit_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                                text=True, bufsize=1, startupinfo=si)
            for line in self._edit_proc.stdout:
                if self._edit_cancel:
                    self._edit_proc.terminate()
                    self.root.after(0, lambda: self.edit_status.config(text="STOPPED"))
                    break
                line = line.strip()
                if line.startswith('out_time_ms='):
                    try:
                        ms = int(line.split('=')[1])
                        ct = ms / 1_000_000
                        if self._edit_total_dur > 0:
                            pct = min(99.0, (ct / self._edit_total_dur) * 100)
                            msg = f"Editing: {ct:.1f}s / {self._edit_total_dur:.1f}s ({pct:.1f}%)"
                            self.root.after(0, lambda p=pct, m=msg: (self.edit_pv.set(p), self.edit_status.config(text=m)))
                    except Exception:
                        pass
                elif line.startswith('progress=end'):
                    self.root.after(0, lambda: (self.edit_pv.set(100), self.edit_status.config(text="COMPLETE!")))
            self._edit_proc.wait()
            rc = self._edit_proc.returncode
            if rc == 0 and not self._edit_cancel:
                out = self.edit_output_var.get()
                sz = fmt_size(out) if os.path.exists(out) else 'N/A'
                self.root.after(0, lambda: (self._edit_log(f"SUCCESS! {out} ({sz})"),
                                            messagebox.showinfo("Done", f"Edit complete!\n{out}\n{sz}")))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Edit Error", str(e)))
        finally:
            self._edit_running = False
            self._edit_proc = None

    def _stop_edit(self):
        if self._edit_running and self._edit_proc:
            self._edit_cancel = True
            try:
                self._edit_proc.terminate()
            except Exception:
                pass

    def _edit_save_output(self):
        out = self.edit_output_var.get().strip()
        if not out or not os.path.exists(out):
            messagebox.showwarning("No Output", "Run edit first.")
            return
        fmt = os.path.splitext(out)[1].lstrip('.')
        dst = filedialog.asksaveasfilename(title="Save As", defaultextension=f".{fmt}",
            filetypes=[(f"{fmt.upper()}", f"*.{fmt}"), ("All files", "*.*")])
        if dst and dst != out:
            shutil.copy2(out, dst)
            messagebox.showinfo("Saved", f"Saved to:\n{dst}")

    def _edit_export_log(self):
        fp = filedialog.asksaveasfilename(title="Export Log", defaultextension=".txt",
                                           filetypes=[("Text", "*.txt")])
        if fp:
            with open(fp, 'w', encoding='utf-8') as f:
                f.write(self.edit_log.get('1.0', tk.END))
            messagebox.showinfo("Exported", f"Log saved:\n{fp}")

    # ==================== COMMON GUI METHODS ====================
    def _update_dictionary(self, *args):
        search_term = self.dict_search_var.get().lower()
        self.dict_listbox.delete(0, tk.END)
        for key, value in PROBLEM_DICTIONARY.items():
            if search_term in value['name'].lower() or search_term in key.lower():
                self.dict_listbox.insert(tk.END, f"{key} - {value['name']}")

    def _show_problem_detail(self, event):
        selection = self.dict_listbox.curselection()
        if not selection:
            return
        selected = self.dict_listbox.get(selection[0])
        problem_key = selected.split(' - ')[0]
        if problem_key in PROBLEM_DICTIONARY:
            p = PROBLEM_DICTIONARY[problem_key]
            self.dict_detail_text.config(state=tk.NORMAL)
            self.dict_detail_text.delete('1.0', tk.END)
            self.dict_detail_text.insert(tk.END, f"{p['name']}\n\n", 'title')
            self.dict_detail_text.insert(tk.END, "Description:\n", 'label')
            self.dict_detail_text.insert(tk.END, f"{p['description']}\n\n", 'content')
            self.dict_detail_text.insert(tk.END, "Cause:\n", 'label')
            self.dict_detail_text.insert(tk.END, f"{p['cause']}\n\n", 'content')
            self.dict_detail_text.insert(tk.END, "Solution:\n", 'label')
            self.dict_detail_text.insert(tk.END, f"{p['solution']}\n\n", 'content')
            self.dict_detail_text.insert(tk.END, "Example:\n", 'label')
            self.dict_detail_text.insert(tk.END, f"{p['example']}\n", 'content')
            self.dict_detail_text.config(state=tk.DISABLED)

    def _parse_problem_start_time(self, time_range_str):
        """Parse 'MM:SS.mmm -> MM:SS.mmm' and return start time in seconds."""
        try:
            start_str = time_range_str.split('->')[0].strip()
            parts = start_str.split(':')
            if len(parts) == 3:
                h, m, s = parts
                return int(h) * 3600 + int(m) * 60 + float(s)
            elif len(parts) == 2:
                m, s = parts
                return int(m) * 60 + float(s)
            else:
                return float(parts[0])
        except Exception:
            return 0.0

    def _on_critical_problem_dbl_click(self, event=None):
        """Double-click on critical problem: play 2 seconds before problem start."""
        selection = self.critical_tr.selection()
        if not selection:
            return
        item = self.critical_tr.item(selection[0])
        values = item['values']
        if len(values) >= 2:
            time_range = str(values[1])
            start_time = self._parse_problem_start_time(time_range)
            # Update critical problem index for arrow navigation
            all_items = self.critical_tr.get_children()
            for idx, iid in enumerate(all_items):
                if iid == selection[0]:
                    self._critical_problem_index = idx
                    break
            # Play 2 seconds before problem start
            seek_t = max(0.0, start_time - 2.0)
            self._play_problem_in_active_tab(seek_t)
            self._log(f"  >> Critical: {format_time(start_time)} (playing from {format_time(seek_t)})", 'i')

    def _navigate_critical_problems(self, direction):
        """Navigate critical problems with left/right arrow keys."""
        all_items = self.critical_tr.get_children()
        if not all_items:
            return
        if self._critical_problem_index == -1:
            self._critical_problem_index = 0 if direction == 'next' else len(all_items) - 1
        else:
            if direction == 'next':
                self._critical_problem_index = (self._critical_problem_index + 1) % len(all_items)
            else:
                self._critical_problem_index = (self._critical_problem_index - 1) % len(all_items)
        idx = self._critical_problem_index
        if idx < len(all_items):
            iid = all_items[idx]
            self.critical_tr.selection_set(iid)
            self.critical_tr.see(iid)
            item = self.critical_tr.item(iid)
            values = item['values']
            if len(values) >= 2:
                start_time = self._parse_problem_start_time(str(values[1]))
                seek_t = max(0.0, start_time - 2.0)
                self._play_problem_in_active_tab(seek_t)

    def _startup_log(self):
        gpu_info = gpu_acc.get_gpu_info()
        self._log("=" * 60, 'h')
        self._log("  Orvix Lite — Video QC", 'h')
        self._log(f"  GPU: {gpu_info['name']} ({gpu_info['type']})", 'h')
        self._log(f"  Pillow: {'OK' if PIL_AVAILABLE else 'NOT FOUND - pip install Pillow'}", 'ok' if PIL_AVAILABLE else 'e')
        self._log(f"  FFmpeg: {ffmpeg_mgr.ffmpeg_path or 'NOT FOUND'}", 'ok' if ffmpeg_mgr.ffmpeg_path else 'e')
        self._log(f"  SoundDevice: {'OK' if _HAS_SD else 'pip install sounddevice'}", 'ok' if _HAS_SD else 'w')
        self._log("  Player: Aspect-correct fill, no black bars", 'ok')
        self._log("  Sync: Wall-clock video+audio, zero lag", 'ok')
        self._log("  VU Meter: Slim horizontal dB, 60fps", 'ok')
        self._log("  Double-click: plays 2s before problem start", 'ok')
        self._log("  Keys: Left/Right=prev/next | Space=play/pause", 'ok')
        self._log("  Auto-stop: old player stops on tab change", 'ok')
        self._log("=" * 60, 'h')

    def _update_display(self):
        self.status_badge.config(
            text=f"GPU: {gpu_acc.gpu_name} ({gpu_acc.gpu_type})  |  Orvix Lite  |  Video QC")

    def _tick(self):
        et = get_english_time()
        self.time_lbl.config(text=et['time'])
        self.date_lbl.config(text=et['date'])
        self.root.after(1000, self._tick)

    def _open_file(self):
        fp = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[
                ("Video files", "*.mp4 *.mov *.avi *.mkv *.webm *.wmv *.flv *.ts *.mpg *.mxf *.m4v *.3gp"),
                ("All files", "*.*")
            ])
        if not fp:
            return
        for _p in self._players.values():
            try:
                _p.stop()
            except Exception:
                pass
        self.file = fp
        name = os.path.basename(fp)
        self.file_lbl.config(text=f"  {name}", fg=self.FG)
        self.go_btn.config(state=tk.NORMAL)
        self.probs = []
        self.current_problem_index = -1
        self._critical_problem_index = -1
        self._clear_problems()
        self._set_progress(0, f"File loaded: {name}")
        self._log(f"{'─' * 60}", 'h')
        self._log(f"  FILE LOADED: {fp}", 'i')
        self._log(f"{'─' * 60}", 'h')
        self._notify_all_players(fp)
        threading.Thread(target=self._load_file_info, daemon=True).start()

    def _load_file_info(self):
        info = FileInfoExtractor.extract(self.file)
        self.file_info = info
        self.root.after(0, lambda: self._display_file_info(info))
        self.root.after(0, lambda: self._display_broadcast_info(info))

    def _display_broadcast_info(self, info):
        fi = info.get('file', {})
        self.file_info_text.config(state=tk.NORMAL)
        self.file_info_text.delete('1.0', tk.END)
        file_text = f"Filename  : {fi.get('name', 'N/A')}\n"
        file_text += f"Path      : {fi.get('path', 'N/A')}\n"
        file_text += f"Size      : {fi.get('size', 'N/A')}\n"
        file_text += f"Extension : {fi.get('extension', 'N/A')}\n"
        self.file_info_text.insert('1.0', file_text)
        self.file_info_text.config(state=tk.DISABLED)
        vi = info.get('video', {})
        self.video_info_text.config(state=tk.NORMAL)
        self.video_info_text.delete('1.0', tk.END)
        v_text = f"Codec     : {vi.get('codec_full', 'N/A')}\n"
        v_text += f"Resolution: {vi.get('resolution', 'N/A')}\n"
        v_text += f"FPS       : {vi.get('fps_display', 'N/A')}\n"
        v_text += f"Frames    : {vi.get('total_frames', 0):,}\n"
        v_text += f"Bitrate   : {vi.get('bitrate', 'N/A')}\n"
        v_text += f"Pixel Fmt : {vi.get('pixel_format', 'N/A')}\n"
        v_text += f"Scan      : {vi.get('scan_type', 'N/A')}\n"
        v_text += f"Profile   : {vi.get('profile', 'N/A')}\n"
        self.video_info_text.insert('1.0', v_text)
        self.video_info_text.config(state=tk.DISABLED)
        ai = info.get('audio', {})
        self.audio_info_text.config(state=tk.NORMAL)
        self.audio_info_text.delete('1.0', tk.END)
        if ai:
            a_text = f"Codec     : {ai.get('codec_full', 'N/A')}\n"
            a_text += f"Sample Rt : {ai.get('sample_rate_display', 'N/A')}\n"
            a_text += f"Channels  : {ai.get('channels', 0)} — {ai.get('channel_name', 'N/A')}\n"
            a_text += f"Bitrate   : {ai.get('bitrate', 'N/A')}\n"
        else:
            a_text = "No audio stream detected.\n"
        self.audio_info_text.insert('1.0', a_text)
        self.audio_info_text.config(state=tk.DISABLED)
        container = info.get('container', {})
        self.container_info_text.config(state=tk.NORMAL)
        self.container_info_text.delete('1.0', tk.END)
        c_text = f"Format    : {container.get('type', 'N/A')}\n"
        fmt = info.get('format', {})
        if fmt:
            c_text += f"Duration  : {fmt.get('duration', 'N/A')}\n"
            c_text += f"Bitrate   : {fmt.get('bitrate', 'N/A')}\n"
        self.container_info_text.insert('1.0', c_text)
        self.container_info_text.config(state=tk.DISABLED)

    def _display_file_info(self, info):
        t = self.info_text
        t.config(state=tk.NORMAL)
        t.delete('1.0', tk.END)

        def sec(txt):
            t.insert(tk.END, f"\n  {txt}\n", 'section')
            t.insert(tk.END, f"  {'─' * 60}\n", 'sep')

        def row(label, value, tag='value'):
            t.insert(tk.END, f"    {label:<28}", 'label')
            t.insert(tk.END, f"{value}\n", tag)

        t.insert(tk.END, f"  Orvix Lite — Complete File Analysis Report\n", 'title')
        t.insert(tk.END, f"  {get_english_time()['full']}\n", 'sep')
        t.insert(tk.END, f"  {'─' * 60}\n", 'sep')

        # ── FILE INFORMATION ──────────────────────────────────────────────
        fi = info.get('file', {})
        sec("FILE INFORMATION")
        row('Filename', fi.get('name', 'N/A'), 'highlight')
        row('File Path', fi.get('path', 'N/A'), 'path')
        row('File Size', fi.get('size', 'N/A'))
        row('Extension', fi.get('extension', 'N/A'))
        row('Modified Date', fi.get('modified', 'N/A'))

        fmt = info.get('format')
        if fmt and isinstance(fmt, dict):
            row('Duration', fmt.get('duration', 'N/A'), 'highlight')
            row('Overall Bitrate', fmt.get('bitrate', 'N/A'))
            row('Format Name', fmt.get('format_name', 'N/A'))
            nb = fmt.get('nb_streams', 'N/A')
            row('Number of Streams', str(nb))

        # ── VIDEO STREAM ──────────────────────────────────────────────────
        vi = info.get('video')
        if vi:
            sec("VIDEO STREAM — Detailed Parameters")
            row('Codec', vi.get('codec_full', 'N/A'), 'video_param')
            row('Codec Profile', vi.get('profile', 'N/A'), 'video_param')
            row('Codec Level', str(vi.get('level', 'N/A')))
            row('Resolution', vi.get('resolution', 'N/A'), 'video_param')
            row('Sample Aspect Ratio (SAR)', vi.get('sar', 'N/A'))
            row('Display Aspect Ratio (DAR)', vi.get('dar', 'N/A'))
            row('Frame Rate', f"{vi.get('fps_display', 'N/A')} fps", 'video_param')
            row('Total Frames', f"{vi.get('total_frames', 0):,}")
            row('Bit Depth', str(vi.get('bit_depth', 'N/A')))
            row('Pixel Format', vi.get('pixel_format', 'N/A'))
            row('Color Space', vi.get('color_space', 'N/A'))
            row('Color Primaries', vi.get('color_primaries', 'N/A'))
            row('Color Transfer', vi.get('color_transfer', 'N/A'))
            scan = vi.get('scan_type', 'N/A')
            field = vi.get('field_order', 'N/A')
            scan_detail = f"{scan}  (field_order: {field})"
            row('Scan Type', scan_detail, 'video_param')
            row('Video Bitrate', vi.get('bitrate', 'N/A'))

        # ── AUDIO STREAM ──────────────────────────────────────────────────
        ai = info.get('audio')
        if ai:
            sec("AUDIO STREAM — Detailed Parameters")
            row('Codec', ai.get('codec_full', 'N/A'), 'audio_param')
            row('Codec Profile', ai.get('profile', 'N/A'))
            row('Sample Rate', ai.get('sample_rate_display', 'N/A'), 'audio_param')
            ch = ai.get('channels', 0)
            ch_name = ai.get('channel_name', 'N/A')
            ch_layout = ai.get('channel_layout', 'N/A')
            row('Channels', f"{ch}  ({ch_name})", 'audio_param')
            row('Channel Layout', ch_layout)
            row('Bit Depth', str(ai.get('bit_depth', 'N/A')))
            row('Audio Bitrate', ai.get('bitrate', 'N/A'))

        # ── CONTAINER ─────────────────────────────────────────────────────
        container = info.get('container', {})
        sec("CONTAINER")
        row('Container Format', container.get('type', 'N/A'), 'container_param')

        t.insert(tk.END, f"\n  {'─' * 60}\n", 'sep')
        t.config(state=tk.DISABLED)
        self.nb.select(0)

    def _start_analysis(self):
        if not self.file:
            messagebox.showwarning("No file", "Please select a video file first.")
            return
        if self._running:
            return
        self._running = True
        self.probs = []
        self.pcnt = 0
        self.current_problem_index = -1
        self._critical_problem_index = -1
        self._clear_problems()
        self.go_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.exp_btn.config(state=tk.DISABLED)
        self.t0 = time.time()
        self.nb.select(4)
        self._log(f"{'=' * 60}", 'h')
        self._log("  Orvix Lite — ANALYSIS STARTED", 'h')
        self._log(f"  File: {self.file}", 'i')
        self._log(f"  Time: {get_english_time()['full']}", 'ts')
        self._log(f"{'=' * 60}", 'h')
        threading.Thread(target=self._run_analysis, daemon=True).start()

    def _run_analysis(self):
        fi = self.file_info
        if fi is None:
            fi = FileInfoExtractor.extract(self.file)
            self.file_info = fi
        vi = fi.get('video')
        fps = vi.get('fps', 25) if vi else 25
        tot = vi.get('total_frames', 0) if vi else 0
        dur = fi.get('format', {}).get('duration_sec', 0) if fi.get('format') else 0
        if fps <= 0:
            fps = 25
        if tot <= 0 and dur > 0:
            tot = int(dur * fps)
        self._log(f"  FPS: {fps}  Frames: {tot:,}  Duration: {fmt_dur(dur)}", 'i')
        self._log(f"{'─' * 60}", 'h')
        self._log("  VIDEO ANALYSIS", 'i')
        vres = self.va.analyze(
            self.file, fps, tot, dur,
            progress_cb=lambda p, m: self._throttled_analysis_progress(0.7, p, m),
            log_cb=lambda m: self._log(m, 'w' if 'ERROR' in m else 'ok'),
            problem_cb=self._enqueue_problem_safe,
        )
        if vres.get('cancelled'):
            self._log("  Video analysis stopped", 'w')
        else:
            self._log(f"  Video done: {vres.get('frames_analyzed', 0)} frames analyzed", 'ok')
        self._log(f"{'─' * 60}", 'h')
        self._log("  AUDIO ANALYSIS", 'i')
        ares = self.aa.analyze(
            self.file,
            progress_cb=lambda p, m: self._throttled_analysis_progress(1.0, p, m, use_audio_offset=True),
            log_cb=lambda m: self._log(m, 'w' if 'ERROR' in m else 'ok'),
            problem_cb=self._enqueue_problem_safe,
        )
        if not ares.get('has_audio'):
            self._log("  No audio stream detected", 'w')
        elif ares.get('cancelled'):
            self._log("  Audio analysis stopped", 'w')
        else:
            self._log(f"  Audio done: {len(ares.get('problems', []))} issues found", 'ok')
        self.root.after(0, self._finish_analysis)

    def _throttled_analysis_progress(self, scale, p, m, *, use_audio_offset=False):
        """Analiz zamanı progress yeniləməsini seyrəldir (minlərlə after() yığını yox)."""
        try:
            out = float(p) if use_audio_offset else float(p) * scale
        except (TypeError, ValueError):
            return
        now = time.time()
        if out < 99.0 and (now - getattr(self, "_prog_throttle_ts", 0.0)) < 0.12:
            return
        self._prog_throttle_ts = now
        self.root.after(0, lambda o=out, msg=m: self._set_progress(o, msg))

    def _enqueue_problem_safe(self, p):
        """İşçi axından: problemləri növbəyə qoyur; UI partiyalarla yenilənir (əsas thread yüngül)."""
        wake = False
        with self._prob_q_lock:
            self._prob_q_pending.append(p)
            if len(self._prob_q_pending) == 1:
                wake = True
        if wake:
            try:
                self.root.after(0, self._ensure_problem_flush_timer)
            except Exception:
                pass

    def _ensure_problem_flush_timer(self):
        if self._prob_q_flush_id is not None:
            return
        self._prob_q_flush_id = self.root.after(50, self._flush_problem_queue)

    def _flush_problem_queue(self):
        self._prob_q_flush_id = None
        with self._prob_q_lock:
            batch = self._prob_q_pending[:]
            self._prob_q_pending.clear()
        for p in batch:
            self._add_one_problem_row(p)
        if batch:
            self._update_stats_labels()
            try:
                self.root.update_idletasks()
            except Exception:
                pass
        with self._prob_q_lock:
            more = len(self._prob_q_pending) > 0
        if more:
            self._prob_q_flush_id = self.root.after(50, self._flush_problem_queue)

    def _flush_problem_queue_immediate(self):
        """Analiz bitəndə növbədə qalanların hamısını dərhal UI-ya yazır."""
        if self._prob_q_flush_id is not None:
            try:
                self.root.after_cancel(self._prob_q_flush_id)
            except Exception:
                pass
            self._prob_q_flush_id = None
        while True:
            with self._prob_q_lock:
                if not self._prob_q_pending:
                    break
                batch = self._prob_q_pending[:]
                self._prob_q_pending.clear()
            for p in batch:
                self._add_one_problem_row(p)
            if batch:
                self._update_stats_labels()
                try:
                    self.root.update_idletasks()
                except Exception:
                    pass

    def _finish_analysis(self):
        self._flush_problem_queue_immediate()
        self._running = False
        elapsed = time.time() - self.t0
        self.go_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.exp_btn.config(state=tk.NORMAL if self.probs else tk.DISABLED)
        self._set_progress(100, f"Complete! {len(self.probs)} problems in {elapsed:.1f}s")
        self._update_stats_labels()
        self._log(f"{'=' * 60}", 'h')
        self._log(f"  COMPLETE — {len(self.probs)} problems in {elapsed:.1f}s", 'ok')
        self._log(f"{'=' * 60}", 'h')
        if self.probs:
            self.nb.select(1)

    def _stop(self):
        self.va.cancel()
        self.aa.cancel()
        self._log("  Analysis stopped by user", 'e')

    @classmethod
    def _problem_is_critical_for_tab(cls, p):
        """Critical tab: yalnız uzun donma / uzun qara·sessizlik / kəsmə; qalan ERROR-lar All Problems-də."""
        if (p.get('severity') or '').upper() != 'ERROR':
            return False
        t = (p.get('type') or '').upper()
        try:
            dur = float(p.get('duration') or 0)
        except (TypeError, ValueError):
            dur = 0.0
        if t == 'FROZEN':
            return dur >= cls.CRITICAL_TAB_FROZEN_MIN_S
        if t == 'CLIPPING':
            return dur >= cls.CRITICAL_TAB_CLIPPING_MIN_S
        if t == 'BLACK':
            return dur >= cls.CRITICAL_TAB_BLACK_MIN_S
        if t == 'SILENCE':
            return dur >= cls.CRITICAL_TAB_SILENCE_MIN_S
        return False

    def _increment_stat_for_problem(self, p):
        sev = p.get('severity', 'MEDIUM').upper()
        if sev == 'ERROR':
            self._stat_err += 1
        elif sev == 'WARNING':
            self._stat_warn += 1
        elif sev == 'INFO':
            self._stat_info += 1
        cat = (p.get('category') or '').upper()
        if cat == 'VIDEO':
            self._stat_vid += 1
        elif cat == 'AUDIO':
            self._stat_aud += 1

    def _add_one_problem_row(self, p):
        self.probs.append(p)
        self.pcnt += 1
        self._increment_stat_for_problem(p)
        sev = p.get('severity', 'MEDIUM').upper()
        if p.get('type') == 'FROZEN':
            tag = 'error_frozen'
        elif sev == 'ERROR':
            tag = 'error'
        elif sev == 'WARNING':
            tag = 'warning'
        elif sev == 'INFO':
            tag = 'info'
        else:
            tag = ''
        cat = p.get('category', '?').upper()
        start_end = f"{p.get('start_time_str', '?')} -> {p.get('end_time_str', '?')}"
        duration_str = f"{p.get('duration', 0):.2f}s" if p.get('duration', 0) > 0 else '-'
        vals = (str(self.pcnt), sev, cat, p.get('type_az', p.get('type', '?')),
                start_end, duration_str, p.get('description', ''))
        self.tr.insert('', tk.END, iid=str(self.pcnt - 1), values=vals, tags=(tag,))
        if self._problem_is_critical_for_tab(p):
            critical_vals = (str(len(self.critical_tr.get_children()) + 1),
                             start_end,
                             p.get('type_az', p.get('type', '?')),
                             p.get('description', ''))
            self.critical_tr.insert('', tk.END, values=critical_vals, tags=('critical',))

    def _clear_problems(self):
        if self._prob_q_flush_id is not None:
            try:
                self.root.after_cancel(self._prob_q_flush_id)
            except Exception:
                pass
            self._prob_q_flush_id = None
        with self._prob_q_lock:
            self._prob_q_pending.clear()
        self._stat_err = 0
        self._stat_warn = 0
        self._stat_info = 0
        self._stat_vid = 0
        self._stat_aud = 0
        self.pcnt = 0
        for item in self.tr.get_children():
            self.tr.delete(item)
        for item in self.critical_tr.get_children():
            self.critical_tr.delete(item)

    def _update_stats_labels(self):
        total = len(self.probs)
        el = time.time() - self.t0 if self.t0 else 0
        self.st['n'].config(text=f"  {total} Problems")
        self.st['c'].config(text=f"  {self._stat_err} Errors")
        self.st['h'].config(text=f"  {self._stat_warn} Warnings")
        self.st['m'].config(text=f"  {self._stat_info} Info")
        self.st['v'].config(text=f"  {self._stat_vid} Video")
        self.st['a'].config(text=f"  {self._stat_aud} Audio")
        self.st['t'].config(text=f"  {el:.0f}s")

    def _update_stats(self):
        self._update_stats_labels()

    def _get_selected_problem(self):
        sel = self.tr.selection()
        if not sel:
            return None, -1
        iid = sel[0]
        try:
            idx = int(iid)
            if 0 <= idx < len(self.probs):
                return self.probs[idx], idx
        except Exception:
            pass
        return None, -1

    def _navigate_problems(self, direction):
        """Navigate prev/next problem and play video 2s before problem start."""
        if not self.probs or not self.file:
            return
        if direction == 'first':
            self.current_problem_index = 0
        elif direction == 'last':
            self.current_problem_index = len(self.probs) - 1
        elif self.current_problem_index == -1:
            self.current_problem_index = 0 if direction == 'next' else len(self.probs) - 1
        else:
            if direction == 'next':
                self.current_problem_index = (self.current_problem_index + 1) % len(self.probs)
            elif direction == 'prev':
                self.current_problem_index = (self.current_problem_index - 1) % len(self.probs)
        idx = self.current_problem_index
        try:
            self.tr.selection_set(str(idx))
            self.tr.see(str(idx))
            self.tr.focus(str(idx))
        except Exception:
            pass
        self._seek_to_problem_with_preroll(idx)

    def _seek_to_problem_with_preroll(self, index):
        """Play video from 2 seconds before problem start."""
        if not self.file or index < 0 or index >= len(self.probs):
            return
        p = self.probs[index]
        start_t = p.get('start_time', 0.0)
        seek_t = max(0.0, start_t - 2.0)
        self._play_problem_in_active_tab(seek_t)
        self._log(f"  >> Problem {index + 1}: {p['type_az']} at {format_time(start_t)} (playing from {format_time(seek_t)})", 'i')

    def _on_problem_dbl_click(self, event=None):
        """Double-click: play 2 seconds before problem start."""
        p, idx = self._get_selected_problem()
        if p and self.file:
            self.current_problem_index = idx
            self._seek_to_problem_with_preroll(idx)

    def _on_left_arrow(self, event=None):
        """Left arrow: go to previous problem, play 2s before start."""
        self._navigate_problems('prev')
        return "break"

    def _on_right_arrow(self, event=None):
        """Right arrow: go to next problem, play 2s before start."""
        self._navigate_problems('next')
        return "break"

    def _on_ctrl_left(self, event=None):
        self._navigate_problems('first')
        return "break"

    def _on_ctrl_right(self, event=None):
        self._navigate_problems('last')
        return "break"

    def _export(self):
        if not self.probs:
            messagebox.showinfo("Export", "No problems to export.")
            return
        fp = filedialog.asksaveasfilename(title="Export Report",
            defaultextension=".txt",
            filetypes=[("Text report", "*.txt"), ("CSV", "*.csv"), ("All", "*.*")])
        if not fp:
            return
        try:
            with open(fp, 'w', encoding='utf-8') as f:
                now = get_english_time()
                gpu_info = gpu_acc.get_gpu_info()
                f.write(f"Orvix Lite — ANALYSIS REPORT\n{'=' * 70}\n")
                f.write(f"Generated : {now['full']}\n")
                f.write(f"GPU       : {gpu_info['name']} ({gpu_info['type']})\n")
                if self.file:
                    f.write(f"File      : {self.file}\n")
                f.write(f"Problems  : {len(self.probs)}\n{'=' * 70}\n\n")
                critical = [p for p in self.probs if self._problem_is_critical_for_tab(p)]
                if critical:
                    f.write("CRITICAL PROBLEMS:\n" + "-" * 70 + "\n")
                    for p in critical:
                        f.write(f"[{p.get('start_time_str', '?')} -> {p.get('end_time_str', '?')}] {p.get('type_az', p.get('type', '?'))}\n")
                    f.write("\n")
                f.write("ALL PROBLEMS:\n" + "-" * 70 + "\n")
                for i, p in enumerate(self.probs, 1):
                    f.write(f"[{i:04d}] {p.get('start_time_str', '?'):<12} -> {p.get('end_time_str', '?'):<12} {p.get('severity', '?'):<8} {p.get('type_az', p.get('type', '?')):<20}\n")
            messagebox.showinfo("Export", f"Report saved:\n{fp}")
            self._log(f"  Report exported: {fp}", 'ok')
        except Exception as e:
            messagebox.showerror("Export error", str(e))

    def _log(self, msg, tag='i'):
        def _do():
            ts = datetime.datetime.now().strftime('%H:%M:%S')
            self.lg.insert(tk.END, f"[{ts}] {msg}\n", tag)
            self.lg.see(tk.END)
        if threading.current_thread() is threading.main_thread():
            _do()
        else:
            self.root.after(0, _do)

    def _set_progress(self, pct, msg=''):
        def _do():
            self.pv.set(min(100, max(0, pct)))
            if msg:
                self.pl.config(text=f"  {msg}")
        if threading.current_thread() is threading.main_thread():
            _do()
        else:
            self.root.after(0, _do)

