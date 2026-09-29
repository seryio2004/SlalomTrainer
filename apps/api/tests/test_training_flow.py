from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.db import Base, get_db
from app.main import app
from app.models import Athlete, Club, Membership, User
from app.security import hash_password


def test_training_flow_and_isolation(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    engine = create_engine('sqlite+pysqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        a, b = Club(name='A'), Club(name='B')
        db.add_all([a, b]); db.flush()
        ids = {}
        for name, roles, club in [('admin', ['club_admin', 'coach'], a), ('coach', ['coach'], a), ('athlete', ['athlete'], a), ('athlete2', ['athlete'], a), ('other', ['athlete'], b)]:
            user = User(email=name + '@example.org', name=name, password_hash=hash_password('testpassword123'))
            db.add(user); db.flush()
            member = Membership(club_id=club.id, user_id=user.id, roles=roles)
            db.add(member); db.flush()
            athlete = Athlete(club_id=club.id, membership_id=member.id) if 'athlete' in roles else None
            if athlete: db.add(athlete); db.flush()
            ids[name] = (member.id, athlete.id if athlete else None)
        db.commit()
        club_id, other_id = a.id, b.id

    def db_override():
        with Session(engine, expire_on_commit=False) as db:
            yield db

    app.dependency_overrides[get_db] = db_override
    try:
        clients = {name: TestClient(app) for name in ids}
        headers = {}
        for name, client in clients.items():
            assert client.post('/api/v1/auth/login', json={'email': name + '@example.org', 'password': 'testpassword123'}).status_code == 200
            headers[name] = {'X-CSRF-Token': client.cookies['tei_csrf']}
        base = '/api/v1/clubs/' + club_id
        session = {'title': 'Agua', 'training_type': 'water', 'scheduled_start': (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(), 'planned_minutes': 60, 'athlete_ids': [ids['athlete'][1]]}
        assert clients['coach'].post(base + '/sessions', json=session, headers=headers['coach']).status_code == 403
        grant = {'coach_membership_id': ids['coach'][0], 'athlete_id': ids['athlete'][1]}
        assert clients['admin'].post(base + '/grants', json=grant, headers=headers['admin']).status_code == 201
        created = clients['coach'].post(base + '/sessions', json=session, headers=headers['coach'])
        assert created.status_code == 201, created.text
        own = clients['athlete'].get(base + '/assignments').json()
        assert len(own) == 1 and own[0]['title'] == 'Agua'
        assert clients['other'].get(base + '/assignments').status_code == 403
        assert clients['athlete'].get('/api/v1/clubs/' + other_id + '/assignments').status_code == 403
        url = base + '/assignments/' + own[0]['id'] + '/report'
        assert clients['coach'].post(url, json={'status': 'completed'}, headers=headers['coach']).status_code == 403
        assert clients['athlete'].post(url, json={'status': 'completed'}).status_code == 403
        payload = {'status': 'completed', 'actual_minutes': 45, 'rpe': 7, 'feeling': 3, 'sensations': 'Cómodo', 'work_done': 'Técnica de puertas', 'best': 'La entrada', 'worst': 'La salida'}
        assert clients['athlete'].post(url, json={'status': 'completed', 'actual_minutes': 45, 'rpe': 7}, headers=headers['athlete']).status_code == 422
        saved = clients['athlete'].post(url, json=payload, headers=headers['athlete'])
        assert saved.status_code == 200, saved.text
        assert saved.json()['load'] == 315
        assert clients['athlete'].post(url, json=payload, headers=headers['athlete']).status_code == 200
        assert clients['athlete'].post(url, json={**payload, 'actual_minutes': 46}, headers=headers['athlete']).status_code == 409
        summary_url = base + '/sessions/' + created.json()['id'] + '/summary'
        summary = clients['coach'].get(summary_url)
        assert summary.status_code == 200 and summary.json()['known_load'] == 315
        assert summary.json()['counts']['completed'] == 1
        assert clients['other'].get(summary_url).status_code == 403
        own_dashboard = clients['athlete'].get(base + '/dashboard/athlete')
        assert own_dashboard.status_code == 200
        assert own_dashboard.json()['fatigue']['available'] is True
        assert own_dashboard.json()['assignments'][0]['water_feedback']['best'] == 'La entrada'
        coach_dashboard = clients['coach'].get(base + '/athletes/' + ids['athlete'][1] + '/dashboard')
        assert coach_dashboard.status_code == 200
        assert clients['other'].get(base + '/athletes/' + ids['athlete'][1] + '/dashboard').status_code == 403
        home = dict(session, title='Estiramientos', training_type='mobility', venue='home')
        assert clients['coach'].post(base + '/sessions', json=home, headers=headers['coach']).status_code == 422
        home['steps'] = ['Respira antes de empezar', 'Estira cadera con suavidad']
        created_home = clients['coach'].post(base + '/sessions', json=home, headers=headers['coach'])
        assert created_home.status_code == 201
        home_assignment = next(item for item in clients['athlete'].get(base + '/assignments').json() if item['title'] == 'Estiramientos')
        assert home_assignment['venue'] == 'home'
        assert home_assignment['prescription']['steps'] == home['steps']
        assert clients['athlete'].get(summary_url).status_code == 403
        # Group access is a separate grant and publication resolves its members once.
        assert ids['athlete2'][1] not in {item['id'] for item in clients['coach'].get(base + '/athletes').json()}
        group = clients['admin'].post(base + '/groups', json={'name': 'Grupo de prueba'}, headers=headers['admin'])
        assert group.status_code == 201, group.text
        group_id = group.json()['id']
        add_athlete = clients['admin'].post(base + '/groups/' + group_id + '/athletes', json={'athlete_id': ids['athlete2'][1]}, headers=headers['admin'])
        assert add_athlete.status_code == 201, add_athlete.text
        group_payload = dict(session, title='Sesión grupal', scheduled_start=(datetime.now(timezone.utc) + timedelta(days=1)).isoformat(), athlete_ids=[], group_id=group_id)
        assert clients['coach'].post(base + '/sessions', json=group_payload, headers=headers['coach']).status_code == 403
        grant_group = clients['admin'].post(base + '/groups/' + group_id + '/coaches', json={'coach_membership_id': ids['coach'][0]}, headers=headers['admin'])
        assert grant_group.status_code == 201, grant_group.text
        assert clients['coach'].get(base + '/groups').json()[0]['athlete_ids'] == [ids['athlete2'][1]]
        group_session = clients['coach'].post(base + '/sessions', json=group_payload, headers=headers['coach'])
        assert group_session.status_code == 201 and group_session.json()['assigned'] == 1
        assert len(clients['athlete2'].get(base + '/assignments').json()) == 1
        assert clients['coach'].get(base + '/sessions/' + group_session.json()['id'] + '/summary').json()['group_name'] == 'Grupo de prueba'
        assert clients['other'].get(base + '/groups').status_code == 403
        # A partial session without RPE has unknown load, not a fabricated zero.
        later = dict(session, title='Movilidad', training_type='mobility')
        later_created = clients['coach'].post(base + '/sessions', json=later, headers=headers['coach'])
        assert later_created.status_code == 201
        second_assignment = next(item for item in clients['athlete'].get(base + '/assignments').json() if item['title'] == 'Movilidad')
        second_report = clients['athlete'].post(base + '/assignments/' + second_assignment['id'] + '/report', json={'status': 'partial', 'actual_minutes': 20}, headers=headers['athlete'])
        assert second_report.status_code == 200 and second_report.json()['load'] is None
        second_summary = clients['coach'].get(base + '/sessions/' + later_created.json()['id'] + '/summary').json()
        assert second_summary['load_coverage'] == 0
        assert clients['athlete'].post('/api/v1/auth/logout', headers=headers['athlete']).status_code == 204
        assert clients['athlete'].get('/api/v1/me').status_code == 401
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
