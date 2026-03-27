"""HTTP client for Orvix license server (stdlib only)."""
from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from typing import Any


def _post(base: str, path: str, body: dict[str, Any], timeout: float = 30.0) -> dict[str, Any]:
    url = base.rstrip("/") + path
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8")
            err = json.loads(detail)
            msg = err.get("detail", detail)
            if isinstance(msg, list):
                msg = "; ".join(
                    str(x.get("msg", x)) if isinstance(x, dict) else str(x) for x in msg
                )
        except Exception:
            msg = str(e)
        raise RuntimeError(msg) from e


def api_device_register(base: str, install_id: str) -> dict[str, Any]:
    return _post(base, "/api/v1/device/register", {"install_id": install_id})


def api_trial_start(base: str, install_id: str) -> dict[str, Any]:
    return _post(base, "/api/v1/trial/start", {"install_id": install_id})


def api_license_activate(base: str, install_id: str, license_key: str) -> dict[str, Any]:
    return _post(base, "/api/v1/license/activate", {"install_id": install_id, "license_key": license_key.strip()})


def api_session_ping(base: str, install_id: str, token: str) -> dict[str, Any]:
    return _post(base, "/api/v1/session/ping", {"install_id": install_id, "token": token})
