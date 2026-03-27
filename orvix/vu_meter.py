"""VU meter — LED seqment üslubu + oxunaqlı alt dB şkalası."""
import math
import threading
import tkinter as tk

import numpy as np


def _blend(c0: tuple, c1: tuple, t: float) -> str:
    t = max(0.0, min(1.0, t))
    r = int(c0[0] + (c1[0] - c0[0]) * t)
    g = int(c0[1] + (c1[1] - c0[1]) * t)
    b = int(c0[2] + (c1[2] - c0[2]) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


class VerticalVUMeter(tk.Canvas):
    """
    İki kanal: LED seqmentlər + pik işarəsi + dB oxu.
    Alt şkala: panel eninə görə avtomatik seyrək/sıx nöqtələr, kənarlar kəsilmir.
    """

    DECAY = 0.05
    PEAK_HOLD = 36
    # Tam en üçün tam dəst; dar paneldə _ticks_for_width istifadə olunur
    DB_TICKS_FULL = (0, -6, -12, -18, -24, -36, -48, -60)

    def __init__(self, parent, channels=2, **kw):
        kw.setdefault("bg", "#0a0e14")
        kw.setdefault("highlightthickness", 0)
        super().__init__(parent, **kw)
        self._channels = max(1, min(8, channels))
        self._rms = np.zeros(8, dtype=np.float32)
        self._peak = np.zeros(8, dtype=np.float32)
        self._hold = np.zeros(8, dtype=np.float32)
        self._hold_cnt = np.zeros(8, dtype=np.int32)
        self._lock = threading.Lock()
        self._after_id = None
        self._decay_loop()

    def set_channels(self, n):
        with self._lock:
            self._channels = max(1, min(8, n))

    def set_levels(self, rms_arr, peak_arr):
        with self._lock:
            n = min(len(rms_arr), self._channels, 8)
            for i in range(n):
                r = float(rms_arr[i])
                p = float(peak_arr[i])
                if r > self._rms[i]:
                    self._rms[i] = r
                if p > self._peak[i]:
                    self._peak[i] = p
                if p > self._hold[i]:
                    self._hold[i] = p
                    self._hold_cnt[i] = self.PEAK_HOLD

    def _rms_to_db(self, rms: float) -> float:
        if rms <= 0:
            return -96.0
        return max(-96.0, min(0.0, 20.0 * math.log10(float(rms) + 1e-15)))

    def _db_to_frac(self, db: float) -> float:
        return max(0.0, min(1.0, (float(db) + 60.0) / 60.0))

    def _format_db_main(self, db: float) -> str:
        if db <= -90:
            return "−∞"
        return f"{db:.1f}"

    def _heat_at_frac(self, frac: float) -> str:
        frac = max(0.0, min(1.0, frac))
        c0 = (30, 58, 88)
        c1 = (14, 165, 233)
        c2 = (251, 191, 36)
        c3 = (248, 113, 113)
        if frac < 0.5:
            return _blend(c0, c1, frac / 0.5)
        if frac < 0.82:
            return _blend(c1, c2, (frac - 0.5) / 0.32)
        return _blend(c2, c3, (frac - 0.82) / 0.18)

    def _ticks_for_width(self, meter_w: float) -> tuple:
        """Dar paneldə etiketlər üst-üstə düşməsin — daha az nöqtə."""
        if meter_w < 200:
            return (0, -20, -40, -60)
        if meter_w < 280:
            return (0, -12, -24, -36, -48, -60)
        if meter_w < 360:
            return (0, -9, -18, -27, -36, -45, -60)
        return self.DB_TICKS_FULL

    def _decay_loop(self):
        with self._lock:
            for i in range(self._channels):
                self._rms[i] = max(0.0, self._rms[i] - self.DECAY)
                self._peak[i] = max(0.0, self._peak[i] - self.DECAY * 0.5)
                if self._hold_cnt[i] > 0:
                    self._hold_cnt[i] -= 1
                else:
                    self._hold[i] = max(0.0, self._hold[i] - self.DECAY * 0.22)
        self._redraw()
        self._after_id = self.after(14, self._decay_loop)

    def _draw_scale(
        self,
        W: int,
        H: int,
        track_x1: int,
        track_x2: int,
        meter_area_w: int,
        scale_top: int,
    ):
        db_ticks = self._ticks_for_width(float(meter_area_w))
        scale_y0 = scale_top
        # Üst üfüqi xətt (şkala bazası)
        self.create_line(
            track_x1, scale_y0, track_x2, scale_y0,
            fill="#334155",
            width=1,
        )
        label_y = scale_y0 + 5
        font_main = ("Segoe UI", 8, "bold")
        font_small = ("Segoe UI", 7)

        for db in db_ticks:
            frac = self._db_to_frac(db)
            tx = track_x1 + int(frac * meter_area_w)
            major = db in (0, -12, -24, -36) or db == 0
            tick_h = 6 if (db == 0 or db == -60 or abs(db) % 12 == 0) else 4
            col = "#fbbf24" if db == 0 else ("#94a3b8" if major else "#64748b")
            self.create_line(
                tx, scale_y0, tx, scale_y0 - tick_h,
                fill=col,
                width=2 if db == 0 else 1,
            )
            if db <= -60:
                lab = "−60"
            elif db == 0:
                lab = "0"
            else:
                lab = str(db)
            # Kənar etiketləri kəsilməsin
            if frac <= 0.04:
                ax, an = tx + 2, "nw"
            elif frac >= 0.96:
                ax, an = tx - 2, "ne"
            else:
                ax, an = tx, "n"
            self.create_text(
                ax,
                label_y,
                text=lab,
                fill="#e2e8f0" if db == 0 else "#94a3b8",
                font=font_main if db == 0 or abs(db) % 12 == 0 else font_small,
                anchor=an,
            )

    def _redraw(self):
        try:
            self.delete("all")
            W = self.winfo_width() or 420
            H = self.winfo_height() or 80
            if W < 40 or H < 28:
                return

            with self._lock:
                n = min(self._channels, 2)
                rms = self._rms[:n].copy()
                hold = self._hold[:n].copy()

            lbl_w = 20
            readout_w = 52
            bottom_scale = 26
            pad = 5
            meter_area_w = W - lbl_w - readout_w - pad - 6
            meter_area_h = H - bottom_scale - 8
            if meter_area_w < 28 or n == 0:
                return

            ch_gap = 5
            ch_h = max(12, (meter_area_h - ch_gap * (n - 1)) // n)
            scale_top = H - bottom_scale + 2
            track_x1 = lbl_w + pad
            track_x2 = track_x1 + int(meter_area_w)

            # Fon panel
            self.create_rectangle(
                1, 1, W - 2, H - 2,
                fill="#0c111c",
                outline="#1e293b",
                width=1,
            )

            for i in range(n):
                cy = 4 + i * (ch_h + ch_gap)
                ch_name = ["L", "R"][i] if i < 2 else str(i + 1)
                self.create_text(
                    lbl_w - 1,
                    cy + ch_h // 2,
                    text=ch_name,
                    fill="#38bdf8" if i == 0 else "#7dd3fc",
                    font=("Segoe UI", 9, "bold"),
                    anchor="e",
                )

                rms_db = self._rms_to_db(rms[i])
                hold_db = self._rms_to_db(hold[i])
                rms_frac = self._db_to_frac(rms_db)
                hold_frac = self._db_to_frac(hold_db)

                track_y1 = cy + 1
                track_y2 = cy + ch_h - 1
                tw = track_x2 - track_x1
                if tw < 8:
                    continue

                # Arxa iz (LED çuxuru)
                self.create_rectangle(
                    track_x1, track_y1, track_x2, track_y2,
                    fill="#020617",
                    outline="#1e293b",
                    width=1,
                )

                # LED seqmentlər
                gap = 2
                seg_w = max(3, (tw - gap) // max(12, tw // 7))
                num = max(8, min(48, (tw + gap) // (seg_w + gap)))
                seg_w = max(2, (tw - (num - 1) * gap) // num)
                total_w = num * seg_w + (num - 1) * gap
                ox = track_x1 + (tw - total_w) // 2

                lit = rms_frac * num

                for si in range(num):
                    x0 = ox + si * (seg_w + gap)
                    y1, y2 = track_y1 + 3, track_y2 - 3
                    pos = (si + 0.5) / num
                    seg_on = (si + 1) <= lit + 1e-9
                    if seg_on and rms_frac > 1e-6:
                        col = self._heat_at_frac(pos)
                        outline = "#0f172a"
                    else:
                        col = "#151f2e"
                        outline = "#0f172a"
                    self.create_rectangle(
                        x0, y1, x0 + seg_w, y2,
                        fill=col,
                        outline=outline,
                        width=1,
                    )

                # Pik: incə qızılı xətt seqment üstündə
                if hold_frac > 0.02 and num > 0:
                    ps = min(num - 1, max(0, int(hold_frac * num + 0.5)))
                    px = ox + ps * (seg_w + gap) + seg_w // 2
                    self.create_line(
                        px - 1, track_y1 - 1, px + 1, track_y1 - 1,
                        fill="#fcd34d",
                        width=3,
                    )

                main_txt = self._format_db_main(rms_db)
                db_line = f"{main_txt} dB" if rms_db > -90 else "−∞"
                rx = track_x2 + 5
                self.create_text(
                    rx,
                    cy + ch_h // 2,
                    text=db_line,
                    fill="#f1f5f9",
                    font=("Consolas", 10, "bold"),
                    anchor="w",
                )

            self._draw_scale(W, H, track_x1, track_x2, meter_area_w, scale_top)

        except Exception:
            pass

    def destroy(self):
        if self._after_id:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
        super().destroy()
