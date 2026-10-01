"""Load clearly marked, repeatable synthetic data into the local development club."""

import os
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select

from .db import SessionLocal
from .models import (
    Assignment, Athlete, Club, CoachGroupGrant, Execution, Feedback,
    Membership, TrainingGroup, TrainingGroupMembership, User, WorkoutSession,
)
from .security import hash_password, verify_password
from .planning_demo import add_planning_demo

ADMIN_EMAIL = "admin@example.org"
GROUP_NAME = "Grupo Demo · Cadete K1"
GROUP_DESCRIPTION = "Datos ficticios para probar la vista de entrenador."
ATHLETE_PASSWORD = "12345678"
VIEW_ATHLETE_EMAIL = "demo.vista@example.org"
VIEW_ATHLETE_PASSWORD = "12345678"
ATHLETES = [
    ("Alba Demo", "demo.alba@example.org"),
    ("Bruno Demo", "demo.bruno@example.org"),
    ("Clara Demo", "demo.clara@example.org"),
    ("Diego Demo", "demo.diego@example.org"),
    ("Elena Demo", "demo.elena@example.org"),
    ("Vista Deportista Demo", VIEW_ATHLETE_EMAIL),
]
# Offset in days, local hour, title, type, planned minutes, instructions, sample results.
WORKOUTS = [
    (-3, 17, "Demo · Técnica de puertas", "water", 70, "Calentamiento 15 min; 4 mangas técnicas de 8 puertas; vuelta a la calma 10 min.", "mixed"),
    (-1, 18, "Demo · Fuerza general", "gym", 55, "Sentadilla 3×8, remo 3×10, press 3×8; descanso 90 s; ajustar carga a la técnica.", "some"),
    (1, 17, "Demo · Carrera suave", "running", 40, "Carrera continua a ritmo cómodo; registrar duración real y RPE.", None),
    (2, 18, "Demo · Ergómetro por intervalos", "ergometer", 45, "10 min suaves; 5×3 min de trabajo y 2 min suaves; 5 min de vuelta a la calma.", None),
    (3, 19, "Demo · Estiramientos en casa", "mobility", 25, "Haz la rutina sin rebotes y detente si aparece dolor. Material: esterilla.", None),
    (4, 17, "Demo · Core y movilidad", "core", 30, "Plancha 3×30 s, puente lateral por lado y movilidad de cadera/torácica.", None),
]


def main() -> None:
    if os.environ.get("APP_ENV") != "development":
        raise SystemExit("La carga de ejemplo solo funciona con APP_ENV=development")
    with SessionLocal.begin() as db:
        admin = db.scalar(select(User).where(User.email == ADMIN_EMAIL))
        if not admin:
            raise SystemExit("Primero crea la cuenta de ejemplo con app.bootstrap")
        coach = db.scalar(select(Membership).where(Membership.user_id == admin.id, Membership.active.is_(True)))
        if not coach or "coach" not in coach.roles:
            raise SystemExit("La cuenta de ejemplo no tiene rol de entrenador")
        club = db.get(Club, coach.club_id)
        group = db.scalar(select(TrainingGroup).where(TrainingGroup.club_id == club.id, TrainingGroup.name == GROUP_NAME))
        if group and group.description != GROUP_DESCRIPTION:
            raise SystemExit("Ya existe un grupo con ese nombre que no pertenece a esta demo")
        if group is None:
            group = TrainingGroup(club_id=club.id, name=GROUP_NAME, description=GROUP_DESCRIPTION)
            db.add(group)
            db.flush()
        if not group.active:
            raise SystemExit("El grupo de demo está desactivado")
        today = datetime.now(ZoneInfo(club.timezone)).date()
        athlete_ids = []
        for name, email in ATHLETES:
            password = VIEW_ATHLETE_PASSWORD if email == VIEW_ATHLETE_EMAIL else ATHLETE_PASSWORD
            user = db.scalar(select(User).where(User.email == email))
            if user is None:
                user = User(email=email, name=name, password_hash=hash_password(password))
                db.add(user)
                db.flush()
            elif user.name != name:
                raise SystemExit(f"El email {email} ya pertenece a otra cuenta")
            elif email == VIEW_ATHLETE_EMAIL and not verify_password(password, user.password_hash):
                user.password_hash = hash_password(password)
            member = db.scalar(select(Membership).where(Membership.club_id == club.id, Membership.user_id == user.id))
            if member is None:
                member = Membership(club_id=club.id, user_id=user.id, roles=["athlete"])
                db.add(member)
                db.flush()
            if not member.active or "athlete" not in member.roles:
                raise SystemExit(f"La cuenta {email} no es un deportista activo")
            athlete = db.scalar(select(Athlete).where(Athlete.club_id == club.id, Athlete.membership_id == member.id))
            if athlete is None:
                athlete = Athlete(club_id=club.id, membership_id=member.id)
                db.add(athlete)
                db.flush()
            athlete_ids.append(athlete.id)
            link = db.scalar(select(TrainingGroupMembership).where(
                TrainingGroupMembership.club_id == club.id,
                TrainingGroupMembership.group_id == group.id,
                TrainingGroupMembership.athlete_id == athlete.id,
            ).order_by(TrainingGroupMembership.joined_on.desc(), TrainingGroupMembership.left_on.asc().nulls_first()))
            if link is None:
                db.add(TrainingGroupMembership(club_id=club.id, group_id=group.id, athlete_id=athlete.id, joined_on=today - timedelta(days=30)))
            elif link.left_on is not None:
                raise SystemExit(f"{email} salió del grupo; no se reactivará automáticamente")
        grant = db.scalar(select(CoachGroupGrant).where(
            CoachGroupGrant.club_id == club.id,
            CoachGroupGrant.coach_membership_id == coach.id,
            CoachGroupGrant.group_id == group.id,
        ))
        if grant is None:
            db.add(CoachGroupGrant(club_id=club.id, coach_membership_id=coach.id, group_id=group.id))

        for day_offset, hour, title, training_type, minutes, instructions, results in WORKOUTS:
            session = db.scalar(select(WorkoutSession).where(
                WorkoutSession.club_id == club.id,
                WorkoutSession.group_id == group.id,
                WorkoutSession.title == title,
            ))
            if session is None:
                local_start = datetime.combine(today + timedelta(days=day_offset), time(hour), ZoneInfo(club.timezone))
                venue = "home" if title == "Demo · Estiramientos en casa" else "club"
                steps = [
                    "Prepara una esterilla y respira con calma durante un minuto.",
                    "Estira los flexores de cadera: dos veces por lado, sin rebotes.",
                    "Moviliza la zona torácica con giros suaves: ocho repeticiones por lado.",
                    "Termina con gemelos e isquios: mantén cada posición con una respiración cómoda.",
                ] if venue == "home" else []
                prescription = {"title": title, "training_type": training_type, "venue": venue, "instructions": instructions, "steps": steps, "planned_minutes": minutes}
                session = WorkoutSession(
                    club_id=club.id, coach_membership_id=coach.id, group_id=group.id,
                    title=title, training_type=training_type, venue=venue,
                    scheduled_start=local_start.astimezone(timezone.utc), planned_minutes=minutes,
                    prescription=prescription,
                )
                db.add(session)
                db.flush()
            for index, athlete_id in enumerate(athlete_ids):
                existing = db.scalar(select(Assignment).where(
                    Assignment.club_id == club.id,
                    Assignment.session_id == session.id,
                    Assignment.athlete_id == athlete_id,
                ))
                if existing:
                    if training_type == "water" and existing.status in ("completed", "partial"):
                        feedback = db.scalar(select(Feedback).where(Feedback.club_id == club.id, Feedback.assignment_id == existing.id))
                        if feedback and not feedback.sensations:
                            feedback.sensations = "Buenas sensaciones al entrar en las puertas."
                            feedback.work_done = "Trazada y ritmo en cuatro mangas técnicas."
                            feedback.best = "La precisión en la primera mitad."
                            feedback.worst = "La salida de la última puerta."
                    continue
                sample_index = 0 if index == len(ATHLETES) - 1 else index
                status = "planned"
                if results == "mixed":
                    status = "completed" if sample_index < 3 else "partial" if sample_index == 3 else "skipped"
                elif results == "some" and sample_index < 3:
                    status = "completed" if sample_index < 2 else "partial"
                assignment = Assignment(
                    club_id=club.id, session_id=session.id, athlete_id=athlete_id,
                    status=status, prescription_snapshot=session.prescription.copy(),
                )
                db.add(assignment)
                db.flush()
                if status != "planned":
                    duration = None if status == "skipped" else minutes - (15 if status == "partial" else 0)
                    rpe = None if status == "skipped" else 5 + sample_index
                    db.add(Execution(club_id=club.id, assignment_id=assignment.id, actual_minutes=duration, notes="Registro ficticio"))
                    db.add(Feedback(
                        club_id=club.id, assignment_id=assignment.id, rpe=rpe,
                        feeling=4 if status == "completed" else 3 if status == "partial" else None,
                        has_pain=sample_index == 3, pain_area="hombro" if sample_index == 3 else None,
                        comment="Datos de prueba",
                        sensations="Buenas sensaciones al entrar en las puertas." if training_type == "water" and status != "skipped" else None,
                        work_done="Trazada y ritmo en cuatro mangas técnicas." if training_type == "water" and status != "skipped" else None,
                        best="La precisión en la primera mitad." if training_type == "water" and status != "skipped" else None,
                        worst="La salida de la última puerta." if training_type == "water" and status != "skipped" else None,
                    ))
        add_planning_demo(db, club, coach, group, athlete_ids[-1])
        print(f"Grupo: {group.name} · {len(athlete_ids)} deportistas · {len(WORKOUTS)} sesiones de ejemplo")
        print(f"Entrenador: {ADMIN_EMAIL}")
        print(f"Deportista de prueba: {VIEW_ATHLETE_EMAIL} / {VIEW_ATHLETE_PASSWORD}")


if __name__ == "__main__":
    main()
