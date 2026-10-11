"""Persist structured journal analysis metadata."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261011_0003"
down_revision: str | None = "20261011_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("journal_entries", sa.Column("analysis_summary", sa.Text(), nullable=True))
    op.add_column(
        "journal_entries",
        sa.Column("people_mentioned", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "observations",
        sa.Column("include_in_weekly_report", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("observations", "include_in_weekly_report")
    op.drop_column("journal_entries", "people_mentioned")
    op.drop_column("journal_entries", "analysis_summary")
