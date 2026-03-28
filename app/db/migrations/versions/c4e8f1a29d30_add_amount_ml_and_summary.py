"""add_amount_ml_and_summary

Revision ID: c4e8f1a29d30
Revises: bb6ad5534a69
Create Date: 2026-03-28

Changes:
  - baby_logs.amount_ml (INTEGER nullable) — ml consumed per formula feed
  - voice_entries.summary (TEXT nullable)  — auto-generated AI summary for note entries
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4e8f1a29d30"
down_revision: Union[str, None] = "bb6ad5534a69"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("baby_logs", sa.Column("amount_ml", sa.Integer(), nullable=True))
    op.add_column("voice_entries", sa.Column("summary", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("baby_logs", "amount_ml")
    op.drop_column("voice_entries", "summary")
