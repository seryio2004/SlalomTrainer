"""Record actions in the same transaction as their domain changes."""
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from fastapi import HTTPException

from .models import AuditEvent


def record(db: Session, actor, club_id: str, action: str, entity_id: str) -> None:
    db.add(AuditEvent(
        club_id=club_id,
        actor_user_id=actor.user.id,
        action=action,
        entity_id=entity_id,
    ))


def commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(409, "Ya existe un registro incompatible; recarga los datos") from error
