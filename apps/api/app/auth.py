"""Login, logout and current identity."""
import os
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Response
from sqlalchemy import select

from .deps import ActorDep, Db, require_csrf
from .models import AuthSession, Membership, User, utc_now
from .schemas import LoginIn
from .security import new_secret, secret_hash, verify_password

router = APIRouter()


@router.get("/api/v1/health")
def health() -> dict:
    return {"status": "ok"}


@router.post("/api/v1/auth/login")
def login(data: LoginIn, response: Response, db: Db) -> dict:
    user = db.scalar(select(User).where(User.email == str(data.email).lower().strip()))
    if not user or not user.active or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Credenciales incorrectas")
    token, csrf = new_secret(), new_secret()
    auth = AuthSession(user_id=user.id, token_hash=secret_hash(token), csrf_hash=secret_hash(csrf), expires_at=utc_now() + timedelta(days=7))
    db.add(auth)
    db.commit()
    response.set_cookie("tei_session", token, httponly=True, secure=os.environ.get("APP_ENV") != "development", samesite="strict", max_age=604800, path="/")
    response.set_cookie("tei_csrf", csrf, httponly=False, secure=os.environ.get("APP_ENV") != "development", samesite="strict", max_age=604800, path="/")
    return {"id": user.id, "name": user.name}


@router.get("/api/v1/me")
def me(actor: ActorDep, db: Db) -> dict:
    members = db.scalars(select(Membership).where(Membership.user_id == actor.user.id, Membership.active.is_(True))).all()
    return {"id": actor.user.id, "name": actor.user.name, "memberships": [{"id": m.id, "club_id": m.club_id, "roles": m.roles} for m in members]}


@router.post("/api/v1/auth/logout", status_code=204)
def logout(response: Response, actor: ActorDep, db: Db, x_csrf_token: Annotated[str | None, Header()] = None) -> None:
    require_csrf(actor, x_csrf_token)
    actor.auth.revoked_at = utc_now()
    db.commit()
    response.delete_cookie("tei_session", path="/")
    response.delete_cookie("tei_csrf", path="/")


