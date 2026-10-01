from copy import deepcopy
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Assignment, CoachAthleteGrant, Execution


def body(w, **changes):
    return {
        'title': 'Fuerza sintética', 'training_type': 'gym', 'venue': 'club',
        'scheduled_start': (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
        'planned_minutes': 60, 'athlete_ids': [w.ids['athlete']['athlete']],
        'objective': 'Técnica de fuerza',
        'blocks': [{'id': 'main', 'title': 'Principal', 'instructions': '', 'exercises': [
            {'id': 'squat', 'name': 'Sentadilla', 'sets': 3, 'reps': 8, 'kg': 30, 'side': 'bilateral', 'load_convention': 'total'},
        ]}], **changes,
    }


def publish(w, data=None):
    response = w.clients['coach'].post(w.base + '/sessions', json=data or body(w))
    assert response.status_code == 201, response.text
    assignment = w.clients['athlete'].get(w.base + '/assignments').json()[-1]
    return response.json()['id'], assignment


def test_library_revisions_freeze_sessions_and_isolate_clubs(workspace):
    w = workspace; coach = w.clients['coach']
    exercise = coach.post(w.base + '/exercises', json={'name': 'Sentadilla', 'reference': True}).json()
    data = body(w); data['blocks'][0]['exercises'][0]['exercise_id'] = exercise['id']
    template = coach.post(w.base + '/templates', json={'prescription': data})
    assert template.status_code == 201
    session_id, assignment = publish(w, data)
    revised = deepcopy(data); revised['blocks'][0]['exercises'][0]['kg'] = 40
    assert coach.put(w.base + '/templates/' + template.json()['id'], json={'version': 1, 'prescription': revised}).status_code == 200
    assert coach.put(w.base + '/templates/' + template.json()['id'], json={'version': 1, 'prescription': revised}).status_code == 409
    assert coach.get(w.base + '/templates').json()[0]['revisions'][0]['prescription']['blocks'][0]['exercises'][0]['kg'] == 30
    assert w.clients['athlete'].get(w.base + '/assignments').json()[0]['prescription'] == assignment['prescription']
    assert w.clients['manager'].get(w.base + '/templates').status_code == 403
    assert w.clients['outsider'].get(w.base + '/exercises').status_code == 403
    assert w.clients['outsider'].post(w.base + '/sessions', json=data).status_code == 403
    assert coach.post(w.base + '/sessions', json=body(w, blocks=[{'id': 'a', 'title': 'A', 'exercises': [{'id': 'x', 'name': 'Ajeno', 'exercise_id': 'other-club'}]}])).status_code == 422
    assert coach.post(w.base + '/sessions', json=body(w, blocks=[{'id': 'a', 'title': 'A'}, {'id': 'a', 'title': 'B'}])).status_code == 422


def test_adaptation_independent_permissions_and_draft_freeze(workspace):
    w = workspace
    with Session(w.engine) as db:
        db.add(CoachAthleteGrant(club_id=w.club_id, coach_membership_id=w.ids['coach']['member'], athlete_id=w.ids['peer']['athlete'])); db.commit()
    data = body(w, athlete_ids=[w.ids['athlete']['athlete'], w.ids['peer']['athlete']])
    session_id, original = publish(w, data)
    peer = w.clients['peer'].get(w.base + '/assignments').json()[0]
    revised = deepcopy(data); revised['blocks'][0]['exercises'][0]['kg'] = 20
    target = w.base + '/assignments/' + original['id']
    request = {'version': original['version'], 'reason': 'Adaptación sintética', 'prescription': revised}
    assert w.clients['manager'].put(target + '/prescription', json=request).status_code == 403
    assert w.clients['outsider'].put(target + '/prescription', json=request).status_code == 403
    response = w.clients['coach'].put(target + '/prescription', json=request)
    assert response.status_code == 200, response.text
    current = response.json()
    assert current['prescription']['blocks'][0]['exercises'][0]['kg'] == 20
    assert current['original_prescription']['blocks'][0]['exercises'][0]['kg'] == 30
    assert w.clients['peer'].get(w.base + '/assignments').json()[0]['prescription'] == peer['prescription']
    assert w.clients['coach'].put(target + '/prescription', json=request).status_code == 409
    assert w.clients['coach'].patch(w.base + '/sessions/' + session_id, json={**{key: value for key, value in data.items() if key != 'athlete_ids'}, 'version': 1}).status_code == 409
    draft = w.clients['athlete'].put(target + '/draft', json={'version': current['version'], 'status': 'partial', 'actual_minutes': 10})
    assert draft.status_code == 200, draft.text
    assert draft.json()['load'] is None and draft.json()['status'] == 'planned'
    request['version'] = draft.json()['version']
    assert w.clients['coach'].put(target + '/prescription', json=request).status_code == 409
    assert w.clients['peer'].post(target + '/report', json={'version': 1, 'actual_date': datetime.now(timezone.utc).date().isoformat(), 'status': 'completed'}).status_code == 404


def test_correction_retry_conflict_load_and_real_date(workspace):
    w = workspace; _, assignment = publish(w); target = w.base + '/assignments/' + assignment['id']
    data = {'version': assignment['version'], 'status': 'completed', 'actual_minutes': 60, 'rpe': 7, 'actual_date': datetime.now(timezone.utc).date().isoformat(),
            'results': [{'item_id': 'squat', 'name': 'Sentadilla', 'origin': 'prescribed', 'set_number': 1, 'reps': 8, 'kg': 30, 'load_convention': 'total', 'side': 'bilateral'}]}
    response = w.clients['athlete'].post(target + '/report', json=data)
    assert response.status_code == 200, response.text
    assert response.json()['load'] == 420
    assert w.clients['athlete'].post(target + '/report', json=data).status_code == 200
    correction = {**data, 'version': response.json()['version'], 'actual_minutes': 45, 'reason': 'Duración corregida'}
    assert w.clients['coach'].patch(target + '/report', json=correction).status_code == 403
    assert w.clients['athlete'].patch(target + '/report', json={**correction, 'reason': ''}).status_code == 422
    fixed = w.clients['athlete'].patch(target + '/report', json=correction)
    assert fixed.status_code == 200 and fixed.json()['load'] == 315
    assert fixed.json()['execution_revisions'][0]['data']['actual_minutes'] == 60
    assert w.clients['athlete'].patch(target + '/report', json=correction).status_code == 409
    follow = w.clients['athlete'].get(w.base + '/follow-up').json()
    assert follow['daily'][0]['known_load'] == 315
    assert follow['compliance_denominator'] == 0  # planned date is future, actual date is today
    assert w.clients['manager'].get(w.base + '/follow-up', params={'athlete_id': w.ids['athlete']['athlete']}).status_code == 403
    assert w.clients['admin'].get(w.base + '/follow-up', params={'athlete_id': w.ids['athlete']['athlete']}).status_code == 404
    with Session(w.engine) as db:
        assert len(db.scalars(select(Execution)).all()) == 1


def test_missing_values_rest_and_unprescribed_results(workspace):
    w = workspace; _, assignment = publish(w); target = w.base + '/assignments/' + assignment['id']
    assert w.clients['athlete'].post(target + '/report', json={'version': 1, 'actual_date': datetime.now(timezone.utc).date().isoformat(), 'status': 'completed', 'results': [{'name': 'Inventado', 'origin': 'prescribed', 'set_number': 1}]}).status_code == 422
    response = w.clients['athlete'].post(target + '/report', json={'version': 1, 'actual_date': datetime.now(timezone.utc).date().isoformat(), 'status': 'partial', 'actual_minutes': 10, 'results': [{'name': 'Plancha', 'origin': 'added', 'set_number': 1, 'seconds': 30, 'side': 'left'}]})
    assert response.status_code == 200
    assert response.json()['load'] is None and response.json()['rpe'] is None
    _, rest = publish(w, body(w, training_type='rest', title='Descanso', blocks=[]))
    target = w.base + '/assignments/' + rest['id']
    assert w.clients['athlete'].post(target + '/report', json={'version': 1, 'actual_date': datetime.now(timezone.utc).date().isoformat(), 'status': 'completed', 'rpe': 1}).status_code == 422
    assert w.clients['athlete'].post(target + '/report', json={'version': 1, 'actual_date': datetime.now(timezone.utc).date().isoformat(), 'status': 'completed'}).status_code == 200


def test_strength_and_tests_comparability(workspace):
    w = workspace; coach = w.clients['coach']
    exercise = coach.post(w.base + '/exercises', json={'name': 'Sentadilla'}).json()['id']
    for reps, side in [(8, 'left'), (8, 'right'), (12, 'left')]:
        data = body(w); data['blocks'][0]['exercises'][0]['exercise_id'] = exercise
        _, assignment = publish(w, data)
        response = w.clients['athlete'].post(w.base + '/assignments/' + assignment['id'] + '/report', json={'version': 1, 'actual_date': datetime.now(timezone.utc).date().isoformat(), 'status': 'completed', 'results': [{'name': 'Sentadilla', 'item_id': 'squat', 'exercise_id': exercise, 'set_number': 1, 'reps': reps, 'kg': 30, 'side': side, 'load_convention': 'per_side'}]})
        assert response.status_code == 200, response.text
    for resistance in ['Drag 100', 'Drag 120', None]:
        _, assignment = publish(w, body(w, training_type='test'))
        result = {'meters': 500, 'seconds': 120, 'model': 'Máquina sintética', 'resistance': resistance, 'protocol': '500 m', 'protocol_version': 1}
        assert w.clients['athlete'].post(w.base + '/assignments/' + assignment['id'] + '/report', json={'version': 1, 'actual_date': datetime.now(timezone.utc).date().isoformat(), 'status': 'completed', 'discipline': result}).status_code == 200
    data = w.clients['athlete'].get(w.base + '/follow-up').json()
    assert len(data['strength']) == 3
    assert sorted(row['known_volume_kg_reps'] for row in data['strength']) == [240, 240, 360]
    assert len(data['tests']) == 3
    assert sum(row['comparable'] for row in data['tests']) == 2


def test_export_only_own_reports_and_no_credentials(workspace):
    w = workspace; _, assignment = publish(w)
    w.clients['athlete'].post(w.base + '/assignments/' + assignment['id'] + '/report', json={'version': 1, 'actual_date': datetime.now(timezone.utc).date().isoformat(), 'status': 'completed', 'comment': 'Valor sintético privado'})
    own = w.clients['athlete'].post(w.base + '/personal-data/export')
    assert own.status_code == 200 and own.headers['cache-control'] == 'no-store'
    assert own.json()['assignments'][0]['comment'] == 'Valor sintético privado'
    peer = w.clients['peer'].post(w.base + '/personal-data/export')
    assert peer.json()['assignments'] == [] and 'Valor sintético privado' not in peer.text
    assert all(key not in own.text for key in ('password_hash', 'token_hash', 'encrypted_refresh_token'))
    assert w.clients['outsider'].post(w.base + '/personal-data/export').status_code == 403
    assert w.clients['athlete'].post(w.base + '/personal-data/export', headers={'X-CSRF-Token': 'wrong'}).status_code == 403


def test_stale_submission_and_utc_normalization(workspace):
    w = workspace
    data = body(w, scheduled_start='2030-03-31T03:30:00+02:00')
    _, item = publish(w, data)
    assert item['scheduled_start'].startswith('2030-03-31T01:30:00')
    target = w.base + '/assignments/' + item['id']
    changed = w.clients['coach'].put(target + '/prescription', json={'version': 1, 'reason': 'Cambio', 'prescription': data})
    assert changed.status_code == 200
    assert w.clients['athlete'].post(target + '/report', json={'version': 1, 'actual_date': datetime.now(timezone.utc).date().isoformat(), 'status': 'completed'}).status_code == 409
    assert w.clients['athlete'].post(target + '/report', json={'status': 'completed'}).status_code == 422


def test_group_union_frozen_context_coverage_and_revocation(workspace):
    w = workspace; admin = w.clients['admin']; coach = w.clients['coach']
    groups = []
    for name in ['Grupo A', 'Grupo B']:
        group = admin.post(w.base + '/groups', json={'name': name}).json()['id']; groups.append(group)
        assert admin.post(w.base + '/groups/' + group + '/coaches', json={'coach_membership_id': w.ids['coach']['member']}).status_code == 201
        for person in ['athlete', 'peer']:
            assert admin.post(w.base + '/groups/' + group + '/athletes', json={'athlete_id': w.ids[person]['athlete']}).status_code == 201
    session_id, athlete = publish(w, body(w, group_id=groups[0]))
    peer = w.clients['peer'].get(w.base + '/assignments').json()[0]
    day = datetime.now(timezone.utc).date().isoformat()
    assert w.clients['athlete'].post(w.base + '/assignments/' + athlete['id'] + '/report', json={'version': 1, 'status': 'completed', 'actual_date': day, 'actual_minutes': 45, 'rpe': 7}).status_code == 200
    assert w.clients['peer'].post(w.base + '/assignments/' + peer['id'] + '/report', json={'version': 1, 'status': 'partial', 'actual_date': day, 'actual_minutes': 20}).status_code == 200
    response = coach.get(w.base + '/follow-up', params=[('group_ids', group) for group in groups])
    assert response.status_code == 200, response.text
    data = response.json()
    assert data['athletes'] == 2 and data['daily'][0]['sessions'] == 2
    assert data['daily'][0]['known_load'] == 315 and data['daily'][0]['load_coverage'] == 1
    assert data['daily'][0]['mean_rpe'] == 7 and data['daily'][0]['rpe_sample'] == 1
    assert w.clients['admin'].get(w.base + '/follow-up', params={'group_ids': groups[0]}).status_code == 403
    assert admin.delete(w.base + '/groups/' + groups[0] + '/athletes/' + w.ids['athlete']['athlete']).status_code == 204
    assert coach.get(w.base + '/follow-up', params=[('group_ids', group) for group in groups]).json()['daily'][0]['sessions'] == 2
    assert w.clients['outsider'].get(w.base + '/follow-up', params={'group_ids': groups[0]}).status_code == 403


def test_running_optional_protocol_fields_and_unknown_execution_date(workspace):
    w = workspace; _, item = publish(w, body(w, training_type='running'))
    target = w.base + '/assignments/' + item['id'] + '/report'
    result = w.clients['athlete'].post(target, json={'version': 1, 'status': 'partial', 'discipline': {'meters': 1000, 'seconds': 300, 'protocol_version': None}})
    assert result.status_code == 200, result.text
    assert result.json()['actual_date'] is None
    data = w.clients['athlete'].get(w.base + '/follow-up').json()
    assert data['undated_executions'] == 1 and data['daily'] == []
    corrected = w.clients['athlete'].patch(target, json={'version': result.json()['version'], 'status': 'partial', 'reason': 'Fecha confirmada', 'actual_date': datetime.now(timezone.utc).date().isoformat(), 'discipline': {'meters': 1000, 'seconds': 300}})
    assert corrected.status_code == 200
    data = w.clients['athlete'].get(w.base + '/follow-up').json()
    assert data['metrics'][0]['pace_seconds_km'] == 300
    assert data['daily'][0]['known_load'] is None
