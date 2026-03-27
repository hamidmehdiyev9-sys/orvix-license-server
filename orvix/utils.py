"""Vaxt, ffprobe, format köməkçiləri."""
import datetime
import json
import os
import subprocess

from orvix.ffmpeg_core import ffmpeg_mgr

def format_time(seconds):
    if seconds is None:
        return "00:00.000"
    try:
        seconds = float(seconds)
        if seconds < 0:
            seconds = 0
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
        else:
            return f"{minutes:02d}:{secs:06.3f}"
    except Exception:
        return "00:00.000"


def get_english_time():
    now = datetime.datetime.now()
    wd = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][now.weekday()]
    mo = ['January', 'February', 'March', 'April', 'May', 'June',
          'July', 'August', 'September', 'October', 'November', 'December'][now.month - 1]
    return {
        'time': now.strftime("%H:%M:%S"),
        'date': f"{wd}, {now.day} {mo} {now.year}",
        'full': f"{wd}, {now.day} {mo} {now.year} {now.strftime('%H:%M:%S')}"
    }


def run_ffprobe(fp):
    if not ffmpeg_mgr.ffprobe_path:
        return None
    try:
        cmd = [ffmpeg_mgr.ffprobe_path, '-v', 'quiet', '-print_format', 'json',
               '-show_format', '-show_streams', fp]
        si = ffmpeg_mgr._get_startupinfo()
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30, startupinfo=si)
        if r and r.returncode == 0 and r.stdout:
            return json.loads(r.stdout)
    except Exception:
        pass
    return None


def fmt_bitrate(bps):
    if not bps:
        return 'N/A'
    try:
        b = int(bps)
        if b >= 1000000:
            return f"{b / 1000000:.2f} Mbps"
        if b >= 1000:
            return f"{b / 1000:.0f} Kbps"
        return f"{b} bps"
    except Exception:
        return str(bps)


def fmt_dur(s):
    try:
        return format_time(float(s))
    except Exception:
        return str(s)


def fmt_size(fp):
    try:
        sz = os.path.getsize(fp)
        if sz >= 1073741824:
            return f"{sz / 1073741824:.3f} GB"
        if sz >= 1048576:
            return f"{sz / 1048576:.2f} MB"
        if sz >= 1024:
            return f"{sz / 1024:.1f} KB"
        return f"{sz} bytes"
    except Exception:
        return 'N/A'


CODEC_NAMES = {
    'h264': 'H.264 / AVC', 'hevc': 'H.265 / HEVC', 'aac': 'AAC', 'mp3': 'MP3'
}
CH_NAMES = {1: 'Mono', 2: 'Stereo', 6: '5.1 Surround', 8: '7.1 Surround'}


def get_codec_full(name, profile=None):
    n = CODEC_NAMES.get(name, name or 'N/A')
    if profile and profile not in ('N/A', '', 'unknown'):
        n += f" [{profile}]"
    return n


PROBLEM_DICTIONARY = {
    'FROZEN': {'name': 'Frozen Frame', 'description': 'Video kadri donub', 'cause': 'Kodlashdirma xetasi', 'solution': 'Yeniden kodlashdirin', 'example': 'Eyni kadr 2 saniyeden cox'},
    'BLACK': {'name': 'Black Frame', 'description': 'Kadr tam qaradir', 'cause': 'Kamera baglanib', 'solution': 'Video menbeyini yoxlayin', 'example': 'Parlaqlig 16-dan ashagi'},
    'OVERBRIGHT': {'name': 'Overbright Frame', 'description': 'Heddinden artiq parlaq', 'cause': 'Heddinden artiq ishiq', 'solution': 'Ekspozisiyani azaldin', 'example': 'Parlaqlig 235-den yuxari'},
    'FLICKER': {'name': 'Flash/Flicker', 'description': 'Ani parlaqlig deyishmesi', 'cause': 'Ishiq menbei', 'solution': 'Kamera tenzimeleri', 'example': 'Deyishme 30%-den cox'},
    'BLUR': {'name': 'Blur', 'description': 'Bulaniqlig', 'cause': 'Fokus problemi', 'solution': 'Fokusu duzheldin', 'example': 'Laplacian 100-den ashagi'},
    'DUPLICATE': {'name': 'Duplicate Frame', 'description': 'Tekrarlanan kadr', 'cause': 'Kodlashdirma xetasi', 'solution': 'Yeniden kodlashdirin', 'example': 'Ardicil eyni kadrlar'},
    'COLOR_SHIFT': {'name': 'Color Shift', 'description': 'Reng deyishmesi', 'cause': 'Ag balansi', 'solution': 'Reng korreksiyasi', 'example': 'RGB deyishmesi 30%'},
    'SCENE_CHANGE': {'name': 'Scene Change', 'description': 'Sehne deyishmesi', 'cause': 'Normal montaj', 'solution': 'Kechid effektleri', 'example': 'Deyishme 50%'},
    'FRAME_DROP': {'name': 'Frame Drop', 'description': 'Kadr itmesi', 'cause': 'Yavas sistem', 'solution': 'Sistem resurslari', 'example': '5% itib'},
    'SILENCE': {'name': 'Silence', 'description': 'Sessizlik', 'cause': 'Mikrofon bagli deyil', 'solution': 'Seviyyeni artirin', 'example': 'RMS -60dB'},
    'LOW_VOLUME': {'name': 'Low Volume', 'description': 'Ashagi ses', 'cause': 'Mikrofon seviyyesi ashagi', 'solution': 'Normalizasiya', 'example': 'RMS -40dB'},
    'CLIPPING': {'name': 'Clipping', 'description': 'Kesilmish ses', 'cause': 'Ses cox yuksek', 'solution': 'Limiter tetbiq edin', 'example': '0 dBFS'},
    'CHANNEL_MISSING': {'name': 'Channel Missing', 'description': 'Kanal itmesi', 'cause': 'Kabel problemi', 'solution': 'Kanali berpa edin', 'example': 'Bir kanal yox'},
    'PHASE': {'name': 'Phase Problem', 'description': 'Faza uygunsuzlugu', 'cause': 'Sehv mikrofon', 'solution': 'Fazani deyishin', 'example': 'Ses boghuq'},
    'HUM': {'name': 'Hum', 'description': 'Elektrik sesi', 'cause': 'Torpaqlama', 'solution': 'Balansi kabel', 'example': '50/60 Hz'},
}

