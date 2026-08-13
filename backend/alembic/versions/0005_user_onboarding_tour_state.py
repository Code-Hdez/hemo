"""Persist per-user onboarding tour state."""

from alembic import op
import sqlalchemy as sa

revision = "0005_user_onboarding_tour_state"
down_revision = "0004_llm_chat_runtime_metadata"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def _constraints(table: str) -> set[str]:
    return {item["name"] for item in sa.inspect(op.get_bind()).get_check_constraints(table)}


def upgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("users"):
        return

    columns = _columns("users")
    with op.batch_alter_table("users") as batch:
        if "onboarding_tour_status" not in columns:
            batch.add_column(
                sa.Column(
                    "onboarding_tour_status",
                    sa.String(20),
                    nullable=False,
                    server_default="pending",
                )
            )
        if "onboarding_tour_version" not in columns:
            batch.add_column(sa.Column("onboarding_tour_version", sa.String(80), nullable=True))
        if "onboarding_tour_dismissed_at" not in columns:
            batch.add_column(sa.Column("onboarding_tour_dismissed_at", sa.DateTime(), nullable=True))

    op.execute(
        "UPDATE users SET onboarding_tour_status = 'pending' "
        "WHERE onboarding_tour_status IS NULL OR onboarding_tour_status = ''"
    )

    if "ck_users_onboarding_tour_status" not in _constraints("users"):
        with op.batch_alter_table("users") as batch:
            batch.create_check_constraint(
                "ck_users_onboarding_tour_status",
                "onboarding_tour_status IN ('pending', 'completed', 'skipped')",
            )


def downgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("users"):
        return

    columns = _columns("users")
    constraints = _constraints("users")
    with op.batch_alter_table("users") as batch:
        if "ck_users_onboarding_tour_status" in constraints:
            batch.drop_constraint("ck_users_onboarding_tour_status", type_="check")
        for name in [
            "onboarding_tour_dismissed_at",
            "onboarding_tour_version",
            "onboarding_tour_status",
        ]:
            if name in columns:
                batch.drop_column(name)
