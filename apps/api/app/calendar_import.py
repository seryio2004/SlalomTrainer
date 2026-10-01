"""Import a reviewed personal calendar manifest into a local club.

The manifest is private data. Keep it out of Git and run with APP_ENV=development.
"""

import argparse
import json
import os
import secrets
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import NAMESPACE_URL, uuid5
from zoneinfo import ZoneInfo

from sqlalchemy import select

from .audit import record
from .db import SessionLocal
from .models import (
    Assignment, Athlete, Club, CoachGroupGrant, Membership, Microcycle,
    PlanDay, Season, TrainingGroup, TrainingGroupMembership, TrainingPhase,
    TrainingPlan, User, WorkoutSession,
)
from .security import hash_password


def training_type(title: str) -> str:
    lower = title.casefold()
    for word, kind in (
        ("agua", "water"), ("ergómetro", "ergometer"),
        ("gym", "gym"), ("fuerza", "gym"),
        ("trail", "running"), ("correr", "running"),
        ("core", "core"), ("estiramientos", "mobility"),
    ):
        if word in lower:
            return kind
    raise ValueError(f"No se reconoce el tipo de entrenamiento: {title}")


def validate_events(manifest: dict, timezone_name: str) -> list[dict]:
    zone = ZoneInfo(timezone_name)
    by_schedule = {}
    for event in manifest["events"]:
        title = event["title"].strip()
        start = datetime.fromisoformat(event["start"])
        end = datetime.fromisoformat(event["end"])
        if not start.tzinfo or not end.tzinfo or end <= start:
            raise ValueError(f"Horario inválido: {title}")
        if len(title) > 160 or len(event["description"]) > 4000:
            raise ValueError(f"Contenido demasiado largo: {title}")
        if start.astimezone(zone).date() > date(2027, 6, 30):
            raise ValueError(f"Fecha fuera del período: {title}")
        minutes = round((end - start).total_seconds() / 60)
        if not 1 <= minutes <= 1440:
            raise ValueError(f"Duración inválida: {title}")
        kind = training_type(title)
        venue = "home" if "casa" in title.casefold() or kind == "mobility" else "club"
        description = event["description"].strip()
        steps = [part.strip() for part in description.split("•")[1:]] if venue == "home" else []
        if venue == "home" and (not steps or len(steps) > 20 or any(len(step) > 500 for step in steps)):
            raise ValueError(f"Faltan pasos claros para el entrenamiento en casa: {title}")
        key = (title, start.astimezone(timezone.utc).isoformat())
        if key in by_schedule:
            continue
        by_schedule[key] = {
            "title": title,
            "source_event_id": event["id"],
            "start": start.astimezone(timezone.utc),
            "day": start.astimezone(zone).date(),
            "minutes": minutes,
            "kind": kind,
            "venue": venue,
            "instructions": description,
            "steps": steps,
        }
    return sorted(by_schedule.values(), key=lambda event: event["start"])


def get_or_create(db, model, filters: dict, values: dict):
    row = db.scalar(select(model).filter_by(**filters))
    if row is None:
        row = model(**filters, **values)
        db.add(row)
        db.flush()
    return row


def plan_day(db, club: Club, coach: Membership, person: str, local_day: date) -> PlanDay:
    year = local_day.year
    year_start, year_end = date(year, 1, 1), date(year, 12, 31)
    season = get_or_create(db, Season, {
        "club_id": club.id, "name": f"Personal · {person} · {year}",
    }, {
        "starts_on": year_start, "ends_on": year_end,
        "age_reference_date": year_end, "objectives": "Entrenamientos personales importados",
        "status": "draft",
    })
    if season.status == "closed":
        raise ValueError(f"La temporada personal {year} está cerrada")
    phase = get_or_create(db, TrainingPhase, {
        "club_id": club.id, "season_id": season.id,
        "name": "Preparación personal",
    }, {
        "starts_on": year_start, "ends_on": year_end,
        "objectives": "Programa de entrenamiento personal",
    })
    plan = get_or_create(db, TrainingPlan, {
        "club_id": club.id, "phase_id": phase.id,
        "coach_membership_id": coach.id, "name": f"Plan personal · {person}",
    }, {
        "starts_on": year_start, "ends_on": year_end,
        "objectives": "Sesiones importadas de calendario",
    })
    if plan.status == "archived":
        raise ValueError(f"El plan personal {year} está archivado")
    monday = local_day - timedelta(days=local_day.weekday())
    cycle = get_or_create(db, Microcycle, {
        "club_id": club.id, "plan_id": plan.id,
        "name": f"Semana del {monday.isoformat()}",
    }, {
        "starts_on": max(monday, year_start),
        "ends_on": min(monday + timedelta(days=6), year_end),
        "objectives": "Entrenamientos de la semana",
    })
    return get_or_create(db, PlanDay, {
        "club_id": club.id, "microcycle_id": cycle.id,
        "local_date": local_day,
    }, {})


def import_events(db, events: list[dict], email: str, name: str, group_name: str):
    coach_user = db.scalar(select(User).where(User.email == "admin@example.org"))
    if coach_user is None:
        raise ValueError("Falta la cuenta entrenadora admin@example.org")
    coach = db.scalar(select(Membership).where(
        Membership.user_id == coach_user.id, Membership.active.is_(True),
    ))
    if coach is None or "coach" not in coach.roles:
        raise ValueError("La cuenta de ejemplo no puede entrenar")
    club = db.get(Club, coach.club_id)
    actor = SimpleNamespace(user=coach_user)
    user = db.scalar(select(User).where(User.email == email))
    password = None
    if user is None:
        password = secrets.token_urlsafe(24)
        user = User(email=email, name=name, password_hash=hash_password(password))
        db.add(user)
        db.flush()
    member = get_or_create(db, Membership, {
        "club_id": club.id, "user_id": user.id,
    }, {"roles": ["athlete"]})
    if not member.active or "athlete" not in member.roles:
        raise ValueError("La cuenta existe pero no es un deportista activo en este club")
    athlete = get_or_create(db, Athlete, {
        "club_id": club.id, "membership_id": member.id,
    }, {})
    group = get_or_create(db, TrainingGroup, {
        "club_id": club.id, "name": group_name,
    }, {"description": "Entrenamientos personales importados de Google Calendar"})
    if not group.active:
        raise ValueError("El grupo personal está archivado")
    today = datetime.now(ZoneInfo(club.timezone)).date()
    link = db.scalar(select(TrainingGroupMembership).where(
        TrainingGroupMembership.club_id == club.id,
        TrainingGroupMembership.group_id == group.id,
        TrainingGroupMembership.athlete_id == athlete.id,
        TrainingGroupMembership.left_on.is_(None),
    ))
    if link is None:
        db.add(TrainingGroupMembership(
            club_id=club.id, group_id=group.id,
            athlete_id=athlete.id, joined_on=today,
        ))
    get_or_create(db, CoachGroupGrant, {
        "club_id": club.id, "coach_membership_id": coach.id,
        "group_id": group.id,
    }, {})

    created = 0
    for event in events:
        day = plan_day(db, club, coach, name, event["day"])
        session_id = str(uuid5(
            NAMESPACE_URL,
            f"teitraining:{club.id}:{group.id}:{event['title']}:{event['start'].isoformat()}",
        ))
        if db.get(WorkoutSession, session_id):
            continue
        prescription = {
            "title": event["title"], "training_type": event["kind"],
            "venue": event["venue"], "instructions": event["instructions"],
            "steps": event["steps"], "planned_minutes": event["minutes"],
            "source": "Google Calendar",
            "source_event_id": event["source_event_id"],
        }
        db.add(WorkoutSession(
            id=session_id, club_id=club.id, coach_membership_id=coach.id,
            group_id=group.id, plan_day_id=day.id,
            title=event["title"], training_type=event["kind"],
            venue=event["venue"], scheduled_start=event["start"],
            planned_minutes=event["minutes"], prescription=prescription,
        ))
        db.add(Assignment(
            club_id=club.id, session_id=session_id, athlete_id=athlete.id,
            prescription_snapshot=prescription.copy(),
        ))
        record(db, actor, club.id, "session.imported", session_id)
        created += 1
    return created, password


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--group", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if os.environ.get("APP_ENV") != "development":
        raise SystemExit("Esta importación local requiere APP_ENV=development")
    manifest = json.loads(args.manifest.read_text())
    with SessionLocal.begin() as db:
        coach_user = db.scalar(select(User).where(User.email == "admin@example.org"))
        if coach_user is None:
            raise SystemExit("Falta admin@example.org")
        coach = db.scalar(select(Membership).where(Membership.user_id == coach_user.id))
        club = db.get(Club, coach.club_id)
        events = validate_events(manifest, club.timezone)
        if args.dry_run:
            print(f"Vista previa: {len(events)} sesiones únicas, {events[0]['day']} a {events[-1]['day']}")
            return
        created, password = import_events(db, events, args.email.lower().strip(), args.name.strip(), args.group.strip())
    print(f"Grupo: {args.group} · Nuevas sesiones: {created} · Total revisado: {len(events)}")
    if password:
        print(f"Contraseña inicial para {args.email}: {password}")
    else:
        print("Cuenta existente: se conserva su contraseña")


if __name__ == "__main__":
    main()
