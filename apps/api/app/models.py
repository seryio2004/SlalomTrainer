from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKeyConstraint, Integer, JSON, String, UniqueConstraint, Index, text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def new_id() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(String(256))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Club(Base):
    __tablename__ = "clubs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(160))
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Madrid")


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("club_id", "user_id"),
        UniqueConstraint("club_id", "id"),
        ForeignKeyConstraint(["user_id"], ["users.id"]),
        ForeignKeyConstraint(["club_id"], ["clubs.id"]),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    club_id: Mapped[str] = mapped_column(String(36), index=True)
    user_id: Mapped[str] = mapped_column(String(36))
    roles: Mapped[list[str]] = mapped_column(JSON)  # club_admin, coach, athlete
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Athlete(Base):
    __tablename__ = "athletes"
    __table_args__ = (
        UniqueConstraint("club_id", "id"),
        UniqueConstraint("club_id", "membership_id"),
        ForeignKeyConstraint(["club_id", "membership_id"], ["memberships.club_id", "memberships.id"]),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    club_id: Mapped[str] = mapped_column(String(36), index=True)
    membership_id: Mapped[str] = mapped_column(String(36))
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class TrainingGroup(Base):
    __tablename__ = "training_groups"
    __table_args__ = (
        UniqueConstraint("club_id", "id"),
        UniqueConstraint("club_id", "name"),
        ForeignKeyConstraint(["club_id"], ["clubs.id"]),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    club_id: Mapped[str] = mapped_column(String(36), index=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(String(500), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class TrainingGroupMembership(Base):
    __tablename__ = "training_group_memberships"
    __table_args__ = (
        Index(
            "one_open_group_membership", "club_id", "group_id", "athlete_id",
            unique=True,
            sqlite_where=text("left_on IS NULL"),
            postgresql_where=text("left_on IS NULL"),
        ),
        ForeignKeyConstraint(["club_id", "group_id"], ["training_groups.club_id", "training_groups.id"]),
        ForeignKeyConstraint(["club_id", "athlete_id"], ["athletes.club_id", "athletes.id"]),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    club_id: Mapped[str] = mapped_column(String(36), index=True)
    group_id: Mapped[str] = mapped_column(String(36))
    athlete_id: Mapped[str] = mapped_column(String(36))
    joined_on: Mapped[date] = mapped_column(Date)
    left_on: Mapped[date | None] = mapped_column(Date, nullable=True)


class CoachGroupGrant(Base):
    __tablename__ = "coach_group_grants"
    __table_args__ = (
        UniqueConstraint("club_id", "coach_membership_id", "group_id"),
        ForeignKeyConstraint(["club_id", "coach_membership_id"], ["memberships.club_id", "memberships.id"]),
        ForeignKeyConstraint(["club_id", "group_id"], ["training_groups.club_id", "training_groups.id"]),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    club_id: Mapped[str] = mapped_column(String(36), index=True)
    coach_membership_id: Mapped[str] = mapped_column(String(36))
    group_id: Mapped[str] = mapped_column(String(36))


class CoachAthleteGrant(Base):
    __tablename__ = "coach_athlete_grants"
    __table_args__ = (
        UniqueConstraint("club_id", "coach_membership_id", "athlete_id"),
        ForeignKeyConstraint(["club_id", "coach_membership_id"], ["memberships.club_id", "memberships.id"]),
        ForeignKeyConstraint(["club_id", "athlete_id"], ["athletes.club_id", "athletes.id"]),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    club_id: Mapped[str] = mapped_column(String(36), index=True)
    coach_membership_id: Mapped[str] = mapped_column(String(36))
    athlete_id: Mapped[str] = mapped_column(String(36))


class WorkoutSession(Base):
    __tablename__ = "workout_sessions"
    __table_args__ = (
        UniqueConstraint("club_id", "id"),
        ForeignKeyConstraint(["club_id", "coach_membership_id"], ["memberships.club_id", "memberships.id"]),
        ForeignKeyConstraint(["club_id", "group_id"], ["training_groups.club_id", "training_groups.id"]),
        ForeignKeyConstraint(["club_id", "plan_day_id"], ["plan_days.club_id", "plan_days.id"]),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    club_id: Mapped[str] = mapped_column(String(36), index=True)
    coach_membership_id: Mapped[str] = mapped_column(String(36))
    group_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    plan_day_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    title: Mapped[str] = mapped_column(String(160))
    training_type: Mapped[str] = mapped_column(String(32))
    venue: Mapped[str] = mapped_column(String(8), default="club")
    scheduled_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    planned_minutes: Mapped[int] = mapped_column(Integer)
    prescription: Mapped[dict] = mapped_column(JSON)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(16), default="planned")


class Assignment(Base):
    __tablename__ = "assignments"
    __table_args__ = (
        UniqueConstraint("club_id", "id"),
        UniqueConstraint("club_id", "session_id", "athlete_id"),
        ForeignKeyConstraint(["club_id", "session_id"], ["workout_sessions.club_id", "workout_sessions.id"]),
        ForeignKeyConstraint(["club_id", "athlete_id"], ["athletes.club_id", "athletes.id"]),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    club_id: Mapped[str] = mapped_column(String(36), index=True)
    session_id: Mapped[str] = mapped_column(String(36))
    athlete_id: Mapped[str] = mapped_column(String(36))
    status: Mapped[str] = mapped_column(String(16), default="planned")
    prescription_snapshot: Mapped[dict] = mapped_column(JSON)
    prescription_revisions: Mapped[list] = mapped_column(JSON, default=list)
    version: Mapped[int] = mapped_column(Integer, default=1)


class Execution(Base):
    __tablename__ = "executions"
    __table_args__ = (
        UniqueConstraint("club_id", "assignment_id"),
        ForeignKeyConstraint(["club_id", "assignment_id"], ["assignments.club_id", "assignments.id"]),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    club_id: Mapped[str] = mapped_column(String(36), index=True)
    assignment_id: Mapped[str] = mapped_column(String(36))
    actual_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actual_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    state: Mapped[str] = mapped_column(String(16), default="submitted")
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    revisions: Mapped[list] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Feedback(Base):
    __tablename__ = "feedback"
    __table_args__ = (
        UniqueConstraint("club_id", "assignment_id"),
        ForeignKeyConstraint(["club_id", "assignment_id"], ["assignments.club_id", "assignments.id"]),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    club_id: Mapped[str] = mapped_column(String(36), index=True)
    assignment_id: Mapped[str] = mapped_column(String(36))
    rpe: Mapped[int | None] = mapped_column(Integer, nullable=True)
    feeling: Mapped[int | None] = mapped_column(Integer, nullable=True)
    has_pain: Mapped[bool] = mapped_column(Boolean, default=False)
    pain_area: Mapped[str | None] = mapped_column(String(120), nullable=True)
    comment: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    sensations: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    work_done: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    best: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    worst: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (ForeignKeyConstraint(["user_id"], ["users.id"]),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    csrf_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Season(Base):
    __tablename__ = "seasons"
    __table_args__ = (
        UniqueConstraint("club_id", "id"),
        ForeignKeyConstraint(["club_id"], ["clubs.id"]),
        Index(
            "one_active_season_per_club", "club_id", unique=True,
            sqlite_where=text("status = 'active'"),
            postgresql_where=text("status = 'active'"),
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    club_id: Mapped[str] = mapped_column(String(36), index=True)
    name: Mapped[str] = mapped_column(String(160))
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date] = mapped_column(Date)
    age_reference_date: Mapped[date] = mapped_column(Date)
    objectives: Mapped[str] = mapped_column(String(2000), default="")
    status: Mapped[str] = mapped_column(String(16), default="draft")


class TrainingPhase(Base):
    __tablename__ = "training_phases"
    __table_args__ = (
        UniqueConstraint("club_id", "id"),
        ForeignKeyConstraint(["club_id", "season_id"], ["seasons.club_id", "seasons.id"]),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    club_id: Mapped[str] = mapped_column(String(36), index=True)
    season_id: Mapped[str] = mapped_column(String(36))
    name: Mapped[str] = mapped_column(String(160))
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date] = mapped_column(Date)
    objectives: Mapped[str] = mapped_column(String(2000), default="")


class TrainingPlan(Base):
    __tablename__ = "training_plans"
    __table_args__ = (
        UniqueConstraint("club_id", "id"),
        ForeignKeyConstraint(["club_id", "phase_id"], ["training_phases.club_id", "training_phases.id"]),
        ForeignKeyConstraint(["club_id", "coach_membership_id"], ["memberships.club_id", "memberships.id"]),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    club_id: Mapped[str] = mapped_column(String(36), index=True)
    phase_id: Mapped[str] = mapped_column(String(36))
    coach_membership_id: Mapped[str] = mapped_column(String(36))
    name: Mapped[str] = mapped_column(String(160))
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date] = mapped_column(Date)
    objectives: Mapped[str] = mapped_column(String(2000), default="")
    status: Mapped[str] = mapped_column(String(16), default="active")


class Microcycle(Base):
    __tablename__ = "microcycles"
    __table_args__ = (
        UniqueConstraint("club_id", "id"),
        ForeignKeyConstraint(["club_id", "plan_id"], ["training_plans.club_id", "training_plans.id"]),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    club_id: Mapped[str] = mapped_column(String(36), index=True)
    plan_id: Mapped[str] = mapped_column(String(36))
    name: Mapped[str] = mapped_column(String(160))
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date] = mapped_column(Date)
    objectives: Mapped[str] = mapped_column(String(2000), default="")


class PlanDay(Base):
    __tablename__ = "plan_days"
    __table_args__ = (
        UniqueConstraint("club_id", "id"),
        UniqueConstraint("club_id", "microcycle_id", "local_date"),
        ForeignKeyConstraint(["club_id", "microcycle_id"], ["microcycles.club_id", "microcycles.id"]),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    club_id: Mapped[str] = mapped_column(String(36), index=True)
    microcycle_id: Mapped[str] = mapped_column(String(36))
    local_date: Mapped[date] = mapped_column(Date)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        ForeignKeyConstraint(["club_id"], ["clubs.id"]),
        ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    club_id: Mapped[str] = mapped_column(String(36), index=True)
    actor_user_id: Mapped[str] = mapped_column(String(36))
    action: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str] = mapped_column(String(36))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class RecoveryLog(Base):
    __tablename__ = "recovery_logs"
    __table_args__ = (
        UniqueConstraint("club_id", "athlete_id", "local_date"),
        ForeignKeyConstraint(["club_id", "athlete_id"], ["athletes.club_id", "athletes.id"]),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    club_id: Mapped[str] = mapped_column(String(36), index=True)
    athlete_id: Mapped[str] = mapped_column(String(36))
    local_date: Mapped[date] = mapped_column(Date)
    sleep: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fatigue: Mapped[int | None] = mapped_column(Integer, nullable=True)
    soreness: Mapped[int | None] = mapped_column(Integer, nullable=True)
    motivation: Mapped[int | None] = mapped_column(Integer, nullable=True)
    energy: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pain: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pain_area: Mapped[str | None] = mapped_column(String(120), nullable=True)
    comment: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    revisions: Mapped[list] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class GoogleCalendarConnection(Base):
    __tablename__ = "google_calendar_connections"
    __table_args__ = (
        UniqueConstraint("club_id", "athlete_id"),
        ForeignKeyConstraint(["club_id", "athlete_id"], ["athletes.club_id", "athletes.id"]),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    club_id: Mapped[str] = mapped_column(String(36), index=True)
    athlete_id: Mapped[str] = mapped_column(String(36))
    encrypted_refresh_token: Mapped[str] = mapped_column(String(2048))
    calendar_id: Mapped[str | None] = mapped_column(String(320), nullable=True)
    calendar_name: Mapped[str | None] = mapped_column(String(320), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(32), default="choose_calendar")
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)


class GoogleOAuthState(Base):
    __tablename__ = "google_oauth_states"
    __table_args__ = (
        ForeignKeyConstraint(["club_id", "athlete_id"], ["athletes.club_id", "athletes.id"]),
    )
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    club_id: Mapped[str] = mapped_column(String(36))
    athlete_id: Mapped[str] = mapped_column(String(36))
    code_verifier: Mapped[str] = mapped_column(String(128))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ExternalCalendarEvent(Base):
    __tablename__ = "external_calendar_events"
    __table_args__ = (
        UniqueConstraint("connection_id", "assignment_id"),
        UniqueConstraint("connection_id", "google_event_id"),
        ForeignKeyConstraint(["connection_id"], ["google_calendar_connections.id"]),
        ForeignKeyConstraint(["club_id", "assignment_id"], ["assignments.club_id", "assignments.id"]),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    club_id: Mapped[str] = mapped_column(String(36), index=True)
    connection_id: Mapped[str] = mapped_column(String(36), index=True)
    assignment_id: Mapped[str] = mapped_column(String(36))
    google_event_id: Mapped[str] = mapped_column(String(1024))
    payload_hash: Mapped[str] = mapped_column(String(64))
    origin: Mapped[str] = mapped_column(String(16))
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class GoogleCalendarOutbox(Base):
    __tablename__ = "google_calendar_outbox"
    __table_args__ = (
        UniqueConstraint("connection_id", "assignment_id"),
        ForeignKeyConstraint(["connection_id"], ["google_calendar_connections.id"]),
        ForeignKeyConstraint(["club_id", "assignment_id"], ["assignments.club_id", "assignments.id"]),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    club_id: Mapped[str] = mapped_column(String(36), index=True)
    connection_id: Mapped[str] = mapped_column(String(36), index=True)
    assignment_id: Mapped[str] = mapped_column(String(36))
    status: Mapped[str] = mapped_column(String(16), default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)


class Exercise(Base):
    __tablename__ = "exercises"
    __table_args__ = (UniqueConstraint("club_id", "id"), ForeignKeyConstraint(["club_id"], ["clubs.id"]),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    club_id: Mapped[str] = mapped_column(String(36), index=True)
    name: Mapped[str] = mapped_column(String(160))
    instructions: Mapped[str] = mapped_column(String(2000), default="")
    measurement: Mapped[str] = mapped_column(String(32))
    reference: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)


class WorkoutTemplate(Base):
    __tablename__ = "workout_templates"
    __table_args__ = (ForeignKeyConstraint(["club_id", "coach_membership_id"], ["memberships.club_id", "memberships.id"]),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    club_id: Mapped[str] = mapped_column(String(36), index=True)
    coach_membership_id: Mapped[str] = mapped_column(String(36))
    prescription: Mapped[dict] = mapped_column(JSON)
    revisions: Mapped[list] = mapped_column(JSON, default=list)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)


class AccountAction(Base):
    __tablename__ = "account_actions"
    __table_args__ = (
        ForeignKeyConstraint(["user_id"], ["users.id"]),
        ForeignKeyConstraint(["membership_id"], ["memberships.id"]),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    membership_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    kind: Mapped[str] = mapped_column(String(16))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    encrypted_token: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
