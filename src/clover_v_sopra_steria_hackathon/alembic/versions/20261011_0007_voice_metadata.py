"""Persist voice upload and transcription metadata."""

from alembic import op
import sqlalchemy as sa

revision = "20261011_0007"
down_revision = "20261011_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("journal_entries", sa.Column("audio_mime_type", sa.String(length=100), nullable=True))
    op.add_column("journal_entries", sa.Column("transcription_status", sa.String(length=30), nullable=True))
    op.add_column("journal_entries", sa.Column("transcription_duration_ms", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("journal_entries", "transcription_duration_ms")
    op.drop_column("journal_entries", "transcription_status")
    op.drop_column("journal_entries", "audio_mime_type")
