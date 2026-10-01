"""Durable one-way synchronization of planned assignments to Google Calendar."""

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from .db import SessionLocal
from .google_calendar_service import (
    GoogleError, configuration, deterministic_event_id, event_path, event_payload,
    google_request, payload_hash, refresh_access_token,
)
from .models import (
    Assignment, Athlete, ExternalCalendarEvent, GoogleCalendarConnection,
    GoogleCalendarOutbox, Membership, User, WorkoutSession, utc_now,
)

_access_tokens: dict[str, tuple[str, datetime]] = {}


def clear_cached_token(connection_id: str) -> None:
    _access_tokens.pop(connection_id, None)


def access_token(connection: GoogleCalendarConnection) -> str:
    cached = _access_tokens.get(connection.id)
    if cached and cached[1] > utc_now():
        return cached[0]
    config = configuration()
    if config is None:
        raise GoogleError("Google Calendar no está configurado", 503)
    token = refresh_access_token(config, connection.encrypted_refresh_token)
    _access_tokens[connection.id] = (token, utc_now() + timedelta(minutes=45))
    return token


def queue_new_assignments(db: Session, assignments: list[Assignment]) -> None:
    if not assignments:
        return
    club_id = assignments[0].club_id
    athletes = {row.athlete_id for row in assignments}
    connections = db.scalars(select(GoogleCalendarConnection).where(
        GoogleCalendarConnection.club_id == club_id,
        GoogleCalendarConnection.athlete_id.in_(athletes),
        GoogleCalendarConnection.status == "active",
    )).all()
    by_athlete = {row.athlete_id: row for row in connections}
    for assignment in assignments:
        connection = by_athlete.get(assignment.athlete_id)
        if connection:
            db.add(GoogleCalendarOutbox(
                club_id=club_id,
                connection_id=connection.id,
                assignment_id=assignment.id,
            ))


def queue_changed_assignments(db: Session, assignments: list[Assignment]) -> None:
    if not assignments:
        return
    club_id = assignments[0].club_id
    connections = db.scalars(select(GoogleCalendarConnection).where(
        GoogleCalendarConnection.club_id == club_id,
        GoogleCalendarConnection.athlete_id.in_({row.athlete_id for row in assignments}),
        GoogleCalendarConnection.status == "active",
    )).all()
    by_athlete = {row.athlete_id: row for row in connections}
    for assignment in assignments:
        connection = by_athlete.get(assignment.athlete_id)
        if connection is None:
            continue
        job = db.scalar(select(GoogleCalendarOutbox).where(
            GoogleCalendarOutbox.connection_id == connection.id,
            GoogleCalendarOutbox.assignment_id == assignment.id,
        ))
        if job is None:
            db.add(GoogleCalendarOutbox(
                club_id=club_id,
                connection_id=connection.id,
                assignment_id=assignment.id,
            ))
        elif job.status != "processing":
            job.status = "pending"
            job.next_attempt_at = utc_now()
            job.last_error = None


def queue_existing(db: Session, connection: GoogleCalendarConnection) -> dict:
    """Link original Google events and queue other future sessions once."""
    athlete = db.get(Athlete, connection.athlete_id)
    member = db.get(Membership, athlete.membership_id)
    user = db.get(User, member.user_id)
    same_original_calendar = (
        connection.is_primary
        and connection.calendar_id.lower() == user.email.lower()
    )
    rows = db.execute(select(Assignment, WorkoutSession).join(
        WorkoutSession,
        (WorkoutSession.club_id == Assignment.club_id)
        & (WorkoutSession.id == Assignment.session_id),
    ).where(
        Assignment.club_id == connection.club_id,
        Assignment.athlete_id == connection.athlete_id,
        Assignment.status == "planned",
        WorkoutSession.status == "planned",
        WorkoutSession.scheduled_start >= utc_now(),
    )).all()
    queued = linked = 0
    for assignment, session in rows:
        existing = db.scalar(select(ExternalCalendarEvent).where(
            ExternalCalendarEvent.connection_id == connection.id,
            ExternalCalendarEvent.assignment_id == assignment.id,
        ))
        if existing and existing.payload_hash == payload_hash(event_payload(assignment, session)):
            continue
        prescription = assignment.prescription_snapshot
        if existing is None and same_original_calendar and prescription.get("source") == "Google Calendar":
            source_id = prescription.get("source_event_id")
            if source_id:
                db.add(ExternalCalendarEvent(
                    club_id=connection.club_id,
                    connection_id=connection.id,
                    assignment_id=assignment.id,
                    google_event_id=source_id,
                    payload_hash=payload_hash(event_payload(assignment, session)),
                    origin="imported",
                ))
                linked += 1
                continue
        job = db.scalar(select(GoogleCalendarOutbox).where(
            GoogleCalendarOutbox.connection_id == connection.id,
            GoogleCalendarOutbox.assignment_id == assignment.id,
        ))
        if job is None:
            db.add(GoogleCalendarOutbox(
                club_id=connection.club_id,
                connection_id=connection.id,
                assignment_id=assignment.id,
            ))
            queued += 1
        elif job.status != "processing":
            job.status = "pending"
            job.next_attempt_at = utc_now()
            job.last_error = None
            queued += 1
    return {"queued": queued, "linked_existing": linked}


def send_event(connection: GoogleCalendarConnection, assignment: Assignment, session: WorkoutSession, link):
    token = access_token(connection)
    payload = event_payload(assignment, session)
    fingerprint = payload_hash(payload)
    if link and link.payload_hash == fingerprint:
        return link.google_event_id, fingerprint, link.origin
    if link:
        try:
            google_request(
                token, "PATCH", event_path(connection.calendar_id, link.google_event_id),
                params={"sendUpdates": "none"}, body=payload,
            )
            return link.google_event_id, fingerprint, link.origin
        except GoogleError as error:
            if error.status != 404:
                raise

    event_id = deterministic_event_id(assignment.id)
    try:
        google_request(
            token, "POST", event_path(connection.calendar_id),
            params={"sendUpdates": "none"}, body={"id": event_id, **payload},
        )
    except GoogleError as error:
        if error.status != 409:
            raise
        existing = google_request(token, "GET", event_path(connection.calendar_id, event_id))
        marker = existing.get("extendedProperties", {}).get("private", {}).get("teitrainingAssignment")
        if marker != assignment.id:
            raise GoogleError("Existe un evento distinto con el mismo identificador", 409)
        google_request(
            token, "PATCH", event_path(connection.calendar_id, event_id),
            params={"sendUpdates": "none"}, body=payload,
        )
    return event_id, fingerprint, "created"


def process_job(job_id: str) -> None:
    with SessionLocal() as db:
        job = db.get(GoogleCalendarOutbox, job_id)
        if job is None or job.status != "processing":
            return
        connection = db.get(GoogleCalendarConnection, job.connection_id)
        assignment = db.get(Assignment, job.assignment_id)
        session = db.get(WorkoutSession, assignment.session_id) if assignment else None
        link = db.scalar(select(ExternalCalendarEvent).where(
            ExternalCalendarEvent.connection_id == job.connection_id,
            ExternalCalendarEvent.assignment_id == job.assignment_id,
        ))
        if not connection or connection.status != "active" or not assignment or not session:
            job.status = "done"
            db.commit()
            return
        try:
            if session.status == "cancelled":
                if link and link.payload_hash != "cancelled":
                    try:
                        google_request(
                            access_token(connection), "DELETE",
                            event_path(connection.calendar_id, link.google_event_id),
                            params={"sendUpdates": "none"},
                        )
                    except GoogleError as error:
                        if error.status != 404:
                            raise
                event_id = link.google_event_id if link else None
                fingerprint = "cancelled"
                origin = link.origin if link else None
            else:
                event_id, fingerprint, origin = send_event(connection, assignment, session, link)
        except GoogleError as error:
            job.attempts += 1
            job.last_error = str(error)[:500]
            connection.last_error = job.last_error
            if error.status == 401:
                connection.status = "reconnect_required"
                job.status = "paused"
                clear_cached_token(connection.id)
            else:
                job.status = "retry"
                delay = min(3600, 30 * 2 ** min(job.attempts, 7))
                job.next_attempt_at = utc_now() + timedelta(seconds=delay)
            job.locked_at = None
            db.commit()
            return
        if link is None and event_id is not None:
            link = ExternalCalendarEvent(
                club_id=job.club_id,
                connection_id=connection.id,
                assignment_id=assignment.id,
                google_event_id=event_id,
                payload_hash=fingerprint,
                origin=origin,
            )
            db.add(link)
        elif link is not None:
            link.google_event_id = event_id
            link.payload_hash = fingerprint
            link.origin = origin
            link.synced_at = utc_now()
        job.status = "done"
        job.locked_at = None
        job.last_error = None
        connection.last_error = None
        db.commit()
    requeue_changed_job(job_id)


def requeue_changed_job(job_id: str) -> None:
    """Catch edits committed while a Google request was in flight."""
    with SessionLocal() as db:
        job = db.get(GoogleCalendarOutbox, job_id)
        if job is None or job.status != "done":
            return
        connection = db.get(GoogleCalendarConnection, job.connection_id)
        assignment = db.get(Assignment, job.assignment_id)
        session = db.get(WorkoutSession, assignment.session_id) if assignment else None
        link = db.scalar(select(ExternalCalendarEvent).where(
            ExternalCalendarEvent.connection_id == job.connection_id,
            ExternalCalendarEvent.assignment_id == job.assignment_id,
        ))
        if not connection or connection.status != "active" or not assignment or not session:
            return
        expected = (
            "cancelled" if session.status == "cancelled"
            else payload_hash(event_payload(assignment, session))
        )
        actual = link.payload_hash if link else None
        if expected != actual:
            job.status = "pending"
            job.next_attempt_at = utc_now()
            db.commit()


def process_due_jobs(limit: int = 20) -> int:
    now = utc_now()
    with SessionLocal() as db:
        ids = db.scalars(select(GoogleCalendarOutbox.id).where(or_(
            (GoogleCalendarOutbox.status.in_(("pending", "retry")))
            & (GoogleCalendarOutbox.next_attempt_at <= now),
            (GoogleCalendarOutbox.status == "processing")
            & (GoogleCalendarOutbox.locked_at < now - timedelta(minutes=5)),
        )).order_by(GoogleCalendarOutbox.next_attempt_at).limit(limit)).all()
    processed = 0
    for job_id in ids:
        with SessionLocal() as db:
            result = db.execute(update(GoogleCalendarOutbox).where(
                GoogleCalendarOutbox.id == job_id,
                or_(
                    (GoogleCalendarOutbox.status.in_(("pending", "retry")))
                    & (GoogleCalendarOutbox.next_attempt_at <= now),
                    (GoogleCalendarOutbox.status == "processing")
                    & (GoogleCalendarOutbox.locked_at < now - timedelta(minutes=5)),
                ),
            ).values(status="processing", locked_at=now))
            db.commit()
            if result.rowcount != 1:
                continue
        process_job(job_id)
        processed += 1
    return processed


async def poll_outbox() -> None:
    while True:
        try:
            await asyncio.to_thread(process_due_jobs)
        except Exception:
            # A failed poll must not stop future retries; logging omits private data.
            import logging
            logging.exception("Google Calendar sync poll failed")
        await asyncio.sleep(15)
