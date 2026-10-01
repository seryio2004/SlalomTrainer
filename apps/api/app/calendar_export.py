"""Private, one-time iCalendar export of an athlete's planned assignments."""

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import select

from .audit import record
from .deps import ActorDep, Db, athlete_for_member, membership
from .models import Assignment, Club, WorkoutSession

router = APIRouter(prefix="/api/v1/clubs/{club_id}")


def escape_text(value: str) -> str:
    """Escape RFC 5545 TEXT without changing the original instructions."""
    return (
        value.replace("\\", "\\\\")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def fold_line(line: str) -> list[str]:
    """Keep physical lines within 75 UTF-8 octets, including continuation space."""
    lines = []
    current = ""
    for character in line:
        if len((current + character).encode("utf-8")) > 75:
            lines.append(current)
            current = " " + character
        else:
            current += character
    lines.append(current)
    return lines


def instant(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def event_lines(assignment: Assignment, session: WorkoutSession, stamp: str) -> list[str]:
    prescription = assignment.prescription_snapshot
    title = prescription.get("title") or session.title
    from .prescription_text import prescription_text
    description = prescription_text(prescription)
    start = session.scheduled_start
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    lines = [
        "BEGIN:VEVENT",
        f"UID:{assignment.id}@teitraining.local",
        f"DTSTAMP:{stamp}",
        f"DTSTART:{instant(start)}",
    ]
    minutes = prescription.get("planned_minutes", session.planned_minutes)
    if minutes:
        lines.append(f"DTEND:{instant(start + timedelta(minutes=minutes))}")
    lines += [
        f"SUMMARY:{escape_text(title)}",
        f"DESCRIPTION:{escape_text(description)}",
        f"LOCATION:{escape_text('En casa' if prescription.get('venue', session.venue) == 'home' else 'En el club')}",
        f"SEQUENCE:{assignment.version}",
        "STATUS:CONFIRMED",
        "END:VEVENT",
    ]
    return lines


def render_calendar(rows: list[tuple[Assignment, WorkoutSession]]) -> bytes:
    stamp = instant(datetime.now(timezone.utc))
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//TeiTraining//Entrenamientos//ES",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]
    for assignment, session in rows:
        lines.extend(event_lines(assignment, session, stamp))
    lines.append("END:VCALENDAR")
    return ("\r\n".join(
        physical
        for line in lines
        for physical in fold_line(line)
    ) + "\r\n").encode("utf-8")


@router.get("/calendar/export.ics")
def export_calendar(
    club_id: str,
    actor: ActorDep,
    db: Db,
    start: date | None = None,
    end: date | None = None,
    include_imported: bool = False,
):
    member = membership(db, actor, club_id, "athlete")
    athlete = athlete_for_member(db, club_id, member.id)
    if athlete is None:
        raise HTTPException(404, "Perfil deportivo no encontrado")
    club = db.get(Club, club_id)
    today = datetime.now(ZoneInfo(club.timezone)).date()
    start = start or today
    end = end or start + timedelta(days=365)
    if end < start or (end - start).days > 366:
        raise HTTPException(422, "Selecciona un período válido de hasta un año")

    candidates = db.execute(select(Assignment, WorkoutSession).join(
        WorkoutSession,
        (WorkoutSession.club_id == Assignment.club_id)
        & (WorkoutSession.id == Assignment.session_id),
    ).where(
        Assignment.club_id == club_id,
        Assignment.athlete_id == athlete.id,
        Assignment.status == "planned",
        WorkoutSession.status == "planned",
    ).order_by(WorkoutSession.scheduled_start, Assignment.id)).all()
    rows = []
    for assignment, session in candidates:
        scheduled = session.scheduled_start
        if scheduled.tzinfo is None:
            scheduled = scheduled.replace(tzinfo=timezone.utc)
        local_day = scheduled.astimezone(ZoneInfo(club.timezone)).date()
        if not start <= local_day <= end:
            continue
        if not include_imported and assignment.prescription_snapshot.get("source") == "Google Calendar":
            continue
        rows.append((assignment, session))

    headers = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}
    if not rows:
        return Response(status_code=204, headers=headers)
    record(db, actor, club_id, "calendar.exported", athlete.id)
    db.commit()
    headers["Content-Disposition"] = 'attachment; filename="entrenamientos-teitraining.ics"'
    return Response(
        content=render_calendar(rows),
        media_type="text/calendar; charset=utf-8",
        headers=headers,
    )
