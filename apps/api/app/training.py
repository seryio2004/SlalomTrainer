"""Session publishing and individual follow-up."""
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Header, HTTPException
from sqlalchemy import select

from .deps import ActorDep, Db, assignment_view, athlete_for_member, coach_can_see, membership, require_csrf, utc_iso
from .models import Assignment, Athlete, Club, CoachGroupGrant, Execution, Feedback, Membership, TrainingGroup, TrainingGroupMembership, WorkoutSession
from .metrics import fatigue_indicator
from .planning import validate_session_day
from .audit import record
from .google_calendar_sync import queue_changed_assignments, queue_new_assignments
from .schemas import ReportIn, SessionCancelIn, SessionEditIn, SessionIn

router = APIRouter()


@router.get("/api/v1/clubs/{club_id}/sessions")
def coach_sessions(club_id: str, actor: ActorDep, db: Db) -> list[dict]:
    coach = membership(db, actor, club_id, "coach")
    rows = db.scalars(select(WorkoutSession).where(WorkoutSession.club_id == club_id, WorkoutSession.coach_membership_id == coach.id).order_by(WorkoutSession.scheduled_start.desc())).all()
    return [{
        "id": row.id,
        "plan_day_id": row.plan_day_id,
        "title": row.title,
        "scheduled_start": utc_iso(row.scheduled_start),
        "training_type": row.training_type,
        "venue": row.venue,
        "planned_minutes": row.planned_minutes,
        "prescription": row.prescription,
        "group_name": db.get(TrainingGroup, row.group_id).name if row.group_id else None,
        "status": row.status,
        "version": row.version,
    } for row in rows]


def resolve_recipients(db, club_id, coach, data):
    if data.plan_day_id:
        validate_session_day(db, club_id, coach.id, data.plan_day_id, data.scheduled_start)
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
            (TrainingGroupMembership.left_on.is_(None) | (TrainingGroupMembership.left_on > local_day)),
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
    return athletes, group


@router.post("/api/v1/clubs/{club_id}/sessions/preview")
def preview_session(
    club_id: str, data: SessionIn, actor: ActorDep, db: Db,
    x_csrf_token: Annotated[str | None, Header()] = None,
):
    require_csrf(actor, x_csrf_token)
    coach = membership(db, actor, club_id, "coach")
    athletes, _ = resolve_recipients(db, club_id, coach, data)
    from .models import User
    return {
        "athletes": [{
            "id": athlete.id,
            "name": db.get(User, db.get(Membership, athlete.membership_id).user_id).name,
        } for athlete in athletes],
    }


@router.post("/api/v1/clubs/{club_id}/sessions", status_code=201)
def create_session(club_id: str, data: SessionIn, actor: ActorDep, db: Db, x_csrf_token: Annotated[str | None, Header()] = None) -> dict:
    require_csrf(actor, x_csrf_token)
    coach = membership(db, actor, club_id, "coach")
    from .prescriptions import validate_exercises
    validate_exercises(db, club_id, data.blocks)
    athletes, group = resolve_recipients(db, club_id, coach, data)
    athlete_ids = {athlete.id for athlete in athletes}
    if data.preview_athlete_ids is not None and set(data.preview_athlete_ids) != athlete_ids:
        raise HTTPException(409, "Los destinatarios han cambiado; vuelve a previsualizar")
    prescription = {"title": data.title, "training_type": data.training_type, "venue": data.venue, "instructions": data.instructions, "steps": data.steps, "planned_minutes": data.planned_minutes, "details": data.details.model_dump() if data.details else None, "objective": data.objective, "blocks": [block.model_dump() for block in data.blocks]}
    row = WorkoutSession(plan_day_id=data.plan_day_id, club_id=club_id, coach_membership_id=coach.id, group_id=group.id if group else None, title=data.title, training_type=data.training_type, venue=data.venue, scheduled_start=data.scheduled_start, planned_minutes=data.planned_minutes, prescription=prescription)
    db.add(row)
    db.flush()
    assignments = []
    for athlete_id in athlete_ids:
        assignment = Assignment(
            club_id=club_id, session_id=row.id, athlete_id=athlete_id,
            prescription_snapshot={**prescription, "context": {"group_ids": db.scalars(select(TrainingGroupMembership.group_id).where(
                TrainingGroupMembership.club_id == club_id, TrainingGroupMembership.athlete_id == athlete_id,
                TrainingGroupMembership.joined_on <= data.scheduled_start.astimezone(ZoneInfo(db.get(Club, club_id).timezone)).date(),
                (TrainingGroupMembership.left_on.is_(None) | (TrainingGroupMembership.left_on > data.scheduled_start.astimezone(ZoneInfo(db.get(Club, club_id).timezone)).date())),
            )).all() }},
        )
        db.add(assignment)
        assignments.append(assignment)
    db.flush()
    queue_new_assignments(db, assignments)
    record(db, actor, club_id, "session.published", row.id)
    db.commit()
    return {"id": row.id, "assigned": len(athlete_ids), "group_id": row.group_id}


def editable_session(db: Db, club_id: str, session_id: str, coach_id: str, version: int, allow_adaptations: bool = False):
    row = db.scalar(select(WorkoutSession).where(
        WorkoutSession.club_id == club_id,
        WorkoutSession.id == session_id,
        WorkoutSession.coach_membership_id == coach_id,
    ).with_for_update())
    if row is None:
        raise HTTPException(404, "Sesión no encontrada")
    if row.version != version:
        raise HTTPException(409, "La sesión cambió; recarga antes de continuar")
    if row.status != "planned":
        raise HTTPException(409, "La sesión ya está cancelada")
    assignments = db.scalars(select(Assignment).where(
        Assignment.club_id == club_id,
        Assignment.session_id == row.id,
    ).with_for_update()).all()
    if any(assignment.status != "planned" or (not allow_adaptations and any(revision.get("kind", "adaptation") == "adaptation" for revision in assignment.prescription_revisions)) or db.scalar(select(Execution.id).where(Execution.assignment_id == assignment.id)) for assignment in assignments):
        raise HTTPException(409, "La sesión tiene ejecuciones iniciadas o adaptaciones que debes revisar")
    return row, assignments


@router.patch("/api/v1/clubs/{club_id}/sessions/{session_id}")
def edit_session(
    club_id: str, session_id: str, data: SessionEditIn,
    actor: ActorDep, db: Db, x_csrf_token: Annotated[str | None, Header()] = None,
) -> dict:
    require_csrf(actor, x_csrf_token)
    coach = membership(db, actor, club_id, "coach")
    row, assignments = editable_session(db, club_id, session_id, coach.id, data.version)
    from .prescriptions import validate_exercises
    validate_exercises(db, club_id, data.blocks)
    if row.plan_day_id:
        validate_session_day(db, club_id, coach.id, row.plan_day_id, data.scheduled_start)
    prescription = {
        "title": data.title,
        "training_type": data.training_type,
        "venue": data.venue,
        "instructions": data.instructions,
        "steps": data.steps,
        "planned_minutes": data.planned_minutes,
        "details": data.details.model_dump() if data.details else None,
        "objective": data.objective,
        "blocks": [block.model_dump() for block in data.blocks],
    }
    row.title = data.title
    row.training_type = data.training_type
    row.venue = data.venue
    row.scheduled_start = data.scheduled_start
    row.planned_minutes = data.planned_minutes
    row.prescription = prescription
    row.version += 1
    for assignment in assignments:
        source = {
            key: value for key, value in assignment.prescription_snapshot.items()
            if key in ("source", "source_event_id", "context")
        }
        from .models import utc_now
        assignment.prescription_revisions = [*assignment.prescription_revisions, {
            "version": assignment.version, "prescription": assignment.prescription_snapshot,
            "author": actor.user.id, "at": utc_iso(utc_now()), "reason": "Revisión de la sesión común", "kind": "common",
        }]
        assignment.prescription_snapshot = {**prescription, **source}
        assignment.version += 1
    queue_changed_assignments(db, assignments)
    record(db, actor, club_id, "session.updated", row.id)
    db.commit()
    return {"id": row.id, "version": row.version}


@router.post("/api/v1/clubs/{club_id}/sessions/{session_id}/cancel")
def cancel_session(
    club_id: str, session_id: str, data: SessionCancelIn,
    actor: ActorDep, db: Db, x_csrf_token: Annotated[str | None, Header()] = None,
) -> dict:
    require_csrf(actor, x_csrf_token)
    coach = membership(db, actor, club_id, "coach")
    row, assignments = editable_session(db, club_id, session_id, coach.id, data.version, allow_adaptations=True)
    row.status = "cancelled"
    row.version += 1
    for assignment in assignments:
        assignment.status = "cancelled"
        assignment.version += 1
    queue_changed_assignments(db, assignments)
    record(db, actor, club_id, "session.cancelled", row.id)
    db.commit()
    return {"id": row.id, "status": row.status, "version": row.version}


@router.get("/api/v1/clubs/{club_id}/assignments")
def my_assignments(club_id: str, actor: ActorDep, db: Db) -> list[dict]:
    member = membership(db, actor, club_id, "athlete")
    athlete = athlete_for_member(db, club_id, member.id)
    if not athlete:
        raise HTTPException(404, "Perfil deportivo no encontrado")
    rows = db.scalars(select(Assignment).where(Assignment.club_id == club_id, Assignment.athlete_id == athlete.id)).all()
    return [assignment_view(db, row) for row in rows]


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
    counts = {state: sum(item["status"] == state for item in detail) for state in ("planned", "completed", "partial", "skipped", "cancelled")}
    loads = [item["load"] for item in detail if item["load"] is not None]
    return {"id": session.id, "title": session.title, "group_name": db.get(TrainingGroup, session.group_id).name if session.group_id else None, "venue": session.venue, "counts": counts, "known_load": sum(loads) if loads else None, "load_coverage": len(loads), "assigned": len(detail), "mean_rpe": sum(item["rpe"] for item in detail if item["rpe"] is not None) / sum(item["rpe"] is not None for item in detail) if any(item["rpe"] is not None for item in detail) else None, "rpe_sample": sum(item["rpe"] is not None for item in detail), "pain_count": sum(item["has_pain"] is True for item in detail), "without_feedback": sum(item["execution_state"] != "submitted" for item in detail), "assignments": detail}


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
