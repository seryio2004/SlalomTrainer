"""Conservative display-only fatigue signal from recent training and feedback."""
from datetime import datetime, timedelta, timezone
from statistics import mean

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Assignment, Execution, Feedback, WorkoutSession


def fatigue_indicator(db: Session, club_id: str, athlete_id: str) -> dict:
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=7)
    rows = db.execute(
        select(Assignment, WorkoutSession, Execution, Feedback)
        .join(WorkoutSession, (WorkoutSession.club_id == Assignment.club_id) & (WorkoutSession.id == Assignment.session_id))
        .join(Execution, (Execution.club_id == Assignment.club_id) & (Execution.assignment_id == Assignment.id))
        .join(Feedback, (Feedback.club_id == Assignment.club_id) & (Feedback.assignment_id == Assignment.id))
        .where(Assignment.club_id == club_id, Assignment.athlete_id == athlete_id, Assignment.status.in_(("completed", "partial")))
    ).all()
    loads: list[int] = []
    efforts: list[int] = []
    feelings: list[int] = []
    for _, session, execution, feedback in rows:
        scheduled = session.scheduled_start
        scheduled = scheduled if scheduled.tzinfo else scheduled.replace(tzinfo=timezone.utc)
        if not start <= scheduled <= now or session.training_type == "rest":
            continue
        if execution.actual_minutes is not None and feedback.rpe is not None:
            loads.append(execution.actual_minutes * feedback.rpe)
            efforts.append(feedback.rpe)
        if feedback.feeling is not None:
            feelings.append(feedback.feeling)
    if not loads or not feelings:
        return {"band": "unknown", "available": False}
    load_component = min(sum(loads) / 1400, 1)
    effort_component = (mean(efforts) - 1) / 9
    feeling_component = (5 - mean(feelings)) / 4
    score = 0.55 * load_component + 0.25 * effort_component + 0.20 * feeling_component
    bands = ("very_low", "low", "moderate", "high", "very_high")
    return {"band": bands[min(int(score * 5), 4)], "available": True}
