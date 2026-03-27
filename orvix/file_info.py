"""Fayl metadata çıxarışı."""
import datetime
import os

from orvix.utils import (
    CH_NAMES,
    fmt_bitrate,
    fmt_dur,
    fmt_size,
    get_codec_full,
    run_ffprobe,
)

class FileInfoExtractor:
    @staticmethod
    def extract(fp):
        try:
            if not os.path.exists(fp):
                return {
                    'file': {'name': os.path.basename(fp), 'path': fp},
                    'video': {'fps': 25, 'total_frames': 0},
                    'format': {'duration_sec': 0}
                }
            info = {'file': {
                'name': os.path.basename(fp),
                'path': fp,
                'extension': os.path.splitext(fp)[1].lower(),
                'size': fmt_size(fp),
                'size_bytes': os.path.getsize(fp),
                'modified': datetime.datetime.fromtimestamp(os.path.getmtime(fp)).strftime('%Y-%m-%d %H:%M:%S')
            }, 'container': None, 'video': {'fps': 25, 'total_frames': 0},
               'audio': None, 'format': {'duration_sec': 0}, 'extra_streams': []}
            ext = info['file']['extension']
            containers = {
                '.mp4': 'MP4 (MPEG-4 Part 14)', '.mov': 'MOV (QuickTime)',
                '.avi': 'AVI (Audio Video Interleave)', '.mkv': 'MKV (Matroska)',
                '.webm': 'WebM', '.wmv': 'WMV (Windows Media Video)',
                '.flv': 'FLV (Flash Video)', '.ts': 'MPEG-TS',
                '.mpg': 'MPEG-PS', '.mxf': 'MXF',
                '.m4v': 'MPEG-4 Video', '.3gp': '3GPP'
            }
            info['container'] = {'type': containers.get(ext, ext.upper().replace('.', '') + ' Format')}
            data = run_ffprobe(fp)
            if not data:
                file_size_mb = info['file']['size_bytes'] / (1024 * 1024)
                total_frames = int(file_size_mb * 27)
                info['format'] = {
                    'duration': '00:00.000',
                    'duration_sec': total_frames / 25,
                    'bitrate': 'N/A', 'nb_streams': 1, 'format_name': 'N/A'
                }
                return info
            fmt = data.get('format', {})
            dur_sec = float(fmt.get('duration', 0))
            info['format'] = {
                'duration': fmt_dur(dur_sec),
                'duration_sec': dur_sec,
                'bitrate': fmt_bitrate(fmt.get('bit_rate')),
                'nb_streams': int(fmt.get('nb_streams', 0)),
                'format_name': fmt.get('format_long_name', fmt.get('format_name', 'N/A')),
            }
            for s in data.get('streams', []):
                if s.get('codec_type') == 'video':
                    fps = 25
                    for fk in ['r_frame_rate', 'avg_frame_rate']:
                        fs = s.get(fk, '0/1')
                        try:
                            if '/' in fs:
                                n, d = fs.split('/')
                                if float(d) > 0:
                                    f2 = float(n) / float(d)
                                    if 1 < f2 < 300:
                                        fps = f2
                                        break
                        except Exception:
                            pass
                    nb = int(s.get('nb_frames', 0))
                    if nb == 0 and dur_sec > 0 and fps > 0:
                        nb = int(dur_sec * fps)
                    info['video'] = {
                        'codec': s.get('codec_name', 'N/A'),
                        'codec_full': get_codec_full(s.get('codec_name'), s.get('profile')),
                        'resolution': f"{s.get('width', '?')}x{s.get('height', '?')}",
                        'width': s.get('width', '?'),
                        'height': s.get('height', '?'),
                        'fps': round(fps, 3),
                        'fps_display': f"{fps:.3f}".rstrip('0').rstrip('.'),
                        'total_frames': nb,
                        'bit_depth': s.get('bits_per_raw_sample', s.get('bits_per_sample', 'N/A')),
                        'pixel_format': s.get('pix_fmt', 'N/A'),
                        'color_space': s.get('color_space', 'N/A'),
                        'color_primaries': s.get('color_primaries', 'N/A'),
                        'color_transfer': s.get('color_transfer', 'N/A'),
                        'sar': s.get('sample_aspect_ratio', 'N/A'),
                        'dar': s.get('display_aspect_ratio', 'N/A'),
                        'scan_type': 'Progressive' if s.get('field_order', 'progressive') == 'progressive' else 'Interlaced',
                        'field_order': s.get('field_order', 'progressive'),
                        'bitrate': fmt_bitrate(s.get('bit_rate')),
                        'profile': s.get('profile', 'N/A'),
                        'level': s.get('level', 'N/A'),
                    }
                elif s.get('codec_type') == 'audio':
                    channels = int(s.get('channels', 0))
                    sample_rate = int(s.get('sample_rate', 0))
                    bit_rate = s.get('bit_rate', 0)
                    channel_layout = s.get('channel_layout', 'N/A')
                    if channel_layout == 'N/A' and channels > 0:
                        channel_layout = {1: 'mono', 2: 'stereo', 6: '5.1', 8: '7.1'}.get(channels, f'{channels}ch')
                    info['audio'] = {
                        'codec': s.get('codec_name', 'N/A'),
                        'codec_full': get_codec_full(s.get('codec_name'), s.get('profile')),
                        'sample_rate': sample_rate,
                        'sample_rate_display': f"{sample_rate/1000:.1f} kHz" if sample_rate > 0 else 'N/A',
                        'channels': channels,
                        'channel_name': CH_NAMES.get(channels, f'{channels} channels'),
                        'channel_layout': channel_layout,
                        'bitrate': fmt_bitrate(bit_rate),
                        'bit_depth': s.get('bits_per_sample', 'N/A'),
                        'profile': s.get('profile', 'N/A'),
                    }
            return info
        except Exception as e:
            print(f"FileInfoExtractor error: {e}")
            return {
                'file': {'name': os.path.basename(fp), 'path': fp},
                'video': {'fps': 25, 'total_frames': 27000},
                'format': {'duration_sec': 1080}
            }

