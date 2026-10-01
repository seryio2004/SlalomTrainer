from datetime import timedelta
from unittest.mock import patch
from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.account_access import deliver_pending
from app.models import AccountAction, Membership, User, utc_now


def configure(monkeypatch):
    key = Fernet.generate_key(); cipher = Fernet(key)
    monkeypatch.setenv('MAIL_TOKEN_ENCRYPTION_KEY', key.decode())
    monkeypatch.setenv('PUBLIC_WEB_URL', 'http://localhost:5173')
    monkeypatch.setenv('SMTP_HOST', 'smtp.example.invalid')
    monkeypatch.setenv('SMTP_FROM', 'no-reply@example.org')
    return cipher


def last_token(w, cipher, kind):
    with Session(w.engine) as db:
        row = db.scalar(select(AccountAction).where(AccountAction.kind == kind, AccountAction.used_at.is_(None)).order_by(AccountAction.created_at.desc()))
        return cipher.decrypt(row.encrypted_token.encode()).decode(), row.id


def test_invitation_single_use_isolation_and_revocation(workspace, monkeypatch):
    w = workspace; cipher = configure(monkeypatch)
    data = {'email': 'new@example.org', 'name': 'Persona sintética', 'roles': ['athlete']}
    assert w.clients['coach'].post(w.base + '/invitations', json=data).status_code == 403
    assert w.clients['outsider'].post(w.base + '/invitations', json=data).status_code == 403
    response = w.clients['admin'].post(w.base + '/invitations', json=data)
    assert response.status_code == 201, response.text
    assert 'token' not in response.json()
    assert w.clients['athlete'].post('/api/v1/auth/login', json={'email': data['email'], 'password': 'new-testing-password'}).status_code == 401
    token, _ = last_token(w, cipher, 'invitation')
    assert w.clients['athlete'].post('/api/v1/auth/accept', json={'token': token, 'password': 'new-testing-password'}).status_code == 200
    assert w.clients['athlete'].post('/api/v1/auth/accept', json={'token': token, 'password': 'new-testing-password'}).status_code == 422
    assert w.clients['athlete'].post('/api/v1/auth/login', json={'email': data['email'], 'password': 'new-testing-password'}).status_code == 200
    assert w.clients['admin'].patch(w.base + '/members/' + response.json()['id'] + '/status', json={'active': False}).status_code == 200
    assert w.clients['athlete'].get(w.base + '/assignments').status_code == 403


def test_recovery_generic_response_expiry_and_sessions_revoked(workspace, monkeypatch):
    w = workspace; cipher = configure(monkeypatch)
    client = w.clients['athlete']
    known = client.post('/api/v1/auth/recovery', json={'email': 'athlete@example.org'})
    unknown = client.post('/api/v1/auth/recovery', json={'email': 'absent@example.org'})
    assert known.status_code == unknown.status_code == 202 and known.json() == unknown.json()
    token, action_id = last_token(w, cipher, 'recovery')
    assert client.post('/api/v1/auth/recovery', json={'email': 'athlete@example.org'}).status_code == 202
    with Session(w.engine) as db:
        assert len(db.scalars(select(AccountAction)).all()) == 1
    assert client.post('/api/v1/auth/accept', json={'token': token, 'password': 'replacement-password'}).status_code == 200
    assert client.get('/api/v1/me').status_code == 401
    assert client.post('/api/v1/auth/login', json={'email': 'athlete@example.org', 'password': 'testing-password'}).status_code == 401
    assert client.post('/api/v1/auth/login', json={'email': 'athlete@example.org', 'password': 'replacement-password'}).status_code == 200


def test_mail_retries_without_disclosing_token(workspace, monkeypatch):
    w = workspace; configure(monkeypatch)
    w.clients['admin'].post(w.base + '/invitations', json={'email': 'new@example.org', 'name': 'Sintético', 'roles': ['athlete']})
    monkeypatch.setattr('app.db.SessionLocal', lambda: Session(w.engine))
    with patch('app.account_access.send_message', side_effect=OSError('Synthetic failure')):
        deliver_pending()
    with Session(w.engine) as db:
        row = db.scalar(select(AccountAction)); assert row.attempts == 1 and row.encrypted_token
        row.next_attempt_at = utc_now() - timedelta(seconds=1); db.commit()
    with patch('app.account_access.send_message') as sender:
        deliver_pending(); assert sender.call_count == 1
    with Session(w.engine) as db:
        row = db.scalar(select(AccountAction)); assert row.sent_at and row.encrypted_token is None


def test_expired_and_withdrawn_invitation_and_existing_account(workspace, monkeypatch):
    w = workspace; cipher = configure(monkeypatch)
    invitation = {'email': 'expired@example.org', 'name': 'Sintético', 'roles': ['athlete']}
    response = w.clients['admin'].post(w.base + '/invitations', json=invitation)
    token, action_id = last_token(w, cipher, 'invitation')
    with Session(w.engine) as db:
        row = db.get(AccountAction, action_id); row.expires_at = utc_now() - timedelta(seconds=1); db.commit()
    assert w.clients['athlete'].post('/api/v1/auth/accept', json={'token': token, 'password': 'testing-password'}).status_code == 422
    assert w.clients['admin'].post(w.base + '/invitations/' + response.json()['id'] + '/resend').status_code == 200
    token, _ = last_token(w, cipher, 'invitation')
    assert w.clients['admin'].patch(w.base + '/members/' + response.json()['id'] + '/status', json={'active': False}).status_code == 200
    assert w.clients['athlete'].post('/api/v1/auth/accept', json={'token': token, 'password': 'testing-password'}).status_code == 422


def test_roles_revoke_existing_access_and_retain_admin(workspace):
    w = workspace
    assert w.clients['coach'].patch(w.base + '/members/' + w.ids['admin']['member'] + '/roles', json={'roles': ['athlete']}).status_code == 403
    assert w.clients['admin'].patch(w.base + '/members/' + w.ids['manager']['member'] + '/roles', json={'roles': ['athlete']}).status_code == 200
    assert w.clients['admin'].patch(w.base + '/members/' + w.ids['admin']['member'] + '/roles', json={'roles': ['coach']}).status_code == 409
    assert w.clients['admin'].patch(w.base + '/members/' + w.ids['coach']['member'] + '/roles', json={'roles': ['athlete']}).status_code == 200
    assert w.clients['coach'].get(w.base + '/sessions').status_code == 403
