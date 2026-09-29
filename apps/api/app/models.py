from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKeyConstraint, Integer, JSON, String, UniqueConstraint
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
        UniqueConstraint("club_id", "group_id", "athlete_id"),
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
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    club_id: Mapped[str] = mapped_column(String(36), index=True)
    coach_membership_id: Mapped[str] = mapped_column(String(36))
    group_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
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
