"""Per-athlete Google Calendar authorization and one-way sync controls."""

import secrets
from datetime import timedelta, timezone
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select

from .audit import record
from .deps import ActorDep, Db, athlete_for_member, membership, require_csrf
from .google_calendar_service import (
    GoogleError, authorization_url, code_challenge, configuration, exchange_code,
    list_owned_calendars, require_configuration,
)
from .google_calendar_sync import access_token, clear_cached_token, queue_existing
from .models import (
    Athlete, ExternalCalendarEvent, GoogleCalendarConnection, GoogleCalendarOutbox,
    GoogleOAuthState, Membership, utc_now,
)
from .security import secret_hash

router = APIRouter(prefix="/api/v1/clubs/{club_id}/google-calendar")
callback_router = APIRouter(prefix="/api/v1/google-calendar")
Csrf = Annotated[str | None, Header()]


class ChooseCalendar(BaseModel):
    calendar_id: str = Field(min_length=1, max_length=320)


def own_athlete(db, actor, club_id):
    member = membership(db, actor, club_id, "athlete")
    athlete = athlete_for_member(db, club_id, member.id)
    if athlete is None:
        raise HTTPException(404, "Perfil deportivo no encontrado")
    return athlete


def as_http_error(error: GoogleError) -> HTTPException:
    return HTTPException(error.status, str(error))


def connection_for(db, club_id, athlete_id):
    return db.scalar(select(GoogleCalendarConnection).where(
        GoogleCalendarConnection.club_id == club_id,
        GoogleCalendarConnection.athlete_id == athlete_id,
    ))


@router.get("")
def status(club_id: str, actor: ActorDep, db: Db):
    athlete = own_athlete(db, actor, club_id)
    connection = connection_for(db, club_id, athlete.id)
    count = 0
    if connection:
        count = db.scalar(select(func.count()).select_from(GoogleCalendarOutbox).where(
            GoogleCalendarOutbox.connection_id == connection.id,
            GoogleCalendarOutbox.status.in_(("pending", "retry", "processing")),
        ))
    return {
        "configured": configuration() is not None,
        "connected": connection is not None,
        "status": connection.status if connection else "disconnected",
        "calendar_id": connection.calendar_id if connection else None,
        "calendar_name": connection.calendar_name if connection else None,
        "pending": count,
        "last_error": connection.last_error if connection else None,
    }


@router.post("/connect")
def connect(
    club_id: str, actor: ActorDep, db: Db, x_csrf_token: Csrf = None,
):
    require_csrf(actor, x_csrf_token)
    athlete = own_athlete(db, actor, club_id)
    try:
        config = require_configuration()
    except GoogleError as error:
        raise as_http_error(error) from error
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    db.add(GoogleOAuthState(
        token_hash=secret_hash(state), club_id=club_id,
        athlete_id=athlete.id, code_verifier=verifier,
        expires_at=utc_now() + timedelta(minutes=10),
    ))
    db.commit()
    return {"url": authorization_url(config, state, code_challenge(verifier))}


def return_to_app(config, outcome: str) -> RedirectResponse:
    separator = "&" if "?" in config.return_url else "?"
    return RedirectResponse(config.return_url + separator + urlencode({"google": outcome}), status_code=303)


@callback_router.get("/callback")
def callback(db: Db, state: str = "", code: str = "", error: str = ""):
    try:
        config = require_configuration()
    except GoogleError as problem:
        raise as_http_error(problem) from problem
    if not state:
        raise HTTPException(400, "Estado OAuth ausente")
    pending = db.scalar(select(GoogleOAuthState).where(
        GoogleOAuthState.token_hash == secret_hash(state),
    ).with_for_update())
    if not pending or pending.used_at or pending.expires_at.replace(tzinfo=timezone.utc) <= utc_now():
        raise HTTPException(400, "Conexión caducada o ya utilizada")
    pending.used_at = utc_now()
    db.commit()
    if error or not code:
        return return_to_app(config, "denied")
    try:
        tokens = exchange_code(config, code, pending.code_verifier)
    except GoogleError:
        return return_to_app(config, "failed")
    athlete = db.get(Athlete, pending.athlete_id)
    member = db.get(Membership, athlete.membership_id) if athlete else None
    if not member or not member.active or "athlete" not in member.roles:
        return return_to_app(config, "failed")
    connection = connection_for(db, pending.club_id, pending.athlete_id)
    encrypted = config.cipher.encrypt(tokens["refresh_token"].encode()).decode()
    if connection is None:
        connection = GoogleCalendarConnection(
            club_id=pending.club_id, athlete_id=pending.athlete_id,
            encrypted_refresh_token=encrypted,
        )
        db.add(connection)
        db.flush()
    else:
        connection.encrypted_refresh_token = encrypted
        connection.calendar_id = None
        connection.calendar_name = None
        connection.is_primary = False
        connection.status = "choose_calendar"
        connection.last_error = None
        clear_cached_token(connection.id)
    db.commit()
    return return_to_app(config, "connected")


@router.get("/calendars")
def calendars(club_id: str, actor: ActorDep, db: Db):
    athlete = own_athlete(db, actor, club_id)
    connection = connection_for(db, club_id, athlete.id)
    if connection is None:
        raise HTTPException(409, "Conecta Google Calendar primero")
    try:
        return {"calendars": list_owned_calendars(access_token(connection))}
    except GoogleError as error:
        raise as_http_error(error) from error


@router.post("/calendar")
def choose_calendar(
    club_id: str, data: ChooseCalendar, actor: ActorDep, db: Db,
    x_csrf_token: Csrf = None,
):
    require_csrf(actor, x_csrf_token)
    athlete = own_athlete(db, actor, club_id)
    connection = connection_for(db, club_id, athlete.id)
    if connection is None:
        raise HTTPException(409, "Conecta Google Calendar primero")
    try:
        available = list_owned_calendars(access_token(connection))
    except GoogleError as error:
        raise as_http_error(error) from error
    chosen = next((row for row in available if row["id"] == data.calendar_id), None)
    if chosen is None:
        raise HTTPException(422, "Selecciona un calendario propio")
    if connection.calendar_id != chosen["id"]:
        active_job = db.scalar(select(GoogleCalendarOutbox.id).where(
            GoogleCalendarOutbox.connection_id == connection.id,
            GoogleCalendarOutbox.status == "processing",
        ))
        if active_job:
            raise HTTPException(409, "Hay un envío en curso; vuelve a intentarlo en unos segundos")
        db.execute(delete(GoogleCalendarOutbox).where(
            GoogleCalendarOutbox.connection_id == connection.id,
        ))
        db.execute(delete(ExternalCalendarEvent).where(
            ExternalCalendarEvent.connection_id == connection.id,
        ))
    connection.calendar_id = chosen["id"]
    connection.calendar_name = chosen["name"]
    connection.is_primary = chosen["primary"]
    connection.status = "active"
    connection.last_error = None
    result = queue_existing(db, connection)
    record(db, actor, club_id, "calendar.connected", athlete.id)
    db.commit()
    return result


@router.post("/sync")
def sync_now(
    club_id: str, actor: ActorDep, db: Db, x_csrf_token: Csrf = None,
):
    require_csrf(actor, x_csrf_token)
    athlete = own_athlete(db, actor, club_id)
    connection = connection_for(db, club_id, athlete.id)
    if connection is None or connection.status != "active":
        raise HTTPException(409, "Elige un calendario activo")
    result = queue_existing(db, connection)
    db.commit()
    return result


@router.delete("", status_code=204)
def disconnect(
    club_id: str, actor: ActorDep, db: Db, x_csrf_token: Csrf = None,
):
    require_csrf(actor, x_csrf_token)
    athlete = own_athlete(db, actor, club_id)
    connection = connection_for(db, club_id, athlete.id)
    db.execute(delete(GoogleOAuthState).where(
        GoogleOAuthState.club_id == club_id,
        GoogleOAuthState.athlete_id == athlete.id,
    ))
    if connection:
        active_job = db.scalar(select(GoogleCalendarOutbox.id).where(
            GoogleCalendarOutbox.connection_id == connection.id,
            GoogleCalendarOutbox.status == "processing",
        ))
        if active_job:
            raise HTTPException(409, "Hay un envío en curso; vuelve a intentarlo en unos segundos")
        clear_cached_token(connection.id)
        db.execute(delete(GoogleCalendarOutbox).where(
            GoogleCalendarOutbox.connection_id == connection.id,
        ))
        db.execute(delete(ExternalCalendarEvent).where(
            ExternalCalendarEvent.connection_id == connection.id,
        ))
        db.delete(connection)
        record(db, actor, club_id, "calendar.disconnected", athlete.id)
    db.commit()
