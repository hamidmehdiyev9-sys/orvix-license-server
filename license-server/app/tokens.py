from datetime import datetime, timedelta, timezone

import jwt

from app.config import get_settings


def issue_token(device_id: str, mode: str, valid_until: datetime | None) -> str:
    """mode: 'trial' | 'license'"""
    secret = get_settings()["jwt_secret"]
    now = datetime.now(timezone.utc)
    exp = valid_until or (now + timedelta(days=3650))
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    payload = {
        "sub": device_id,
        "mode": mode,
        "exp": exp,
        "iat": now,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, get_settings()["jwt_secret"], algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
