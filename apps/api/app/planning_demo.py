"""Synthetic planning and recovery records, preserving existing user edits."""
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select

from .models import (
    Microcycle, PlanDay, RecoveryLog, Season, TrainingPhase, TrainingPlan,
    WorkoutSession,
)


def add_planning_demo(db, club, coach, group, athlete_id):
    today = datetime.now(ZoneInfo(club.timezone)).date()
    start, end = date(today.year, 1, 1), date(today.year, 12, 31)
    season = db.scalar(select(Season).where(
        Season.club_id == club.id, Season.name == f"Demo · Temporada {today.year}",
    ))
    if season is None:
        active = db.scalar(select(Season.id).where(
            Season.club_id == club.id, Season.status == "active",
        ))
        season = Season(
            club_id=club.id, name=f"Demo · Temporada {today.year}",
            starts_on=start, ends_on=end, age_reference_date=end,
            status="draft" if active else "active", objectives="Planificación ficticia de prueba",
        )
        db.add(season)
        db.flush()
    if season.status != "closed":
        phase = db.scalar(select(TrainingPhase).where(
            TrainingPhase.club_id == club.id, TrainingPhase.season_id == season.id,
            TrainingPhase.name == "Demo · Preparación general",
        ))
        if phase is None:
            phase = TrainingPhase(
                club_id=club.id, season_id=season.id, name="Demo · Preparación general",
                starts_on=season.starts_on, ends_on=season.ends_on,
                objectives="Técnica y condición física",
            )
            db.add(phase)
            db.flush()
        plan = db.scalar(select(TrainingPlan).where(
            TrainingPlan.club_id == club.id, TrainingPlan.phase_id == phase.id,
            TrainingPlan.coach_membership_id == coach.id,
            TrainingPlan.name == "Demo · Cadete K1",
        ))
        if plan is None:
            plan = TrainingPlan(
                club_id=club.id, phase_id=phase.id, coach_membership_id=coach.id,
                name="Demo · Cadete K1", starts_on=phase.starts_on, ends_on=phase.ends_on,
                objectives="Combinar trabajo en el club y movilidad en casa",
            )
            db.add(plan)
            db.flush()
        if plan.status != "archived":
            attach_demo_sessions(db, club, coach, group, plan)

    for offset, sleep, fatigue, energy in [(2, 3, 3, 3), (1, 4, 2, 4), (0, 4, 2, 4)]:
        day = today - timedelta(days=offset)
        existing = db.scalar(select(RecoveryLog.id).where(
            RecoveryLog.club_id == club.id, RecoveryLog.athlete_id == athlete_id,
            RecoveryLog.local_date == day,
        ))
        if existing is None:
            db.add(RecoveryLog(
                club_id=club.id, athlete_id=athlete_id, local_date=day,
                sleep=sleep, fatigue=fatigue, energy=energy,
                comment="Datos ficticios para probar el registro de recuperación.",
            ))


def attach_demo_sessions(db, club, coach, group, plan):
    sessions = db.scalars(select(WorkoutSession).where(
        WorkoutSession.club_id == club.id, WorkoutSession.group_id == group.id,
        WorkoutSession.coach_membership_id == coach.id,
        WorkoutSession.title.like("Demo · %"), WorkoutSession.plan_day_id.is_(None),
    )).all()
    for session in sessions:
        timestamp = session.scheduled_start
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        day = timestamp.astimezone(ZoneInfo(club.timezone)).date()
        if not plan.starts_on <= day <= plan.ends_on:
            continue
        monday = day - timedelta(days=day.weekday())
        name = f"Demo · Semana del {monday.isoformat()}"
        cycle = db.scalar(select(Microcycle).where(
            Microcycle.club_id == club.id, Microcycle.plan_id == plan.id, Microcycle.name == name,
        ))
        if cycle is None:
            cycle = Microcycle(
                club_id=club.id, plan_id=plan.id, name=name,
                starts_on=max(monday, plan.starts_on),
                ends_on=min(monday + timedelta(days=6), plan.ends_on),
                objectives="Semana de ejemplo",
            )
            db.add(cycle)
            db.flush()
        if not cycle.starts_on <= day <= cycle.ends_on:
            continue
        plan_day = db.scalar(select(PlanDay).where(
            PlanDay.club_id == club.id, PlanDay.microcycle_id == cycle.id, PlanDay.local_date == day,
        ))
        if plan_day is None:
            plan_day = PlanDay(club_id=club.id, microcycle_id=cycle.id, local_date=day)
            db.add(plan_day)
            db.flush()
        session.plan_day_id = plan_day.id
