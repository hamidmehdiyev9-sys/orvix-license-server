"""Embedded video player + VU meter."""
import os
import subprocess
import threading
import time
import tkinter as tk
from tkinter import ttk

import cv2
import numpy as np
from PIL import Image, ImageTk

from orvix.audio_player import SoundAudioPlayer
from orvix.deps import PIL_AVAILABLE
from orvix.ffmpeg_core import ffmpeg_mgr
from orvix.utils import format_time
from orvix.vu_meter import VerticalVUMeter

class EmbeddedVideoPlayer:
    """
    Embedded video player:
    - No black bars: video fills the panel using aspect-ratio letterbox inside canvas
    - Prev/Next 10s skip buttons
    - Volume change: smooth (no video restart, only audio level change)
    - Seek: smooth (no shaking)
    - VU Meter: vertical, dB-scaled, at the bottom of the player panel
    - Perfect A/V sync: wall-clock based
    - Only ONE player active at a time
    """

    PLAYER_BG = '#070a10'
    CTRL_BG = '#0b1020'
    BTN_BG = '#111a2e'
    BTN_FG = '#d7e7ff'
    BTN_ACT = '#1a2a4f'
    BTN_HOVER = '#162244'
    TIME_FG = '#6ee7ff'
    ACCENT = '#4ea1ff'
    BORDER = '#162033'

    PLAYER_W = 460
    VIDEO_CANVAS_H_DEFAULT = 228
    MONITOR_GAIN = 0.05

    def __init__(self, parent, on_play_start=None, on_pfl=None, *, panel_width=None, video_canvas_height=None):
        self.parent = parent
        self._on_play_start = on_play_start
        self._on_pfl = on_pfl
        self._panel_w = int(panel_width) if panel_width else self.PLAYER_W
        if self._panel_w < 320:
            self._panel_w = self.PLAYER_W
        self._canvas_h = int(video_canvas_height) if video_canvas_height else self.VIDEO_CANVAS_H_DEFAULT
        if self._canvas_h < 160:
            self._canvas_h = self.VIDEO_CANVAS_H_DEFAULT
        self._filepath = None
        self._cap = None
        self._playing = False
        self._paused = False
        self._stop_flag = False
        self._thread = None
        self._duration = 0.0
        self._fps = 25.0
        self._total_frames = 0
        self._current_time = 0.0
        self._seek_to = None
        self._monitor_vol = self.MONITOR_GAIN
        self._source_vol = 1.0
        self._source_pfl_active = False
        self._monitor_pfl_active = False
        self._audio_proc = None
        self._lock = threading.Lock()
        self._pending_frame = False
        self._latest_frame_data = None
        self._seek_dragging = False
        self._playback_start_wall = None
        self._playback_start_video = 0.0
        self._vu_meter = None
        self._vu_meter_file = None
        self._pfl_src_btn = None
        self._pfl_mon_btn = None
        self._mon_vol_slider = None
        self._mon_vol_lbl = None
        self._vf_canvas_id = None
        self._last_seek_ui_ts = 0.0
        self._time_observer = None
        self._vu_poll_after_id = None
        self._audio_armed = False
        self._audio_player = SoundAudioPlayer()
        # Instagram / converter: mənbə kadrını çıxış en×hündürlük nisbətinə görə mərkəzdən kəs (real-time önizləmə)
        self._ig_preview_tw = None
        self._ig_preview_th = None
        self._preview_badge_text = ""
        # Instagram: 1920×1080 qat önizləmə + siçanla düzən
        self._ig_composite_fn = None
        self._ig_interact_app = None
        self._last_raw_frame_rgb = None
        self._ig_letterbox = None
        self._ig_drag = None
        self._ig_sel_layer = "center"
        self._ig_overlay_bound = False
        self._build_ui(parent)

    def set_time_observer(self, callback):
        """Optional callback(current_time, duration) for external timeline sync."""
        self._time_observer = callback

    def set_preview_target_size(self, tw=None, th=None):
        """Çıxış ölçüsü (məs. 1080×1920) — pleyer kadrı bu nisbətə görə kəsilmiş göstərir. tw=None → söndür."""
        if tw and th and int(tw) > 0 and int(th) > 0:
            self._ig_preview_tw = int(tw)
            self._ig_preview_th = int(th)
        else:
            self._ig_preview_tw = None
            self._ig_preview_th = None

    def set_preview_badge(self, text: str):
        """Başlıqda rejim / ölçü (məs. Reels 1080×1920)."""
        self._preview_badge_text = (text or "").strip()
        try:
            if self._filepath:
                fname = os.path.basename(self._filepath)
                self._title_lbl.config(text=f" {fname[:22]}{self._preview_badge_text}"[:52])
        except Exception:
            pass

    def set_instagram_composite_preview(self, fn):
        """fn(frame_rgb) -> 1920×1080 RGB kadr; None — yalnız mənbə."""
        self._ig_composite_fn = fn

    def set_instagram_layer_interaction(self, app):
        """app — OrvixApp (main); None — disable mouse layout editor."""
        self._ig_interact_app = app
        if app is not None:
            self._ig_bind_overlay_events()
        else:
            self._ig_unbind_overlay_events()
            try:
                self.canvas.delete("ig_overlay")
            except Exception:
                pass

    @staticmethod
    def _crop_frame_to_aspect(frame_rgb, tw: int, th: int):
        """Mənbə kadrını tw:th nisbətinə mərkəz kəsmə (encode ilə uyğun görünüş)."""
        if frame_rgb is None or tw < 1 or th < 1:
            return frame_rgb
        h, w = frame_rgb.shape[:2]
        if w < 2 or h < 2:
            return frame_rgb
        tar = tw / float(th)
        sar = w / float(h)
        if sar > tar:
            new_w = int(round(h * tar))
            x0 = max(0, (w - new_w) // 2)
            return frame_rgb[:, x0 : x0 + new_w].copy()
        new_h = int(round(w / tar))
        y0 = max(0, (h - new_h) // 2)
        return np.ascontiguousarray(frame_rgb[y0 : y0 + new_h, :])

    def _build_ui(self, parent):
        # Main right-side panel — fixed width, fills tab height
        self.frame = tk.Frame(parent, bg=self.PLAYER_BG,
                              highlightthickness=1, highlightbackground=self.BORDER,
                              width=self._panel_w)
        self.frame.pack(side=tk.RIGHT, fill=tk.Y)
        self.frame.pack_propagate(False)

        # === TITLE BAR ===
        title_bar = tk.Frame(self.frame, bg='#090d16', height=28)
        title_bar.pack(fill=tk.X)
        title_bar.pack_propagate(False)

        logo_dot = tk.Label(title_bar, text="\u25cf", bg='#090d16', fg=self.ACCENT,
                            font=('Segoe UI', 11, 'bold'))
        logo_dot.pack(side=tk.LEFT, padx=(6, 2))
        tk.Label(title_bar, text="ORVIX PLAYER",
                 bg='#090d16', fg='#d7e7ff',
                 font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT, padx=(0, 6))

        self._title_lbl = tk.Label(title_bar, text="",
                                   bg='#090d16', fg='#7e8aa6',
                                   font=('Segoe UI', 9))
        self._title_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._status_dot = tk.Label(title_bar, text="\u25cf", bg='#090d16', fg='#2a3550',
                                    font=('Segoe UI', 9, 'bold'))
        self._status_dot.pack(side=tk.RIGHT, padx=6)

        # === VIDEO CANVAS — COMPACT, at top ===
        canvas_frame = tk.Frame(self.frame, bg='#000000', height=self._canvas_h)
        canvas_frame.pack(fill=tk.X, padx=1)
        canvas_frame.pack_propagate(False)

        self.canvas = tk.Canvas(canvas_frame, bg='#000000',
                                highlightthickness=0, cursor='hand2')
        self.canvas.pack(fill=tk.BOTH, expand=True)

        _cx, _cy = max(80, self._panel_w // 2), max(40, self._canvas_h // 2)
        self._placeholder_id = self.canvas.create_text(
            _cx, _cy,
            text="[ No Video ]\n\nDouble-click a problem\nor open a file to play",
            fill='#334056', font=('Segoe UI', 11), justify=tk.CENTER)

        pfl_src_bc = dict(
            bg='#1a3550', fg='#b8d8ff', relief=tk.RAISED, cursor='hand2',
            font=('Segoe UI', 8, 'bold'), activebackground='#244060', activeforeground='#e8f0ff',
            padx=10, pady=4, bd=1, highlightthickness=0,
        )
        pfl_mon_bc = dict(
            bg='#1a3d28', fg='#b8f5d0', relief=tk.RAISED, cursor='hand2',
            font=('Segoe UI', 8, 'bold'), activebackground='#245a38', activeforeground='#e8fff0',
            padx=10, pady=4, bd=1, highlightthickness=0,
        )
        # === SOURCE (file) — üstdə: VU + PFL + səs; PFL olmadan real səs yox, yalnız göstərici ===
        vu_src = tk.Frame(self.frame, bg=self.PLAYER_BG,
                          highlightthickness=1, highlightbackground='#152a40')
        vu_src.pack(fill=tk.X, padx=1, pady=(1, 0))

        vh2 = tk.Frame(vu_src, bg=self.PLAYER_BG, height=16)
        vh2.pack(fill=tk.X)
        vh2.pack_propagate(False)
        tk.Label(vh2, text="  SOURCE  •  file",
                 bg=self.PLAYER_BG, fg='#6a9cbc',
                 font=('Segoe UI', 9, 'bold')).pack(side=tk.LEFT, pady=1)
        tk.Label(vh2, text="dBFS",
                 bg=self.PLAYER_BG, fg='#44506a',
                 font=('Segoe UI', 9)).pack(side=tk.RIGHT, padx=6, pady=1)

        self._vu_meter_file = VerticalVUMeter(vu_src, channels=2, height=82)
        self._vu_meter_file.pack(fill=tk.X, expand=True, padx=2, pady=(0, 1))

        src_ctl = tk.Frame(vu_src, bg='#0a1420', pady=2)
        src_ctl.pack(fill=tk.X, padx=2, pady=(0, 2))
        self._pfl_src_btn = tk.Button(
            src_ctl, text='SRC  PFL', command=self._toggle_source_pfl, **pfl_src_bc
        )
        self._pfl_src_btn.pack(side=tk.LEFT, padx=(2, 4))
        tk.Label(
            src_ctl,
            text='Source level (PFL ON)',
            bg='#0a1420', fg='#3d5068',
            font=('Segoe UI', 8),
        ).pack(side=tk.LEFT, padx=(4, 0))

        # === MONITOR (output) — MON vol slayderi (MON PFL ilə) ===
        vu_mon = tk.Frame(self.frame, bg=self.PLAYER_BG,
                          highlightthickness=1, highlightbackground='#101826')
        vu_mon.pack(fill=tk.X, padx=1, pady=(1, 0))

        vh1 = tk.Frame(vu_mon, bg=self.PLAYER_BG, height=16)
        vh1.pack(fill=tk.X)
        vh1.pack_propagate(False)
        tk.Label(vh1, text="  MONITOR  •  output",
                 bg=self.PLAYER_BG, fg='#7e8aa6',
                 font=('Segoe UI', 9, 'bold')).pack(side=tk.LEFT, pady=1)
        tk.Label(vh1, text="dBFS",
                 bg=self.PLAYER_BG, fg='#44506a',
                 font=('Segoe UI', 9)).pack(side=tk.RIGHT, padx=6, pady=1)

        self._vu_meter = VerticalVUMeter(vu_mon, channels=2, height=82)
        self._vu_meter.pack(fill=tk.X, expand=True, padx=2, pady=(0, 1))

        mon_ctl = tk.Frame(vu_mon, bg='#0a1018', pady=2)
        mon_ctl.pack(fill=tk.X, padx=2, pady=(0, 2))
        self._pfl_mon_btn = tk.Button(
            mon_ctl, text='MON  PFL', command=self._toggle_monitor_pfl, **pfl_mon_bc
        )
        self._pfl_mon_btn.pack(side=tk.LEFT, padx=(2, 4))
        self._mon_vol_lbl = tk.Label(
            mon_ctl, text='5%', bg='#0a1018', fg=self.TIME_FG,
            font=('Consolas', 9, 'bold'), width=5,
        )
        self._mon_vol_lbl.pack(side=tk.LEFT, padx=(2, 2))
        self._mon_vol_slider = ttk.Scale(
            mon_ctl, from_=0, to=200, orient=tk.HORIZONTAL,
            command=self._on_mon_vol_slider, style='Player.Horizontal.TScale',
        )
        self._mon_vol_slider.set(5)
        self._mon_vol_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        tk.Label(
            mon_ctl,
            text='MON PFL ON — level with this slider',
            bg='#0a1018', fg='#3d5068',
            font=('Segoe UI', 8),
        ).pack(side=tk.LEFT, padx=(2, 0))

        # === TIME ROW ===
        time_row = tk.Frame(self.frame, bg=self.PLAYER_BG, pady=1)
        time_row.pack(fill=tk.X, padx=4)

        self._time_lbl = tk.Label(time_row, text="00:00.000",
                                  bg=self.PLAYER_BG, fg=self.TIME_FG,
                                  font=('Consolas', 13, 'bold'))
        self._time_lbl.pack(side=tk.LEFT, padx=2)

        self._dur_lbl = tk.Label(time_row, text="/ 00:00.000",
                                 bg=self.PLAYER_BG, fg='#334a5a',
                                 font=('Consolas', 10))
        self._dur_lbl.pack(side=tk.LEFT)

        # === SEEK BAR ===
        seek_row = tk.Frame(self.frame, bg=self.PLAYER_BG)
        seek_row.pack(fill=tk.X, padx=4, pady=1)

        self._seek_var = tk.DoubleVar(value=0)
        self._seek_bar = ttk.Scale(seek_row, variable=self._seek_var,
                                   from_=0, to=100, orient=tk.HORIZONTAL,
                                   command=self._on_seek_drag,
                                   style='Player.Horizontal.TScale')
        self._seek_bar.pack(fill=tk.X, expand=True)
        self._seek_bar.bind('<ButtonPress-1>',
                            lambda e: setattr(self, '_seek_dragging', True))
        self._seek_bar.bind('<ButtonRelease-1>', self._seek_release)

        # === CONTROL ROW 1: Play | Pause | Stop | -10s | +10s | Vol% ===
        ctrl1 = tk.Frame(self.frame, bg=self.CTRL_BG, pady=3)
        ctrl1.pack(fill=tk.X, padx=2)

        bc = dict(bg=self.BTN_BG, fg=self.BTN_FG, relief=tk.FLAT,
                  cursor='hand2', font=('Segoe UI', 10, 'bold'),
                  activebackground=self.BTN_ACT, activeforeground='#ddeeff',
                  padx=8, pady=5, bd=0)

        self._play_btn = tk.Button(ctrl1, text="\u25b6  Play",
                                   command=self.play_media, **bc)
        self._play_btn.pack(side=tk.LEFT, padx=(3, 1), pady=2)
        self._add_hover(self._play_btn)

        self._pause_btn = tk.Button(ctrl1, text="\u23f8  Pause",
                                    command=self.pause_media, **bc)
        self._pause_btn.pack(side=tk.LEFT, padx=1, pady=2)
        self._pause_btn.config(state=tk.DISABLED)
        self._add_hover(self._pause_btn)

        self._stop_btn = tk.Button(ctrl1, text="\u23f9  Stop",
                                   command=self.stop, **bc)
        self._stop_btn.pack(side=tk.LEFT, padx=1, pady=2)
        self._add_hover(self._stop_btn)

        skip_bc = dict(bg='#0f172c', fg='#a9b3c7', relief=tk.FLAT,
                       cursor='hand2', font=('Segoe UI', 9),
                       activebackground=self.BTN_ACT, activeforeground='#aaccee',
                       padx=8, pady=5, bd=0)
        tk.Button(ctrl1, text="\u23ee  -10s",
                  command=self._skip_backward, **skip_bc).pack(side=tk.LEFT, padx=1, pady=2)
        tk.Button(ctrl1, text="+10s  \u23ed",
                  command=self._skip_forward, **skip_bc).pack(side=tk.LEFT, padx=1, pady=2)

        # === BOTTOM HINT ===
        hint = tk.Frame(self.frame, bg='#090d16', height=18)
        hint.pack(fill=tk.X, side=tk.BOTTOM)
        hint.pack_propagate(False)
        tk.Label(hint,
                 text="Fayl: yaln\u0131z \u00f6nizl\u0259m\u0259 \u2022 Play t\u0259sdiq \u2022 Space: oxu/pauza \u2022 Stop dayand\u0131r\u0131r",
                 bg='#090d16', fg='#2f3b52',
                 font=('Segoe UI', 9)).pack(fill=tk.X, padx=6)

        self._refresh_transport_buttons()
        self._apply_pfl_button_look()
        self._sync_audio_pfl_state()

    def _add_hover(self, btn):
        def on_enter(e):
            btn.config(bg=self.BTN_HOVER)
        def on_leave(e):
            btn.config(bg=self.BTN_BG)
        btn.bind('<Enter>', on_enter)
        btn.bind('<Leave>', on_leave)

    # ── Callbacks ────────────────────────────────────────────────────────────

    def _on_audio_levels(self, rms_mon, peak_mon, rms_src=None, peak_src=None):
        """VU yeniləməsi — yalnız əsas UI thread (Tk təhlükəsiz)."""
        try:
            if self._vu_meter:
                self._vu_meter.set_levels(rms_mon, peak_mon)
            if self._vu_meter_file and rms_src is not None and peak_src is not None:
                self._vu_meter_file.set_levels(rms_src, peak_src)
        except Exception:
            pass

    def _start_vu_polling(self):
        self._stop_vu_polling()
        self._vu_poll_tick()

    def _stop_vu_polling(self):
        aid = self._vu_poll_after_id
        self._vu_poll_after_id = None
        if aid is not None:
            try:
                self.frame.after_cancel(aid)
            except Exception:
                pass

    def _vu_poll_tick(self):
        self._vu_poll_after_id = None
        if not self._playing or self._stop_flag:
            return
        if not self._audio_player.is_streaming():
            return
        snap = self._audio_player.get_levels_snapshot()
        if snap is not None and len(snap) == 4:
            try:
                self._on_audio_levels(snap[0], snap[1], snap[2], snap[3])
            except Exception:
                pass
        self._vu_poll_after_id = self.frame.after(20, self._vu_poll_tick)

    def _sync_audio_pfl_state(self):
        """PFL marşrutu — audio thread ilə uyğun."""
        try:
            self._audio_player.apply_routing(
                self._source_pfl_active,
                self._monitor_pfl_active,
                self._source_vol,
                self._monitor_vol,
            )
        except Exception:
            pass

    def _apply_pfl_button_look(self):
        """PFL qoşulu / söndürülmüş — görünə bilən aydın fərq."""
        try:
            if self._pfl_src_btn:
                if self._source_pfl_active:
                    self._pfl_src_btn.config(
                        text='SRC  PFL  ● ON',
                        bg='#00a8ff', fg='#ffffff',
                        relief=tk.SUNKEN, bd=2,
                        activebackground='#33c4ff', activeforeground='#ffffff',
                    )
                else:
                    self._pfl_src_btn.config(
                        text='SRC  PFL',
                        bg='#1a3550', fg='#88ccff',
                        relief=tk.RAISED, bd=1,
                        activebackground='#244060', activeforeground='#e8f0ff',
                    )
            if self._pfl_mon_btn:
                if self._monitor_pfl_active:
                    self._pfl_mon_btn.config(
                        text='MON  PFL  ● ON',
                        bg='#00c853', fg='#0a1a0f',
                        relief=tk.SUNKEN, bd=2,
                        activebackground='#33dd77', activeforeground='#0a1a0f',
                    )
                else:
                    self._pfl_mon_btn.config(
                        text='MON  PFL',
                        bg='#1a3d28', fg='#a8f0c0',
                        relief=tk.RAISED, bd=1,
                        activebackground='#245a38', activeforeground='#e8fff0',
                    )
        except Exception:
            pass
        self._refresh_mon_vol_ui()

    def _refresh_mon_vol_ui(self):
        """MON vol slayderi yalnız MON PFL aktiv, SRC PFL söndürülmüş olanda."""
        try:
            if self._mon_vol_slider is None:
                return
            if self._monitor_pfl_active and not self._source_pfl_active:
                self._mon_vol_slider.state(["!disabled"])
            else:
                self._mon_vol_slider.state(["disabled"])
        except Exception:
            pass

    def _sync_mon_vol_widgets(self):
        """_monitor_vol → slayder + etiket (proqramatik dəyişiklik)."""
        if self._mon_vol_slider is None:
            return
        try:
            pct = max(0, min(200, int(round(self._monitor_vol * 100))))
            self._mon_vol_slider.set(pct)
            if self._mon_vol_lbl is not None:
                self._mon_vol_lbl.config(text=f'{pct}%')
        except Exception:
            pass

    def _on_mon_vol_slider(self, val):
        try:
            pct = float(val)
        except Exception:
            return
        self._monitor_vol = max(0.0, min(2.0, pct / 100.0))
        try:
            if self._mon_vol_lbl is not None:
                self._mon_vol_lbl.config(text=f'{int(round(pct))}%')
        except Exception:
            pass
        self._sync_audio_pfl_state()

    def _notify_pfl_parent(self):
        if self._on_pfl:
            try:
                self._on_pfl(self, True)
            except Exception:
                pass

    def clear_pfl(self):
        """Digər pleyer PFL açanda — bu pleyerdə hər iki PFL sönsün."""
        if not self._source_pfl_active and not self._monitor_pfl_active:
            return
        self._reset_pfl_ui()

    def apply_problem_playback_mode(self):
        """Problemə klik: səs MONITOR PFL-dan, sabit 5%; SRC PFL söndürülüb."""
        self._monitor_pfl_active = True
        self._source_pfl_active = False
        self._monitor_vol = self.MONITOR_GAIN
        self._source_vol = 1.0
        self._sync_audio_pfl_state()
        self._apply_pfl_button_look()
        self._sync_mon_vol_widgets()
        self._notify_pfl_parent()

    def _toggle_source_pfl(self):
        if not self._filepath:
            return
        self._source_pfl_active = not self._source_pfl_active
        if self._source_pfl_active:
            self._monitor_pfl_active = False
        self._sync_audio_pfl_state()
        self._apply_pfl_button_look()
        if self._source_pfl_active:
            self._notify_pfl_parent()

    def _toggle_monitor_pfl(self):
        if not self._filepath:
            return
        self._monitor_pfl_active = not self._monitor_pfl_active
        if self._monitor_pfl_active:
            self._source_pfl_active = False
        self._sync_audio_pfl_state()
        self._apply_pfl_button_look()
        if self._monitor_pfl_active:
            self._notify_pfl_parent()

    @staticmethod
    def _seek_cap_by_time(cap, t_sec, fps):
        """OpenCV: kadr indeksi ilə seek — FFmpeg audio ilə uyğunlaşmaq üçün."""
        fps = max(0.001, fps or 25.0)
        fi = max(0, int(round(float(t_sec) * fps)))
        try:
            cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
        except Exception:
            cap.set(cv2.CAP_PROP_POS_MSEC, float(t_sec) * 1000.0)
        return fi / fps

    def _seek_release(self, event):
        self._seek_dragging = False
        if self._filepath and self._duration > 0:
            pct = self._seek_var.get() / 100.0
            t = pct * self._duration
            self.seek(t)

    def _on_seek_drag(self, val):
        if self._duration > 0:
            pct = float(val) / 100.0
            t = pct * self._duration
            self._time_lbl.config(text=format_time(t))

    def _skip_backward(self):
        """Jump back 10 seconds."""
        if self._filepath:
            t = max(0.0, self._current_time - 10.0)
            self.seek(t)

    def _skip_forward(self):
        """Jump forward 10 seconds."""
        if self._filepath:
            t = min(self._duration, self._current_time + 10.0)
            self.seek(t)

    def load(self, filepath, start_time=0.0):
        """Load video and start playback from start_time."""
        if not filepath or not os.path.exists(filepath):
            return
        same_file = (self._filepath == filepath and self._filepath is not None)
        self.stop(clear_canvas=not same_file)
        self._filepath = filepath
        fname = os.path.basename(filepath)
        self._title_lbl.config(text=f" {fname[:32]}")
        try:
            cap = cv2.VideoCapture(filepath)
            if cap.isOpened():
                self._fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
                self._total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                self._duration = (self._total_frames / self._fps if self._fps > 0 else 0)
                cap.release()
            else:
                cap.release()
                return
        except Exception as e:
            print(f"VideoCapture open error: {e}")
            return
        self._dur_lbl.config(text=f"/ {format_time(self._duration)}")
        self.canvas.itemconfig(self._placeholder_id, text='')
        self._status_dot.config(fg='#00cc44')
        self._start_playback(start_time)

    def _start_playback(self, start_time=0.0):
        if self._on_play_start:
            try:
                self._on_play_start(self)
            except Exception:
                pass
        self._stop_flag = False
        self._playing = True
        self._paused = False
        self._refresh_transport_buttons()
        st = float(start_time)
        self._playback_start_video = st
        self._current_time = st
        self._playback_start_wall = time.perf_counter()
        self._stop_audio()
        # Səs yalnız ilk video kadır UI-da göstəriləndə başlasın (dodaq sinxronu üçün).
        # Əvvəl after(0) ilə audio dərhal başlayırdı — video gecikdiyi üçün səs irəli düşürdü.
        self._audio_armed = True
        self._thread = threading.Thread(
            target=self._video_loop,
            args=(self._filepath, start_time),
            daemon=True)
        self._thread.start()

    def _start_audio_if_playing(self, t):
        if self._stop_flag or not self._playing:
            return
        self._start_audio(t)

    def _seek_audio_restart(self, t):
        if self._stop_flag:
            return
        self._stop_audio()
        self._start_audio(t)

    # ── Audio ────────────────────────────────────────────────────────────────

    def _start_audio(self, start_time=0.0):
        self._stop_audio()
        if not self._filepath:
            return
        self._sync_audio_pfl_state()
        ok = self._audio_player.start(
            self._filepath,
            start_time=start_time,
            monitor_vol=self._monitor_vol,
        )
        self._sync_audio_pfl_state()
        if ok:
            self._start_vu_polling()
        if not ok:
            # Fallback: ffplay
            if ffmpeg_mgr.ffplay_path:
                try:
                    cmd = [ffmpeg_mgr.ffplay_path, '-nodisp', '-autoexit',
                           '-ss', str(start_time), '-i', self._filepath,
                           '-af', f'volume={max(0.0, min(2.0, self._monitor_vol)):.4f}', '-vn']
                    si = ffmpeg_mgr._get_startupinfo()
                    self._audio_proc = subprocess.Popen(
                        cmd, stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL, startupinfo=si)
                except Exception as e:
                    print(f"Audio fallback error: {e}")

    def _stop_audio(self):
        self._stop_vu_polling()
        try:
            self._audio_player.stop()
        except Exception:
            pass
        if self._audio_proc and self._audio_proc.poll() is None:
            try:
                self._audio_proc.terminate()
                self._audio_proc.wait(timeout=1)
            except Exception:
                try:
                    self._audio_proc.kill()
                except Exception:
                    pass
        self._audio_proc = None

    def _video_loop(self, filepath, start_time):
        """
        Wall-clock pacing; kadr indeksi ilə seek; audio ilk göstərilən kadrla eyni t ilə başlayır.
        """
        try:
            cap = cv2.VideoCapture(filepath)
            if not cap.isOpened():
                return
            fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            frame_delay = 1.0 / fps
            video_start = self._seek_cap_by_time(cap, start_time, fps)
            try:
                self._playback_start_video = video_start
            except Exception:
                pass
            prev_ft = None
            prev_wall = None

            while not self._stop_flag:
                while self._paused and not self._stop_flag:
                    time.sleep(0.015)
                    video_start = self._current_time
                    prev_ft = None
                    prev_wall = None
                if self._stop_flag:
                    break

                with self._lock:
                    seek_t = self._seek_to
                    self._seek_to = None
                if seek_t is not None:
                    video_start = self._seek_cap_by_time(cap, seek_t, fps)
                    self._playback_start_wall = time.perf_counter()
                    self._playback_start_video = video_start
                    prev_ft = None
                    prev_wall = None
                    vs = video_start
                    self.canvas.after(0, lambda t=vs: self._seek_audio_restart(t))

                ret, frame = cap.read()
                if not ret:
                    break

                ft = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
                if ft <= 0.0 and video_start > 0:
                    ft = video_start
                # OpenCV MSEC bəzən geri qalır — möhəri segment başına yapışdır
                if ft + 0.02 < video_start:
                    ft = video_start
                self._current_time = ft
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                with self._lock:
                    self._latest_frame_data = (frame_rgb, ft)
                    if not self._pending_frame:
                        self._pending_frame = True
                        self.canvas.after(0, self._deliver_frame)

                # Real vaxt ↔ media vaxtı: ardıcıl kadrların Δt-sinə görə yuxulama (drift azalır)
                now = time.perf_counter()
                if prev_ft is None:
                    prev_ft = ft
                    prev_wall = now
                else:
                    dt_media = ft - prev_ft
                    if dt_media > 1e-4:
                        slip = dt_media - (now - prev_wall)
                        if slip > 0.0008:
                            time.sleep(slip)
                    elif frame_delay > 0:
                        time.sleep(max(0.001, frame_delay * 0.85))
                    prev_ft = ft
                    prev_wall = time.perf_counter()

            cap.release()
        except Exception as e:
            print(f"Video loop error: {e}")
        finally:
            self._playing = False
            self._paused = False
            if not self._stop_flag:
                try:
                    self.canvas.after(0, self._on_playback_ended)
                except Exception:
                    pass

    def _deliver_frame(self):
        with self._lock:
            frame_data = self._latest_frame_data
            self._latest_frame_data = None
            self._pending_frame = False
        if frame_data is None:
            return
        self._update_canvas_frame(frame_data[0], frame_data[1])
        if self._audio_armed and not self._stop_flag:
            self._audio_armed = False
            ft = frame_data[1]
            self.frame.after(0, lambda t=ft: self._start_audio_if_playing(t))

    def _update_canvas_frame(self, frame_rgb, current_time):
        """Draw frame on canvas, letterboxed — stable scale, one canvas item (less flicker)."""
        if self._stop_flag:
            return
        try:
            if not PIL_AVAILABLE:
                return
            raw = np.ascontiguousarray(frame_rgb) if frame_rgb is not None else None
            comp_used = False
            if self._ig_composite_fn and raw is not None:
                try:
                    frame_rgb = self._ig_composite_fn(raw)
                    if (
                        frame_rgb is not None
                        and frame_rgb.ndim == 3
                        and frame_rgb.shape[0] == 1080
                        and frame_rgb.shape[1] == 1920
                    ):
                        comp_used = True
                        self._last_raw_frame_rgb = raw
                    else:
                        frame_rgb = raw
                        self._last_raw_frame_rgb = raw if self._ig_interact_app else None
                except Exception:
                    frame_rgb = raw
                    self._last_raw_frame_rgb = raw if self._ig_interact_app else None
            else:
                self._last_raw_frame_rgb = raw if (raw is not None and self._ig_interact_app) else None

            if self._ig_preview_tw and self._ig_preview_th:
                frame_rgb = self._crop_frame_to_aspect(frame_rgb, self._ig_preview_tw, self._ig_preview_th)
            cw = int(self.canvas.winfo_width())
            ch = int(self.canvas.winfo_height())
            if cw < 4 or ch < 4:
                return
            h, w = frame_rgb.shape[:2]
            if w == 0 or h == 0:
                return
            scale = min(cw / float(w), ch / float(h))
            new_w = max(1, int(round(w * scale)))
            new_h = max(1, int(round(h * scale)))
            x = int(round((cw - new_w) / 2.0))
            y = int(round((ch - new_h) / 2.0))
            resized = cv2.resize(
                frame_rgb, (new_w, new_h), interpolation=cv2.INTER_LINEAR
            )
            img = Image.fromarray(resized)
            photo = ImageTk.PhotoImage(image=img)
            cid = getattr(self, "_vf_canvas_id", None)
            if cid is None:
                self._vf_canvas_id = self.canvas.create_image(
                    x, y, anchor=tk.NW, image=photo, tags="vf"
                )
            else:
                self.canvas.itemconfig(cid, image=photo)
                self.canvas.coords(cid, x, y)
            self.canvas._photo = photo

            # Instagram: siçan ↔ 1920×1080 — kompozit və ya tək video (eyni letterbox məntiqi)
            try:
                from orvix.instagram_layer_preview import crop_window_1920_for_output

                app = self._ig_interact_app
                if comp_used and self._ig_preview_tw and self._ig_preview_th:
                    tw, th = int(self._ig_preview_tw), int(self._ig_preview_th)
                    x0, y0, cww, chh = crop_window_1920_for_output(tw, th)
                    self._ig_letterbox = {
                        "vx": x,
                        "vy": y,
                        "nw": new_w,
                        "nh": new_h,
                        "fw": w,
                        "fh": h,
                        "crop_x0": x0,
                        "crop_y0": y0,
                        "crop_cw": cww,
                        "crop_ch": chh,
                    }
                elif (
                    app is not None
                    and self._filepath
                    and os.path.isfile(self._filepath)
                    and self._ig_preview_tw
                    and self._ig_preview_th
                    and self._ig_has_layer_paths(app)
                ):
                    tw, th = int(self._ig_preview_tw), int(self._ig_preview_th)
                    x0, y0, cww, chh = crop_window_1920_for_output(tw, th)
                    self._ig_letterbox = {
                        "vx": x,
                        "vy": y,
                        "nw": new_w,
                        "nh": new_h,
                        "fw": w,
                        "fh": h,
                        "crop_x0": x0,
                        "crop_y0": y0,
                        "crop_cw": cww,
                        "crop_ch": chh,
                    }
                else:
                    self._ig_letterbox = None
            except Exception:
                self._ig_letterbox = None

            self._ig_draw_overlay()
            self._time_lbl.config(text=format_time(current_time))
            now = time.perf_counter()
            if self._duration > 0 and not self._seek_dragging:
                if now - self._last_seek_ui_ts >= 0.04:
                    self._last_seek_ui_ts = now
                    pct = (current_time / self._duration) * 100.0
                    self._seek_var.set(min(100.0, pct))
            if self._time_observer:
                try:
                    self._time_observer(current_time, self._duration)
                except Exception:
                    pass
        except Exception:
            pass

    def _on_playback_ended(self):
        self._playing = False
        self._paused = False
        try:
            self._status_dot.config(fg='#112233')
            self._refresh_transport_buttons()
        except Exception:
            pass

    # ── Playback control ─────────────────────────────────────────────────────

    def _refresh_transport_buttons(self):
        """Play / Pause / Stop — avtomatik oxu yox, yalnız düymələr."""
        try:
            if not self._filepath:
                self._play_btn.config(state=tk.DISABLED, text="\u25b6  Play")
                self._pause_btn.config(state=tk.DISABLED)
                self._stop_btn.config(state=tk.DISABLED)
                if self._pfl_src_btn:
                    self._pfl_src_btn.config(state=tk.DISABLED)
                if self._pfl_mon_btn:
                    self._pfl_mon_btn.config(state=tk.DISABLED)
                return
            self._stop_btn.config(state=tk.NORMAL)
            self._play_btn.config(state=tk.NORMAL)
            if self._pfl_src_btn:
                self._pfl_src_btn.config(state=tk.NORMAL)
            if self._pfl_mon_btn:
                self._pfl_mon_btn.config(state=tk.NORMAL)
            if self._playing and not self._paused:
                self._play_btn.config(state=tk.DISABLED, text="\u25b6  Play")
                self._pause_btn.config(state=tk.NORMAL)
            elif self._paused:
                self._play_btn.config(state=tk.NORMAL, text="\u25b6  Davam")
                self._pause_btn.config(state=tk.DISABLED)
            else:
                self._play_btn.config(text="\u25b6  Play")
                self._pause_btn.config(state=tk.DISABLED)
        except Exception:
            pass

    def play_media(self):
        if not self._filepath:
            return
        if not self._playing:
            self._start_playback(self._current_time)
        elif self._paused:
            self._paused = False
            self._playback_start_wall = time.perf_counter()
            self._playback_start_video = self._current_time
            self._start_audio(self._current_time)
            self._refresh_transport_buttons()

    def pause_media(self):
        if not self._playing or self._paused:
            return
        self._paused = True
        self._stop_audio()
        self._refresh_transport_buttons()

    def toggle_play(self):
        """Space: oxuyursa pauza, dayanıbsa və ya pauzadadırsa oxu."""
        if not self._filepath:
            return
        if not self._playing or self._paused:
            self.play_media()
        else:
            self.pause_media()

    def _reset_pfl_ui(self):
        self._source_pfl_active = False
        self._monitor_pfl_active = False
        self._monitor_vol = self.MONITOR_GAIN
        self._source_vol = 1.0
        self._sync_audio_pfl_state()
        self._apply_pfl_button_look()
        self._sync_mon_vol_widgets()

    def stop(self, clear_canvas=True):
        self._stop_flag = True
        self._playing = False
        self._paused = False
        if clear_canvas:
            self._vf_canvas_id = None
        try:
            self.canvas.delete("ig_overlay")
        except Exception:
            pass
        self._ig_letterbox = None
        self._ig_drag = None
        self._stop_audio()
        self._reset_pfl_ui()
        try:
            self._status_dot.config(fg='#112233')
            self._refresh_transport_buttons()
        except Exception:
            pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.08)
        self._thread = None

    def _show_frame_at_time(self, seconds):
        """Önizləmə: oxu olmadan konkret zamanda bir kadır (seek, fayl açılışı)."""
        if not self._filepath or not os.path.exists(self._filepath):
            return
        try:
            cap = cv2.VideoCapture(self._filepath)
            if not cap.isOpened():
                return
            fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            at = self._seek_cap_by_time(cap, seconds, fps)
            ret, frame = cap.read()
            cap.release()
            if not ret or frame is None:
                return
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self._stop_flag = False
            self._update_canvas_frame(frame_rgb, at)
            if self._duration > 0 and not self._seek_dragging:
                pct = (at / self._duration) * 100.0
                self._seek_var.set(min(100.0, max(0.0, pct)))
        except Exception:
            pass

    def seek(self, seconds):
        """Seek — oxunurken thread; əks halda yalnız kadır önizləməsi (avtomatik play yox)."""
        if not self._filepath:
            return
        seconds = max(0.0, min(seconds, self._duration))
        self._current_time = seconds
        if self._playing and not self._paused:
            with self._lock:
                self._seek_to = seconds
        elif self._playing and self._paused:
            with self._lock:
                self._seek_to = seconds
            self.frame.after(0, lambda t=seconds: self._show_frame_at_time(t))
        else:
            self._show_frame_at_time(seconds)

    def vol_up(self):
        """↑ — MONITOR yolu (MON PFL ON): sürətli +5%."""
        if not self._monitor_pfl_active or self._source_pfl_active:
            return
        self._monitor_vol = min(2.0, self._monitor_vol + 0.05)
        self._sync_mon_vol_widgets()
        self._sync_audio_pfl_state()

    def vol_down(self):
        """↓ — MONITOR yolu: sürətli −5%."""
        if not self._monitor_pfl_active or self._source_pfl_active:
            return
        self._monitor_vol = max(0.0, self._monitor_vol - 0.05)
        self._sync_mon_vol_widgets()
        self._sync_audio_pfl_state()

    def preview_file(self, filepath):
        """Load metadata and first frame only — no playback (e.g. Converter tab preview)."""
        self.stop()
        if not filepath or not os.path.exists(filepath):
            return
        try:
            cap = cv2.VideoCapture(filepath)
            if not cap.isOpened():
                return
            self._fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            self._total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self._duration = self._total_frames / self._fps if self._fps > 0 else 0.0
            ret, frame = cap.read()
            cap.release()
            if not ret or frame is None:
                return
            self._filepath = filepath
            fname = os.path.basename(filepath)
            self._title_lbl.config(text=f" {fname[:22]}{self._preview_badge_text}"[:52])
            self._dur_lbl.config(text=f"/ {format_time(self._duration)}")
            self.canvas.itemconfig(self._placeholder_id, text="")
            self._current_time = 0.0
            self._seek_var.set(0.0)
            self._time_lbl.config(text=format_time(0.0))
            self._status_dot.config(fg=self.ACCENT)
            self._playing = False
            self._paused = False
            self._stop_flag = False
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self._refresh_transport_buttons()
            self._vf_canvas_id = None
            self._update_canvas_frame(frame_rgb, 0.0)
            self.frame.after(50, lambda fr=frame_rgb: self._update_canvas_frame(fr, 0.0)
                             if not self._playing else None)
        except Exception as e:
            print(f"preview_file error: {e}")

    def preview_rgb_frame(self, frame_rgb, current_time=0.0):
        """
        Fayl mənbəyi olmadan (Instagram) yalnız RGB kadr — qatlar əsas video seçilməmiş də görünsün.
        _filepath = None; Play söndürülür.
        """
        self.stop()
        self._filepath = None
        self._fps = 25.0
        self._total_frames = 0
        self._duration = 0.0
        self._current_time = float(current_time)
        self._playing = False
        self._paused = False
        self._stop_flag = False
        try:
            self._title_lbl.config(text=f" Layer preview{self._preview_badge_text}"[:52])
            self._dur_lbl.config(text=" — select main video")
            self.canvas.itemconfig(self._placeholder_id, text="")
        except Exception:
            pass
        self._refresh_transport_buttons()
        self._vf_canvas_id = None
        raw = np.ascontiguousarray(frame_rgb) if frame_rgb is not None else None
        if raw is None or raw.size == 0:
            return
        self._update_canvas_frame(raw, self._current_time)

    def refresh_composite_at_current_time(self):
        """
        Instagram: mənbə fayl eyni qalır, yalnız qat şəkilləri dəyişəndə.
        preview_file() çağırmır (stop/reset etmir) — cari zamanda bir kadr yenilənir.
        Sinxron çağırış: after(0) gecikməsi olmadan pəncərə dərhal yenilənir.
        """
        if not self._filepath or not os.path.exists(self._filepath):
            return
        try:
            t = float(self._current_time)
        except Exception:
            t = 0.0
        t = max(0.0, t)
        try:
            self._show_frame_at_time(t)
        except Exception:
            pass

    def set_file_info(self, filepath, fps, total_frames, duration):
        self._filepath = filepath
        self._fps = fps
        self._total_frames = total_frames
        self._duration = duration
        fname = os.path.basename(filepath)
        self._title_lbl.config(text=f" {fname[:32]}")
        self._dur_lbl.config(text=f"/ {format_time(duration)}")
        self.canvas.itemconfig(self._placeholder_id, text='')

    def refresh_instagram_overlay_from_settings(self):
        """Pauza / siçan buraxıldıqdan sonra önizləməni yenilə."""
        if self._last_raw_frame_rgb is None:
            return
        try:
            self._update_canvas_frame(self._last_raw_frame_rgb, self._current_time)
        except Exception:
            pass

    def _ig_bind_overlay_events(self):
        if self._ig_overlay_bound:
            return
        self.canvas.bind("<ButtonPress-1>", self._ig_on_down)
        self.canvas.bind("<B1-Motion>", self._ig_on_motion)
        self.canvas.bind("<ButtonRelease-1>", self._ig_on_up)
        self._ig_overlay_bound = True

    def _ig_unbind_overlay_events(self):
        if not self._ig_overlay_bound:
            return
        try:
            self.canvas.unbind("<ButtonPress-1>")
            self.canvas.unbind("<B1-Motion>")
            self.canvas.unbind("<ButtonRelease-1>")
        except Exception:
            pass
        self._ig_overlay_bound = False

    def _ig_layer_source_path(self, app, key: str) -> str:
        """Hər qat üçün diskdə mövcud fayl; center — ayrıca şəkil/video və ya əsas mənbə videosu."""
        if not app:
            return ""
        key = (key or "").strip().lower()

        def _norm(p: str) -> str:
            p = (p or "").strip().strip('"').strip("'")
            return p

        try:
            if key == "center":
                if hasattr(app, "insta_layer_center_var"):
                    p = _norm(app.insta_layer_center_var.get())
                    if p and os.path.isfile(p):
                        return p
                if hasattr(app, "sn_input_var"):
                    p = _norm(app.sn_input_var.get())
                    if p and os.path.isfile(p):
                        return p
                fp = getattr(self, "_filepath", None) or ""
                if fp and os.path.isfile(fp):
                    return fp
                return ""
            vmap = {
                "bg": "insta_layer_bg_var",
                "top": "insta_layer_top_var",
                "bottom": "insta_layer_bottom_var",
            }
            vn = vmap.get(key)
            if not vn or not hasattr(app, vn):
                return ""
            p = _norm(getattr(app, vn).get())
            return p if p and os.path.isfile(p) else ""
        except Exception:
            return ""

    def _ig_layer_has_file(self, app, key: str) -> bool:
        return bool(self._ig_layer_source_path(app, key))

    def _ig_has_layer_paths(self, app):
        """Ən azı bir qatın real faylı varsa overlay + sürüşdürmə (kvadratlar yalnız həmin qatlar üçün)."""
        if not app:
            return False
        for k in ("bg", "top", "bottom", "center"):
            if self._ig_layer_has_file(app, k):
                return True
        return False

    def _ig_canvas_to_1920(self, mx, my):
        lb = self._ig_letterbox
        if not lb:
            return None
        vx, vy, nw, nh = lb["vx"], lb["vy"], lb["nw"], lb["nh"]
        fw, fh = lb["fw"], lb["fh"]
        if mx < vx or my < vy or mx > vx + nw or my > vy + nh:
            return None
        px = (mx - vx) / float(max(1e-6, nw)) * fw
        py = (my - vy) / float(max(1e-6, nh)) * fh
        return lb["crop_x0"] + px, lb["crop_y0"] + py

    def _ig_1920_to_canvas(self, px, py):
        lb = self._ig_letterbox
        if not lb:
            return None, None
        px_c = px - lb["crop_x0"]
        py_c = py - lb["crop_y0"]
        vx, vy, nw, nh = lb["vx"], lb["vy"], lb["nw"], lb["nh"]
        fw, fh = lb["fw"], lb["fh"]
        cx = vx + px_c / float(max(1e-6, fw)) * nw
        cy = vy + py_c / float(max(1e-6, fh)) * nh
        return cx, cy

    def _ig_draw_overlay(self):
        try:
            self.canvas.delete("ig_overlay")
        except Exception:
            pass
        app = self._ig_interact_app
        if not app or not self._ig_letterbox or not self._ig_has_layer_paths(app):
            return
        try:
            from orvix.instagram_layer_layout import layout_to_json, parse_layout_json

            raw = ""
            if hasattr(app, "insta_layer_layout_json_var"):
                raw = (app.insta_layer_layout_json_var.get() or "").strip()
            layout = parse_layout_json(raw)
        except Exception:
            return
        order = ("bg", "top", "bottom", "center")
        colors = {"bg": "#64748b", "top": "#38bdf8", "bottom": "#fbbf24", "center": "#a78bfa"}
        for key in order:
            if not self._ig_layer_has_file(app, key):
                continue
            r = layout.get(key) or {}
            rx, ry, rw, rh = int(r.get("x", 0)), int(r.get("y", 0)), int(r.get("w", 0)), int(r.get("h", 0))
            x1, y1 = self._ig_1920_to_canvas(rx, ry)
            x2, y2 = self._ig_1920_to_canvas(rx + rw, ry + rh)
            if x1 is None or y1 is None:
                continue
            col = colors.get(key, "#fff")
            wv = 3 if key == self._ig_sel_layer else 1
            self.canvas.create_rectangle(
                x1, y1, x2, y2, outline=col, width=wv, dash=(4, 3), tags="ig_overlay"
            )
            self.canvas.create_text(
                x1 + 3, y1 + 2, text=key.upper(), fill=col, anchor=tk.NW, font=("Segoe UI", 8, "bold"), tags="ig_overlay"
            )
        sel = self._ig_sel_layer
        if sel in layout and self._ig_layer_has_file(app, sel):
            r = layout[sel]
            rx, ry, rw, rh = int(r["x"]), int(r["y"]), int(r["w"]), int(r["h"])
            pts = [
                (rx, ry),
                (rx + rw // 2, ry),
                (rx + rw, ry),
                (rx + rw, ry + rh // 2),
                (rx + rw, ry + rh),
                (rx + rw // 2, ry + rh),
                (rx, ry + rh),
                (rx, ry + rh // 2),
            ]
            hs = max(5.0, self._ig_letterbox["nw"] * 0.012)
            for i, (px, py) in enumerate(pts):
                cx, cy = self._ig_1920_to_canvas(px, py)
                if cx is None:
                    continue
                self.canvas.create_rectangle(
                    cx - hs / 2,
                    cy - hs / 2,
                    cx + hs / 2,
                    cy + hs / 2,
                    fill="#f472b6",
                    outline="#fff",
                    width=1,
                    tags="ig_overlay",
                )

    def _ig_hit_handle(self, px, py, r):
        """px,py — 1920; r — düzbucaq. Qaytarır: n, ne, e, se, s, sw, w, nw və ya None."""
        rx, ry, rw, rh = int(r["x"]), int(r["y"]), int(r["w"]), int(r["h"])
        tol = max(24.0, min(rw, rh) * 0.04)
        pts = {
            "nw": (rx, ry),
            "n": (rx + rw // 2, ry),
            "ne": (rx + rw, ry),
            "e": (rx + rw, ry + rh // 2),
            "se": (rx + rw, ry + rh),
            "s": (rx + rw // 2, ry + rh),
            "sw": (rx, ry + rh),
            "w": (rx, ry + rh // 2),
        }
        for name, (hx, hy) in pts.items():
            if abs(px - hx) <= tol and abs(py - hy) <= tol:
                return name
        return None

    def _ig_hit_layer(self, px, py, layout, app):
        for key in ("center", "top", "bottom", "bg"):
            if not self._ig_layer_has_file(app, key):
                continue
            r = layout.get(key)
            if not r:
                continue
            rx, ry, rw, rh = int(r["x"]), int(r["y"]), int(r["w"]), int(r["h"])
            if rx <= px <= rx + rw and ry <= py <= ry + rh:
                return key
        return None

    def _ig_on_down(self, ev):
        app = self._ig_interact_app
        if not app or not self._ig_letterbox or not self._ig_has_layer_paths(app):
            return
        hit = self._ig_canvas_to_1920(ev.x, ev.y)
        if hit is None:
            return
        px, py = hit
        try:
            from orvix.instagram_layer_layout import parse_layout_json

            raw = ""
            if hasattr(app, "insta_layer_layout_json_var"):
                raw = (app.insta_layer_layout_json_var.get() or "")
            layout = parse_layout_json(raw)
        except Exception:
            return
        for key in ("center", "top", "bottom", "bg"):
            if not self._ig_layer_has_file(app, key):
                continue
            r = layout.get(key)
            if not r:
                continue
            hname = self._ig_hit_handle(px, py, r)
            if hname:
                self._ig_sel_layer = key
                try:
                    if hasattr(app, "insta_layer_active_var"):
                        app.insta_layer_active_var.set(key)
                except Exception:
                    pass
                self._ig_drag = {
                    "mode": hname,
                    "layer": key,
                    "px0": px,
                    "py0": py,
                    "rect0": dict(r),
                }
                try:
                    self._ig_draw_overlay()
                except Exception:
                    pass
                return
        layer = self._ig_hit_layer(px, py, layout, app)
        if layer:
            self._ig_sel_layer = layer
            try:
                if hasattr(app, "insta_layer_active_var"):
                    app.insta_layer_active_var.set(layer)
            except Exception:
                pass
            r = layout[layer]
            self._ig_drag = {
                "mode": "move",
                "layer": layer,
                "px0": px,
                "py0": py,
                "rect0": dict(r),
            }
        try:
            self._ig_draw_overlay()
        except Exception:
            pass

    def _ig_apply_rect_delta(self, layout, layer, mode, dx, dy):
        r = layout[layer]
        rx, ry, rw, rh = int(r["x"]), int(r["y"]), int(r["w"]), int(r["h"])
        m = mode
        if m == "move":
            r["x"] = rx + int(round(dx))
            r["y"] = ry + int(round(dy))
            return
        if m == "e":
            r["w"] = max(32, rw + int(round(dx)))
        elif m == "w":
            nx = rx + int(round(dx))
            r["w"] = max(32, rw - int(round(dx)))
            r["x"] = nx
        elif m == "s":
            r["h"] = max(32, rh + int(round(dy)))
        elif m == "n":
            ny = ry + int(round(dy))
            r["h"] = max(32, rh - int(round(dy)))
            r["y"] = ny
        elif m == "se":
            r["w"] = max(32, rw + int(round(dx)))
            r["h"] = max(32, rh + int(round(dy)))
        elif m == "sw":
            nx = rx + int(round(dx))
            r["w"] = max(32, rw - int(round(dx)))
            r["x"] = nx
            r["h"] = max(32, rh + int(round(dy)))
        elif m == "ne":
            ny = ry + int(round(dy))
            r["h"] = max(32, rh - int(round(dy)))
            r["y"] = ny
            r["w"] = max(32, rw + int(round(dx)))
        elif m == "nw":
            nx = rx + int(round(dx))
            ny = ry + int(round(dy))
            r["w"] = max(32, rw - int(round(dx)))
            r["h"] = max(32, rh - int(round(dy)))
            r["x"] = nx
            r["y"] = ny

    def _ig_on_motion(self, ev):
        d = self._ig_drag
        app = self._ig_interact_app
        if not d or not app or not self._ig_letterbox:
            return
        hit = self._ig_canvas_to_1920(ev.x, ev.y)
        if hit is None:
            return
        px, py = hit
        dx = px - d["px0"]
        dy = py - d["py0"]
        try:
            from orvix.instagram_layer_layout import layout_to_json, parse_layout_json

            if not hasattr(app, "insta_layer_layout_json_var"):
                return
            layout = parse_layout_json((app.insta_layer_layout_json_var.get() or ""))
            layer = d["layer"]
            if layer not in layout:
                return
            layout[layer] = dict(d["rect0"])
            self._ig_apply_rect_delta(layout, layer, d["mode"], dx, dy)
            layout = parse_layout_json(layout_to_json(layout))
            app.insta_layer_layout_json_var.set(layout_to_json(layout))
        except Exception:
            return
        try:
            if hasattr(app, "_instagram_sync_layer_params_ui"):
                app._instagram_sync_layer_params_ui()
        except Exception:
            pass
        self.refresh_instagram_overlay_from_settings()

    def _ig_on_up(self, _ev):
        if self._ig_drag:
            self._ig_drag = None
            try:
                app = self._ig_interact_app
                if app:
                    if hasattr(app, "_instagram_sync_layer_params_ui"):
                        app._instagram_sync_layer_params_ui()
                    if hasattr(app, "_instagram_workspace_preview_mode"):
                        app._instagram_workspace_preview_mode()
            except Exception:
                pass

    def destroy(self):
        self.stop()
        try:
            self._audio_player.stop()
        except Exception:
            pass
        for _vu in (self._vu_meter, self._vu_meter_file):
            if _vu:
                try:
                    _vu.destroy()
                except Exception:
                    pass
        try:
            self.frame.destroy()
        except Exception:
            pass

