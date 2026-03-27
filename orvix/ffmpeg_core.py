"""FFmpeg / FFprobe / FFplay tapılması və müvəqqəti qovluq."""
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

from orvix.ffmpeg_cuda import probe_cuda_capabilities


class FFmpegManager:
    def __init__(self):
        self.ffmpeg_path = None
        self.ffprobe_path = None
        self.ffplay_path = None
        self.cuda_caps = None
        self.temp_dir = os.path.join(tempfile.gettempdir(), 'orvix_ffmpeg')
        os.makedirs(self.temp_dir, exist_ok=True)

    def _get_startupinfo(self):
        if os.name == 'nt':
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = subprocess.SW_HIDE
            return si
        return None

    def _download_ffmpeg_windows(self):
        """
        Best-effort: download ffmpeg/ffprobe/ffplay into self.temp_dir.
        Keeps app functional on PCs without FFmpeg installed.
        """
        if os.name != 'nt':
            return False
        try:
            os.makedirs(self.temp_dir, exist_ok=True)
            ff_path = os.path.join(self.temp_dir, 'ffmpeg.exe')
            fp_path = os.path.join(self.temp_dir, 'ffprobe.exe')
            fl_path = os.path.join(self.temp_dir, 'ffplay.exe')
            # If already present, don't redownload.
            if os.path.exists(ff_path):
                return True

            url = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip'
            zip_path = os.path.join(self.temp_dir, 'ffmpeg_release_essentials.zip')

            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'OrvixLite/ffmpeg-bootstrap'}
            )
            with urllib.request.urlopen(req, timeout=45) as r:
                data = r.read()
            with open(zip_path, 'wb') as f:
                f.write(data)

            extracted = False
            with zipfile.ZipFile(zip_path, 'r') as z:
                # Find executables inside the zip.
                names = z.namelist()
                def pick(exe):
                    exe_l = exe.lower()
                    for n in names:
                        nl = n.lower()
                        if nl.endswith('/' + exe_l) or nl.endswith('\\' + exe_l) or nl.endswith(exe_l):
                            if '/bin/' in nl or '\\bin\\' in nl:
                                return n
                    for n in names:
                        if n.lower().endswith(exe_l):
                            return n
                    return None

                for exe, outp in [('ffmpeg.exe', ff_path), ('ffprobe.exe', fp_path), ('ffplay.exe', fl_path)]:
                    member = pick(exe)
                    if not member:
                        continue
                    with z.open(member) as src, open(outp, 'wb') as dst:
                        shutil.copyfileobj(src, dst)
                    extracted = True

            try:
                os.remove(zip_path)
            except Exception:
                pass
            return extracted and os.path.exists(ff_path)
        except Exception:
            return False

    def find_ffmpeg(self):
        base = (os.path.dirname(sys.executable) if getattr(sys, 'frozen', False)
                else os.path.dirname(os.path.abspath(__file__)))
        candidates = [
            os.path.join(base, 'ffmpeg.exe'),
            os.path.join(base, 'bin', 'ffmpeg.exe'),
            os.path.join(os.getcwd(), 'ffmpeg.exe'),
            os.path.join(self.temp_dir, 'ffmpeg.exe'),
        ]
        ff = shutil.which('ffmpeg')
        if ff:
            candidates.append(ff)
        for p in candidates:
            if p and os.path.exists(p):
                self.ffmpeg_path = p
                pp = p.replace('ffmpeg.exe', 'ffprobe.exe')
                self.ffprobe_path = pp if os.path.exists(pp) else shutil.which('ffprobe') or 'ffprobe'
                pplay = p.replace('ffmpeg.exe', 'ffplay.exe')
                self.ffplay_path = pplay if os.path.exists(pplay) else shutil.which('ffplay') or 'ffplay'
                self.cuda_caps = probe_cuda_capabilities(self.ffmpeg_path, self._get_startupinfo())
                return True
        ff = shutil.which('ffmpeg')
        if ff:
            self.ffmpeg_path = ff
            self.ffprobe_path = shutil.which('ffprobe') or ff
            self.ffplay_path = shutil.which('ffplay') or ff.replace('ffmpeg', 'ffplay')
            self.cuda_caps = probe_cuda_capabilities(self.ffmpeg_path, self._get_startupinfo())
            return True
        for name in ['ffmpeg', '/usr/bin/ffmpeg', '/usr/local/bin/ffmpeg']:
            if shutil.which(name):
                self.ffmpeg_path = shutil.which(name)
                self.ffprobe_path = shutil.which('ffprobe') or ''
                self.ffplay_path = shutil.which('ffplay') or ''
                self.cuda_caps = probe_cuda_capabilities(self.ffmpeg_path, self._get_startupinfo())
                return True

        # Last resort: auto-download on Windows (portable exe use-case)
        if self._download_ffmpeg_windows():
            p = os.path.join(self.temp_dir, 'ffmpeg.exe')
            if os.path.exists(p):
                self.ffmpeg_path = p
                pp = os.path.join(self.temp_dir, 'ffprobe.exe')
                self.ffprobe_path = pp if os.path.exists(pp) else shutil.which('ffprobe') or 'ffprobe'
                pl = os.path.join(self.temp_dir, 'ffplay.exe')
                self.ffplay_path = pl if os.path.exists(pl) else shutil.which('ffplay') or 'ffplay'
                self.cuda_caps = probe_cuda_capabilities(self.ffmpeg_path, self._get_startupinfo())
                return True
        self.cuda_caps = probe_cuda_capabilities(None, None)
        return False


ffmpeg_mgr = FFmpegManager()
ffmpeg_mgr.find_ffmpeg()
