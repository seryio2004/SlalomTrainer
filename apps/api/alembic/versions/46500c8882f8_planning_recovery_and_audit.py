"""Planning recovery and audit

Revision ID: 46500c8882f8
Revises: 7c6d91e2a41f
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '46500c8882f8'
down_revision: Union[str, Sequence[str], None] = '7c6d91e2a41f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('audit_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('club_id', sa.String(length=36), nullable=False),
        sa.Column('actor_user_id', sa.String(length=36), nullable=False),
        sa.Column('action', sa.String(length=80), nullable=False),
        sa.Column('entity_id', sa.String(length=36), nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['club_id'], ['clubs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_events_club_id'), 'audit_events', ['club_id'], unique=False)
    op.create_table('seasons',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('club_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=160), nullable=False),
        sa.Column('starts_on', sa.Date(), nullable=False),
        sa.Column('ends_on', sa.Date(), nullable=False),
        sa.Column('age_reference_date', sa.Date(), nullable=False),
        sa.Column('objectives', sa.String(length=2000), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.ForeignKeyConstraint(['club_id'], ['clubs.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('club_id', 'id')
    )
    op.create_index(op.f('ix_seasons_club_id'), 'seasons', ['club_id'], unique=False)
    op.create_index('one_active_season_per_club', 'seasons', ['club_id'], unique=True, sqlite_where=sa.text("status = 'active'"), postgresql_where=sa.text("status = 'active'"))
    op.create_table('training_phases',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('club_id', sa.String(length=36), nullable=False),
        sa.Column('season_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=160), nullable=False),
        sa.Column('starts_on', sa.Date(), nullable=False),
        sa.Column('ends_on', sa.Date(), nullable=False),
        sa.Column('objectives', sa.String(length=2000), nullable=False),
        sa.ForeignKeyConstraint(['club_id', 'season_id'], ['seasons.club_id', 'seasons.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('club_id', 'id')
    )
    op.create_index(op.f('ix_training_phases_club_id'), 'training_phases', ['club_id'], unique=False)
    op.create_table('recovery_logs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('club_id', sa.String(length=36), nullable=False),
        sa.Column('athlete_id', sa.String(length=36), nullable=False),
        sa.Column('local_date', sa.Date(), nullable=False),
        sa.Column('sleep', sa.Integer(), nullable=True),
        sa.Column('fatigue', sa.Integer(), nullable=True),
        sa.Column('soreness', sa.Integer(), nullable=True),
        sa.Column('motivation', sa.Integer(), nullable=True),
        sa.Column('energy', sa.Integer(), nullable=True),
        sa.Column('pain', sa.Integer(), nullable=True),
        sa.Column('pain_area', sa.String(length=120), nullable=True),
        sa.Column('comment', sa.String(length=2000), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('revisions', sa.JSON(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['club_id', 'athlete_id'], ['athletes.club_id', 'athletes.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('club_id', 'athlete_id', 'local_date')
    )
    op.create_index(op.f('ix_recovery_logs_club_id'), 'recovery_logs', ['club_id'], unique=False)
    op.create_table('training_plans',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('club_id', sa.String(length=36), nullable=False),
        sa.Column('phase_id', sa.String(length=36), nullable=False),
        sa.Column('coach_membership_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=160), nullable=False),
        sa.Column('starts_on', sa.Date(), nullable=False),
        sa.Column('ends_on', sa.Date(), nullable=False),
        sa.Column('objectives', sa.String(length=2000), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.ForeignKeyConstraint(['club_id', 'coach_membership_id'], ['memberships.club_id', 'memberships.id'], ),
        sa.ForeignKeyConstraint(['club_id', 'phase_id'], ['training_phases.club_id', 'training_phases.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('club_id', 'id')
    )
    op.create_index(op.f('ix_training_plans_club_id'), 'training_plans', ['club_id'], unique=False)
    op.create_table('microcycles',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('club_id', sa.String(length=36), nullable=False),
        sa.Column('plan_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=160), nullable=False),
        sa.Column('starts_on', sa.Date(), nullable=False),
        sa.Column('ends_on', sa.Date(), nullable=False),
        sa.Column('objectives', sa.String(length=2000), nullable=False),
        sa.ForeignKeyConstraint(['club_id', 'plan_id'], ['training_plans.club_id', 'training_plans.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('club_id', 'id')
    )
    op.create_index(op.f('ix_microcycles_club_id'), 'microcycles', ['club_id'], unique=False)
    op.create_table('plan_days',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('club_id', sa.String(length=36), nullable=False),
        sa.Column('microcycle_id', sa.String(length=36), nullable=False),
        sa.Column('local_date', sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(['club_id', 'microcycle_id'], ['microcycles.club_id', 'microcycles.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('club_id', 'id'),
        sa.UniqueConstraint('club_id', 'microcycle_id', 'local_date')
    )
    op.create_index(op.f('ix_plan_days_club_id'), 'plan_days', ['club_id'], unique=False)
    with op.batch_alter_table("workout_sessions") as batch:
        batch.add_column(sa.Column("plan_day_id", sa.String(36), nullable=True))
        batch.create_foreign_key(
            "fk_workout_sessions_plan_day", "plan_days",
            ["club_id", "plan_day_id"], ["club_id", "id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("workout_sessions") as batch:
        batch.drop_constraint("fk_workout_sessions_plan_day", type_="foreignkey")
        batch.drop_column("plan_day_id")
    op.drop_index(op.f('ix_plan_days_club_id'), table_name='plan_days')
    op.drop_table('plan_days')
    op.drop_index(op.f('ix_microcycles_club_id'), table_name='microcycles')
    op.drop_table('microcycles')
    op.drop_index(op.f('ix_training_plans_club_id'), table_name='training_plans')
    op.drop_table('training_plans')
    op.drop_index(op.f('ix_recovery_logs_club_id'), table_name='recovery_logs')
    op.drop_table('recovery_logs')
    op.drop_index(op.f('ix_training_phases_club_id'), table_name='training_phases')
    op.drop_table('training_phases')
    op.drop_index('one_active_season_per_club', table_name='seasons', sqlite_where=sa.text("status = 'active'"), postgresql_where=sa.text("status = 'active'"))
    op.drop_index(op.f('ix_seasons_club_id'), table_name='seasons')
    op.drop_table('seasons')
    op.drop_index(op.f('ix_audit_events_club_id'), table_name='audit_events')
    op.drop_table('audit_events')
