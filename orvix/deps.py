"""İstəyə bağlı kitabxanalar və mövcudluq bayraqları."""
import sys

try:
    import sounddevice as sd  # noqa: F401
    _HAS_SD = True
except ImportError:
    _HAS_SD = False

try:
    from PIL import Image, ImageTk  # noqa: F401
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("WARNING: Pillow not found. pip install Pillow")

try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError as e:
    OPENCV_AVAILABLE = False
    print(f"OpenCV not found: {e}")
    sys.exit(1)

try:
    from scipy import signal  # noqa: F401
    from scipy.fft import fft, fftfreq
    SCIPY_AVAILABLE = True
except Exception:
    SCIPY_AVAILABLE = False
