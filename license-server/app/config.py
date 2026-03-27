import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


@lru_cache
def get_settings():
    return {
        "database_url": os.environ.get(
            "DATABASE_URL",
            "sqlite:///./orvix_license.db",
        ),
        "jwt_secret": os.environ.get("JWT_SECRET", "change-me-in-production-min-32-chars!!"),
        "admin_password": os.environ.get("ADMIN_PASSWORD", "admin"),
        "trial_days": int(os.environ.get("TRIAL_DAYS", "7")),
        "cors_origins": os.environ.get("CORS_ORIGINS", "*"),
    }


def fix_sqlite_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url
