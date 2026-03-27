import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _uuid():
    return str(uuid.uuid4())


class LicenseKey(Base):
    __tablename__ = "license_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    key_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    label: Mapped[str] = mapped_column(String(256), default="")
    # If set, license cannot be used after this instant (subscription end)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    max_activations: Mapped[int] = mapped_column(Integer, default=1)
    activation_count: Mapped[int] = mapped_column(Integer, default=0)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    install_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    license_key_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("license_keys.id"), nullable=True)
    trial_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_consumed: Mapped[bool] = mapped_column(Boolean, default=False)
    last_ping_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    label: Mapped[str] = mapped_column(String(256), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    license_key = relationship("LicenseKey", backref="devices")
