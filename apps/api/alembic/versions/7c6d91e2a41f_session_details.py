"""Home/club sessions and detailed water feedback.

Revision ID: 7c6d91e2a41f
Revises: 4e3a1c6b7d20
"""
from alembic import op
import sqlalchemy as sa

revision = "7c6d91e2a41f"
down_revision = "4e3a1c6b7d20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workout_sessions", sa.Column("venue", sa.String(8), nullable=False, server_default="club"))
    for name in ("sensations", "work_done", "best", "worst"):
        op.add_column("feedback", sa.Column(name, sa.String(1000), nullable=True))


def downgrade() -> None:
    for name in ("worst", "best", "work_done", "sensations"):
        op.drop_column("feedback", name)
    op.drop_column("workout_sessions", "venue")
