from __future__ import annotations

from datetime import datetime

from decimal import Decimal

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.shared.dates import utc_now


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    data: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, nullable=False
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    pet_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("pets.id", ondelete="SET NULL"), index=True
    )
    performed_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    laboratory: Mapped[str | None] = mapped_column(String(200))
    extraction_confidence: Mapped[float | None] = mapped_column(Float)
    data_origin: Mapped[str] = mapped_column(String(60), default="unknown")


class AnalysisParameter(Base):
    """Normalized, provenance-aware clinical value used by conversational context.

    The original analysis JSON remains an audit envelope, while these rows make
    numerical comparisons and provenance checks explicit and testable.
    """

    __tablename__ = "analysis_parameters"
    __table_args__ = (
        UniqueConstraint("analysis_id", "ordinal", name="uq_analysis_parameter_ordinal"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    analysis_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("analyses.id", ondelete="CASCADE"), index=True
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(80), index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    original_name: Mapped[str | None] = mapped_column(String(180))
    numeric_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    value_text: Mapped[str] = mapped_column(String(80))
    original_unit: Mapped[str | None] = mapped_column(String(80))
    normalized_unit: Mapped[str | None] = mapped_column(String(80))
    reference_min: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    reference_max: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    reference_origin: Mapped[str] = mapped_column(String(40), default="unknown")
    recorded_flag: Mapped[str | None] = mapped_column(String(30))
    derived_flag: Mapped[str | None] = mapped_column(String(30))
    extraction_confidence: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)
    data_origin: Mapped[str] = mapped_column(String(60), default="unknown")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
