"""Club administration. Audit metadata never contains private recovery values."""
from datetime import datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, update

from .audit import commit, record
from .deps import ActorDep, Db, membership, require_csrf, utc_iso
from .models import (
    AccountAction, AuditEvent, Club, CoachAthleteGrant, CoachGroupGrant, Membership,
    TrainingGroup, TrainingGroupMembership, User,
)

router = APIRouter(prefix="/api/v1/clubs/{club_id}")
Csrf = Annotated[str | None, Header()]


class ActiveIn(BaseModel):
    active: bool


class GroupUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=500)
    active: bool = True


@router.get("/administration")
def administration(club_id: str, actor: ActorDep, db: Db):
    membership(db, actor, club_id, "club_admin")
    today = datetime.now(ZoneInfo(db.get(Club, club_id).timezone)).date()
    groups = db.scalars(select(TrainingGroup).where(
        TrainingGroup.club_id == club_id,
    ).order_by(TrainingGroup.name)).all()
    group_links = db.scalars(select(TrainingGroupMembership).where(
        TrainingGroupMembership.club_id == club_id,
        TrainingGroupMembership.joined_on <= today,
        (TrainingGroupMembership.left_on.is_(None) | (TrainingGroupMembership.left_on > today)),
    )).all()
    group_grants = db.scalars(select(CoachGroupGrant).where(CoachGroupGrant.club_id == club_id)).all()
    direct = db.scalars(select(CoachAthleteGrant).where(CoachAthleteGrant.club_id == club_id)).all()
    return {
        "groups": [{
            "id": row.id, "name": row.name, "description": row.description,
            "active": row.active,
            "athlete_ids": [link.athlete_id for link in group_links if link.group_id == row.id],
            "coach_ids": [grant.coach_membership_id for grant in group_grants if grant.group_id == row.id],
        } for row in groups],
        "grants": [{
            "id": row.id, "coach_membership_id": row.coach_membership_id,
            "athlete_id": row.athlete_id,
        } for row in direct],
    }


@router.patch("/members/{member_id}/status")
def member_status(
    club_id: str, member_id: str, data: ActiveIn, actor: ActorDep, db: Db,
    x_csrf_token: Csrf = None,
):
    require_csrf(actor, x_csrf_token)
    admin = membership(db, actor, club_id, "club_admin")
    member = db.scalar(select(Membership).where(
        Membership.club_id == club_id, Membership.id == member_id,
    ).with_for_update())
    if not member:
        raise HTTPException(404, "Miembro no encontrado")
    if member.id == admin.id and not data.active:
        raise HTTPException(409, "No puedes desactivar tu propia membresía")
    if not data.active:
        db.execute(update(AccountAction).where(AccountAction.membership_id == member.id, AccountAction.used_at.is_(None)).values(used_at=datetime.now().astimezone(), encrypted_token=None))
    if member.active != data.active:
        member.active = data.active
        action = "member.activated" if data.active else "member.deactivated"
        record(db, actor, club_id, action, member.id)
    commit(db)
    return {"id": member.id, "active": member.active}


@router.patch("/groups/{group_id}")
def edit_group(
    club_id: str, group_id: str, data: GroupUpdate, actor: ActorDep, db: Db,
    x_csrf_token: Csrf = None,
):
    require_csrf(actor, x_csrf_token)
    membership(db, actor, club_id, "club_admin")
    group = db.scalar(select(TrainingGroup).where(
        TrainingGroup.club_id == club_id, TrainingGroup.id == group_id,
    ))
    if not group:
        raise HTTPException(404, "Grupo no encontrado")
    for field, value in data.model_dump().items():
        setattr(group, field, value)
    record(db, actor, club_id, "group.updated", group.id)
    commit(db)
    return {"id": group.id}


@router.delete("/groups/{group_id}/athletes/{athlete_id}", status_code=204)
def remove_group_athlete(
    club_id: str, group_id: str, athlete_id: str, actor: ActorDep, db: Db,
    x_csrf_token: Csrf = None,
):
    require_csrf(actor, x_csrf_token)
    membership(db, actor, club_id, "club_admin")
    link = db.scalar(select(TrainingGroupMembership).where(
        TrainingGroupMembership.club_id == club_id,
        TrainingGroupMembership.group_id == group_id,
        TrainingGroupMembership.athlete_id == athlete_id,
        TrainingGroupMembership.left_on.is_(None),
    ))
    if not link:
        raise HTTPException(404, "Pertenencia activa no encontrada")
    # End is exclusive: access is revoked immediately on the club's local date.
    link.left_on = datetime.now(ZoneInfo(db.get(Club, club_id).timezone)).date()
    record(db, actor, club_id, "group.athlete_removed", link.id)
    commit(db)


@router.delete("/groups/{group_id}/coaches/{coach_id}", status_code=204)
def revoke_group_coach(
    club_id: str, group_id: str, coach_id: str, actor: ActorDep, db: Db,
    x_csrf_token: Csrf = None,
):
    require_csrf(actor, x_csrf_token)
    membership(db, actor, club_id, "club_admin")
    grant = db.scalar(select(CoachGroupGrant).where(
        CoachGroupGrant.club_id == club_id,
        CoachGroupGrant.group_id == group_id,
        CoachGroupGrant.coach_membership_id == coach_id,
    ))
    if not grant:
        raise HTTPException(404, "Permiso no encontrado")
    record(db, actor, club_id, "group.coach_revoked", grant.id)
    db.delete(grant)
    commit(db)


@router.delete("/grants/{grant_id}", status_code=204)
def revoke_direct_grant(
    club_id: str, grant_id: str, actor: ActorDep, db: Db,
    x_csrf_token: Csrf = None,
):
    require_csrf(actor, x_csrf_token)
    membership(db, actor, club_id, "club_admin")
    grant = db.scalar(select(CoachAthleteGrant).where(
        CoachAthleteGrant.club_id == club_id, CoachAthleteGrant.id == grant_id,
    ))
    if not grant:
        raise HTTPException(404, "Permiso no encontrado")
    record(db, actor, club_id, "coach.direct_access_revoked", grant.id)
    db.delete(grant)
    commit(db)


@router.get("/audit")
def audit_events(
    club_id: str, actor: ActorDep, db: Db,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    membership(db, actor, club_id, "club_admin")
    rows = db.scalars(select(AuditEvent).where(
        AuditEvent.club_id == club_id,
    ).order_by(AuditEvent.occurred_at.desc()).limit(limit)).all()
    return [{
        "id": row.id,
        "action": row.action,
        "actor": db.get(User, row.actor_user_id).name,
        "entity_id": row.entity_id,
        "occurred_at": utc_iso(row.occurred_at),
    } for row in rows]


class RolesIn(BaseModel):
    roles: set[str]


@router.patch('/members/{member_id}/roles')
def change_roles(club_id: str, member_id: str, data: RolesIn, actor: ActorDep, db: Db, x_csrf_token: Csrf = None):
    require_csrf(actor, x_csrf_token)
    membership(db, actor, club_id, 'club_admin')
    if not data.roles or not data.roles <= {'club_admin', 'coach', 'athlete'}:
        raise HTTPException(422, 'Selecciona roles válidos')
    # Serialize administrator changes to retain at least one active administrator.
    db.scalar(select(Club).where(Club.id == club_id).with_for_update())
    member = db.scalar(select(Membership).where(Membership.club_id == club_id, Membership.id == member_id))
    if not member:
        raise HTTPException(404, 'Miembro no encontrado')
    admins = [row for row in db.scalars(select(Membership).where(Membership.club_id == club_id, Membership.active.is_(True))) if 'club_admin' in row.roles]
    if member.active and 'club_admin' in member.roles and 'club_admin' not in data.roles and len(admins) == 1:
        raise HTTPException(409, 'El club necesita al menos un administrador activo')
    if 'athlete' in data.roles:
        from .models import Athlete
        if not db.scalar(select(Athlete.id).where(Athlete.club_id == club_id, Athlete.membership_id == member.id)):
            db.add(Athlete(club_id=club_id, membership_id=member.id))
    member.roles = sorted(data.roles)
    record(db, actor, club_id, 'member.roles_changed', member.id)
    commit(db)
    return {'id': member.id, 'roles': member.roles}
