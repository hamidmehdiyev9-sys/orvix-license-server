"""
Compatibility entry for hosts that expect `server.py` (e.g. older Render / GitHub setups).

The real FastAPI app lives in `app.main:app`. Use either:

  uvicorn server:app --host 0.0.0.0 --port $PORT

or (equivalent):

  uvicorn app.main:app --host 0.0.0.0 --port $PORT
"""
import os

from app.main import app

__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
