from datetime import datetime, timedelta, timezone


def create_hierarchy(workspace):
    base = workspace.base + "/planning"
    admin = workspace.clients["admin"]
    coach = workspace.clients["coach"]
    year = datetime.now().year
    period = {
        "name": "Temporada", "starts_on": f"{year}-01-01",
        "ends_on": f"{year}-12-31", "objectives": "Preparación",
    }
    season = admin.post(base + "/seasons", json={
        **period, "age_reference_date": f"{year}-12-31", "status": "active",
    })
    assert season.status_code == 201, season.text
    phase = admin.post(base + "/phases", json={**period, "season_id": season.json()["id"]})
    assert phase.status_code == 201, phase.text
    plan = coach.post(base + "/plans", json={**period, "phase_id": phase.json()["id"]})
    assert plan.status_code == 201, plan.text
    cycle = coach.post(base + "/microcycles", json={**period, "plan_id": plan.json()["id"]})
    assert cycle.status_code == 201, cycle.text
    day = coach.post(base + "/days", json={
        "microcycle_id": cycle.json()["id"], "local_date": f"{year}-06-12",
    })
    assert day.status_code == 201, day.text
    return period, season.json(), phase.json(), plan.json(), cycle.json(), day.json()


def test_planning_hierarchy_dates_publication_and_isolation(workspace):
    w = workspace
    period, season, phase, plan, cycle, day = create_hierarchy(w)
    admin, coach = w.clients["admin"], w.clients["coach"]
    base = w.base + "/planning"
    assert w.clients["athlete"].get(base).status_code == 403
    assert w.clients["outsider"].get(base).status_code == 403
    assert w.clients["manager"].get(base).json()["plans"] == []
    assert len(coach.get(base).json()["days"]) == 1
    assert coach.post(base + "/seasons", json={
        **period, "age_reference_date": season["age_reference_date"], "status": "active",
    }).status_code == 403
    duplicate = admin.post(base + "/seasons", json={
        **period, "age_reference_date": season["age_reference_date"], "status": "active",
    })
    assert duplicate.status_code == 409
    second = coach.post(base + "/plans", json={**period, "name": "Plan paralelo", "phase_id": phase["id"]})
    assert second.status_code == 201
    assert len(coach.get(base).json()["plans"]) == 2
    wrong = coach.post(base + "/microcycles", json={
        **period, "plan_id": plan["id"], "starts_on": "1990-01-01",
    })
    assert wrong.status_code == 422
    assert admin.post(base + "/days", json={
        "microcycle_id": cycle["id"], "local_date": day["local_date"],
    }).status_code == 404
    assert coach.post(base + "/days", json={
        "microcycle_id": cycle["id"], "local_date": day["local_date"],
    }).status_code == 409
    outsider = w.clients["outsider"]
    assert outsider.post(f"/api/v1/clubs/{w.other_id}/planning/plans", json={
        **period, "phase_id": phase["id"],
    }).status_code == 404
    session = {
        "title": "Entreno del plan", "training_type": "gym", "planned_minutes": 40,
        "scheduled_start": day["local_date"] + "T10:00:00+02:00",
        "athlete_ids": [w.ids["athlete"]["athlete"]], "plan_day_id": day["id"],
    }
    response = coach.post(w.base + "/sessions", json=session)
    assert response.status_code == 201, response.text
    assignments = w.clients["athlete"].get(w.base + "/assignments").json()
    assert assignments[0]["plan_day_id"] == day["id"]
    assert coach.post(w.base + "/sessions", json={
        **session, "scheduled_start": period["starts_on"] + "T10:00:00Z",
    }).status_code == 422
    assert admin.patch(base + "/seasons/" + season["id"], json={"status": "closed"}).status_code == 200
    assert coach.post(w.base + "/sessions", json=session).status_code == 409
    assert len(coach.get(base).json()["plans"]) == 2
    assert admin.get(w.base + "/audit").json()
    assert coach.get(w.base + "/audit").status_code == 403


def test_recovery_optional_values_versions_history_and_scope(workspace):
    w = workspace
    athlete = w.clients["athlete"]
    today = datetime.now(timezone.utc).date().isoformat()
    url = w.base + "/recovery/" + today
    first = athlete.put(url, json={"sleep": 4, "fatigue": 2})
    assert first.status_code == 200, first.text
    assert first.json()["energy"] is None
    assert first.json()["version"] == 1
    assert athlete.put(url, json={"sleep": 5}).status_code == 409
    assert athlete.put(url, json={"version": 1, "sleep": 5}).status_code == 422
    edited = athlete.put(url, json={"version": 1, "sleep": 5, "reason": "Me equivoqué al seleccionar"})
    assert edited.status_code == 200, edited.text
    assert edited.json()["version"] == 2
    assert edited.json()["revisions"][0]["sleep"] == 4
    assert athlete.put(url, json={"version": 1, "sleep": 3, "reason": "Pestaña antigua"}).status_code == 409
    assert len(athlete.get(w.base + "/recovery").json()["records"]) == 1
    assert w.clients["peer"].get(w.base + "/recovery").json()["records"] == []
    preview = w.base + "/athletes/" + w.ids["athlete"]["athlete"] + "/recovery"
    assert w.clients["coach"].get(preview).status_code == 200
    assert w.clients["manager"].get(preview).status_code == 403
    assert w.clients["admin"].get(preview).status_code == 404
    assert w.clients["outsider"].get(preview).status_code == 403
    tomorrow = (datetime.now(timezone.utc).date() + timedelta(days=2)).isoformat()
    assert athlete.put(w.base + "/recovery/" + tomorrow, json={"sleep": 4}).status_code == 422
    assert athlete.put(url, json={"pain_area": "hombro", "pain": 0, "version": 2, "reason": "x"}).status_code == 422
    assert athlete.get(w.base + "/recovery?start=2020-01-01&end=2026-01-01").status_code == 422
    events = w.clients["admin"].get(w.base + "/audit").json()
    assert len(events) == 2
    assert all("sleep" not in row and "revisions" not in row for row in events)


def test_administration_revokes_access_and_preserves_assignments(workspace):
    w = workspace
    admin, coach = w.clients["admin"], w.clients["coach"]
    group = admin.post(w.base + "/groups", json={"name": "Nuevo grupo"}).json()
    url = w.base + "/groups/" + group["id"]
    assert admin.post(url + "/athletes", json={"athlete_id": w.ids["peer"]["athlete"]}).status_code == 201
    assert admin.post(url + "/coaches", json={"coach_membership_id": w.ids["coach"]["member"]}).status_code == 201
    preview = w.base + "/athletes/" + w.ids["peer"]["athlete"] + "/dashboard"
    assert coach.get(preview).status_code == 200
    response = coach.post(w.base + "/sessions", json={
        "title": "Sesión", "training_type": "gym", "planned_minutes": 30,
        "scheduled_start": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        "group_id": group["id"],
    })
    assert response.status_code == 201
    assert admin.delete(url + "/athletes/" + w.ids["peer"]["athlete"]).status_code == 204
    assert coach.get(preview).status_code == 404
    assert admin.post(url + "/athletes", json={"athlete_id": w.ids["peer"]["athlete"]}).status_code == 201
    assert coach.get(preview).status_code == 200
    from sqlalchemy import select
    from app.models import TrainingGroupMembership
    from sqlalchemy.orm import Session
    with Session(w.engine) as db:
        periods = db.scalars(select(TrainingGroupMembership).where(
            TrainingGroupMembership.group_id == group["id"],
        )).all()
        assert len(periods) == 2
        assert sum(period.left_on is None for period in periods) == 1
    assert len(w.clients["peer"].get(w.base + "/assignments").json()) == 1
    member_url = w.base + "/members/" + w.ids["peer"]["member"] + "/status"
    assert coach.patch(member_url, json={"active": False}).status_code == 403
    assert admin.patch(member_url, json={"active": False}).status_code == 200
    assert w.clients["peer"].get(w.base + "/assignments").status_code == 403
    assert admin.patch(member_url, json={"active": True}).status_code == 200
    assert len(w.clients["peer"].get(w.base + "/assignments").json()) == 1
    assert admin.patch(w.base + "/members/" + w.ids["admin"]["member"] + "/status", json={"active": False}).status_code == 409
    assert w.clients["outsider"].get(w.base + "/administration").status_code == 403


def test_preview_deduplicates_and_blocks_changed_recipients(workspace):
    w = workspace
    admin, coach = w.clients["admin"], w.clients["coach"]
    group = admin.post(w.base + "/groups", json={"name": "Destinatarios"}).json()
    group_url = w.base + "/groups/" + group["id"]
    athlete_id = w.ids["athlete"]["athlete"]
    admin.post(group_url + "/athletes", json={"athlete_id": athlete_id})
    admin.post(group_url + "/coaches", json={"coach_membership_id": w.ids["coach"]["member"]})
    body = {
        "title": "Previsualización", "training_type": "gym", "planned_minutes": 30,
        "scheduled_start": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        "group_id": group["id"], "athlete_ids": [athlete_id],
    }
    preview = coach.post(w.base + "/sessions/preview", json=body)
    assert preview.status_code == 200
    assert [item["id"] for item in preview.json()["athletes"]] == [athlete_id]
    assert coach.get(w.base + "/sessions").json() == []
    peer_id = w.ids["peer"]["athlete"]
    admin.post(group_url + "/athletes", json={"athlete_id": peer_id})
    stale = coach.post(w.base + "/sessions", json={**body, "preview_athlete_ids": [athlete_id]})
    assert stale.status_code == 409
    assert coach.get(w.base + "/sessions").json() == []
    updated = coach.post(w.base + "/sessions/preview", json=body).json()
    ids = [item["id"] for item in updated["athletes"]]
    assert set(ids) == {athlete_id, peer_id}
    published = coach.post(w.base + "/sessions", json={**body, "preview_athlete_ids": ids})
    assert published.status_code == 201
    assert published.json()["assigned"] == 2
    assert len(w.clients["athlete"].get(w.base + "/assignments").json()) == 1
    assert w.clients["manager"].post(w.base + "/sessions/preview", json=body).status_code == 403
    assert coach.post(w.base + "/sessions/preview", json={
        **body, "athlete_ids": ["not-in-this-club"],
    }).status_code == 403
