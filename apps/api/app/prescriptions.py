"""Club exercise catalogue, coach-owned templates and individual adaptations."""
from copy import deepcopy
from typing import Annotated, Literal
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, update
from .audit import commit, record
from .deps import ActorDep, Db, coach_can_see, membership, require_csrf, utc_iso
from .models import Assignment, Execution, Exercise, WorkoutSession, WorkoutTemplate, utc_now
from .schemas import SessionIn

router = APIRouter(prefix="/api/v1/clubs/{club_id}")


class ExerciseIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=160)
    instructions: str = Field(default="", max_length=2000)
    measurement: Literal["repetitions", "time", "distance", "other"] = "repetitions"
    reference: bool = False
    active: bool = True
    version: int = Field(default=0, ge=0)


class TemplateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prescription: SessionIn
    version: int = Field(default=0, ge=0)
    active: bool = True


class AdaptationIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    version: int = Field(ge=1)
    reason: str = Field(min_length=1, max_length=500)
    prescription: SessionIn


def content(data: SessionIn):
    return data.model_dump(mode="json", include={"title", "training_type", "venue", "planned_minutes", "instructions", "steps", "objective", "blocks", "details"})


def validate_exercises(db, club_id, blocks):
    ids = {item.exercise_id for block in blocks for item in block.exercises if item.exercise_id}
    if ids:
        found = db.scalars(select(Exercise.id).where(Exercise.club_id == club_id, Exercise.id.in_(ids))).all()
        if set(found) != ids:
            raise HTTPException(422, "Hay ejercicios fuera del catálogo del club")


@router.get("/exercises")
def exercises(club_id: str, actor: ActorDep, db: Db):
    membership(db, actor, club_id, "coach")
    return [{"id": r.id, "name": r.name, "instructions": r.instructions, "measurement": r.measurement,
             "reference": r.reference, "active": r.active, "version": r.version}
            for r in db.scalars(select(Exercise).where(Exercise.club_id == club_id).order_by(Exercise.name))]


@router.post("/exercises", status_code=201)
def create_exercise(club_id: str, data: ExerciseIn, actor: ActorDep, db: Db, x_csrf_token: Annotated[str | None, Header()] = None):
    require_csrf(actor, x_csrf_token)
    membership(db, actor, club_id, "coach")
    row = Exercise(club_id=club_id, **data.model_dump(exclude={"version"}))
    db.add(row); db.flush()
    record(db, actor, club_id, "exercise.created", row.id)
    commit(db)
    return {"id": row.id, "version": row.version}


@router.put("/exercises/{exercise_id}")
def edit_exercise(club_id: str, exercise_id: str, data: ExerciseIn, actor: ActorDep, db: Db, x_csrf_token: Annotated[str | None, Header()] = None):
    require_csrf(actor, x_csrf_token)
    membership(db, actor, club_id, "coach")
    result = db.execute(update(Exercise).where(Exercise.id == exercise_id, Exercise.club_id == club_id, Exercise.version == data.version).values(**data.model_dump(exclude={"version"}), version=data.version + 1))
    if result.rowcount != 1:
        raise HTTPException(409, "Ejercicio inexistente o modificado; recarga el catálogo")
    record(db, actor, club_id, "exercise.updated", exercise_id)
    commit(db)
    return {"id": exercise_id, "version": data.version + 1}


@router.get("/templates")
def templates(club_id: str, actor: ActorDep, db: Db):
    coach = membership(db, actor, club_id, "coach")
    return [{"id": r.id, "prescription": r.prescription, "version": r.version, "active": r.active, "revisions": r.revisions}
            for r in db.scalars(select(WorkoutTemplate).where(WorkoutTemplate.club_id == club_id, WorkoutTemplate.coach_membership_id == coach.id))]


@router.post("/templates", status_code=201)
def create_template(club_id: str, data: TemplateIn, actor: ActorDep, db: Db, x_csrf_token: Annotated[str | None, Header()] = None):
    require_csrf(actor, x_csrf_token)
    coach = membership(db, actor, club_id, "coach")
    validate_exercises(db, club_id, data.prescription.blocks)
    row = WorkoutTemplate(club_id=club_id, coach_membership_id=coach.id, prescription=content(data.prescription), active=data.active)
    db.add(row); db.flush()
    record(db, actor, club_id, "template.created", row.id)
    commit(db)
    return {"id": row.id, "version": row.version}


@router.put("/templates/{template_id}")
def revise_template(club_id: str, template_id: str, data: TemplateIn, actor: ActorDep, db: Db, x_csrf_token: Annotated[str | None, Header()] = None):
    require_csrf(actor, x_csrf_token)
    coach = membership(db, actor, club_id, "coach")
    row = db.scalar(select(WorkoutTemplate).where(WorkoutTemplate.id == template_id, WorkoutTemplate.club_id == club_id, WorkoutTemplate.coach_membership_id == coach.id))
    if not row:
        raise HTTPException(404, "Plantilla no encontrada")
    validate_exercises(db, club_id, data.prescription.blocks)
    revision = {"version": row.version, "prescription": row.prescription, "author": actor.user.id, "at": utc_iso(utc_now())}
    result = db.execute(update(WorkoutTemplate).where(WorkoutTemplate.id == row.id, WorkoutTemplate.version == data.version).values(prescription=content(data.prescription), version=data.version + 1, active=data.active, revisions=[*row.revisions, revision]))
    if result.rowcount != 1:
        raise HTTPException(409, "La plantilla cambió; recarga antes de guardar")
    record(db, actor, club_id, "template.revised", row.id)
    commit(db)
    return {"id": row.id, "version": data.version + 1}


@router.put("/assignments/{assignment_id}/prescription")
def adapt(club_id: str, assignment_id: str, data: AdaptationIn, actor: ActorDep, db: Db, x_csrf_token: Annotated[str | None, Header()] = None):
    require_csrf(actor, x_csrf_token)
    coach = membership(db, actor, club_id, "coach")
    row = db.scalar(select(Assignment).where(Assignment.id == assignment_id, Assignment.club_id == club_id).with_for_update())
    if not row or not coach_can_see(db, club_id, coach.id, row.athlete_id):
        raise HTTPException(404, "Asignación no encontrada")
    session = db.get(WorkoutSession, row.session_id)
    if session.coach_membership_id != coach.id:
        raise HTTPException(403, "Solo el entrenador responsable puede adaptar la sesión")
    if row.status != "planned" or db.scalar(select(Execution.id).where(Execution.assignment_id == row.id)):
        raise HTTPException(409, "No puedes adaptar una ejecución iniciada")
    if session.scheduled_start.replace(tzinfo=utc_now().tzinfo) <= utc_now():
        raise HTTPException(409, "Solo puedes adaptar sesiones futuras")
    validate_exercises(db, club_id, data.prescription.blocks)
    previous = {"version": row.version, "prescription": deepcopy(row.prescription_snapshot), "author": actor.user.id, "at": utc_iso(utc_now()), "reason": data.reason}
    # Schedule and session identity remain common. Adapt only the prescription.
    value = {**row.prescription_snapshot, **content(data.prescription)}
    result = db.execute(update(Assignment).where(Assignment.id == row.id, Assignment.version == data.version).values(prescription_snapshot=value, prescription_revisions=[*row.prescription_revisions, previous], version=data.version + 1))
    if result.rowcount != 1:
        raise HTTPException(409, "La asignación cambió; recarga antes de adaptar")
    from .google_calendar_sync import queue_changed_assignments
    queue_changed_assignments(db, [row])
    record(db, actor, club_id, "prescription.adapted", row.id)
    commit(db)
    from .deps import assignment_view
    return assignment_view(db, row)
