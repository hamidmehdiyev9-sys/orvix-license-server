"""Persist install_id + token for license server."""
from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any


def _path() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home())
        d = Path(base) / "Orvix"
    else:
        d = Path.home() / ".orvix"
    d.mkdir(parents=True, exist_ok=True)
    return d / "license_state.json"


def load_state() -> dict[str, Any]:
    p = _path()
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(data: dict[str, Any]) -> None:
    p = _path()
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_or_create_install_id() -> str:
    st = load_state()
    iid = (st.get("install_id") or "").strip()
    if len(iid) < 8:
        iid = uuid.uuid4().hex
        st["install_id"] = iid
        save_state(st)
    return iid


def update_token(server: str, token: str) -> None:
    st = load_state()
    st["install_id"] = st.get("install_id") or get_or_create_install_id()
    st["server"] = server.rstrip("/")
    st["token"] = token
    save_state(st)
