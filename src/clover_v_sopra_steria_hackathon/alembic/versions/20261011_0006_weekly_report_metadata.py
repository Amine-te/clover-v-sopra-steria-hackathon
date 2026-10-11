"""Persist weekly report approval and aggregation metadata."""

from alembic import op
import sqlalchemy as sa

revision = "20261011_0006"
down_revision = "20261011_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("weekly_reports", sa.Column("approved", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("weekly_reports", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("weekly_reports", sa.Column("source_entry_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("weekly_reports", sa.Column("structured_item_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("weekly_reports", sa.Column("reportable_item_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("weekly_reports", sa.Column("excluded_private_count", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    for column in (
        "excluded_private_count",
        "reportable_item_count",
        "structured_item_count",
        "source_entry_count",
        "approved_at",
        "approved",
    ):
        op.drop_column("weekly_reports", column)
