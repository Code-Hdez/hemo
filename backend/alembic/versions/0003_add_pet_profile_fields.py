"""Add missing pet profile fields.

Existing production databases may have been created before pets gained photo and
residence consent metadata. This migration adds those columns only when they are
missing so it can be applied safely to live databases.
"""

from alembic import op
import sqlalchemy as sa

from app.modules.pets.models import Pet

revision = "0003_add_pet_profile_fields"
down_revision = "0002_persist_user_roles"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def _table_exists(table: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table)


def upgrade() -> None:
    if not _table_exists("pets"):
        Pet.__table__.create(bind=op.get_bind())

    columns = _columns("pets")
    with op.batch_alter_table("pets") as batch:
        if "residence_precision" not in columns:
            batch.add_column(sa.Column("residence_precision", sa.String(40), nullable=True))
        if "residence_consent_at" not in columns:
            batch.add_column(sa.Column("residence_consent_at", sa.DateTime(), nullable=True))
        if "profile_photo_key" not in columns:
            batch.add_column(sa.Column("profile_photo_key", sa.String(255), nullable=True))


def downgrade() -> None:
    if not _table_exists("pets"):
        return

    columns = _columns("pets")
    with op.batch_alter_table("pets") as batch:
        if "profile_photo_key" in columns:
            batch.drop_column("profile_photo_key")
        if "residence_consent_at" in columns:
            batch.drop_column("residence_consent_at")
        if "residence_precision" in columns:
            batch.drop_column("residence_precision")
