from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app import google_calendar, google_calendar_sync
from app.google_calendar_service import GoogleError, SCOPES
from app.models import (
    Assignment, ExternalCalendarEvent, GoogleCalendarConnection,
    GoogleCalendarOutbox,
)


def test_google_connection_links_imports_and_syncs_new_sessions(workspace, monkeypatch):
    w = workspace
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/v1/google-calendar/callback")
    monkeypatch.setenv("GOOGLE_RETURN_URL", "http://localhost:5173/")
    monkeypatch.setenv("GOOGLE_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("GOOGLE_CALENDAR_SYNC_POLL", "0")
    monkeypatch.setattr(
        google_calendar_sync, "SessionLocal",
        sessionmaker(bind=w.engine, expire_on_commit=False),
    )
    google_calendar_sync._access_tokens.clear()

    coach = w.clients["coach"]
    athlete = w.clients["athlete"]
    endpoint = w.base + "/google-calendar"
    tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()

    def publish(title):
        result = coach.post(w.base + "/sessions", json={
            "title": title, "training_type": "gym", "venue": "club",
            "planned_minutes": 45, "scheduled_start": tomorrow,
            "instructions": "Fuerza y control", "athlete_ids": [w.ids["athlete"]["athlete"]],
        })
        assert result.status_code == 201, result.text
        return result.json()["id"]

    imported_id = publish("Ya estaba en Google")
    native_id = publish("Sesión propia")
    with Session(w.engine) as db:
        imported = db.scalar(select(Assignment).where(Assignment.session_id == imported_id))
        imported.prescription_snapshot = {
            **imported.prescription_snapshot,
            "source": "Google Calendar",
            "source_event_id": "original-google-id",
        }
        db.commit()

    assert athlete.get(endpoint).json()["configured"] is True
    assert coach.get(endpoint).status_code == 403
    started = athlete.post(endpoint + "/connect")
    assert started.status_code == 200
    authorization = urlparse(started.json()["url"])
    parameters = parse_qs(authorization.query)
    assert parameters["scope"][0].split() == list(SCOPES)
    assert parameters["code_challenge_method"] == ["S256"]
    state = parameters["state"][0]
    monkeypatch.setattr(google_calendar, "exchange_code", lambda *_: {
        "refresh_token": "private-refresh-token",
        "scope": " ".join(SCOPES),
    })
    callback = athlete.get(
        "/api/v1/google-calendar/callback",
        params={"state": state, "code": "authorized-code"},
        follow_redirects=False,
    )
    assert callback.status_code == 303
    assert "google=connected" in callback.headers["location"]
    assert athlete.get("/api/v1/google-calendar/callback", params={
        "state": state, "code": "again",
    }).status_code == 400
    assert athlete.get(endpoint).json()["status"] == "choose_calendar"

    calendar_id = "athlete@example.org"
    monkeypatch.setattr(google_calendar, "access_token", lambda *_: "access-token")
    monkeypatch.setattr(google_calendar_sync, "access_token", lambda *_: "access-token")
    monkeypatch.setattr(google_calendar, "list_owned_calendars", lambda *_: [
        {"id": calendar_id, "name": "Mi calendario", "primary": True},
    ])
    assert athlete.get(endpoint + "/calendars").json()["calendars"][0]["id"] == calendar_id
    selected = athlete.post(endpoint + "/calendar", json={"calendar_id": calendar_id})
    assert selected.status_code == 200, selected.text
    assert selected.json() == {"queued": 1, "linked_existing": 1}
    assert athlete.post(endpoint + "/calendar", json={"calendar_id": "not-owned"}).status_code == 422

    created = {}
    fail_once = {"active": True}

    def fake_google_request(_, method, path, *, params=None, body=None):
        event_id = path.rsplit("/", 1)[-1]
        if method == "POST":
            if fail_once["active"]:
                fail_once["active"] = False
                raise GoogleError("Error temporal")
            assert body["id"] not in created
            created[body["id"]] = body
            return body
        if method == "PATCH":
            assert event_id in created
            created[event_id] = {**created[event_id], **body}
            return created[event_id]
        if method == "GET":
            return created[event_id]
        if method == "DELETE":
            created.pop(event_id, None)
            return {}
        raise AssertionError(method)

    monkeypatch.setattr(google_calendar_sync, "google_request", fake_google_request)
    assert google_calendar_sync.process_due_jobs() == 1
    with Session(w.engine) as db:
        retry = db.scalar(select(GoogleCalendarOutbox))
        assert retry.status == "retry"
        retry.next_attempt_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()
    assert google_calendar_sync.process_due_jobs() == 1
    assert len(created) == 1
    assert athlete.get(endpoint).json()["pending"] == 0

    with Session(w.engine) as db:
        connection = db.scalar(select(GoogleCalendarConnection))
        assert "private-refresh-token" not in connection.encrypted_refresh_token
        links = db.scalars(select(ExternalCalendarEvent)).all()
        assert len(links) == 2
        assert {link.origin for link in links} == {"imported", "created"}
        assert next(link for link in links if link.origin == "imported").google_event_id == "original-google-id"

    new_id = publish("Nueva publicación")
    assert google_calendar_sync.process_due_jobs() == 1
    assert len(created) == 2
    edit = coach.patch(w.base + f"/sessions/{new_id}", json={
        "version": 1, "title": "Nueva publicación", "training_type": "gym",
        "venue": "club", "scheduled_start": tomorrow,
        "planned_minutes": 45, "instructions": "Contenido corregido", "steps": [],
    })
    assert edit.status_code == 200, edit.text
    assert athlete.patch(w.base + f"/sessions/{new_id}", json={
        "version": 2, "title": "Sin permiso", "training_type": "gym",
        "venue": "club", "scheduled_start": tomorrow,
        "planned_minutes": 45, "instructions": "", "steps": [],
    }).status_code == 403
    assert google_calendar_sync.process_due_jobs() == 1
    assert len(created) == 2
    assert any(event["description"] == "Contenido corregido" for event in created.values())
    assert coach.patch(w.base + f"/sessions/{new_id}", json={
        "version": 1, "title": "Cambios obsoletos", "training_type": "gym",
        "venue": "club", "scheduled_start": tomorrow,
        "planned_minutes": 45, "instructions": "", "steps": [],
    }).status_code == 409

    cancelled = coach.post(w.base + f"/sessions/{new_id}/cancel", json={"version": 2})
    assert cancelled.status_code == 200, cancelled.text
    assert google_calendar_sync.process_due_jobs() == 1
    assert len(created) == 1
    assert coach.post(w.base + f"/sessions/{new_id}/cancel", json={"version": 3}).status_code == 409
    assert athlete.get(w.base + "/assignments").json()
    with Session(w.engine) as db:
        assignment = db.scalar(select(Assignment).where(Assignment.session_id == new_id))
        assert assignment.status == "cancelled"
        link = db.scalar(select(ExternalCalendarEvent).where(
            ExternalCalendarEvent.assignment_id == assignment.id,
        ))
        assert link.payload_hash == "cancelled"

    assert athlete.delete(endpoint).status_code == 204
    assert athlete.get(endpoint).json()["connected"] is False
    with Session(w.engine) as db:
        assert db.scalars(select(ExternalCalendarEvent)).all() == []
