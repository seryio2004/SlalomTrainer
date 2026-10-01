"""Coverage-aware follow-up using execution dates and frozen assignment context."""
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Annotated
from zoneinfo import ZoneInfo
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select
from .deps import ActorDep, Db, assignment_view, athlete_for_member, coach_can_see, membership
from .models import Assignment, Athlete, Club, CoachGroupGrant, TrainingGroup

router = APIRouter(prefix="/api/v1/clubs/{club_id}")


def aggregate(items):
    measured = [row for row in items if row['load'] is not None]
    rpes = [row['rpe'] for row in items if row['status'] in ('completed', 'partial') and row['execution_state'] == 'submitted' and row['rpe'] is not None]
    total = sum(row['load'] for row in measured)
    load_athletes = len({row['athlete_id'] for row in measured})
    return {"sessions": len(items), "known_load": total if measured else None,
            "load_coverage": len(measured), "mean_load": total / load_athletes if load_athletes else None, "load_athletes": load_athletes, "athletes": len({row["athlete_id"] for row in items}),
            "mean_rpe": sum(rpes) / len(rpes) if rpes else None, "rpe_sample": len(rpes),
            "pain_count": sum(row['has_pain'] is True for row in items),
            "without_feedback": sum(row['execution_state'] != 'submitted' for row in items)}


def analyze(items, zone, start, end):
    today = datetime.now(ZoneInfo(zone)).date()
    days = defaultdict(list)
    weeks = defaultdict(list)
    compliance = {key: 0 for key in ('completed', 'partial', 'skipped', 'unregistered')}
    undated = 0
    strength = defaultdict(list)
    tests = defaultdict(list)
    metrics = []
    for row in items:
        scheduled = datetime.fromisoformat(row['scheduled_start']).astimezone(ZoneInfo(zone)).date()
        eligible = row['training_type'] != 'rest' and row['status'] not in ('cancelled', 'replaced')
        if eligible and start <= scheduled <= min(end, today) and datetime.fromisoformat(row['scheduled_start']) <= datetime.now(timezone.utc):
            compliance[row['status'] if row['status'] in ('completed', 'partial', 'skipped') else 'unregistered'] += 1
        if not eligible or row['status'] not in ('completed', 'partial') or row['execution_state'] != 'submitted':
            continue
        if not row['actual_date']:
            undated += 1
            continue
        actual = date.fromisoformat(row['actual_date'])
        if not start <= actual <= end:
            continue
        days[actual.isoformat()].append(row)
        monday = actual - timedelta(days=actual.weekday())
        weeks[monday.isoformat()].append(row)
        data = row.get('execution_data') or {}
        for series in data.get('results', []):
            # kg × reps is meaningful only for explicit external load conventions.
            convention = series.get('load_convention')
            comparable = bool(series.get('exercise_id') and convention in ('total', 'per_side') and series.get('kg') is not None and series.get('reps') is not None and series.get('seconds') is None and series.get('meters') is None)
            key = (series.get('exercise_id') or series['name'], series.get('side'), convention, 'repetitions' if series.get('reps') is not None else 'time' if series.get('seconds') is not None else 'distance', series.get('reps'))
            volume = series['kg'] * series['reps'] if comparable else None
            strength[key].append({**series, 'date': actual.isoformat(), 'assignment_id': row['id'], 'volume_kg_reps': volume, 'comparable': comparable})
        result = data.get('discipline')
        if result:
            pace = result['seconds'] * 1000 / result['meters'] if result.get('meters') and result.get('seconds') else None
            metric = {**result, 'date': actual.isoformat(), 'training_type': row['training_type'], 'pace_seconds_km': pace, 'assignment_id': row['id']}
            metrics.append(metric)
            if row['training_type'] == 'test':
                comparable = all(result.get(key) is not None for key in ('meters', 'seconds', 'protocol', 'protocol_version', 'model', 'resistance')) and bool(result.get('meters')) and bool(result.get('seconds')) and all(result.get(key) for key in ('protocol', 'model', 'resistance'))
                key = tuple(result.get(field) for field in ('meters', 'protocol', 'protocol_version', 'model', 'resistance')) if comparable else ('unverified', row['id'])
                tests[key].append({**metric, 'comparable': bool(comparable)})
    weekly = [{"week": key, **aggregate(value)} for key, value in sorted(weeks.items())]
    for week in weekly:
        previous_key = (date.fromisoformat(week['week']) - timedelta(days=7)).isoformat()
        previous = next((row for row in weekly if row['week'] == previous_key), None)
        # Missing observations never mean zero. Compare only complete recorded load coverage.
        complete = week['load_coverage'] == week['sessions']
        sufficient = previous and previous['load_coverage'] == previous['sessions'] and previous['known_load'] is not None and complete
        week['previous_known_load'] = previous['known_load'] if previous else None
        week['difference'] = week['known_load'] - previous['known_load'] if sufficient and week['known_load'] is not None else None
    return {'timezone': zone, 'start': start, 'end': end, 'compliance': compliance,
            'compliance_denominator': sum(compliance.values()), 'undated_executions': undated,
            'daily': [{'date': key, **aggregate(value)} for key, value in sorted(days.items())], 'weekly': weekly,
            'strength': [{'exercise': value[0]['name'], 'exercise_id': value[0].get('exercise_id'), 'side': key[1], 'load_convention': key[2], 'measurement': key[3],
                          'records': sorted(value, key=lambda row: row['date']), 'known_volume_kg_reps': sum(row['volume_kg_reps'] for row in value if row['volume_kg_reps'] is not None) if any(row['volume_kg_reps'] is not None for row in value) else None,
                          'best_kg': max(row['kg'] for row in value if row['comparable']) if any(row['comparable'] for row in value) else None} for key, value in strength.items()],
            'tests': [{'comparable': value[0]['comparable'], 'records': sorted(value, key=lambda row: row['date'])} for value in tests.values()], 'metrics': metrics}


@router.get('/follow-up')
def follow_up(club_id: str, actor: ActorDep, db: Db, athlete_id: str | None = None,
              group_ids: Annotated[list[str] | None, Query()] = None,
              start: date | None = None, end: date | None = None, training_type: str | None = None, exercise_id: str | None = None):
    member = membership(db, actor, club_id)
    if athlete_id or group_ids:
        if 'coach' not in member.roles:
            raise HTTPException(403, 'Sin permiso de entrenador')
    if athlete_id:
        athlete = db.scalar(select(Athlete).where(Athlete.club_id == club_id, Athlete.id == athlete_id))
        if not athlete or not coach_can_see(db, club_id, member.id, athlete.id):
            raise HTTPException(404, 'Deportista no encontrado')
        ids = [athlete.id]
    elif 'coach' in member.roles and group_ids:
        if any(not db.scalar(select(TrainingGroup.id).where(TrainingGroup.club_id == club_id, TrainingGroup.id == group_id)) for group_id in group_ids):
            raise HTTPException(404, 'Grupo no encontrado')
        if any(not db.scalar(select(CoachGroupGrant.id).where(CoachGroupGrant.club_id == club_id, CoachGroupGrant.coach_membership_id == member.id, CoachGroupGrant.group_id == group_id)) for group_id in group_ids):
            raise HTTPException(403, 'Grupo fuera de tu ámbito')
        # Explicit groups filter historical context; authorization remains current per athlete.
        candidates = db.scalars(select(Athlete).where(Athlete.club_id == club_id)).all()
        ids = [athlete.id for athlete in candidates if coach_can_see(db, club_id, member.id, athlete.id)]
    else:
        athlete = athlete_for_member(db, club_id, member.id) if 'athlete' in member.roles else None
        if not athlete:
            raise HTTPException(403, 'Selecciona un deportista o grupo autorizado')
        ids = [athlete.id]
    zone = db.get(Club, club_id).timezone
    today = datetime.now(ZoneInfo(zone)).date()
    start, end = start or today - timedelta(days=83), end or today
    if end < start or (end - start).days > 366:
        raise HTTPException(422, 'El período debe ser válido y no superar un año')
    assignments = db.scalars(select(Assignment).where(Assignment.club_id == club_id, Assignment.athlete_id.in_(ids))).all()
    items = [assignment_view(db, row) for row in assignments if not group_ids or set(row.prescription_snapshot.get('context', {}).get('group_ids', [])) & set(group_ids)]
    if training_type:
        items = [row for row in items if row['training_type'] == training_type]
    result = analyze(items, zone, start, end)
    if exercise_id:
        result['strength'] = [row for row in result['strength'] if row['exercise_id'] == exercise_id]
    result['athletes'] = len({row['athlete_id'] for row in items})
    return result
