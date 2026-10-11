"""Store why each clarification question was asked."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261011_0004"
down_revision: str | None = "20261011_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "clarifications",
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("clarifications", "reason")
