"""Structured prescription library, individual revisions and execution corrections."""
from alembic import op
import sqlalchemy as sa

revision = "c621prescription"
down_revision = "8d2b22777103"
branch_labels = depends_on = None


def upgrade():
    op.add_column("assignments", sa.Column("prescription_revisions", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("executions", sa.Column("actual_date", sa.Date(), nullable=True))
    op.add_column("executions", sa.Column("state", sa.String(16), nullable=False, server_default="submitted"))
    op.add_column("executions", sa.Column("data", sa.JSON(), nullable=False, server_default="{}"))
    op.add_column("executions", sa.Column("revisions", sa.JSON(), nullable=False, server_default="[]"))
    # Historical reports have no independent execution date: leave it unknown.
    op.create_table("exercises",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("club_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("instructions", sa.String(2000), nullable=False),
        sa.Column("measurement", sa.String(32), nullable=False),
        sa.Column("reference", sa.Boolean(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.UniqueConstraint("club_id", "id"),
        sa.ForeignKeyConstraint(["club_id"], ["clubs.id"]))
    op.create_index("ix_exercises_club_id", "exercises", ["club_id"])
    op.create_table("workout_templates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("club_id", sa.String(36), nullable=False),
        sa.Column("coach_membership_id", sa.String(36), nullable=False),
        sa.Column("prescription", sa.JSON(), nullable=False),
        sa.Column("revisions", sa.JSON(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["club_id", "coach_membership_id"], ["memberships.club_id", "memberships.id"]))
    op.create_index("ix_workout_templates_club_id", "workout_templates", ["club_id"])


def downgrade():
    # Destructive reversal requires a copy: structured results and revision histories are lost.
    op.drop_table("workout_templates")
    op.drop_table("exercises")
    for column in ("revisions", "data", "state", "actual_date"):
        with op.batch_alter_table("executions") as batch:
            batch.drop_column(column)
    with op.batch_alter_table("assignments") as batch:
        batch.drop_column("prescription_revisions")
