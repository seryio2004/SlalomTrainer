"""Invitations and password recovery. Tokens are single use and never returned by API."""
import asyncio
import os
import smtplib
from datetime import timedelta, timezone
from email.message import EmailMessage
from types import SimpleNamespace
from typing import Annotated, Literal
from urllib.parse import urlencode
from cryptography.fernet import Fernet
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import select, update
from .audit import commit, record
from .deps import ActorDep, Db, membership, require_csrf
from .models import AccountAction, Athlete, AuthSession, Membership, User, utc_now
from .security import hash_password, new_secret, secret_hash, verify_password

router = APIRouter()


class InviteIn(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    email: EmailStr
    name: str = Field(min_length=1, max_length=160)
    roles: set[Literal['club_admin', 'coach', 'athlete']] = Field(min_length=1)


class EmailIn(BaseModel):
    email: EmailStr


class AcceptIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    token: str = Field(min_length=20, max_length=256)
    password: str = Field(min_length=12, max_length=128)


def mail_configuration():
    required = ('SMTP_HOST', 'SMTP_FROM', 'PUBLIC_WEB_URL', 'MAIL_TOKEN_ENCRYPTION_KEY')
    if not all(os.environ.get(key) for key in required):
        return None
    try:
        cipher = Fernet(os.environ['MAIL_TOKEN_ENCRYPTION_KEY'].encode())
    except (ValueError, TypeError):
        return None
    url = os.environ['PUBLIC_WEB_URL'].rstrip('/')
    if os.environ.get('APP_ENV') != 'development' and not url.startswith('https://'):
        return None
    return cipher, url


def enqueue(db, user_id, kind, membership_id=None):
    config = mail_configuration()
    if not config:
        raise HTTPException(503, 'El correo de acceso no está configurado')
    # Replace older links of the same purpose. A new invitation cannot revive a withdrawn link.
    db.execute(update(AccountAction).where(AccountAction.user_id == user_id, AccountAction.kind == kind, AccountAction.membership_id == membership_id, AccountAction.used_at.is_(None)).values(used_at=utc_now(), encrypted_token=None))
    token = new_secret()
    row = AccountAction(user_id=user_id, membership_id=membership_id, kind=kind,
                        token_hash=secret_hash(token), encrypted_token=config[0].encrypt(token.encode()).decode(),
                        expires_at=utc_now() + timedelta(hours=48 if kind == 'invitation' else 1))
    db.add(row)
    return row


@router.post('/api/v1/clubs/{club_id}/invitations', status_code=201)
def invite(club_id: str, data: InviteIn, actor: ActorDep, db: Db, x_csrf_token: Annotated[str | None, Header()] = None):
    require_csrf(actor, x_csrf_token)
    membership(db, actor, club_id, 'club_admin')
    user = db.scalar(select(User).where(User.email == str(data.email).lower()))
    if not user:
        user = User(email=str(data.email).lower(), name=data.name, password_hash=hash_password(new_secret()), active=False)
        db.add(user); db.flush()
    member = db.scalar(select(Membership).where(Membership.user_id == user.id, Membership.club_id == club_id))
    if member:
        raise HTTPException(409, 'El usuario ya tiene una membresía; gestiona su estado o reenvía la invitación')
    member = Membership(user_id=user.id, club_id=club_id, roles=sorted(data.roles), active=False)
    db.add(member); db.flush()
    if 'athlete' in data.roles:
        db.add(Athlete(club_id=club_id, membership_id=member.id))
    enqueue(db, user.id, 'invitation', member.id)
    record(db, actor, club_id, 'member.invited', member.id)
    commit(db)
    return {'id': member.id, 'status': 'queued'}


@router.post('/api/v1/clubs/{club_id}/invitations/{member_id}/resend')
def resend(club_id: str, member_id: str, actor: ActorDep, db: Db, x_csrf_token: Annotated[str | None, Header()] = None):
    require_csrf(actor, x_csrf_token)
    membership(db, actor, club_id, 'club_admin')
    member = db.scalar(select(Membership).where(Membership.id == member_id, Membership.club_id == club_id, Membership.active.is_(False)))
    prior = db.scalar(select(AccountAction.id).where(AccountAction.membership_id == member_id, AccountAction.kind == 'invitation'))
    if not member or not prior:
        raise HTTPException(404, 'Invitación no encontrada')
    enqueue(db, member.user_id, 'invitation', member.id)
    record(db, actor, club_id, 'member.invitation_resent', member.id)
    commit(db)
    return {'status': 'queued'}


@router.post('/api/v1/auth/recovery', status_code=202)
def recover(data: EmailIn, db: Db):
    if not mail_configuration():
        raise HTTPException(503, 'El correo de acceso no está configurado')
    user = db.scalar(select(User).where(User.email == str(data.email).lower(), User.active.is_(True)))
    if user:
        active = db.scalar(select(Membership.id).where(Membership.user_id == user.id, Membership.active.is_(True)))
        recent = db.scalar(select(AccountAction.id).where(AccountAction.user_id == user.id, AccountAction.kind == 'recovery', AccountAction.created_at > utc_now() - timedelta(minutes=5)))
        if active and not recent:
            enqueue(db, user.id, 'recovery')
            commit(db)
    return {'message': 'Si la cuenta está activa, recibirás un enlace para recuperar el acceso'}


@router.post('/api/v1/auth/accept')
def accept(data: AcceptIn, db: Db):
    row = db.scalar(select(AccountAction).where(AccountAction.token_hash == secret_hash(data.token)))
    if not row or row.used_at or row.expires_at.replace(tzinfo=timezone.utc) <= utc_now():
        raise HTTPException(422, 'Enlace inválido o caducado')
    user = db.get(User, row.user_id)
    member = db.get(Membership, row.membership_id) if row.membership_id else None
    if row.kind == 'invitation' and user.active and not verify_password(data.password, user.password_hash):
        raise HTTPException(401, 'Para aceptar con una cuenta existente, usa su contraseña actual')
    consumed = db.execute(update(AccountAction).where(AccountAction.id == row.id, AccountAction.used_at.is_(None), AccountAction.expires_at > utc_now()).values(used_at=utc_now(), encrypted_token=None).execution_options(synchronize_session="fetch"))
    if consumed.rowcount != 1:
        raise HTTPException(409, 'El enlace ya se ha utilizado')
    if row.kind == 'invitation':
        if not member or member.active:
            raise HTTPException(409, 'La invitación ya no está pendiente')
        member.active = True
        if not user.active:
            user.password_hash = hash_password(data.password)
            user.active = True
        record(db, SimpleNamespace(user=user), member.club_id, 'member.invitation_accepted', member.id)
    else:
        if not user.active:
            raise HTTPException(422, 'Enlace inválido o caducado')
        user.password_hash = hash_password(data.password)
        db.execute(update(AuthSession).where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None)).values(revoked_at=utc_now()))
        for linked in db.scalars(select(Membership).where(Membership.user_id == user.id, Membership.active.is_(True))):
            record(db, SimpleNamespace(user=user), linked.club_id, 'account.password_recovered', user.id)
    commit(db)
    return {'message': 'Acceso actualizado. Inicia sesión'}


def send_message(row, user, config):
    token = config[0].decrypt(row.encrypted_token.encode()).decode()
    message = EmailMessage()
    message['From'] = os.environ['SMTP_FROM']
    message['To'] = user.email
    message['Subject'] = 'Invitación a TeiTraining' if row.kind == 'invitation' else 'Recuperar acceso a TeiTraining'
    # Fragment avoids leaking credentials in request logs and Referer headers.
    message.set_content('Abre este enlace y establece tu contraseña (o usa la actual si ya tienes cuenta):\n' + config[1] + '/#' + urlencode({'access_token': token}))
    with smtplib.SMTP(os.environ['SMTP_HOST'], int(os.environ.get('SMTP_PORT', '587')), timeout=15) as smtp:
        smtp.starttls()
        if os.environ.get('SMTP_USER'):
            smtp.login(os.environ['SMTP_USER'], os.environ['SMTP_PASSWORD'])
        smtp.send_message(message)


def deliver_pending():
    from .db import SessionLocal
    config = mail_configuration()
    if not config:
        return
    with SessionLocal() as db:
        rows = db.scalars(select(AccountAction).where(AccountAction.used_at.is_(None), AccountAction.sent_at.is_(None), AccountAction.encrypted_token.is_not(None), AccountAction.expires_at > utc_now(), AccountAction.next_attempt_at <= utc_now()).order_by(AccountAction.created_at).limit(10).with_for_update(skip_locked=True)).all()
        for row in rows:
            try:
                send_message(row, db.get(User, row.user_id), config)
                row.sent_at = utc_now()
                row.encrypted_token = None
            except Exception:
                # Do not log SMTP bodies, addresses, credentials or token contents.
                row.attempts += 1
                row.next_attempt_at = utc_now() + timedelta(seconds=min(3600, 30 * 2 ** min(row.attempts, 7)))
        db.commit()


async def poll_mail():
    while True:
        try:
            await asyncio.to_thread(deliver_pending)
        except Exception:
            pass  # Retry on transient database failures; no sensitive exception output.
        await asyncio.sleep(15)


@router.get('/api/v1/clubs/{club_id}/invitations')
def invitation_status(club_id: str, actor: ActorDep, db: Db):
    membership(db, actor, club_id, 'club_admin')
    from .deps import utc_iso
    rows = db.execute(select(AccountAction, Membership).join(Membership, Membership.id == AccountAction.membership_id).where(Membership.club_id == club_id, AccountAction.kind == 'invitation', AccountAction.used_at.is_(None)).order_by(AccountAction.created_at.desc())).all()
    return [{'member_id': member.id, 'name': db.get(User, member.user_id).name, 'expires_at': utc_iso(row.expires_at),
             'sent_at': utc_iso(row.sent_at) if row.sent_at else None, 'attempts': row.attempts,
             'expired': row.expires_at.replace(tzinfo=timezone.utc) <= utc_now()} for row, member in rows]
