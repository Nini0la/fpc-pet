from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/test.db")
    monkeypatch.setenv("ACCESS_CODE", "correct horse battery staple")
    monkeypatch.setenv("SESSION_SECRET", "s" * 32)
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://testserver")
    import app.main

    importlib.reload(app.main)
    with TestClient(app.main.app) as c:
        yield c


def login(client, code="correct horse battery staple", username="owner"):
    r = client.post(
        "/api/auth/login",
        json={"access_code": code, "username": username},
        headers={"origin": "http://testserver"},
    )
    return r


def csrf(client):
    return {"origin": "http://testserver", "x-csrf-token": client.cookies.get("csrf_token")}


def test_login_fail_closed_and_cookie_security(client):
    assert login(client, "wrong").status_code == 401
    r = login(client)
    assert r.status_code == 200
    assert "HttpOnly" in r.headers["set-cookie"]
    assert client.get("/api/auth/me").json()["username"] == "owner"
    assert client.post("/api/auth/logout").status_code == 403
    assert client.post("/api/auth/logout", headers=csrf(client)).status_code == 204


def test_chat_persists_chronology_and_derived_provenance(client):
    login(client)
    r = client.post(
        "/api/chat/messages",
        json={
            "content": "I need to send Patrick the plan before Friday; it takes 4 hours",
            "event_id": "evt-1",
        },
        headers=csrf(client),
    )
    assert r.status_code == 201
    messages = client.get("/api/chat/messages").json()
    assert [m["role"] for m in messages] == ["user", "assistant"]
    commitments = client.get("/api/commitments").json()
    assert commitments[0]["title"] == "send Patrick the plan"
    assert commitments[0]["effort_minutes"] == 240
    links = client.get(f"/api/provenance/{commitments[0]['id']}").json()
    assert links[0]["derivation"] == "deterministic-explicit-phrase-v1"
    assert links[0]["confidence"] == 0.95


def test_event_idempotency_and_input_bound(client):
    login(client)
    h = csrf(client)
    payload = {"content": "I'm considering local inference", "event_id": "same"}
    assert client.post("/api/chat/messages", json=payload, headers=h).status_code == 201
    assert client.post("/api/chat/messages", json=payload, headers=h).status_code == 200
    assert len(client.get("/api/threads").json()) == 1
    assert (
        client.post(
            "/api/chat/messages", json={"content": "x" * 4001, "event_id": "long"}, headers=h
        ).status_code
        == 422
    )


def test_foreign_ids_look_missing_and_queries_are_tenant_scoped(client):
    login(client, username="alice")
    client.post(
        "/api/chat/messages",
        json={"content": "I'm considering secret project", "event_id": "a"},
        headers=csrf(client),
    )
    item = client.get("/api/threads").json()[0]
    client.post("/api/auth/logout", headers=csrf(client))
    login(client, username="bob")
    assert client.get("/api/threads").json() == []
    assert client.get(f"/api/threads/{item['id']}").status_code == 404
    assert (
        client.patch(
            f"/api/threads/{item['id']}",
            json={"title": "stolen", "version": 1},
            headers=csrf(client),
        ).status_code
        == 404
    )


def test_correction_audit_is_content_free_and_delete_prevents_recall(client):
    login(client)
    h = csrf(client)
    client.post(
        "/api/chat/messages",
        json={"content": "hang onto this idea: local inference club", "event_id": "idea"},
        headers=h,
    )
    item = client.get("/api/threads").json()[0]
    assert (
        client.patch(
            f"/api/threads/{item['id']}",
            json={"title": "local systems club", "version": 1},
            headers=h,
        ).status_code
        == 200
    )
    audit = client.get(f"/api/provenance/{item['id']}").json()
    assert audit[-1]["derivation"] == "user-correction"
    assert "local systems" not in str(audit[-1])
    assert client.delete(f"/api/threads/{item['id']}", headers=h).status_code == 204
    assert client.get("/api/history/recall", params={"q": "local systems"}).json() == []


def test_shared_history_actor_accuracy(client):
    login(client)
    h = csrf(client)
    for actor, summary in [
        ("user", "User submitted the plan"),
        ("assistant", "Assistant found a source"),
        ("joint", "We designed the demo"),
        ("discussed_only", "We only discussed deployment"),
    ]:
        r = client.post("/api/episodes", json={"summary": summary, "actor": actor}, headers=h)
        assert r.status_code == 201
    recalled = client.get("/api/history/recall", params={"q": "plan source demo deployment"}).json()
    assert {x["actor"] for x in recalled} == {"user", "assistant", "joint", "discussed_only"}
    assert all(x["source"] and x["confidence"] <= 1 for x in recalled)


def test_commitment_and_episode_correction_and_deletion(client):
    login(client)
    h = csrf(client)
    client.post(
        "/api/chat/messages",
        json={"content": "I need to write report", "event_id": "cc"},
        headers=h,
    )
    commitment = client.get("/api/commitments").json()[0]
    assert (
        client.patch(
            f"/api/commitments/{commitment['id']}",
            json={"title": "write final report", "version": 1},
            headers=h,
        ).status_code
        == 200
    )
    assert client.delete(f"/api/commitments/{commitment['id']}", headers=h).status_code == 204
    assert client.get("/api/commitments").json() == []
    episode = client.post(
        "/api/episodes", json={"summary": "We shipped draft", "actor": "joint"}, headers=h
    ).json()
    assert (
        client.patch(
            f"/api/episodes/{episode['id']}",
            json={"summary": "We shipped final", "version": 1},
            headers=h,
        ).status_code
        == 200
    )
    assert client.delete(f"/api/episodes/{episode['id']}", headers=h).status_code == 204
    assert client.get("/api/history/recall", params={"q": "shipped"}).json() == []


def test_completion_and_thread_lifecycle_transitions(client):
    login(client)
    h = csrf(client)
    client.post(
        "/api/chat/messages", json={"content": "I need to file taxes", "event_id": "c1"}, headers=h
    )
    client.post(
        "/api/chat/messages", json={"content": "I finished file taxes", "event_id": "c2"}, headers=h
    )
    assert client.get("/api/commitments").json()[0]["state"] == "complete"
    client.post(
        "/api/chat/messages",
        json={"content": "hang onto this idea: local club", "event_id": "t1"},
        headers=h,
    )
    client.post(
        "/api/chat/messages",
        json={"content": "Make the local club dormant", "event_id": "t2"},
        headers=h,
    )
    assert client.get("/api/threads").json()[0]["state"] == "dormant"
    client.post(
        "/api/chat/messages",
        json={"content": "Let's reactivate the local club", "event_id": "t3"},
        headers=h,
    )
    assert client.get("/api/threads").json()[0]["state"] == "active"


def test_pronoun_completion_and_abandonment_use_recent_matching_state(client):
    login(client)
    h = csrf(client)
    client.post(
        "/api/chat/messages",
        json={"content": "I need to submit demo", "event_id": "pc1"},
        headers=h,
    )
    client.post(
        "/api/chat/messages",
        json={"content": "Actually, I finished that already", "event_id": "pc2"},
        headers=h,
    )
    assert client.get("/api/commitments").json()[0]["state"] == "complete"
    client.post(
        "/api/chat/messages",
        json={"content": "hang onto this idea: boxing", "event_id": "pa1"},
        headers=h,
    )
    response = client.post(
        "/api/chat/messages",
        json={"content": "I am abandoning boxing", "event_id": "pa2"},
        headers=h,
    )
    assert response.status_code == 201
    assert client.get("/api/threads").json()[0]["state"] == "abandoned"


def test_database_state_survives_new_session(client):
    login(client)
    client.post(
        "/api/chat/messages",
        json={"content": "persistent note", "event_id": "persist"},
        headers=csrf(client),
    )
    from sqlalchemy import func, select

    import app.main
    from app.models import Message

    with app.main.SessionLocal() as fresh_process_session:
        assert fresh_process_session.scalar(select(func.count()).select_from(Message)) == 2


def test_scheduled_and_user_events_share_runtime(client):
    login(client)
    r = client.post(
        "/api/events/scheduled",
        json={"event_id": "tick-1", "kind": "dormancy_scan"},
        headers=csrf(client),
    )
    assert r.status_code == 202
    assert r.json()["handled_by"] == "AgentRuntime.handle"
