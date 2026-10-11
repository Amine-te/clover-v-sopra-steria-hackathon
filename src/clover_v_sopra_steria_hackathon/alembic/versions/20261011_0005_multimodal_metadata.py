"""Persist M5 multimodal provenance and entry association."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261011_0005"
down_revision: str | None = "20261011_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("vocal_affect_signals", sa.Column("top_label", sa.String(50), nullable=True))
    op.add_column("vocal_affect_signals", sa.Column("quality", sa.String(30), nullable=False, server_default="unknown"))
    op.add_column("vocal_affect_signals", sa.Column("model_version", sa.String(80), nullable=False, server_default=""))
    op.add_column("vocal_affect_signals", sa.Column("provider", sa.String(80), nullable=False, server_default="mock"))
    op.add_column("wearable_windows", sa.Column("entry_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_wearable_windows_entry_id",
        "wearable_windows",
        "journal_entries",
        ["entry_id"],
        ["id"],
    )
    op.create_index("ix_wearable_windows_entry_id", "wearable_windows", ["entry_id"])


def downgrade() -> None:
    op.drop_index("ix_wearable_windows_entry_id", table_name="wearable_windows")
    op.drop_constraint("fk_wearable_windows_entry_id", "wearable_windows", type_="foreignkey")
    op.drop_column("wearable_windows", "entry_id")
    for column in ("provider", "model_version", "quality", "top_label"):
        op.drop_column("vocal_affect_signals", column)
