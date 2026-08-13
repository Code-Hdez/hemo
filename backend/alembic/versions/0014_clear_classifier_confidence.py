"""Clear the ML classifier confidence stored as extraction confidence."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0014_clear_classifier_conf"
down_revision = "0013_chat_hot_path_indexes"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return set()
    return {str(column["name"]) for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    """Null out ``analyses.extraction_confidence`` on every existing row.

    Both writers of this column — ``db.queries.save_analysis`` and the backfill
    in 0007 — took ``payload["confidence"]``, which is ``prediction.confidence``
    from the ML classifier, never a confidence reported by the document
    extractor. The chat reads the column back as fact_type
    "extraction_confidence" and shows it to the model as digitisation quality,
    so every stored row currently asserts something nobody measured. No stored
    row holds a genuine extraction confidence (nothing ever wrote one), which
    is why clearing all of them loses no real data. Per-parameter extraction
    confidences are untouched: those in ``analysis_parameters`` do come from
    the extractor.
    """
    if "extraction_confidence" not in _columns("analyses"):
        return
    analyses = sa.table(
        "analyses",
        sa.column("extraction_confidence", sa.Float),
    )
    op.get_bind().execute(
        analyses.update()
        .where(analyses.c.extraction_confidence.isnot(None))
        .values(extraction_confidence=None)
    )


def downgrade() -> None:
    """No-op: the cleared values were the classifier's, not the extractor's.

    Restoring them would mean copying ``data->>'confidence'`` back into a
    column that means something else, which is the defect this revision exists
    to remove.
    """
