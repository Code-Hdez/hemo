"""Current schema baseline.

New databases are created from application metadata. Existing databases must
be audited and stamped at this revision before applying later revisions.
"""
from alembic import op

from app.db.base import Base

revision = "0001_current_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
