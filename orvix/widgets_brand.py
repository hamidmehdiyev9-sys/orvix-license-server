"""Logo və slogan animasiyası."""
import math
import tkinter as tk

class AnimatedLogo(tk.Canvas):
    def __init__(self, parent, width=280, height=72, **kw):
        bg = kw.pop('bg', '#08101c')
        kw.setdefault('highlightthickness', 0)
        super().__init__(parent, width=width, height=height, bg=bg, **kw)
        self.w = width
        self.h = height
        self._t = 0.0
        self._items = {}
        self._build_static()
        self._animate()

    def _clamp(self, v):
        return max(0, min(255, int(v)))

    def _hex_i(self, r, g, b):
        return f'#{self._clamp(r):02x}{self._clamp(g):02x}{self._clamp(b):02x}'

    def _build_static(self):
        w, h = self.w, self.h
        cx, cy = 38, h // 2
        self._items['bg_circle'] = self.create_oval(cx - 30, cy - 30, cx + 30, cy + 30, fill='#060e1e', outline='#0a1e30', width=1)
        self._items['ring_outer'] = self.create_oval(cx - 28, cy - 28, cx + 28, cy + 28, outline='#0060c0', width=2, fill='')
        self._items['ring_inner'] = self.create_oval(cx - 18, cy - 18, cx + 18, cy + 18, outline='#003060', width=1, fill='')
        bar_heights = [8, 14, 20, 14, 8]
        bar_x_start = cx - 14
        self._items['bars'] = []
        for i, bh in enumerate(bar_heights):
            bx = bar_x_start + i * 7
            bar = self.create_rectangle(bx - 2, cy - bh // 2, bx + 2, cy + bh // 2, fill='#0080c0', outline='')
            self._items['bars'].append(bar)
        self._items['arc_top'] = self.create_arc(cx - 32, cy - 32, cx + 32, cy + 32, start=40, extent=100, outline='#00a8ff', width=2, style='arc')
        self._items['arc_bot'] = self.create_arc(cx - 32, cy - 32, cx + 32, cy + 32, start=220, extent=100, outline='#003870', width=1, style='arc')
        self._items['orb'] = self.create_oval(cx + 26, cy - 3, cx + 32, cy + 3, fill='#00aaff', outline='')
        tx = 86
        self._items['txt_orvix'] = self.create_text(tx, cy - 14, text="ORVIX", fill='#cce8ff', font=('Segoe UI', 21, 'bold'), anchor='w')
        self._items['txt_pro_bg'] = self.create_rectangle(tx + 118, cy - 26, tx + 162, cy - 8, fill='#0060c0', outline='')
        self._items['txt_pro'] = self.create_text(tx + 140, cy - 17, text="Lite", fill='#ffffff', font=('Segoe UI', 9, 'bold'), anchor='center')
        self._items['txt_ver'] = self.create_text(tx + 168, cy - 17, text="v24", fill='#446699', font=('Segoe UI', 9, 'bold'), anchor='w')
        self._items['divider'] = self.create_line(tx, cy - 1, tx + 200, cy - 1, fill='#0d2030', width=1)
        self._items['slogan'] = self.create_text(tx, cy + 11, text="Video QC | Frame sync | VU meter", fill='#1a3344', font=('Segoe UI', 10), anchor='w')

    def _animate(self):
        self._t += 0.03
        t = self._t
        cx, cy = 38, self.h // 2
        pulse = 0.5 + 0.5 * math.sin(t * 1.5)
        ring_r = int(20 + 50 * pulse)
        ring_g = int(80 + 80 * pulse)
        ring_b = int(150 + 80 * pulse)
        self.itemconfig(self._items['ring_outer'], outline=self._hex_i(ring_r, ring_g, ring_b), width=1 + int(pulse * 2))
        bar_phases = [0, 0.8, 1.6, 2.4, 3.2]
        bar_max_h = [8, 15, 22, 15, 8]
        bar_x_start = cx - 14
        for i, (bar, phase, max_h) in enumerate(zip(self._items['bars'], bar_phases, bar_max_h)):
            bh = int(max_h * (0.35 + 0.65 * abs(math.sin(t * 2.5 + phase))))
            bh = max(3, bh)
            bx = bar_x_start + i * 7
            brightness = 0.3 + 0.7 * abs(math.sin(t * 2.5 + phase))
            r = int(0 * brightness)
            g = int(140 * brightness)
            b = int(210 * brightness)
            self.coords(bar, bx - 2, cy - bh // 2, bx + 2, cy + bh // 2)
            self.itemconfig(bar, fill=self._hex_i(r, g, b))
        angle = t * 50 % 360
        rad = math.radians(angle)
        orb_r = 30
        dx = cx + orb_r * math.cos(rad)
        dy = cy + orb_r * math.sin(rad)
        dot_sz = 3 + int(pulse)
        self.coords(self._items['orb'], dx - dot_sz, dy - dot_sz, dx + dot_sz, dy + dot_sz)
        orb_b = int(180 + 75 * pulse)
        self.itemconfig(self._items['orb'], fill=self._hex_i(0, ring_g, orb_b))
        arc_angle = (t * 30) % 360
        self.itemconfig(self._items['arc_top'], start=arc_angle + 40)
        self.itemconfig(self._items['arc_bot'], start=arc_angle + 220)
        tv = 0.85 + 0.15 * math.sin(t * 1.2 + 0.5)
        r_t = int(180 * tv + 30)
        g_t = int(205 * tv + 20)
        b_t = 255
        self.itemconfig(self._items['txt_orvix'], fill=self._hex_i(r_t, g_t, b_t))
        self.after(33, self._animate)



class AnimatedSlogan(tk.Canvas):
    """
    Animated slogan: 'See the Unseen — Every Frame Holds a Truth.'
    Color-cycling marquee with a soft glow pulse.
    """
    SLOGAN = "See the Unseen \u2014 Every Frame Holds a Truth."

    def __init__(self, parent, width=520, height=22, **kw):
        kw.setdefault('bg', '#080f1c')
        kw.setdefault('highlightthickness', 0)
        super().__init__(parent, width=width, height=height, **kw)
        self._t = 0.0
        self._txt_id = self.create_text(
            width // 2, height // 2,
            text=self.SLOGAN,
            fill='#0a3060',
            font=('Segoe UI', 11, 'italic'),
            anchor='center'
        )
        self._after_id = None
        self._animate()

    def _clamp(self, v):
        return max(0, min(255, int(v)))

    def _hex_i(self, r, g, b):
        return f'#{self._clamp(r):02x}{self._clamp(g):02x}{self._clamp(b):02x}'

    def _animate(self):
        self._t += 0.018
        t = self._t
        # Slow cycle through teal/blue/violet hues
        phase = t % (2 * math.pi)
        r = int(30 + 60 * abs(math.sin(phase * 0.4)))
        g = int(100 + 80 * abs(math.sin(phase * 0.6 + 1.0)))
        b = int(180 + 60 * abs(math.sin(phase * 0.5 + 2.0)))
        self.itemconfig(self._txt_id, fill=self._hex_i(r, g, b))
        self._after_id = self.after(40, self._animate)

    def destroy(self):
        if self._after_id:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
        super().destroy()
