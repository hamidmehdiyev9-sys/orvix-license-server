"""Video və audio analiz."""
import os
import subprocess
import tempfile
import threading
import time
import wave

import numpy as np

from orvix.deps import SCIPY_AVAILABLE
from orvix.ffmpeg_core import ffmpeg_mgr
from orvix.gpu import gpu_acc
from orvix.utils import format_time

class ProfessionalVideoAnalyzer:
    def __init__(self):
        self.cancel_flag = False
        self.active_problems = {}
        self.gpu = gpu_acc
        self.buffer_size = 50

    def analyze(self, fp, fps, total_frames, duration,
                progress_cb=None, log_cb=None, problem_cb=None):
        self.cancel_flag = False
        problems = []
        t0 = time.time()
        frame_count = 0
        self.active_problems = {}
        if not ffmpeg_mgr.ffmpeg_path:
            if log_cb:
                log_cb("[ERROR] FFmpeg not found")
            return {'problems': [], 'analysis_time': 0, 'rate': 0}
        if not total_frames or total_frames == 0:
            try:
                file_size_mb = os.path.getsize(fp) / (1024 * 1024) if os.path.exists(fp) else 0
                total_frames = max(1000, int(file_size_mb * 27))
            except Exception:
                total_frames = 27000
        analyze_frames = total_frames
        gpu_info = self.gpu.get_gpu_info()
        if log_cb:
            log_cb(f"  MAX PERFORMANCE MODE: {total_frames:,} frames")
            log_cb(f"  GPU: {gpu_info['name']} ({gpu_info['type']})")
        cmd = [
            ffmpeg_mgr.ffmpeg_path,
            '-i', fp,
            '-vf', f'fps={fps},scale=320:180',
            '-f', 'image2pipe',
            '-pix_fmt', 'rgb24',
            '-vcodec', 'rawvideo',
            '-threads', 'auto',
            '-'
        ]
        try:
            si = ffmpeg_mgr._get_startupinfo()
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=320 * 180 * 3 * 200,
                startupinfo=si
            )
        except Exception as e:
            if log_cb:
                log_cb(f"[ERROR] FFmpeg launch: {e}")
            return {'problems': [], 'analysis_time': 0, 'rate': 0}
        frame_size = 320 * 180 * 3
        prev_frame = None
        prev_luma = None
        prev_hash = None
        frames_processed = 0
        while True:
            if self.cancel_flag or (time.time() - t0) > 600:
                for ptype, pdata in self.active_problems.items():
                    p = self._create_problem(ptype, pdata['name'], 'VIDEO', pdata['start'],
                                             duration, pdata.get('value', 0), f'{pdata["name"]}', pdata['severity'])
                    problems.append(p)
                    if problem_cb:
                        problem_cb(p)
                try:
                    proc.kill()
                except Exception:
                    pass
                return {'cancelled': True, 'problems': problems,
                        'analysis_time': time.time() - t0, 'frames_analyzed': frames_processed}
            raw_batch = []
            for _ in range(50):
                raw = proc.stdout.read(frame_size)
                if not raw or len(raw) < frame_size:
                    break
                raw_batch.append(raw)
            if not raw_batch:
                break
            for raw in raw_batch:
                frame_count += 1
                if frame_count > analyze_frames:
                    break
                if frame_count % 3 != 1:
                    continue
                frames_processed += 1
                current_time = frame_count / fps
                frame = np.frombuffer(raw, dtype=np.uint8).reshape((180, 320, 3))
                gray = self.gpu.to_gray(frame)
                luma = np.mean(gray)
                current_hash = hash(frame.tobytes()) % (2 ** 32)
                if frames_processed % 1000 == 0 and progress_cb:
                    pct = min(99, (frame_count / analyze_frames) * 100)
                    elapsed = time.time() - t0
                    fps_analysis = frames_processed / elapsed if elapsed > 0 else 0
                    eta = (analyze_frames / 3 - frames_processed) / fps_analysis if fps_analysis > 0 else 0
                    progress_cb(pct, f"Video: {frame_count}/{analyze_frames} | {fps_analysis:.0f} fps | ETA: {eta:.0f}s")
                if prev_frame is not None:
                    diff = self.gpu.frame_diff(frame, prev_frame)
                    if diff < 3:
                        if 'FROZEN' not in self.active_problems:
                            self.active_problems['FROZEN'] = {'start': current_time, 'name': 'Frozen Frame', 'severity': 'ERROR', 'value': 0}
                    else:
                        if 'FROZEN' in self.active_problems:
                            start = self.active_problems['FROZEN']['start']
                            if current_time - start >= 2.0:
                                p = self._create_problem('FROZEN', 'Frozen Frame', 'VIDEO', start, current_time,
                                                         current_time - start, f'Donma: {current_time - start:.2f}s', 'ERROR')
                                problems.append(p)
                                if problem_cb:
                                    problem_cb(p)
                            del self.active_problems['FROZEN']
                if luma < 16:
                    if 'BLACK' not in self.active_problems:
                        self.active_problems['BLACK'] = {'start': current_time, 'name': 'Black Frame', 'severity': 'ERROR', 'value': luma}
                else:
                    if 'BLACK' in self.active_problems:
                        start = self.active_problems['BLACK']['start']
                        if current_time - start >= 0.2:
                            p = self._create_problem('BLACK', 'Black Frame', 'VIDEO', start, current_time, luma,
                                                     f'Qara ekran: {current_time - start:.2f}s', 'ERROR')
                            problems.append(p)
                            if problem_cb:
                                problem_cb(p)
                        del self.active_problems['BLACK']
                if prev_luma is not None:
                    change = abs(luma - prev_luma) / max(prev_luma, 1) * 100
                    if change > 30:
                        if 'FLICKER' not in self.active_problems:
                            self.active_problems['FLICKER'] = {'start': current_time, 'name': 'Flash/Flicker', 'severity': 'WARNING', 'value': change}
                    else:
                        if 'FLICKER' in self.active_problems:
                            start = self.active_problems['FLICKER']['start']
                            if current_time - start >= 0.1:
                                p = self._create_problem('FLICKER', 'Flash/Flicker', 'VIDEO', start, current_time,
                                                         change, 'Titreme', 'WARNING')
                                problems.append(p)
                                if problem_cb:
                                    problem_cb(p)
                            del self.active_problems['FLICKER']
                if prev_hash is not None and current_hash == prev_hash:
                    if 'DUPLICATE' not in self.active_problems:
                        self.active_problems['DUPLICATE'] = {'start': current_time, 'name': 'Duplicate Frame', 'severity': 'WARNING', 'value': 0}
                else:
                    if 'DUPLICATE' in self.active_problems:
                        start = self.active_problems['DUPLICATE']['start']
                        if current_time - start >= 1.0:
                            p = self._create_problem('DUPLICATE', 'Duplicate Frame', 'VIDEO', start, current_time,
                                                     current_time - start, 'Tekrarlanan kadr', 'WARNING')
                            problems.append(p)
                            if problem_cb:
                                problem_cb(p)
                        del self.active_problems['DUPLICATE']
                prev_frame = frame.copy()
                prev_luma = luma
                prev_hash = current_hash
        for ptype, pdata in self.active_problems.items():
            p = self._create_problem(ptype, pdata['name'], 'VIDEO', pdata['start'], duration,
                                     pdata.get('value', 0), f'{pdata["name"]}', pdata['severity'])
            problems.append(p)
            if problem_cb:
                problem_cb(p)
        try:
            proc.wait(timeout=3)
        except Exception:
            pass
        elapsed = time.time() - t0
        return {'problems': problems, 'analysis_time': elapsed,
                'rate': frames_processed / elapsed if elapsed > 0 else 0,
                'frames_analyzed': frames_processed}

    def _create_problem(self, ptype, pname, category, start, end, value, desc, severity):
        return {
            'type': ptype, 'type_az': pname, 'category': category, 'severity': severity,
            'start_time': round(start, 3), 'end_time': round(end, 3),
            'start_time_str': format_time(start), 'end_time_str': format_time(end),
            'duration': round(end - start, 3) if end > start else 0,
            'value': f"{value:.2f}" if isinstance(value, (int, float)) else str(value),
            'description': desc
        }

    def cancel(self):
        self.cancel_flag = True


class ProfessionalAudioAnalyzer:
    def __init__(self):
        self.cancel_flag = False
        self.active_problems = {}

    def analyze(self, fp, progress_cb=None, log_cb=None, problem_cb=None):
        self.cancel_flag = False
        problems = []
        t0 = time.time()
        self.active_problems = {}
        tmp = tempfile.mktemp(suffix='.wav')
        try:
            cmd = [ffmpeg_mgr.ffmpeg_path, '-i', fp, '-vn', '-acodec', 'pcm_s16le',
                   '-ar', '48000', '-ac', '2', '-y', tmp]
            si = ffmpeg_mgr._get_startupinfo()
            subprocess.run(cmd, capture_output=True, text=True, timeout=180, startupinfo=si)
            if not os.path.exists(tmp) or os.path.getsize(tmp) < 100:
                return {'has_audio': False, 'problems': []}
            wf = wave.open(tmp, 'rb')
            sr = wf.getframerate()
            sw = wf.getsampwidth()
            nch = wf.getnchannels()
            nframes = wf.getnframes()
            duration = nframes / sr
            block_size = 8192
            n_blocks = nframes // block_size
            max_amp = float(2 ** (sw * 8 - 1))
            for block_idx in range(n_blocks):
                if self.cancel_flag or (time.time() - t0) > 180:
                    wf.close()
                    return {'cancelled': True, 'has_audio': True, 'problems': problems}
                frames = wf.readframes(block_size)
                if not frames:
                    break
                current_time = block_idx * block_size / sr
                if sw == 2:
                    data = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
                else:
                    data = np.frombuffer(frames, dtype=np.int32).astype(np.float32)
                if nch == 2:
                    data = data.reshape(-1, 2)
                    left = data[:, 0] / max_amp
                    right = data[:, 1] / max_amp
                else:
                    left = data / max_amp
                    right = left
                rms_left = 20 * np.log10(np.sqrt(np.mean(left ** 2)) + 1e-10)
                rms_right = 20 * np.log10(np.sqrt(np.mean(right ** 2)) + 1e-10)
                rms_avg = (rms_left + rms_right) / 2
                if progress_cb and block_idx % 5 == 0:
                    pct = (block_idx / n_blocks) * 100
                    progress_cb(70 + pct * 0.3, f"Audio: {pct:.0f}%")
                if rms_avg < -60:
                    if 'SILENCE' not in self.active_problems:
                        self.active_problems['SILENCE'] = {'start': current_time, 'name': 'Silence', 'severity': 'ERROR', 'value': rms_avg}
                else:
                    if 'SILENCE' in self.active_problems:
                        start = self.active_problems['SILENCE']['start']
                        if current_time - start >= 0.5:
                            p = self._create_problem('SILENCE', 'Silence', 'AUDIO', start, current_time, rms_avg, 'Sessizlik', 'ERROR')
                            problems.append(p)
                            if problem_cb:
                                problem_cb(p)
                        del self.active_problems['SILENCE']
                clip_count = np.sum(np.abs(left) > 0.99) + np.sum(np.abs(right) > 0.99)
                if clip_count > 0:
                    if 'CLIPPING' not in self.active_problems:
                        self.active_problems['CLIPPING'] = {'start': current_time, 'name': 'Clipping', 'severity': 'ERROR', 'value': rms_avg}
                else:
                    if 'CLIPPING' in self.active_problems:
                        start = self.active_problems['CLIPPING']['start']
                        if current_time - start >= 0.1:
                            p = self._create_problem('CLIPPING', 'Clipping', 'AUDIO', start, current_time, rms_avg, 'Kesilmish ses', 'ERROR')
                            problems.append(p)
                            if problem_cb:
                                problem_cb(p)
                        del self.active_problems['CLIPPING']
                if SCIPY_AVAILABLE and block_idx % 20 == 0 and len(left) > 100:
                    fft_data = np.abs(fft(left))
                    freqs = fftfreq(len(left), 1 / sr)
                    mag_50 = np.mean(fft_data[(freqs >= 45) & (freqs <= 55)]) if np.any((freqs >= 45) & (freqs <= 55)) else 0
                    mag_60 = np.mean(fft_data[(freqs >= 55) & (freqs <= 65)]) if np.any((freqs >= 55) & (freqs <= 65)) else 0
                    mag_avg = np.mean(fft_data[5:]) if len(fft_data) > 5 else 1
                    if mag_avg > 0 and (mag_50 / mag_avg > 3 or mag_60 / mag_avg > 3):
                        if 'HUM' not in self.active_problems:
                            self.active_problems['HUM'] = {'start': current_time, 'name': 'Hum', 'severity': 'WARNING', 'value': max(mag_50, mag_60)}
                    else:
                        if 'HUM' in self.active_problems:
                            start = self.active_problems['HUM']['start']
                            if current_time - start >= 0.5:
                                p = self._create_problem('HUM', 'Hum', 'AUDIO', start, current_time, max(mag_50, mag_60), 'Elektrik sesi', 'WARNING')
                                problems.append(p)
                                if problem_cb:
                                    problem_cb(p)
                            del self.active_problems['HUM']
            for ptype, pdata in self.active_problems.items():
                p = self._create_problem(ptype, pdata['name'], 'AUDIO', pdata['start'], duration,
                                         pdata.get('value', 0), f'{pdata["name"]}', pdata['severity'])
                problems.append(p)
                if problem_cb:
                    problem_cb(p)
            wf.close()
            return {'has_audio': True, 'problems': problems}
        except Exception as e:
            if log_cb:
                log_cb(f"  [Audio error] {e}")
            return {'has_audio': False, 'problems': []}
        finally:
            try:
                os.remove(tmp)
            except Exception:
                pass

    def _create_problem(self, ptype, pname, category, start, end, value, desc, severity):
        return {
            'type': ptype, 'type_az': pname, 'category': category, 'severity': severity,
            'start_time': round(start, 3), 'end_time': round(end, 3),
            'start_time_str': format_time(start), 'end_time_str': format_time(end),
            'duration': round(end - start, 3) if end > start else 0,
            'value': f"{value:.2f}" if isinstance(value, (int, float)) else str(value),
            'description': desc
        }

    def cancel(self):
        self.cancel_flag = True
