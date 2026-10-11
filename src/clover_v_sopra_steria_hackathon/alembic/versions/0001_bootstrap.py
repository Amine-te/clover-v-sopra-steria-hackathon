"""Bootstrap — empty initial migration (no Karis domain tables yet).

Revision ID: 0001_bootstrap
Revises:
Create Date: 2026-10-11
"""

from collections.abc import Sequence

revision: str = "0001_bootstrap"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
