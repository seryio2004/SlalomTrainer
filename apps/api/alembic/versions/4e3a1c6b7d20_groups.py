"""Add training groups. Revision ID: 4e3a1c6b7d20; Revises: b5bfc97a50c5."""
from alembic import op
import sqlalchemy as sa

revision = "4e3a1c6b7d20"
down_revision = "b5bfc97a50c5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "training_groups",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("club_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["clubs.id"]),
        sa.UniqueConstraint("club_id", "id"),
        sa.UniqueConstraint("club_id", "name"),
    )
    op.create_index("ix_training_groups_club_id", "training_groups", ["club_id"])
    op.create_table(
        "training_group_memberships",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("club_id", sa.String(36), nullable=False),
        sa.Column("group_id", sa.String(36), nullable=False),
        sa.Column("athlete_id", sa.String(36), nullable=False),
        sa.Column("joined_on", sa.Date(), nullable=False),
        sa.Column("left_on", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(["club_id", "group_id"], ["training_groups.club_id", "training_groups.id"]),
        sa.ForeignKeyConstraint(["club_id", "athlete_id"], ["athletes.club_id", "athletes.id"]),
        sa.UniqueConstraint("club_id", "group_id", "athlete_id"),
    )
    op.create_index("ix_training_group_memberships_club_id", "training_group_memberships", ["club_id"])
    op.create_table(
        "coach_group_grants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("club_id", sa.String(36), nullable=False),
        sa.Column("coach_membership_id", sa.String(36), nullable=False),
        sa.Column("group_id", sa.String(36), nullable=False),
        sa.ForeignKeyConstraint(["club_id", "coach_membership_id"], ["memberships.club_id", "memberships.id"]),
        sa.ForeignKeyConstraint(["club_id", "group_id"], ["training_groups.club_id", "training_groups.id"]),
        sa.UniqueConstraint("club_id", "coach_membership_id", "group_id"),
    )
    op.create_index("ix_coach_group_grants_club_id", "coach_group_grants", ["club_id"])
    with op.batch_alter_table("workout_sessions") as batch:
        batch.add_column(sa.Column("group_id", sa.String(36), nullable=True))
        batch.create_foreign_key("fk_workout_sessions_group", "training_groups", ["club_id", "group_id"], ["club_id", "id"])


def downgrade() -> None:
    with op.batch_alter_table("workout_sessions") as batch:
        batch.drop_constraint("fk_workout_sessions_group", type_="foreignkey")
        batch.drop_column("group_id")
    op.drop_index("ix_coach_group_grants_club_id", "coach_group_grants")
    op.drop_table("coach_group_grants")
    op.drop_index("ix_training_group_memberships_club_id", "training_group_memberships")
    op.drop_table("training_group_memberships")
    op.drop_index("ix_training_groups_club_id", "training_groups")
    op.drop_table("training_groups")
