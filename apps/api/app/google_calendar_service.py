"""Google OAuth configuration and Calendar HTTP operations.

Tokens stay server-side; responses never include token contents.
"""

import base64
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urlencode

import httpx
from cryptography.fernet import Fernet, InvalidToken

from .models import Assignment, WorkoutSession

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
CALENDAR_URL = "https://www.googleapis.com/calendar/v3"
SCOPES = (
    "https://www.googleapis.com/auth/calendar.events.owned",
    "https://www.googleapis.com/auth/calendar.calendarlist.readonly",
)


@dataclass(frozen=True)
class GoogleConfig:
    client_id: str
    client_secret: str
    redirect_uri: str
    return_url: str
    cipher: Fernet


class GoogleError(Exception):
    def __init__(self, message: str, status: int = 502):
        super().__init__(message)
        self.status = status


def configuration() -> GoogleConfig | None:
    names = (
        "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REDIRECT_URI",
        "GOOGLE_RETURN_URL", "GOOGLE_TOKEN_ENCRYPTION_KEY",
    )
    values = [os.environ.get(name, "").strip() for name in names]
    if not all(values):
        return None
    try:
        return GoogleConfig(*values[:4], Fernet(values[4].encode()))
    except (ValueError, base64.binascii.Error) as error:
        raise GoogleError("Configuración de cifrado inválida", 503) from error


def require_configuration() -> GoogleConfig:
    config = configuration()
    if config is None:
        raise GoogleError("Google Calendar no está configurado en este servidor", 503)
    return config


def authorization_url(config: GoogleConfig, state: str, challenge: str) -> str:
    parameters = {
        "client_id": config.client_id,
        "redirect_uri": config.redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return AUTH_URL + "?" + urlencode(parameters)


def code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def exchange_code(config: GoogleConfig, code: str, verifier: str) -> dict:
    try:
        with httpx.Client(timeout=12) as client:
            response = client.post(TOKEN_URL, data={
                "code": code,
                "client_id": config.client_id,
                "client_secret": config.client_secret,
                "redirect_uri": config.redirect_uri,
                "grant_type": "authorization_code",
                "code_verifier": verifier,
            })
    except httpx.HTTPError as error:
        raise GoogleError("No se pudo contactar con Google") from error
    if response.status_code != 200:
        raise GoogleError("Google no ha completado la conexión")
    result = response.json()
    if not result.get("refresh_token"):
        raise GoogleError("Google no entregó acceso sin conexión; vuelve a conectar")
    if not set(SCOPES).issubset(set(result.get("scope", "").split())):
        raise GoogleError("Faltan permisos de calendario; vuelve a conectar")
    return result


def refresh_access_token(config: GoogleConfig, encrypted_refresh_token: str) -> str:
    try:
        token = config.cipher.decrypt(encrypted_refresh_token.encode()).decode()
    except InvalidToken as error:
        raise GoogleError("No se puede leer la conexión guardada; vuelve a conectarla", 401) from error
    try:
        with httpx.Client(timeout=12) as client:
            response = client.post(TOKEN_URL, data={
                "client_id": config.client_id,
                "client_secret": config.client_secret,
                "refresh_token": token,
                "grant_type": "refresh_token",
            })
    except httpx.HTTPError as error:
        raise GoogleError("No se pudo contactar con Google") from error
    if response.status_code == 400:
        raise GoogleError("La conexión de Google ha caducado; vuelve a conectarla", 401)
    if response.status_code != 200:
        raise GoogleError("No se pudo renovar la conexión con Google")
    result = response.json()
    if not result.get("access_token"):
        raise GoogleError("Google no devolvió un token de acceso")
    return result["access_token"]


def google_request(
    access_token: str,
    method: str,
    path: str,
    *,
    params: dict | None = None,
    body: dict | None = None,
) -> dict:
    try:
        with httpx.Client(timeout=15) as client:
            response = client.request(
                method,
                CALENDAR_URL + path,
                headers={"Authorization": "Bearer " + access_token},
                params=params,
                json=body,
            )
    except httpx.HTTPError as error:
        raise GoogleError("No se pudo contactar con Google") from error
    if response.status_code not in (200, 201, 204):
        if response.status_code in (401, 403):
            raise GoogleError("Google ha retirado el permiso del calendario", 401)
        if response.status_code == 404:
            raise GoogleError("El calendario o evento de Google ya no existe", 404)
        if response.status_code == 409:
            raise GoogleError("El evento ya existe en Google", 409)
        raise GoogleError("Google Calendar no respondió correctamente")
    return response.json() if response.content else {}


def list_owned_calendars(access_token: str) -> list[dict]:
    rows = []
    page = None
    while True:
        parameters = {"maxResults": 250}
        if page:
            parameters["pageToken"] = page
        result = google_request(
            access_token, "GET", "/users/me/calendarList", params=parameters,
        )
        rows.extend({
            "id": item["id"],
            "name": item.get("summaryOverride") or item.get("summary") or item["id"],
            "primary": item.get("primary", False),
        } for item in result.get("items", []) if item.get("accessRole") == "owner")
        page = result.get("nextPageToken")
        if not page:
            return rows


def utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def event_payload(assignment: Assignment, session: WorkoutSession) -> dict:
    prescription = assignment.prescription_snapshot
    from .prescription_text import prescription_text
    start = utc_datetime(session.scheduled_start)
    end = start + timedelta(minutes=max(prescription.get("planned_minutes", session.planned_minutes), 1))
    return {
        "summary": prescription.get("title") or session.title,
        "description": prescription_text(prescription),
        "location": "En casa" if prescription.get("venue", session.venue) == "home" else "En el club",
        "start": {"dateTime": start.isoformat(), "timeZone": "UTC"},
        "end": {"dateTime": end.isoformat(), "timeZone": "UTC"},
        "extendedProperties": {
            "private": {"teitrainingAssignment": assignment.id},
        },
    }


def payload_hash(payload: dict) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def event_path(calendar_id: str, event_id: str | None = None) -> str:
    path = "/calendars/" + quote(calendar_id, safe="") + "/events"
    return path if event_id is None else path + "/" + quote(event_id, safe="")


def deterministic_event_id(assignment_id: str) -> str:
    # Google event IDs accept base32hex, which includes UUID hex digits 0-9 and a-f.
    return "tei" + assignment_id.replace("-", "")
