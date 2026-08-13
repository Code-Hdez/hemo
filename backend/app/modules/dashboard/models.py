from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.shared.dates import utc_now


class DashboardMetric(Base):
    __tablename__ = "dashboard_metrics"

    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    data: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, nullable=False
    )
