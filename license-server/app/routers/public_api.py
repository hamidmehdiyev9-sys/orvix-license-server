from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import get_settings
from app.crypto_keys import hash_license_key
from app.db import get_db
from app.models import Device, LicenseKey
from app.tokens import decode_token, issue_token

router = APIRouter(prefix="/api/v1", tags=["public"])


class InstallBody(BaseModel):
    install_id: str = Field(..., min_length=8, max_length=128)


class TrialBody(InstallBody):
    pass


class ActivateBody(InstallBody):
    license_key: str = Field(..., min_length=4, max_length=256)


class PingBody(BaseModel):
    install_id: str
    token: str


def _now():
    return datetime.now(timezone.utc)


@router.post("/device/register")
def device_register(body: InstallBody, db: Session = Depends(get_db)):
    d = db.query(Device).filter(Device.install_id == body.install_id).first()
    if not d:
        d = Device(install_id=body.install_id)
        db.add(d)
        db.commit()
        db.refresh(d)
    return {"ok": True, "device_id": d.id, "install_id": d.install_id}


@router.post("/trial/start")
def trial_start(body: TrialBody, db: Session = Depends(get_db)):
    settings = get_settings()
    d = db.query(Device).filter(Device.install_id == body.install_id).first()
    if not d:
        d = Device(install_id=body.install_id)
        db.add(d)
        db.commit()
        db.refresh(d)

    if d.trial_consumed:
        raise HTTPException(400, "Trial already used on this device")

    now = _now()
    ends = now + timedelta(days=settings["trial_days"])
    d.trial_started_at = now
    d.trial_ends_at = ends
    d.trial_consumed = True
    d.last_ping_at = now
    db.commit()

    token = issue_token(d.id, "trial", ends)
    return {
        "ok": True,
        "token": token,
        "trial_ends_at": ends.isoformat(),
        "mode": "trial",
    }


@router.post("/license/activate")
def license_activate(body: ActivateBody, db: Session = Depends(get_db)):
    h = hash_license_key(body.license_key)
    lk = db.query(LicenseKey).filter(LicenseKey.key_hash == h).first()
    if not lk or lk.revoked:
        raise HTTPException(400, "Invalid or revoked license key")

    now = _now()
    if lk.valid_until and lk.valid_until <= now:
        raise HTTPException(400, "License expired")

    d = db.query(Device).filter(Device.install_id == body.install_id).first()
    if not d:
        d = Device(install_id=body.install_id)
        db.add(d)
        db.commit()
        db.refresh(d)

    if d.license_key_id != lk.id:
        if lk.activation_count >= lk.max_activations:
            raise HTTPException(400, "Activation limit reached")
        lk.activation_count += 1

    d.license_key_id = lk.id
    d.last_ping_at = now
    db.commit()

    valid_until = lk.valid_until
    token = issue_token(d.id, "license", valid_until)
    return {
        "ok": True,
        "token": token,
        "license_valid_until": lk.valid_until.isoformat() if lk.valid_until else None,
        "mode": "license",
    }


@router.post("/session/ping")
def session_ping(body: PingBody, db: Session = Depends(get_db)):
    payload = decode_token(body.token)
    if not payload or payload.get("sub") is None:
        raise HTTPException(401, "Invalid token")

    device_id = payload["sub"]
    d = db.query(Device).filter(Device.id == device_id, Device.install_id == body.install_id).first()
    if not d:
        raise HTTPException(401, "Device mismatch")

    now = _now()
    mode = payload.get("mode", "trial")

    if mode == "trial":
        if not d.trial_ends_at or now > d.trial_ends_at:
            raise HTTPException(403, "Trial expired")
        valid_until = d.trial_ends_at
    else:
        if not d.license_key_id:
            raise HTTPException(403, "No license")
        lk = db.query(LicenseKey).filter(LicenseKey.id == d.license_key_id).first()
        if not lk or lk.revoked:
            raise HTTPException(403, "License revoked")
        valid_until = lk.valid_until
        if valid_until and now > valid_until:
            raise HTTPException(403, "License expired")

    d.last_ping_at = now
    db.commit()

    new_token = issue_token(d.id, mode, valid_until)
    return {
        "ok": True,
        "valid": True,
        "token": new_token,
        "mode": mode,
        "valid_until": valid_until.isoformat() if valid_until else None,
    }
