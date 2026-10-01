from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Assignment


def unfold(payload: bytes) -> str:
    physical = payload.split(b"\r\n")
    assert all(len(line) <= 75 for line in physical)
    assert b"\n" not in payload.replace(b"\r\n", b"")
    logical = []
    for line in physical:
        if line.startswith(b" "):
            logical[-1] += line[1:]
        elif line:
            logical.append(line)
    return b"\r\n".join(logical).decode("utf-8")


def test_athlete_calendar_export_is_private_and_skips_imported_events(workspace):
    w = workspace
    url = w.base + "/calendar/export.ics"
    athlete = w.clients["athlete"]
    coach = w.clients["coach"]
    assert athlete.get(url).status_code == 204
    assert coach.get(url).status_code == 403
    assert w.clients["manager"].get(url).status_code == 403
    assert w.clients["outsider"].get(url).status_code == 403

    tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    base_session = {
        "training_type": "core", "venue": "home", "planned_minutes": 30,
        "scheduled_start": tomorrow,
        "athlete_ids": [w.ids["athlete"]["athlete"]],
        "instructions": "Técnica, control; sin dolor.\nUsa \\ banda elástica.",
        "steps": ["Respira y prepara la esterilla.", "Estira el hombro suavemente."],
    }
    own = coach.post(w.base + "/sessions", json={
        **base_session, "title": "Casa, core; técnica",
    })
    imported = coach.post(w.base + "/sessions", json={
        **base_session, "title": "Importado de Google",
    })
    assert own.status_code == 201 and imported.status_code == 201

    with Session(w.engine) as db:
        row = db.scalar(select(Assignment).where(
            Assignment.session_id == imported.json()["id"],
        ))
        row.prescription_snapshot = {
            **row.prescription_snapshot,
            "source": "Google Calendar",
        }
        db.commit()

    exported = athlete.get(url)
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("text/calendar")
    assert exported.headers["cache-control"] == "no-store"
    assert "attachment" in exported.headers["content-disposition"]
    content = unfold(exported.content)
    assert content.startswith("BEGIN:VCALENDAR\r\nVERSION:2.0")
    assert content.count("BEGIN:VEVENT") == 1
    assert "SUMMARY:Casa\\, core\\; técnica" in content
    assert "DESCRIPTION:Técnica\\, control\\; sin dolor.\\nUsa \\\\ banda elástica." in content
    assert "Indicaciones paso a paso" in content
    assert "LOCATION:En casa" in content
    assert "DTSTART:" in content and "DTEND:" in content
    assert "Importado de Google" not in content
    assert f"UID:{w.ids['athlete']['athlete']}" not in content

    with_imported = athlete.get(url + "?include_imported=true")
    assert with_imported.status_code == 200
    assert unfold(with_imported.content).count("BEGIN:VEVENT") == 2
    assert athlete.get(url + "?start=2020-01-01&end=2026-12-31").status_code == 422
    assert w.clients["peer"].get(url).status_code == 204
