"""Normalize clinical values and preserve extraction provenance."""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision = "0007_analysis_parameters"
down_revision = "0006_chat_context_memory"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def _decimal(value: object) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None


def _float(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return min(1.0, max(0.0, float(value)))
    except (TypeError, ValueError):
        return None


def _datetime(value: object) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed.replace(tzinfo=None) if parsed.tzinfo is not None else parsed


def _canonical_name(item: dict[str, object]) -> str:
    direct = str(item.get("canonical_name") or item.get("name") or "unknown").strip()
    aliases = {
        "plt": "Platelets",
        "platelets": "Platelets",
        "plaquetas": "Platelets",
        "leucocitos": "WBC",
        "hematíes": "RBC",
        "hematies": "RBC",
    }
    return aliases.get(direct.lower(), direct)[:80] or "unknown"


def _laboratory(payload: dict[str, object]) -> str | None:
    value = payload.get("laboratory") or payload.get("clinic")
    snapshot = payload.get("_case_snapshot")
    if not value and isinstance(snapshot, dict):
        value = snapshot.get("laboratory") or snapshot.get("clinic")
        metadata = snapshot.get("metadata")
        if not value and isinstance(metadata, dict):
            value = metadata.get("laboratory") or metadata.get("clinic")
    text = str(value).strip() if value is not None else ""
    return text[:200] or None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("analyses"):
        return

    columns = _columns("analyses")
    with op.batch_alter_table("analyses") as batch:
        if "performed_at" not in columns:
            batch.add_column(sa.Column("performed_at", sa.DateTime(), nullable=True))
        if "laboratory" not in columns:
            batch.add_column(sa.Column("laboratory", sa.String(200), nullable=True))
        if "extraction_confidence" not in columns:
            batch.add_column(
                sa.Column("extraction_confidence", sa.Float(), nullable=True)
            )
        if "data_origin" not in columns:
            batch.add_column(
                sa.Column(
                    "data_origin",
                    sa.String(60),
                    nullable=False,
                    server_default="unknown",
                )
            )

    indexes = {
        index["name"] for index in sa.inspect(op.get_bind()).get_indexes("analyses")
    }
    if "ix_analyses_performed_at" not in indexes:
        op.create_index("ix_analyses_performed_at", "analyses", ["performed_at"])

    if not sa.inspect(op.get_bind()).has_table("analysis_parameters"):
        op.create_table(
            "analysis_parameters",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "analysis_id",
                sa.String(36),
                sa.ForeignKey("analyses.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("ordinal", sa.Integer(), nullable=False),
            sa.Column("canonical_name", sa.String(80), nullable=False),
            sa.Column("display_name", sa.String(120), nullable=False),
            sa.Column("original_name", sa.String(180), nullable=True),
            sa.Column("numeric_value", sa.Numeric(20, 8), nullable=True),
            sa.Column("value_text", sa.String(80), nullable=False),
            sa.Column("original_unit", sa.String(80), nullable=True),
            sa.Column("normalized_unit", sa.String(80), nullable=True),
            sa.Column("reference_min", sa.Numeric(20, 8), nullable=True),
            sa.Column("reference_max", sa.Numeric(20, 8), nullable=True),
            sa.Column(
                "reference_origin",
                sa.String(40),
                nullable=False,
                server_default="unknown",
            ),
            sa.Column("recorded_flag", sa.String(30), nullable=True),
            sa.Column("derived_flag", sa.String(30), nullable=True),
            sa.Column("extraction_confidence", sa.Float(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column(
                "data_origin",
                sa.String(60),
                nullable=False,
                server_default="unknown",
            ),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.UniqueConstraint(
                "analysis_id", "ordinal", name="uq_analysis_parameter_ordinal"
            ),
        )
        op.create_index(
            "ix_analysis_parameters_analysis_id",
            "analysis_parameters",
            ["analysis_id"],
        )
        op.create_index(
            "ix_analysis_parameters_canonical_name",
            "analysis_parameters",
            ["canonical_name"],
        )

    connection = op.get_bind()
    analyses = sa.table(
        "analyses",
        sa.column("id", sa.String),
        sa.column("data", sa.Text),
        sa.column("performed_at", sa.DateTime),
        sa.column("laboratory", sa.String),
        sa.column("extraction_confidence", sa.Float),
        sa.column("data_origin", sa.String),
    )
    parameters = sa.table(
        "analysis_parameters",
        sa.column("id", sa.String),
        sa.column("analysis_id", sa.String),
        sa.column("ordinal", sa.Integer),
        sa.column("canonical_name", sa.String),
        sa.column("display_name", sa.String),
        sa.column("original_name", sa.String),
        sa.column("numeric_value", sa.Numeric),
        sa.column("value_text", sa.String),
        sa.column("original_unit", sa.String),
        sa.column("normalized_unit", sa.String),
        sa.column("reference_min", sa.Numeric),
        sa.column("reference_max", sa.Numeric),
        sa.column("reference_origin", sa.String),
        sa.column("recorded_flag", sa.String),
        sa.column("derived_flag", sa.String),
        sa.column("extraction_confidence", sa.Float),
        sa.column("notes", sa.Text),
        sa.column("data_origin", sa.String),
        sa.column("created_at", sa.DateTime),
    )

    for row in connection.execute(sa.select(analyses.c.id, analyses.c.data)):
        try:
            payload = json.loads(row.data or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        connection.execute(
            analyses.update()
            .where(analyses.c.id == row.id)
            .values(
                performed_at=_datetime(payload.get("created_at")),
                laboratory=_laboratory(payload),
                extraction_confidence=_float(payload.get("confidence")),
                data_origin=str(payload.get("extraction_provider") or "legacy_json")[:60],
            )
        )
        lab_values = payload.get("lab_values")
        if not isinstance(lab_values, list):
            continue
        for ordinal, item in enumerate(lab_values):
            if not isinstance(item, dict):
                continue
            value_text = str(item.get("value") if item.get("value") is not None else "")
            has_range = item.get("ref_min") is not None or item.get("ref_max") is not None
            origin = str(
                item.get("reference_origin")
                or ("system_default_legacy" if has_range else "unknown")
            )
            status_origin = str(item.get("status_origin") or "derived")
            status_value = str(item.get("status") or "") or None
            connection.execute(
                parameters.insert().values(
                    id=str(uuid4()),
                    analysis_id=row.id,
                    ordinal=ordinal,
                    canonical_name=_canonical_name(item),
                    display_name=str(item.get("name") or "Parámetro")[:120],
                    original_name=(
                        str(item.get("original_name"))[:180]
                        if item.get("original_name") is not None
                        else None
                    ),
                    numeric_value=_decimal(item.get("value")),
                    value_text=value_text[:80],
                    original_unit=(
                        str(item.get("unit"))[:80]
                        if item.get("unit") is not None
                        else None
                    ),
                    normalized_unit=(
                        str(item.get("normalized_unit"))[:80]
                        if item.get("normalized_unit") is not None
                        else None
                    ),
                    reference_min=_decimal(item.get("ref_min")),
                    reference_max=_decimal(item.get("ref_max")),
                    reference_origin=origin[:40],
                    recorded_flag=status_value if status_origin == "recorded" else None,
                    derived_flag=(
                        str(item.get("derived_status") or status_value)[:30]
                        if status_origin != "recorded" or item.get("derived_status")
                        else None
                    ),
                    extraction_confidence=_float(item.get("extraction_confidence")),
                    notes=(str(item.get("notes")) if item.get("notes") else None),
                    data_origin=str(item.get("data_origin") or "legacy_json")[:60],
                    created_at=datetime.utcnow(),
                )
            )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("analysis_parameters"):
        op.drop_table("analysis_parameters")
    if not inspector.has_table("analyses"):
        return
    indexes = {
        index["name"] for index in sa.inspect(op.get_bind()).get_indexes("analyses")
    }
    if "ix_analyses_performed_at" in indexes:
        op.drop_index("ix_analyses_performed_at", table_name="analyses")
    columns = _columns("analyses")
    with op.batch_alter_table("analyses") as batch:
        for name in [
            "data_origin",
            "extraction_confidence",
            "laboratory",
            "performed_at",
        ]:
            if name in columns:
                batch.drop_column(name)
