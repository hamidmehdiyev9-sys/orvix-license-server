from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.db import init_db
from app.routers import admin_web, public_api

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Orvix License API", version="1.0.0")

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings["cors_origins"] == "*" else settings["cors_origins"].split(","),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SessionMiddleware, secret_key=settings["jwt_secret"], max_age=14 * 24 * 3600)

app.include_router(public_api.router)
app.include_router(admin_web.router)


@app.on_event("startup")
def _startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}
