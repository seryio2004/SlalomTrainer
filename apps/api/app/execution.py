"""Atomic draft/submission/correction of individual execution and feedback."""
from datetime import datetime
from typing import Annotated
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Header, HTTPException
from sqlalchemy import select, update
from .audit import commit, record
from .deps import ActorDep, Db, assignment_view, athlete_for_member, membership, require_csrf, utc_iso
from .models import Assignment, Club, Execution, Exercise, Feedback, WorkoutSession, utc_now
from .schemas import ExecutionReportIn

router = APIRouter(prefix="/api/v1/clubs/{club_id}/assignments")
FEEDBACK = ("rpe", "feeling", "has_pain", "pain_area", "comment", "sensations", "work_done", "best", "worst")


def payload(data):
    return data.model_dump(mode="json", exclude={"version", "reason"})


def validate_report(db, club_id, row, data, draft):
    today = datetime.now(ZoneInfo(db.get(Club, club_id).timezone)).date()
    if data.actual_date and data.actual_date > today:
        raise HTTPException(422, "La fecha de realización no puede ser futura")
    kind = row.prescription_snapshot.get("training_type", db.get(WorkoutSession, row.session_id).training_type)
    if not draft and kind == "water" and data.status in ("completed", "partial"):
        if not all((getattr(data, field) or "").strip() for field in ("sensations", "work_done", "best", "worst")):
            raise HTTPException(422, "En agua indica sensaciones, trabajo realizado, lo mejor y lo peor")
    if (data.status == "skipped" or kind == "rest") and (data.actual_minutes is not None or data.rpe is not None or data.results or data.discipline):
        raise HTTPException(422, "Una omisión o descanso no lleva duración activa, RPE ni resultados")
    if not data.has_pain and (data.pain_area or data.pain_intensity is not None):
        raise HTTPException(422, "Indica molestias para guardar zona o intensidad")
    items = {item["id"]: item for block in row.prescription_snapshot.get("blocks", []) for item in block["exercises"]}
    keys = set()
    for result in data.results:
        key = (result.item_id or result.name, result.set_number, result.side)
        if key in keys:
            raise HTTPException(422, "Hay series duplicadas")
        keys.add(key)
        if result.origin == "prescribed":
            target = items.get(result.item_id)
            if not target or result.name != target["name"] or result.exercise_id != target.get("exercise_id"):
                raise HTTPException(422, "El resultado no corresponde a la prescripción efectiva")
        if result.exercise_id and not db.scalar(select(Exercise.id).where(Exercise.id == result.exercise_id, Exercise.club_id == club_id)):
            raise HTTPException(422, "Ejercicio fuera del catálogo del club")
    return data.actual_date


def save(club_id, assignment_id, data, actor, db, csrf, mode):
    require_csrf(actor, csrf)
    member = membership(db, actor, club_id, "athlete")
    athlete = athlete_for_member(db, club_id, member.id)
    row = db.scalar(select(Assignment).where(Assignment.club_id == club_id, Assignment.id == assignment_id).with_for_update())
    if not row or not athlete or row.athlete_id != athlete.id:
        raise HTTPException(404, "Asignación no encontrada")
    if row.status in ("cancelled", "replaced"):
        raise HTTPException(409, "La asignación está cancelada o sustituida")
    execution = db.scalar(select(Execution).where(Execution.club_id == club_id, Execution.assignment_id == row.id))
    feedback = db.scalar(select(Feedback).where(Feedback.club_id == club_id, Feedback.assignment_id == row.id))
    value = payload(data)
    if mode == "submit" and execution and execution.state == "submitted":
        # A successful response may be lost: the identical retry is safe even with an old version.
        legacy_same = not execution.data and feedback and row.status == data.status and execution.actual_minutes == data.actual_minutes and all(getattr(feedback, key) == getattr(data, key) for key in FEEDBACK) and not data.results and not data.discipline and data.actual_date is None
        if execution.data == value or legacy_same:
            return assignment_view(db, row)
        raise HTTPException(409, "El registro ya se envió; usa la corrección con motivo")
    if mode == "correct" and (not execution or execution.state != "submitted" or not data.reason.strip()):
        raise HTTPException(422, "La corrección necesita un registro enviado y un motivo")
    if mode == "draft" and execution and execution.state == "submitted":
        raise HTTPException(409, "No puedes convertir un registro enviado en borrador")
    if data.version != row.version:
        raise HTTPException(409, "La asignación cambió; recarga antes de guardar")
    actual_date = validate_report(db, club_id, row, data, mode == "draft")
    previous_status = row.status
    current_version = row.version
    result = db.execute(update(Assignment).where(Assignment.id == row.id, Assignment.version == current_version).values(version=current_version + 1, status="planned" if mode == "draft" else data.status))
    if result.rowcount != 1:
        raise HTTPException(409, "La asignación cambió; recarga antes de guardar")
    if not execution:
        execution = Execution(club_id=club_id, assignment_id=row.id, revisions=[])
        db.add(execution)
    elif mode == "correct":
        previous = execution.data or {"status": previous_status, "actual_minutes": execution.actual_minutes, **{key: getattr(feedback, key) for key in FEEDBACK}}
        execution.revisions = [*execution.revisions, {"data": previous, "actual_date": execution.actual_date.isoformat() if execution.actual_date else None, "version": current_version, "author": actor.user.id, "at": utc_iso(utc_now()), "reason": data.reason}]
    execution.data = value
    execution.actual_minutes = data.actual_minutes
    execution.actual_date = actual_date
    execution.notes = data.comment
    execution.state = "draft" if mode == "draft" else "submitted"
    execution.submitted_at = utc_now()
    if mode != "draft":
        if not feedback:
            feedback = Feedback(club_id=club_id, assignment_id=row.id)
            db.add(feedback)
        for key in FEEDBACK:
            setattr(feedback, key, getattr(data, key))
    record(db, actor, club_id, f"execution.{mode}", row.id)
    commit(db)
    return assignment_view(db, row)


@router.post("/{assignment_id}/report")
def report(club_id: str, assignment_id: str, data: ExecutionReportIn, actor: ActorDep, db: Db, x_csrf_token: Annotated[str | None, Header()] = None):
    return save(club_id, assignment_id, data, actor, db, x_csrf_token, "submit")


@router.put("/{assignment_id}/draft")
def draft(club_id: str, assignment_id: str, data: ExecutionReportIn, actor: ActorDep, db: Db, x_csrf_token: Annotated[str | None, Header()] = None):
    return save(club_id, assignment_id, data, actor, db, x_csrf_token, "draft")


@router.patch("/{assignment_id}/report")
def correct(club_id: str, assignment_id: str, data: ExecutionReportIn, actor: ActorDep, db: Db, x_csrf_token: Annotated[str | None, Header()] = None):
    return save(club_id, assignment_id, data, actor, db, x_csrf_token, "correct")
