import secrets
from datetime import datetime, timezone

from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import get_settings
from app.crypto_keys import hash_license_key
from app.db import get_db
from app.models import Device, LicenseKey

_TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory=str(_TEMPLATES))


@router.get("/login", response_class=HTMLResponse)
def admin_login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login")
def admin_login(
    request: Request,
    password: str = Form(...),
):
    if password != get_settings()["admin_password"]:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Wrong password"},
            status_code=401,
        )
    request.session["admin"] = True
    return RedirectResponse("/admin/", status_code=303)


@router.get("/logout")
def admin_logout(request: Request):
    request.session.clear()
    return RedirectResponse("/admin/login", status_code=303)


def require_admin(request: Request):
    if not request.session.get("admin"):
        return RedirectResponse("/admin/login", status_code=302)
    return None


@router.get("/", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    redir = require_admin(request)
    if redir:
        return redir
    n_keys = db.query(LicenseKey).count()
    n_dev = db.query(Device).count()
    active_trials = db.query(Device).filter(Device.trial_ends_at.isnot(None)).count()
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "n_keys": n_keys, "n_dev": n_dev, "active_trials": active_trials},
    )


@router.get("/keys", response_class=HTMLResponse)
def admin_keys(request: Request, db: Session = Depends(get_db)):
    redir = require_admin(request)
    if redir:
        return redir
    keys = db.query(LicenseKey).order_by(LicenseKey.created_at.desc()).all()
    return templates.TemplateResponse("keys.html", {"request": request, "keys": keys})


@router.post("/keys/create")
def admin_keys_create(
    request: Request,
    label: str = Form(""),
    max_activations: str = Form("1"),
    valid_until: str = Form(""),
    db: Session = Depends(get_db),
):
    redir = require_admin(request)
    if redir:
        return redir
    plain = f"ORVIX-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}"
    h = hash_license_key(plain)
    vu = None
    if valid_until.strip():
        try:
            vu = datetime.fromisoformat(valid_until.replace("Z", "+00:00"))
            if vu.tzinfo is None:
                vu = vu.replace(tzinfo=timezone.utc)
        except ValueError:
            vu = None
    try:
        ma = max(1, int(max_activations))
    except ValueError:
        ma = 1
    lk = LicenseKey(
        key_hash=h,
        label=label or plain[:20],
        max_activations=ma,
        valid_until=vu,
    )
    db.add(lk)
    db.commit()
    return templates.TemplateResponse(
        "key_created.html",
        {"request": request, "plain_key": plain, "label": lk.label},
    )


@router.post("/keys/{key_id}/revoke")
def admin_keys_revoke(key_id: str, request: Request, db: Session = Depends(get_db)):
    redir = require_admin(request)
    if redir:
        return redir
    lk = db.query(LicenseKey).filter(LicenseKey.id == key_id).first()
    if lk:
        lk.revoked = True
        db.commit()
    return RedirectResponse("/admin/keys", status_code=303)


@router.get("/devices", response_class=HTMLResponse)
def admin_devices(request: Request, db: Session = Depends(get_db)):
    redir = require_admin(request)
    if redir:
        return redir
    devices = db.query(Device).order_by(Device.created_at.desc()).limit(500).all()
    return templates.TemplateResponse("devices.html", {"request": request, "devices": devices})
