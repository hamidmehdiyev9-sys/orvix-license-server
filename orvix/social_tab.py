"""
Social Network Converter — platform seçimi və hər şəbəkə üçün convert parametrləri (böyük iş pəncərəsi).
"""
import tkinter as tk

PLATFORM_ORDER = [
    "Instagram",
    "Facebook",
    "TikTok",
    "Telegram",
    "WhatsApp",
    "YouTube",
    "Snapchat",
    "Twitter / X",
    "LinkedIn",
    "Pinterest",
    "VKontakte (VK)",
    "Reddit",
    "Triller",
    "Messenger",
]

SOCIAL_PLATFORMS = {
    "Instagram": {
        "res": "1080x1080",
        "vc": "libx264",
        "vb": "6.5M",
        "ac": "aac",
        "ab": "128k",
        "fps": "30",
        "fmt": "mp4",
    },
    "Facebook": {
        "res": "1920x1080",
        "vc": "libx264",
        "vb": "4M",
        "ac": "aac",
        "ab": "192k",
        "fps": "30",
        "fmt": "mp4",
    },
    "TikTok": {
        "res": "1080x1920",
        "vc": "libx264",
        "vb": "5M",
        "ac": "aac",
        "ab": "128k",
        "fps": "30",
        "fmt": "mp4",
    },
    "Telegram": {
        "res": "1280x720",
        "vc": "libx264",
        "vb": "2.5M",
        "ac": "aac",
        "ab": "128k",
        "fps": "30",
        "fmt": "mp4",
    },
    "WhatsApp": {
        "res": "1080x1920",
        "vc": "libx264",
        "vb": "3M",
        "ac": "aac",
        "ab": "128k",
        "fps": "30",
        "fmt": "mp4",
    },
    "YouTube": {
        "res": "1920x1080",
        "vc": "libx264",
        "vb": "8M",
        "ac": "aac",
        "ab": "192k",
        "fps": "30",
        "fmt": "mp4",
    },
    "Snapchat": {
        "res": "1080x1920",
        "vc": "libx264",
        "vb": "5M",
        "ac": "aac",
        "ab": "128k",
        "fps": "30",
        "fmt": "mp4",
    },
    "Twitter / X": {
        "res": "1280x720",
        "vc": "libx264",
        "vb": "2M",
        "ac": "aac",
        "ab": "128k",
        "fps": "30",
        "fmt": "mp4",
    },
    "LinkedIn": {
        "res": "1920x1080",
        "vc": "libx264",
        "vb": "3.5M",
        "ac": "aac",
        "ab": "128k",
        "fps": "30",
        "fmt": "mp4",
    },
    "Pinterest": {
        "res": "1000x1500",
        "vc": "libx264",
        "vb": "3M",
        "ac": "aac",
        "ab": "128k",
        "fps": "30",
        "fmt": "mp4",
    },
    "VKontakte (VK)": {
        "res": "1280x720",
        "vc": "libx264",
        "vb": "2.5M",
        "ac": "aac",
        "ab": "128k",
        "fps": "30",
        "fmt": "mp4",
    },
    "Reddit": {
        "res": "1280x720",
        "vc": "libx264",
        "vb": "2M",
        "ac": "aac",
        "ab": "128k",
        "fps": "30",
        "fmt": "mp4",
    },
    "Triller": {
        "res": "1080x1920",
        "vc": "libx264",
        "vb": "5M",
        "ac": "aac",
        "ab": "128k",
        "fps": "30",
        "fmt": "mp4",
    },
    "Messenger": {
        "res": "1280x720",
        "vc": "libx264",
        "vb": "2M",
        "ac": "aac",
        "ab": "128k",
        "fps": "30",
        "fmt": "mp4",
    },
}


def install_social_platform_notebook(app, parent, *, bg, bg3, fg, fg2, accent):
    """
    Köhnə API uyğunluğu: notebook əvəzinə platform seçici + böyük iş pəncərəsi düyməsi.
    """
    install_social_platform_selector(app, parent, bg=bg, bg3=bg3, fg=fg, fg2=fg2, accent=accent)


def install_social_platform_selector(app, parent, *, bg, bg3, fg, fg2, accent):
    from orvix.social_workspace import open_social_workspace

    app._sn_platforms = dict(SOCIAL_PLATFORMS)
    app._sn_platform_order = list(PLATFORM_ORDER)
    app.sn_platform_var = tk.StringVar(value=app._sn_platform_order[0])
    app._sn_platform_tab_frames = {}

    wrap = tk.Frame(parent, bg=bg3, padx=10, pady=10, highlightthickness=1, highlightbackground="#4c3d6b")
    wrap.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

    tk.Label(
        wrap,
        text="Pick a platform — opens that platform's Video Convert workspace",
        bg=bg3,
        fg=accent,
        font=("Segoe UI", 11, "bold"),
    ).pack(anchor="w")
    tk.Label(
        wrap,
        text="Each platform has its own settings; MP4 export only (starting with Instagram).",
        bg=bg3,
        fg=fg2,
        font=("Segoe UI", 9),
        wraplength=720,
        justify=tk.LEFT,
    ).pack(anchor="w", pady=(4, 8))

    grid = tk.Frame(wrap, bg=bg3)
    grid.pack(fill=tk.BOTH, expand=True)
    cols = 4
    for i, name in enumerate(app._sn_platform_order):
        r, c = divmod(i, cols)
        tk.Button(
            grid,
            text=name,
            font=("Segoe UI", 9),
            bg="#5b21b6",
            fg="#faf5ff",
            activebackground="#6d28d9",
            activeforeground="#fff",
            relief=tk.FLAT,
            padx=6,
            pady=10,
            cursor="hand2",
            command=lambda n=name: open_social_workspace(app, n),
        ).grid(row=r, column=c, padx=4, pady=4, sticky="nsew")
    for c in range(cols):
        grid.columnconfigure(c, weight=1)


def platform_frame(app, name: str):
    """Köhnə kod uyğunluğu — boş qaytarır (notebook ləğv olunub)."""
    return getattr(app, "_sn_platform_tab_frames", {}).get(name)
