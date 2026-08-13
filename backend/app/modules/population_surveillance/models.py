from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.shared.dates import utc_now


class EpidemiologyEvent(Base):
    __tablename__ = "epidemiology_events"
    __table_args__ = (
        UniqueConstraint(
            "analysis_id",
            "zone_code",
            "finding",
            name="uq_epidemiology_analysis_zone_finding",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    analysis_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("analyses.id", ondelete="CASCADE"), index=True
    )
    pet_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("pets.id", ondelete="SET NULL"), index=True
    )
    zone_code: Mapped[str] = mapped_column(String(80), index=True)
    zone_label: Mapped[str] = mapped_column(String(200))
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    finding: Mapped[str] = mapped_column(String(160), index=True)
    severity: Mapped[str] = mapped_column(String(20))
    occurred_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
