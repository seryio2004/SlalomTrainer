"""Shared request dependencies and authorized projections."""
import hmac
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_db
from .models import Assignment, Athlete, AuthSession, Club, CoachAthleteGrant, CoachGroupGrant, Execution, Feedback, Membership, TrainingGroup, TrainingGroupMembership, User, WorkoutSession, utc_now
from .security import secret_hash

Db = Annotated[Session, Depends(get_db)]


class Actor:
    def __init__(self, user: User, auth: AuthSession, csrf_cookie: str | None):
        self.user = user
        self.auth = auth
        self.csrf_cookie = csrf_cookie


def current_actor(
    db: Db,
    tei_session: Annotated[str | None, Cookie()] = None,
    tei_csrf: Annotated[str | None, Cookie()] = None,
) -> Actor:
    if not tei_session:
        raise HTTPException(401, "Inicia sesión")
    auth = db.scalar(select(AuthSession).where(AuthSession.token_hash == secret_hash(tei_session)))
    if not auth or auth.revoked_at or auth.expires_at.replace(tzinfo=timezone.utc) <= utc_now():
        raise HTTPException(401, "Sesión caducada")
    user = db.get(User, auth.user_id)
    if not user or not user.active:
        raise HTTPException(401, "Cuenta desactivada")
    return Actor(user, auth, tei_csrf)


ActorDep = Annotated[Actor, Depends(current_actor)]


def require_csrf(actor: Actor, token: str | None) -> None:
    if not token or not actor.csrf_cookie or not hmac.compare_digest(token, actor.csrf_cookie):
        raise HTTPException(403, "Token de formulario inválido")
    if not hmac.compare_digest(secret_hash(token), actor.auth.csrf_hash):
        raise HTTPException(403, "Token de formulario inválido")


def membership(db: Session, actor: Actor, club_id: str, role: str | None = None) -> Membership:
    member = db.scalar(select(Membership).where(Membership.club_id == club_id, Membership.user_id == actor.user.id, Membership.active.is_(True)))
    if not member or (role and role not in member.roles):
        raise HTTPException(403, "Sin permiso en este club")
    return member


def athlete_for_member(db: Session, club_id: str, member_id: str) -> Athlete | None:
    return db.scalar(select(Athlete).where(Athlete.club_id == club_id, Athlete.membership_id == member_id))


def coach_can_see(db: Session, club_id: str, coach_member_id: str, athlete_id: str) -> bool:
    direct = db.scalar(select(CoachAthleteGrant.id).where(
        CoachAthleteGrant.club_id == club_id,
        CoachAthleteGrant.coach_membership_id == coach_member_id,
        CoachAthleteGrant.athlete_id == athlete_id,
    ))
    if direct is not None:
        return True
    club = db.get(Club, club_id)
    today = datetime.now(ZoneInfo(club.timezone)).date()
    group = db.scalar(select(TrainingGroupMembership.id).join(
        TrainingGroup,
        (TrainingGroup.club_id == TrainingGroupMembership.club_id)
        & (TrainingGroup.id == TrainingGroupMembership.group_id),
    ).join(
        CoachGroupGrant,
        (CoachGroupGrant.club_id == TrainingGroupMembership.club_id)
        & (CoachGroupGrant.group_id == TrainingGroupMembership.group_id),
    ).where(
        TrainingGroupMembership.club_id == club_id,
        TrainingGroupMembership.athlete_id == athlete_id,
        TrainingGroup.active.is_(True),
        TrainingGroupMembership.joined_on <= today,
        (TrainingGroupMembership.left_on.is_(None) | (TrainingGroupMembership.left_on > today)),
        CoachGroupGrant.coach_membership_id == coach_member_id,
    ))
    return group is not None


def utc_iso(value: datetime) -> str:
    """SQLite drops timezone information; persisted session instants are UTC."""
    return (value if value.tzinfo else value.replace(tzinfo=timezone.utc)).isoformat()


def assignment_view(db: Session, assignment: Assignment) -> dict:
    session = db.get(WorkoutSession, assignment.session_id)
    execution = db.scalar(select(Execution).where(Execution.club_id == assignment.club_id, Execution.assignment_id == assignment.id))
    feedback = db.scalar(select(Feedback).where(Feedback.club_id == assignment.club_id, Feedback.assignment_id == assignment.id))
    load = None
    if assignment.status in ("completed", "partial") and assignment.prescription_snapshot.get("training_type", session.training_type) != "rest" and execution and execution.state == "submitted" and feedback and execution.actual_minutes is not None and feedback.rpe is not None:
        load = execution.actual_minutes * feedback.rpe
    return {
        "id": assignment.id, "athlete_id": assignment.athlete_id,
        "session_id": assignment.session_id, "status": assignment.status,
        "plan_day_id": session.plan_day_id,
        "title": assignment.prescription_snapshot.get("title", session.title), "training_type": assignment.prescription_snapshot.get("training_type", session.training_type), "venue": assignment.prescription_snapshot.get("venue", session.venue),
        "scheduled_start": utc_iso(session.scheduled_start), "planned_minutes": assignment.prescription_snapshot.get("planned_minutes", session.planned_minutes),
        "prescription": assignment.prescription_snapshot,
        "version": assignment.version,
        "original_prescription": assignment.prescription_revisions[0]["prescription"] if assignment.prescription_revisions else assignment.prescription_snapshot,
        "prescription_revisions": assignment.prescription_revisions,
        "execution_state": execution.state if execution else None,
        "actual_date": execution.actual_date.isoformat() if execution and execution.actual_date else None,
        "execution_data": execution.data if execution else None,
        "execution_revisions": execution.revisions if execution else [],
        "actual_minutes": execution.actual_minutes if execution else None,
        "rpe": feedback.rpe if feedback else None,
        "feeling": feedback.feeling if feedback else None,
        "has_pain": feedback.has_pain if feedback else None,
        "pain_area": feedback.pain_area if feedback else None,
        "comment": feedback.comment if feedback else None,
        "water_feedback": {
            "sensations": feedback.sensations,
            "work_done": feedback.work_done,
            "best": feedback.best,
            "worst": feedback.worst,
        } if feedback and session.training_type == "water" else None,
        "load": load,
    }


