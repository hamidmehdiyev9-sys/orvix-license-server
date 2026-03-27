import hashlib

from app.config import get_settings


def hash_license_key(plain: str) -> str:
    pepper = get_settings()["jwt_secret"]
    h = hashlib.sha256((pepper + ":" + plain.strip().upper()).encode("utf-8"))
    return h.hexdigest()
