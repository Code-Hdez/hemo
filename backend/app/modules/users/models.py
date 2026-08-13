from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.shared.dates import utc_now


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'admin')", name="ck_users_role"),
        CheckConstraint(
            "onboarding_tour_status IN ('pending', 'completed', 'skipped')",
            name="ck_users_onboarding_tour_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(
        String(254), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(Text, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    role: Mapped[str] = mapped_column(
        String(20), default="user", server_default="user", nullable=False
    )
    onboarding_tour_status: Mapped[str] = mapped_column(
        String(20), default="pending", server_default="pending", nullable=False
    )
    onboarding_tour_version: Mapped[str | None] = mapped_column(String(80))
    onboarding_tour_dismissed_at: Mapped[datetime | None] = mapped_column(DateTime)
