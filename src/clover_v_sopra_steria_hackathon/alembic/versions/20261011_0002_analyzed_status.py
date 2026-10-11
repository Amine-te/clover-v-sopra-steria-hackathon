"""Add the analyzed journal lifecycle state.

The project stores enums as validated VARCHAR columns, so this lifecycle
extension requires no PostgreSQL DDL. The revision records the domain change
without rewriting the existing M2 tables.
"""

from collections.abc import Sequence

revision: str = "20261011_0002"
down_revision: str | None = "461316c4aac8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
