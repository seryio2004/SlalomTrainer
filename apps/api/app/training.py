"""Session publishing and individual follow-up."""
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Header, HTTPException
from sqlalchemy import select

from .deps import ActorDep, Db, assignment_view, athlete_for_member, coach_can_see, membership, require_csrf, utc_iso
from .models import Assignment, Athlete, Club, CoachGroupGrant, Execution, Feedback, Membership, TrainingGroup, TrainingGroupMembership, WorkoutSession
from .metrics import fatigue_indicator
from .schemas import ReportIn, SessionIn

router = APIRouter()


@router.get("/api/v1/clubs/{club_id}/sessions")
def coach_sessions(club_id: str, actor: ActorDep, db: Db) -> list[dict]:
    coach = membership(db, actor, club_id, "coach")
    rows = db.scalars(select(WorkoutSession).where(WorkoutSession.club_id == club_id, WorkoutSession.coach_membership_id == coach.id).order_by(WorkoutSession.scheduled_start.desc())).all()
    return [{"id": row.id, "title": row.title, "scheduled_start": utc_iso(row.scheduled_start), "training_type": row.training_type, "venue": row.venue, "prescription": row.prescription, "group_name": db.get(TrainingGroup, row.group_id).name if row.group_id else None} for row in rows]


@router.post("/api/v1/clubs/{club_id}/sessions", status_code=201)
def create_session(club_id: str, data: SessionIn, actor: ActorDep, db: Db, x_csrf_token: Annotated[str | None, Header()] = None) -> dict:
    require_csrf(actor, x_csrf_token)
    coach = membership(db, actor, club_id, "coach")
    athlete_ids = set(data.athlete_ids)
    if len(athlete_ids) != len(data.athlete_ids):
        raise HTTPException(422, "Destinatarios duplicados")
    group = None
    if data.group_id:
        group = db.scalar(select(TrainingGroup).where(TrainingGroup.club_id == club_id, TrainingGroup.id == data.group_id, TrainingGroup.active.is_(True)))
        grant = db.scalar(select(CoachGroupGrant.id).where(CoachGroupGrant.club_id == club_id, CoachGroupGrant.group_id == data.group_id, CoachGroupGrant.coach_membership_id == coach.id))
        if not group or not grant:
            raise HTTPException(403, "No puedes asignar a este grupo")
        local_day = data.scheduled_start.astimezone(ZoneInfo(db.get(Club, club_id).timezone)).date()
        group_athletes = db.scalars(select(TrainingGroupMembership.athlete_id).where(
            TrainingGroupMembership.club_id == club_id,
            TrainingGroupMembership.group_id == group.id,
            TrainingGroupMembership.joined_on <= local_day,
            (TrainingGroupMembership.left_on.is_(None) | (TrainingGroupMembership.left_on >= local_day)),
        )).all()
        athlete_ids.update(group_athletes)
    if not athlete_ids:
        raise HTTPException(422, "Selecciona un grupo con deportistas o deportistas concretos")
    athletes = db.scalars(select(Athlete).where(Athlete.club_id == club_id, Athlete.id.in_(athlete_ids))).all()
    if len(athletes) != len(athlete_ids) or any(
        not db.get(Membership, a.membership_id).active or not coach_can_see(db, club_id, coach.id, a.id)
        for a in athletes
    ):
        raise HTTPException(403, "Hay destinatarios fuera de tu ámbito")
    prescription = {"title": data.title, "training_type": data.training_type, "venue": data.venue, "instructions": data.instructions, "steps": data.steps, "planned_minutes": data.planned_minutes}
    row = WorkoutSession(club_id=club_id, coach_membership_id=coach.id, group_id=group.id if group else None, title=data.title, training_type=data.training_type, venue=data.venue, scheduled_start=data.scheduled_start, planned_minutes=data.planned_minutes, prescription=prescription)
    db.add(row)
    db.flush()
    for athlete_id in athlete_ids:
        db.add(Assignment(club_id=club_id, session_id=row.id, athlete_id=athlete_id, prescription_snapshot=prescription.copy()))
    db.commit()
    return {"id": row.id, "assigned": len(athlete_ids), "group_id": row.group_id}


@router.get("/api/v1/clubs/{club_id}/assignments")
def my_assignments(club_id: str, actor: ActorDep, db: Db) -> list[dict]:
    member = membership(db, actor, club_id, "athlete")
    athlete = athlete_for_member(db, club_id, member.id)
    if not athlete:
        raise HTTPException(404, "Perfil deportivo no encontrado")
    rows = db.scalars(select(Assignment).where(Assignment.club_id == club_id, Assignment.athlete_id == athlete.id)).all()
    return [assignment_view(db, row) for row in rows]


@router.post("/api/v1/clubs/{club_id}/assignments/{assignment_id}/report")
def report(club_id: str, assignment_id: str, data: ReportIn, actor: ActorDep, db: Db, x_csrf_token: Annotated[str | None, Header()] = None) -> dict:
    require_csrf(actor, x_csrf_token)
    member = membership(db, actor, club_id, "athlete")
    athlete = athlete_for_member(db, club_id, member.id)
    row = db.scalar(select(Assignment).where(Assignment.club_id == club_id, Assignment.id == assignment_id).with_for_update())
    if not row or not athlete or row.athlete_id != athlete.id:
        raise HTTPException(404, "Asignación no encontrada")
    if row.status != "planned":
        execution = db.scalar(select(Execution).where(Execution.club_id == club_id, Execution.assignment_id == row.id))
        feedback = db.scalar(select(Feedback).where(Feedback.club_id == club_id, Feedback.assignment_id == row.id))
        if execution and feedback and (
            row.status == data.status and execution.actual_minutes == data.actual_minutes
            and feedback.rpe == data.rpe and feedback.feeling == data.feeling
            and feedback.has_pain == data.has_pain and feedback.pain_area == data.pain_area
            and feedback.comment == data.comment
            and feedback.sensations == data.sensations and feedback.work_done == data.work_done
            and feedback.best == data.best and feedback.worst == data.worst
        ):
            return assignment_view(db, row)
        raise HTTPException(409, "El registro ya se envió con otros datos")
    session = db.get(WorkoutSession, row.session_id)
    if session.training_type == "water" and data.status in ("completed", "partial"):
        if not all((getattr(data, field) or "").strip() for field in ("sensations", "work_done", "best", "worst")):
            raise HTTPException(422, "En agua indica sensaciones, trabajo realizado, lo mejor y lo peor")
    if data.status == "skipped" and (data.actual_minutes is not None or data.rpe is not None):
        raise HTTPException(422, "Una sesión omitida no tiene duración ni RPE")
    if data.has_pain is False and data.pain_area:
        raise HTTPException(422, "Indica molestias para guardar la zona")
    row.status = data.status
    row.version += 1
    db.add(Execution(club_id=club_id, assignment_id=row.id, actual_minutes=data.actual_minutes, notes=data.comment))
    db.add(Feedback(club_id=club_id, assignment_id=row.id, rpe=data.rpe, feeling=data.feeling, has_pain=data.has_pain, pain_area=data.pain_area, comment=data.comment, sensations=data.sensations, work_done=data.work_done, best=data.best, worst=data.worst))
    db.commit()
    return assignment_view(db, row)


@router.get("/api/v1/clubs/{club_id}/sessions/{session_id}/summary")
def summary(club_id: str, session_id: str, actor: ActorDep, db: Db) -> dict:
    coach = membership(db, actor, club_id, "coach")
    session = db.scalar(select(WorkoutSession).where(WorkoutSession.club_id == club_id, WorkoutSession.id == session_id))
    if not session:
        raise HTTPException(404, "Sesión no encontrada")
    rows = db.scalars(select(Assignment).where(Assignment.club_id == club_id, Assignment.session_id == session_id)).all()
    if any(not coach_can_see(db, club_id, coach.id, row.athlete_id) for row in rows):
        raise HTTPException(403, "Hay deportistas fuera de tu ámbito")
    detail = [assignment_view(db, row) for row in rows]
    counts = {state: sum(item["status"] == state for item in detail) for state in ("planned", "completed", "partial", "skipped")}
    loads = [item["load"] for item in detail if item["load"] is not None]
    return {"id": session.id, "title": session.title, "group_name": db.get(TrainingGroup, session.group_id).name if session.group_id else None, "venue": session.venue, "counts": counts, "known_load": sum(loads), "load_coverage": len(loads), "assignments": detail}


@router.get("/api/v1/clubs/{club_id}/dashboard/athlete")
def my_dashboard(club_id: str, actor: ActorDep, db: Db) -> dict:
    member = membership(db, actor, club_id, "athlete")
    athlete = athlete_for_member(db, club_id, member.id)
    if not athlete:
        raise HTTPException(404, "Perfil deportivo no encontrado")
    return athlete_dashboard(db, club_id, athlete)


@router.get("/api/v1/clubs/{club_id}/athletes/{athlete_id}/dashboard")
def coach_athlete_dashboard(club_id: str, athlete_id: str, actor: ActorDep, db: Db) -> dict:
    coach = membership(db, actor, club_id, "coach")
    athlete = db.scalar(select(Athlete).where(Athlete.club_id == club_id, Athlete.id == athlete_id))
    if not athlete or not coach_can_see(db, club_id, coach.id, athlete.id):
        raise HTTPException(404, "Deportista no encontrado")
    return athlete_dashboard(db, club_id, athlete)


def athlete_dashboard(db, club_id: str, athlete: Athlete) -> dict:
    from .models import User
    member = db.get(Membership, athlete.membership_id)
    user = db.get(User, member.user_id)
    assignments = db.scalars(select(Assignment).where(Assignment.club_id == club_id, Assignment.athlete_id == athlete.id)).all()
    return {
        "athlete_id": athlete.id,
        "name": user.name,
        "assignments": [assignment_view(db, row) for row in assignments],
        "fatigue": fatigue_indicator(db, club_id, athlete.id),
    }
