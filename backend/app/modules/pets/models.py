from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.shared.dates import utc_now


class Pet(Base):
    __tablename__ = "pets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    breed: Mapped[str | None] = mapped_column(String(150))
    birth_year: Mapped[int | None] = mapped_column(SmallInteger)
    sex: Mapped[str | None] = mapped_column(String(20))
    weight_kg: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)
    residence_zone_code: Mapped[str | None] = mapped_column(String(80), index=True)
    residence_label: Mapped[str | None] = mapped_column(String(200))
    residence_lat: Mapped[float | None] = mapped_column(Float)
    residence_lng: Mapped[float | None] = mapped_column(Float)
    residence_precision: Mapped[str | None] = mapped_column(String(40))
    residence_consent_at: Mapped[datetime | None] = mapped_column(DateTime)
    profile_photo_key: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, nullable=False
    )


class Breed(Base):
    __tablename__ = "breeds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
