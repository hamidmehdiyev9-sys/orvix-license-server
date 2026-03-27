"""Sistem SSL / Windows uyğunluğu."""
import ssl
import sys


def fix_windows_compatibility():
    try:
        if sys.platform == "win32":
            try:
                ssl._create_default_https_context = ssl._create_unverified_context
            except Exception:
                pass
    except Exception:
        pass
