"""Club membership and direct coach grants for the first slice."""
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException
from sqlalchemy import select

from .deps import ActorDep, Db, athlete_for_member, coach_can_see, membership, require_csrf
from .models import Athlete, Club, CoachAthleteGrant, CoachGroupGrant, Membership, TrainingGroup, TrainingGroupMembership, User
from .schemas import GrantIn, GroupAthleteIn, GroupCoachIn, GroupIn, MemberIn
from .security import hash_password

router = APIRouter()


@router.get("/api/v1/clubs/{club_id}/members")
def members(club_id: str, actor: ActorDep, db: Db) -> list[dict]:
    membership(db, actor, club_id, "club_admin")
    rows = db.scalars(select(Membership).where(Membership.club_id == club_id)).all()
    return [{"id": m.id, "user_id": m.user_id, "name": db.get(User, m.user_id).name, "email": db.get(User, m.user_id).email, "roles": m.roles, "active": m.active, "athlete_id": (athlete_for_member(db, club_id, m.id).id if athlete_for_member(db, club_id, m.id) else None)} for m in rows]


@router.post("/api/v1/clubs/{club_id}/members", status_code=201)
def create_member(club_id: str, data: MemberIn, actor: ActorDep, db: Db, x_csrf_token: Annotated[str | None, Header()] = None) -> dict:
    require_csrf(actor, x_csrf_token)
    membership(db, actor, club_id, "club_admin")
    if os.environ.get("APP_ENV") != "development":
        raise HTTPException(501, "El alta segura por invitación está pendiente")
    if not data.roles or db.scalar(select(User.id).where(User.email == str(data.email).lower().strip())):
        raise HTTPException(409, "Email existente o roles vacíos")
    user = User(email=str(data.email).lower().strip(), name=data.name.strip(), password_hash=hash_password(data.password))
    db.add(user)
    db.flush()
    member = Membership(club_id=club_id, user_id=user.id, roles=sorted(data.roles))
    db.add(member)
    db.flush()
    athlete = None
    if "athlete" in data.roles:
        athlete = Athlete(club_id=club_id, membership_id=member.id)
        db.add(athlete)
        db.flush()
    result = {"id": member.id, "user_id": user.id, "athlete_id": athlete.id if athlete else None}
    db.commit()
    return result


@router.get("/api/v1/clubs/{club_id}/athletes")
def athletes(club_id: str, actor: ActorDep, db: Db) -> list[dict]:
    member = membership(db, actor, club_id)
    rows = db.scalars(select(Athlete).where(Athlete.club_id == club_id)).all()
    if "club_admin" not in member.roles:
        if "coach" not in member.roles:
            raise HTTPException(403, "Sin permiso")
        rows = [a for a in rows if coach_can_see(db, club_id, member.id, a.id)]
    return [{"id": a.id, "membership_id": a.membership_id, "name": db.get(User, db.get(Membership, a.membership_id).user_id).name} for a in rows]


@router.post("/api/v1/clubs/{club_id}/grants", status_code=201)
def grant(club_id: str, data: GrantIn, actor: ActorDep, db: Db, x_csrf_token: Annotated[str | None, Header()] = None) -> dict:
    require_csrf(actor, x_csrf_token)
    membership(db, actor, club_id, "club_admin")
    coach = db.scalar(select(Membership).where(Membership.club_id == club_id, Membership.id == data.coach_membership_id, Membership.active.is_(True)))
    athlete = db.scalar(select(Athlete).where(Athlete.club_id == club_id, Athlete.id == data.athlete_id))
    if not coach or "coach" not in coach.roles or not athlete:
        raise HTTPException(422, "Entrenador o deportista inválido")
    existing = db.scalar(select(CoachAthleteGrant).where(CoachAthleteGrant.club_id == club_id, CoachAthleteGrant.coach_membership_id == coach.id, CoachAthleteGrant.athlete_id == athlete.id))
    if existing:
        return {"id": existing.id}
    row = CoachAthleteGrant(club_id=club_id, coach_membership_id=coach.id, athlete_id=athlete.id)
    db.add(row)
    db.commit()
    return {"id": row.id}


@router.get("/api/v1/clubs/{club_id}/groups")
def groups(club_id: str, actor: ActorDep, db: Db) -> list[dict]:
    member = membership(db, actor, club_id)
    if not ({"coach", "club_admin"} & set(member.roles)):
        raise HTTPException(403, "Sin permiso")
    rows = db.scalars(select(TrainingGroup).where(TrainingGroup.club_id == club_id, TrainingGroup.active.is_(True)).order_by(TrainingGroup.name)).all()
    if "club_admin" not in member.roles:
        allowed = set(db.scalars(select(CoachGroupGrant.group_id).where(CoachGroupGrant.club_id == club_id, CoachGroupGrant.coach_membership_id == member.id)).all())
        rows = [row for row in rows if row.id in allowed]
    today = datetime.now(ZoneInfo(db.get(Club, club_id).timezone)).date()
    result = []
    for row in rows:
        athlete_ids = db.scalars(select(TrainingGroupMembership.athlete_id).where(
            TrainingGroupMembership.club_id == club_id,
            TrainingGroupMembership.group_id == row.id,
            TrainingGroupMembership.joined_on <= today,
            (TrainingGroupMembership.left_on.is_(None) | (TrainingGroupMembership.left_on >= today)),
        )).all()
        result.append({"id": row.id, "name": row.name, "description": row.description, "athlete_ids": athlete_ids})
    return result


@router.post("/api/v1/clubs/{club_id}/groups", status_code=201)
def create_group(club_id: str, data: GroupIn, actor: ActorDep, db: Db, x_csrf_token: Annotated[str | None, Header()] = None) -> dict:
    require_csrf(actor, x_csrf_token)
    membership(db, actor, club_id, "club_admin")
    name = data.name.strip()
    if not name:
        raise HTTPException(422, "Nombre vacío")
    if db.scalar(select(TrainingGroup.id).where(TrainingGroup.club_id == club_id, TrainingGroup.name == name)):
        raise HTTPException(409, "Ya existe el grupo")
    row = TrainingGroup(club_id=club_id, name=name, description=data.description)
    db.add(row)
    db.commit()
    return {"id": row.id, "name": row.name}


@router.post("/api/v1/clubs/{club_id}/groups/{group_id}/athletes", status_code=201)
def add_group_athlete(club_id: str, group_id: str, data: GroupAthleteIn, actor: ActorDep, db: Db, x_csrf_token: Annotated[str | None, Header()] = None) -> dict:
    require_csrf(actor, x_csrf_token)
    membership(db, actor, club_id, "club_admin")
    group = db.scalar(select(TrainingGroup).where(TrainingGroup.club_id == club_id, TrainingGroup.id == group_id, TrainingGroup.active.is_(True)))
    athlete = db.scalar(select(Athlete).where(Athlete.club_id == club_id, Athlete.id == data.athlete_id))
    if not group or not athlete or not db.get(Membership, athlete.membership_id).active:
        raise HTTPException(404, "Grupo o deportista no encontrado")
    existing = db.scalar(select(TrainingGroupMembership).where(TrainingGroupMembership.club_id == club_id, TrainingGroupMembership.group_id == group_id, TrainingGroupMembership.athlete_id == athlete.id))
    if existing:
        return {"id": existing.id}
    today = datetime.now(ZoneInfo(db.get(Club, club_id).timezone)).date()
    row = TrainingGroupMembership(club_id=club_id, group_id=group_id, athlete_id=athlete.id, joined_on=today)
    db.add(row)
    db.commit()
    return {"id": row.id}


@router.post("/api/v1/clubs/{club_id}/groups/{group_id}/coaches", status_code=201)
def add_group_coach(club_id: str, group_id: str, data: GroupCoachIn, actor: ActorDep, db: Db, x_csrf_token: Annotated[str | None, Header()] = None) -> dict:
    require_csrf(actor, x_csrf_token)
    membership(db, actor, club_id, "club_admin")
    group = db.scalar(select(TrainingGroup).where(TrainingGroup.club_id == club_id, TrainingGroup.id == group_id, TrainingGroup.active.is_(True)))
    coach = db.scalar(select(Membership).where(Membership.club_id == club_id, Membership.id == data.coach_membership_id, Membership.active.is_(True)))
    if not group or not coach or "coach" not in coach.roles:
        raise HTTPException(404, "Grupo o entrenador no encontrado")
    existing = db.scalar(select(CoachGroupGrant).where(CoachGroupGrant.club_id == club_id, CoachGroupGrant.group_id == group_id, CoachGroupGrant.coach_membership_id == coach.id))
    if existing:
        return {"id": existing.id}
    row = CoachGroupGrant(club_id=club_id, group_id=group_id, coach_membership_id=coach.id)
    db.add(row)
    db.commit()
    return {"id": row.id}
