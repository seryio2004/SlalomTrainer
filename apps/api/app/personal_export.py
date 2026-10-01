"""Authenticated own-data export; excludes credentials and other athletes' reports."""
from typing import Annotated
from fastapi import APIRouter, Header, Response
from sqlalchemy import select
from .audit import commit, record
from .deps import ActorDep, Db, assignment_view, athlete_for_member, membership, require_csrf
from .models import Assignment, RecoveryLog, User, WorkoutTemplate
from .recovery import recovery_view

router = APIRouter(prefix='/api/v1/clubs/{club_id}')


@router.post('/personal-data/export')
def export_own(club_id: str, actor: ActorDep, db: Db, response: Response, x_csrf_token: Annotated[str | None, Header()] = None):
    require_csrf(actor, x_csrf_token)
    member = membership(db, actor, club_id)
    athlete = athlete_for_member(db, club_id, member.id)
    result = {'profile': {'name': actor.user.name, 'email': actor.user.email},
              'membership': {'club_id': club_id, 'roles': member.roles},
              'birth_date': athlete.birth_date if athlete else None,
              'assignments': [], 'recovery': [], 'templates': []}
    if athlete:
        result['assignments'] = [assignment_view(db, row) for row in db.scalars(select(Assignment).where(Assignment.club_id == club_id, Assignment.athlete_id == athlete.id))]
        result['recovery'] = [recovery_view(row) for row in db.scalars(select(RecoveryLog).where(RecoveryLog.club_id == club_id, RecoveryLog.athlete_id == athlete.id))]
    if 'coach' in member.roles:
        result['templates'] = [{'prescription': row.prescription, 'version': row.version, 'revisions': row.revisions} for row in db.scalars(select(WorkoutTemplate).where(WorkoutTemplate.club_id == club_id, WorkoutTemplate.coach_membership_id == member.id))]
    record(db, actor, club_id, 'personal_data.exported', member.id)
    commit(db)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Content-Disposition'] = 'attachment; filename="teitraining-datos.json"'
    return result
