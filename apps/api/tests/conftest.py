from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import Athlete, Club, CoachAthleteGrant, Membership, User
from app.security import hash_password


@pytest.fixture
def workspace(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    ids = {}
    with Session(engine) as db:
        club = Club(name="Club de prueba")
        other = Club(name="Club ajeno")
        db.add_all([club, other])
        db.flush()
        for name, roles, target in [
            ("admin", ["club_admin", "coach"], club),
            ("manager", ["club_admin"], club),
            ("coach", ["coach"], club),
            ("athlete", ["athlete"], club),
            ("peer", ["athlete"], club),
            ("outsider", ["club_admin", "coach"], other),
        ]:
            user = User(
                name=name, email=f"{name}@example.org",
                password_hash=hash_password("testing-password"),
            )
            db.add(user)
            db.flush()
            member = Membership(club_id=target.id, user_id=user.id, roles=roles)
            db.add(member)
            db.flush()
            athlete = None
            if "athlete" in roles:
                athlete = Athlete(club_id=target.id, membership_id=member.id)
                db.add(athlete)
                db.flush()
            ids[name] = {"member": member.id, "athlete": athlete.id if athlete else None}
        db.add(CoachAthleteGrant(
            club_id=club.id, coach_membership_id=ids["coach"]["member"],
            athlete_id=ids["athlete"]["athlete"],
        ))
        db.commit()
        club_id, other_id = club.id, other.id

    def override_db():
        with Session(engine, expire_on_commit=False) as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    clients = {name: TestClient(app) for name in ids}
    for name, client in clients.items():
        response = client.post("/api/v1/auth/login", json={
            "email": f"{name}@example.org", "password": "testing-password",
        })
        assert response.status_code == 200
        client.headers["X-CSRF-Token"] = client.cookies["tei_csrf"]
    try:
        yield SimpleNamespace(
            clients=clients, ids=ids, club_id=club_id, other_id=other_id,
            base=f"/api/v1/clubs/{club_id}", engine=engine,
        )
    finally:
        for client in clients.values():
            client.close()
        app.dependency_overrides.clear()
        engine.dispose()
