"""Club seasons and coach-owned planning, with bounded dates at every level."""
from datetime import date
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select

from .audit import commit, record
from .deps import ActorDep, Db, membership, require_csrf
from .models import Club, Microcycle, PlanDay, Season, TrainingPhase, TrainingPlan

router = APIRouter(prefix="/api/v1/clubs/{club_id}/planning")
Csrf = Annotated[str | None, Header()]


class PeriodIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    name: str = Field(min_length=1, max_length=160)
    starts_on: date
    ends_on: date
    objectives: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def check_dates(self):
        if self.ends_on < self.starts_on:
            raise ValueError("La fecha final debe ser posterior o igual a la inicial")
        return self


class SeasonIn(PeriodIn):
    age_reference_date: date
    status: Literal["draft", "active"] = "draft"


class SeasonStatusIn(BaseModel):
    status: Literal["active", "closed"]


class PhaseIn(PeriodIn):
    season_id: str


class PlanIn(PeriodIn):
    phase_id: str


class MicrocycleIn(PeriodIn):
    plan_id: str


class DayIn(BaseModel):
    microcycle_id: str
    local_date: date


def get_row(db, model, club_id, row_id):
    row = db.scalar(select(model).where(model.club_id == club_id, model.id == row_id))
    if not row:
        raise HTTPException(404, "Elemento de planificación no encontrado")
    return row


def assert_open(season):
    if season.status == "closed":
        raise HTTPException(409, "La temporada está cerrada; su planificación es de consulta")


def assert_period(parent, data):
    if not parent.starts_on <= data.starts_on <= data.ends_on <= parent.ends_on:
        raise HTTPException(422, "Las fechas deben quedar dentro del período superior")


def authorized_plan(db, club_id, plan_id, coach_id):
    plan = get_row(db, TrainingPlan, club_id, plan_id)
    if plan.coach_membership_id != coach_id:
        raise HTTPException(404, "Plan no encontrado")
    phase = get_row(db, TrainingPhase, club_id, plan.phase_id)
    assert_open(get_row(db, Season, club_id, phase.season_id))
    if plan.status == "archived":
        raise HTTPException(409, "El plan está archivado")
    return plan


def validate_session_day(db, club_id, coach_id, day_id, scheduled_start):
    day = get_row(db, PlanDay, club_id, day_id)
    cycle = get_row(db, Microcycle, club_id, day.microcycle_id)
    plan = authorized_plan(db, club_id, cycle.plan_id, coach_id)
    club = db.get(Club, club_id)
    if scheduled_start.astimezone(ZoneInfo(club.timezone)).date() != day.local_date:
        raise HTTPException(422, "La sesión debe celebrarse en la fecha del día de plan elegido")
    return day, plan


def view(row):
    return {
        column.name: getattr(row, column.name)
        for column in row.__table__.columns
    }


def save_new(db, actor, club_id, row, action):
    db.add(row)
    # Explicit ID lets the audit and entity be inserted together without an early flush.
    from .models import new_id
    row.id = new_id()
    record(db, actor, club_id, action, row.id)
    commit(db)
    return view(row)


@router.get("")
def planning(club_id: str, actor: ActorDep, db: Db):
    member = membership(db, actor, club_id)
    if not {"coach", "club_admin"}.intersection(member.roles):
        raise HTTPException(403, "No tienes acceso a planificación")
    seasons = db.scalars(select(Season).where(Season.club_id == club_id).order_by(Season.starts_on.desc())).all()
    phases = db.scalars(select(TrainingPhase).where(TrainingPhase.club_id == club_id).order_by(TrainingPhase.starts_on)).all()
    plans = []
    if "coach" in member.roles:
        plans = db.scalars(select(TrainingPlan).where(
            TrainingPlan.club_id == club_id,
            TrainingPlan.coach_membership_id == member.id,
        ).order_by(TrainingPlan.starts_on)).all()
    plan_ids = [row.id for row in plans]
    cycles = db.scalars(select(Microcycle).where(
        Microcycle.club_id == club_id, Microcycle.plan_id.in_(plan_ids),
    ).order_by(Microcycle.starts_on)).all()
    days = db.scalars(select(PlanDay).where(
        PlanDay.club_id == club_id,
        PlanDay.microcycle_id.in_([row.id for row in cycles]),
    ).order_by(PlanDay.local_date)).all()
    return {
        "timezone": db.get(Club, club_id).timezone,
        "seasons": [view(row) for row in seasons],
        "phases": [view(row) for row in phases],
        "plans": [view(row) for row in plans],
        "microcycles": [view(row) for row in cycles],
        "days": [view(row) for row in days],
    }


@router.post("/seasons", status_code=201)
def create_season(club_id: str, data: SeasonIn, actor: ActorDep, db: Db, x_csrf_token: Csrf = None):
    require_csrf(actor, x_csrf_token)
    membership(db, actor, club_id, "club_admin")
    return save_new(db, actor, club_id, Season(club_id=club_id, **data.model_dump()), "season.created")


@router.patch("/seasons/{season_id}")
def change_season(club_id: str, season_id: str, data: SeasonStatusIn, actor: ActorDep, db: Db, x_csrf_token: Csrf = None):
    require_csrf(actor, x_csrf_token)
    membership(db, actor, club_id, "club_admin")
    row = get_row(db, Season, club_id, season_id)
    assert_open(row)
    row.status = data.status
    record(db, actor, club_id, "season." + data.status, row.id)
    commit(db)
    return view(row)


@router.post("/phases", status_code=201)
def create_phase(club_id: str, data: PhaseIn, actor: ActorDep, db: Db, x_csrf_token: Csrf = None):
    require_csrf(actor, x_csrf_token)
    membership(db, actor, club_id, "club_admin")
    season = get_row(db, Season, club_id, data.season_id)
    assert_open(season)
    assert_period(season, data)
    return save_new(db, actor, club_id, TrainingPhase(club_id=club_id, **data.model_dump()), "phase.created")


@router.post("/plans", status_code=201)
def create_plan(club_id: str, data: PlanIn, actor: ActorDep, db: Db, x_csrf_token: Csrf = None):
    require_csrf(actor, x_csrf_token)
    coach = membership(db, actor, club_id, "coach")
    phase = get_row(db, TrainingPhase, club_id, data.phase_id)
    assert_open(get_row(db, Season, club_id, phase.season_id))
    assert_period(phase, data)
    row = TrainingPlan(club_id=club_id, coach_membership_id=coach.id, **data.model_dump())
    return save_new(db, actor, club_id, row, "plan.created")


@router.post("/plans/{plan_id}/archive")
def archive_plan(club_id: str, plan_id: str, actor: ActorDep, db: Db, x_csrf_token: Csrf = None):
    require_csrf(actor, x_csrf_token)
    coach = membership(db, actor, club_id, "coach")
    row = authorized_plan(db, club_id, plan_id, coach.id)
    row.status = "archived"
    record(db, actor, club_id, "plan.archived", row.id)
    commit(db)
    return view(row)


@router.post("/microcycles", status_code=201)
def create_microcycle(club_id: str, data: MicrocycleIn, actor: ActorDep, db: Db, x_csrf_token: Csrf = None):
    require_csrf(actor, x_csrf_token)
    coach = membership(db, actor, club_id, "coach")
    plan = authorized_plan(db, club_id, data.plan_id, coach.id)
    assert_period(plan, data)
    return save_new(db, actor, club_id, Microcycle(club_id=club_id, **data.model_dump()), "microcycle.created")


@router.post("/days", status_code=201)
def create_day(club_id: str, data: DayIn, actor: ActorDep, db: Db, x_csrf_token: Csrf = None):
    require_csrf(actor, x_csrf_token)
    coach = membership(db, actor, club_id, "coach")
    cycle = get_row(db, Microcycle, club_id, data.microcycle_id)
    authorized_plan(db, club_id, cycle.plan_id, coach.id)
    if not cycle.starts_on <= data.local_date <= cycle.ends_on:
        raise HTTPException(422, "El día debe quedar dentro del microciclo")
    return save_new(db, actor, club_id, PlanDay(club_id=club_id, **data.model_dump()), "plan_day.created")
