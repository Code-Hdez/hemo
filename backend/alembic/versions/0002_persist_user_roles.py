"""Persist user roles and backfill the default role."""
from alembic import op
import sqlalchemy as sa

revision = "0002_persist_user_roles"
down_revision = "0001_current_schema"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    if "role" not in _columns("users"):
        with op.batch_alter_table("users") as batch:
            batch.add_column(sa.Column("role", sa.String(20), nullable=False, server_default="user"))
            batch.create_check_constraint("ck_users_role", "role IN ('user', 'admin')")
    op.execute("UPDATE users SET role = 'user' WHERE role IS NULL OR role = ''")


def downgrade() -> None:
    if "role" in _columns("users"):
        with op.batch_alter_table("users") as batch:
            batch.drop_constraint("ck_users_role", type_="check")
            batch.drop_column("role")
