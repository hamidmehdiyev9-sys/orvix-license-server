"""FFmpeg pipe → sounddevice audio."""
import subprocess
import threading

import numpy as np

from orvix.deps import _HAS_SD
from orvix.ffmpeg_core import ffmpeg_mgr
from orvix.utils import run_ffprobe

if _HAS_SD:
    import sounddevice as sd


class SoundAudioPlayer:
    """
    - SRC PFL: çıxış = fayl nümunəsi olduğu kimi (unity, “necə yazılıbsa”).
    - MON PFL: çıxış = fayl × monitor_vol (məs. problem rejimi 5% = 0.05).
    - Heç bir PFL aktiv deyilsə: çıxış susqun.
    VU snapshot UI thread üçün get_levels_snapshot ilə.
    """

    CHUNK = 256

    def __init__(self, on_levels=None):
        self._on_levels = on_levels
        self._proc = None
        self._stream = None
        self._monitor_vol = 0.05
        self._source_vol = 1.0
        self._source_pfl = False
        self._monitor_pfl = False
        self._channels = 2
        self._rate = 44100
        self._lock = threading.Lock()
        self._levels_lock = threading.Lock()
        self._levels_snapshot = None
        self._running = False
        self._fade_samples_remaining = 0

    def apply_routing(
        self,
        source_pfl: bool,
        monitor_pfl: bool,
        source_vol: float,
        monitor_vol: float,
    ):
        with self._lock:
            sp = bool(source_pfl)
            mp = bool(monitor_pfl)
            if sp:
                mp = False
            elif mp:
                sp = False
            self._source_pfl = sp
            self._monitor_pfl = mp
            self._source_vol = max(0.0, min(2.0, float(source_vol)))
            self._monitor_vol = max(0.0, min(2.0, float(monitor_vol)))

    def is_streaming(self):
        return self._stream is not None and self._running

    def get_levels_snapshot(self):
        with self._levels_lock:
            if self._levels_snapshot is None:
                return None
            a, b, c, d = self._levels_snapshot
            return (a.copy(), b.copy(), c.copy(), d.copy())

    def start(self, filepath, start_time=0.0, monitor_vol=0.05):
        self.stop()
        if not _HAS_SD:
            return False
        if not ffmpeg_mgr.ffmpeg_path:
            return False
        with self._lock:
            self._monitor_vol = max(0.0, min(2.0, float(monitor_vol)))
        try:
            probe = run_ffprobe(filepath)
            for s in (probe or {}).get("streams", []):
                if s.get("codec_type") == "audio":
                    self._channels = int(s.get("channels", 2))
                    self._rate = int(s.get("sample_rate", 44100))
                    break
        except Exception:
            pass
        self._channels = min(self._channels, 2)
        st = max(0.0, float(start_time))
        # -ss həmişə -i-dən sonra: nümunə-dəqiq kəs (OpenCV video ilə eyni möhərə yaxın)
        cmd = [
            ffmpeg_mgr.ffmpeg_path,
            "-nostdin",
            "-i",
            filepath,
            "-ss",
            str(st),
            "-f",
            "f32le",
            "-ar",
            str(self._rate),
            "-ac",
            str(self._channels),
            "-vn",
            "pipe:1",
        ]
        try:
            si = ffmpeg_mgr._get_startupinfo()
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=self.CHUNK * self._channels * 4,
                startupinfo=si,
            )
            self._running = True
            with self._levels_lock:
                self._levels_snapshot = None
            self._stream = sd.RawOutputStream(
                samplerate=self._rate,
                channels=self._channels,
                dtype="float32",
                blocksize=self.CHUNK,
                latency="low",
                callback=self._callback,
            )
            self._stream.start()
            self._fade_samples_remaining = 0
            return True
        except Exception as e:
            print(f"[Audio] Error: {e}")
            self.stop()
            return False

    def _callback(self, outdata, frames, time_info, status):
        needed = frames * self._channels * 4
        try:
            raw = self._proc.stdout.read(needed)
        except Exception:
            raw = b""
        if len(raw) < needed:
            outdata[:] = b"\x00" * len(outdata)
            self._running = False
            return
        arr = np.frombuffer(raw, dtype=np.float32).copy()
        try:
            mat = arr.reshape(-1, self._channels)
            rms_src = np.sqrt(np.mean(mat ** 2, axis=0))
            peak_src = np.max(np.abs(mat), axis=0)
            if rms_src.size == 1:
                rms_src = np.array([rms_src[0], rms_src[0]], dtype=np.float32)
                peak_src = np.array([peak_src[0], peak_src[0]], dtype=np.float32)
        except Exception:
            rms_src = peak_src = np.zeros(2, dtype=np.float32)

        with self._lock:
            sp = self._source_pfl
            mp = self._monitor_pfl
            mv = float(self._monitor_vol)

        if sp:
            out = arr
            rms_mon = np.zeros(2, dtype=np.float32)
            peak_mon = np.zeros(2, dtype=np.float32)
        elif mp:
            out = arr * mv
            try:
                mat_m = out.reshape(-1, self._channels)
                rms_mon = np.sqrt(np.mean(mat_m ** 2, axis=0))
                peak_mon = np.max(np.abs(mat_m), axis=0)
                if rms_mon.size == 1:
                    rms_mon = np.array([rms_mon[0], rms_mon[0]], dtype=np.float32)
                    peak_mon = np.array([peak_mon[0], peak_mon[0]], dtype=np.float32)
            except Exception:
                rms_mon = peak_mon = np.zeros(2, dtype=np.float32)
        else:
            out = np.zeros_like(arr)
            rms_mon = np.zeros(2, dtype=np.float32)
            peak_mon = np.zeros(2, dtype=np.float32)

        rms_sv = rms_src.copy()
        peak_sv = peak_src.copy()

        outdata[:] = out.tobytes()

        try:
            with self._levels_lock:
                self._levels_snapshot = (
                    rms_mon.copy(),
                    peak_mon.copy(),
                    rms_sv.copy(),
                    peak_sv.copy(),
                )
        except Exception:
            pass

    def stop(self):
        self._running = False
        with self._levels_lock:
            self._levels_snapshot = None
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=1)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
        self._proc = None
        self._fade_samples_remaining = 0

    def set_monitor_vol(self, v):
        with self._lock:
            self._monitor_vol = max(0.0, min(2.0, float(v)))

    def set_source_vol(self, v):
        with self._lock:
            self._source_vol = max(0.0, min(2.0, float(v)))

    def set_source_pfl(self, active: bool):
        with self._lock:
            self._source_pfl = bool(active)
            if self._source_pfl:
                self._monitor_pfl = False

    def set_monitor_pfl(self, active: bool):
        with self._lock:
            self._monitor_pfl = bool(active)
            if self._monitor_pfl:
                self._source_pfl = False

    def set_volume(self, v):
        self.set_monitor_vol(v)

    def set_pfl(self, active: bool):
        self.set_monitor_pfl(bool(active))
        if active:
            self.set_source_pfl(False)
