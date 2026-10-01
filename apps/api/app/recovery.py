"""Optional daily recovery, with optimistic versions and private revision history."""
from datetime import date, datetime, timedelta
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select, update

from .audit import commit, record
from .deps import ActorDep, Db, athlete_for_member, coach_can_see, membership, require_csrf, utc_iso
from .models import Athlete, Club, RecoveryLog, new_id, utc_now

router = APIRouter(prefix="/api/v1/clubs/{club_id}")
FIELDS = ("sleep", "fatigue", "soreness", "motivation", "energy", "pain", "pain_area", "comment")


class RecoveryIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    version: int = Field(default=0, ge=0)
    sleep: int | None = Field(default=None, ge=1, le=5)
    fatigue: int | None = Field(default=None, ge=1, le=5)
    soreness: int | None = Field(default=None, ge=1, le=5)
    motivation: int | None = Field(default=None, ge=1, le=5)
    energy: int | None = Field(default=None, ge=1, le=5)
    pain: int | None = Field(default=None, ge=0, le=10)
    pain_area: str | None = Field(default=None, max_length=120)
    comment: str | None = Field(default=None, max_length=2000)
    reason: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def check_values(self):
        if not any(getattr(self, field) is not None for field in FIELDS[:6]) and not self.comment:
            raise ValueError("Indica al menos una valoración o un comentario")
        if self.pain_area and not self.pain:
            raise ValueError("Indica intensidad de dolor para guardar su zona")
        if self.version and not self.reason:
            raise ValueError("Indica el motivo de la corrección")
        return self


def recovery_view(row):
    return {
        "id": row.id,
        "local_date": row.local_date,
        "version": row.version,
        "updated_at": utc_iso(row.updated_at),
        **{field: getattr(row, field) for field in FIELDS},
        "revisions": row.revisions,
    }


def own_athlete(db, actor, club_id):
    member = membership(db, actor, club_id, "athlete")
    athlete = athlete_for_member(db, club_id, member.id)
    if not athlete:
        raise HTTPException(404, "Perfil deportivo no encontrado")
    return athlete


def records(db, club_id, athlete_id, start, end):
    today = datetime.now(ZoneInfo(db.get(Club, club_id).timezone)).date()
    start = start or today - timedelta(days=90)
    end = end or today
    if end < start or (end - start).days > 366:
        raise HTTPException(422, "El período debe ser válido y no superar un año")
    rows = db.scalars(select(RecoveryLog).where(
        RecoveryLog.club_id == club_id,
        RecoveryLog.athlete_id == athlete_id,
        RecoveryLog.local_date >= start,
        RecoveryLog.local_date <= end,
    ).order_by(RecoveryLog.local_date.desc())).all()
    return {"timezone": db.get(Club, club_id).timezone, "today": today, "records": [recovery_view(row) for row in rows]}


@router.get("/recovery")
def my_recovery(
    club_id: str, actor: ActorDep, db: Db,
    start: date | None = None, end: date | None = None,
):
    athlete = own_athlete(db, actor, club_id)
    return records(db, club_id, athlete.id, start, end)


@router.get("/athletes/{athlete_id}/recovery")
def athlete_recovery(
    club_id: str, athlete_id: str, actor: ActorDep, db: Db,
    start: date | None = None, end: date | None = None,
):
    coach = membership(db, actor, club_id, "coach")
    athlete = db.scalar(select(Athlete).where(Athlete.club_id == club_id, Athlete.id == athlete_id))
    if not athlete or not coach_can_see(db, club_id, coach.id, athlete_id):
        raise HTTPException(404, "Deportista no encontrado")
    return records(db, club_id, athlete_id, start, end)


@router.put("/recovery/{local_date}")
def save_recovery(
    club_id: str, local_date: date, data: RecoveryIn, actor: ActorDep, db: Db,
    x_csrf_token: Annotated[str | None, Header()] = None,
):
    require_csrf(actor, x_csrf_token)
    athlete = own_athlete(db, actor, club_id)
    today = datetime.now(ZoneInfo(db.get(Club, club_id).timezone)).date()
    if local_date > today:
        raise HTTPException(422, "No se puede registrar recuperación futura")
    row = db.scalar(select(RecoveryLog).where(
        RecoveryLog.club_id == club_id,
        RecoveryLog.athlete_id == athlete.id,
        RecoveryLog.local_date == local_date,
    ).with_for_update())
    values = data.model_dump(include=set(FIELDS))
    if row:
        if row.version != data.version:
            raise HTTPException(409, "El registro ha cambiado; recárgalo antes de corregirlo")
        previous = {
            **{field: getattr(row, field) for field in FIELDS},
            "version": row.version,
            "updated_at": utc_iso(row.updated_at),
            "corrected_by": actor.user.id,
            "corrected_at": utc_iso(utc_now()),
            "reason": data.reason,
        }
        result = db.execute(update(RecoveryLog).where(
            RecoveryLog.id == row.id, RecoveryLog.version == data.version,
        ).values(
            **values, version=data.version + 1, updated_at=utc_now(),
            revisions=[*row.revisions, previous],
        ))
        if result.rowcount != 1:
            raise HTTPException(409, "El registro ha cambiado; recarga la página")
        record(db, actor, club_id, "recovery.corrected", row.id)
    else:
        if data.version:
            raise HTTPException(409, "El registro que intentas corregir no existe")
        row = RecoveryLog(
            id=new_id(), club_id=club_id, athlete_id=athlete.id,
            local_date=local_date, **values,
        )
        db.add(row)
        record(db, actor, club_id, "recovery.created", row.id)
    commit(db)
    db.refresh(row)
    return recovery_view(row)
