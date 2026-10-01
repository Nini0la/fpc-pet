from __future__ import annotations

import importlib
from datetime import datetime, timedelta, timezone

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


def test_commitment_check_surfaces_and_today_and_reminders_expose_urgency(client):
    import app.main
    from app.agent import AgentRuntime
    from app.clock import FakeClock

    clock = FakeClock(datetime(2026, 9, 28, 9, tzinfo=timezone.utc))
    app.main.runtime = AgentRuntime(clock=clock)
    login(client)
    headers = csrf(client)
    response = client.post(
        "/api/chat/messages",
        json={
            "content": "I need to submit evaluation before Friday; it takes 3 hours",
            "event_id": "commitment",
        },
        headers=headers,
    )
    assert response.status_code == 201
    clock.set(datetime(2026, 10, 1, 9, tzinfo=timezone.utc))
    scan = client.post(
        "/api/events/scheduled",
        json={
            "event_id": "scan",
            "kind": "commitment_check",
            "intended_at": "2026-10-01T08:30:00Z",
            "window_minutes": 60,
        },
        headers=headers,
    )
    assert scan.status_code == 202
    assert scan.json()["surfaced"] == 1

    today = client.get("/api/today").json()
    urgency = today["open_commitments"][0]["urgency"]
    assert urgency["bucket"] == "high"
    assert urgency["factors"]["effort_minutes"] == 180
    reminders = client.get("/api/reminders", params={"limit": 1}).json()
    assert len(reminders["items"]) == 1
    assert reminders["items"][0]["reason_metadata"] == urgency
    assert reminders["has_more"] is False
    assert client.get("/api/reminders", params={"limit": 101}).status_code == 422

    client.post("/api/auth/logout", headers=headers)
    login(client, username="stranger")
    assert client.get("/api/reminders").json()["items"] == []


def test_commitment_check_validates_intended_window_and_kind(client):
    import app.main
    from app.agent import AgentRuntime
    from app.clock import FakeClock

    app.main.runtime = AgentRuntime(
        clock=FakeClock(datetime(2026, 11, 1, 6, 30, tzinfo=timezone.utc))
    )
    login(client)
    headers = csrf(client)
    base = {"event_id": "scan", "kind": "commitment_check", "window_minutes": 60}
    assert client.post(
        "/api/events/scheduled",
        json=base | {"intended_at": "2026-11-01T05:30:00Z"},
        headers=headers,
    ).status_code == 202
    assert client.post(
        "/api/events/scheduled",
        json=base | {"event_id": "old", "intended_at": "2026-11-01T05:29:59Z"},
        headers=headers,
    ).status_code == 422
    assert client.post(
        "/api/events/scheduled",
        json=base | {"event_id": "future", "intended_at": "2026-11-01T06:31:00Z"},
        headers=headers,
    ).status_code == 422
    assert client.post(
        "/api/events/scheduled",
        json={
            "event_id": "wrong-kind",
            "kind": "morning_briefing",
            "intended_at": "2026-11-01T06:00:00Z",
            "window_minutes": 60,
        },
        headers=headers,
    ).status_code == 422


def test_event_idempotency_and_input_bound(client):
    login(client)
    h = csrf(client)
    payload = {"content": "I'm considering local inference", "event_id": "same"}
    assert client.post("/api/chat/messages", json=payload, headers=h).status_code == 201
    assert client.post("/api/chat/messages", json=payload, headers=h).status_code == 200
    assert len(client.get("/api/threads").json()) == 1
    assert client.post(
        "/api/chat/messages",
        json={"content": "different delivery", "event_id": "same"},
        headers=h,
    ).status_code == 409
    assert client.post(
        "/api/events/scheduled",
        json={"event_id": "same", "kind": "dormancy_scan"},
        headers=h,
    ).status_code == 409
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
    assert client.patch(
        f"/api/threads/{item['id']}",
        json={"title": "stale write", "version": 1},
        headers=h,
    ).status_code == 409
    assert client.delete(
        f"/api/threads/{item['id']}", params={"version": 1}, headers=h
    ).status_code == 409
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


def test_chat_builds_explicit_actor_attributed_episode_history_across_sessions(client):
    login(client)
    h = csrf(client)
    interactions = [
        ("history-user", "I submitted the launch plan.", "user"),
        ("history-assistant", "You found the API documentation.", "assistant"),
        ("history-joint", "We designed the prototype.", "joint"),
        ("history-discussed", "We only discussed deploying it.", "discussed_only"),
    ]
    for index, (event_id, content, _actor) in enumerate(interactions):
        response = client.post(
            "/api/chat/messages",
            json={"content": content, "event_id": event_id},
            headers=h,
        )
        assert response.status_code == 201
        if index == 1:
            assert client.post("/api/auth/logout", headers=h).status_code == 204
            assert login(client).status_code == 200
            h = csrf(client)

    episodes = client.get(
        "/api/history/recall",
        params={"q": "submitted documentation designed deploying"},
    ).json()
    assert [(episode["summary"], episode["actor"]) for episode in episodes] == [
        (content, actor) for _, content, actor in interactions
    ]
    message_ids = {message["id"] for message in client.get("/api/chat/messages").json()}
    for episode in episodes:
        assert episode["source"].startswith("message:")
        links = client.get(f"/api/provenance/{episode['id']}").json()
        assert links[0]["source_id"] in message_ids
        assert links == [
            {
                "id": links[0]["id"],
                "source_type": "message",
                "source_id": episode["source"].removeprefix("message:"),
                "confidence": episode["confidence"],
                "derivation": "explicit-chat-episode-v1",
                "metadata_only": False,
            }
        ]


def test_ephemeral_sensitive_and_interrogative_messages_are_not_episodes(client):
    login(client)
    h = csrf(client)
    for event_id, content in [
        ("greeting", "Hello there!"),
        ("question", "How does PostgreSQL concurrency work?"),
        ("secret", "my password is hunter2"),
    ]:
        response = client.post(
            "/api/chat/messages",
            json={"content": content, "event_id": event_id},
            headers=h,
        )
        assert response.status_code == 201

    assert client.get(
        "/api/history/recall", params={"q": "hello PostgreSQL hunter2"}
    ).json() == []


@pytest.mark.parametrize(
    ("credential", "event_id"),
    [
        ("ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij", "github-classic"),
        ("github_pat_" + "Ab1_" * 20, "github-fine-grained"),
        ("AKIAIOSFODNN7EXAMPLE", "aws-access-key"),
        ("Bearer mF_9.B5f-4.1JqM", "bearer"),
        (
            "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0."
            "c2lnbmF0dXJlX3N5bnRoZXRpYw",
            "jwt",
        ),
        ("-----BEGIN PRIVATE KEY-----", "private-key"),
        ("sk-proj-Ab1Cd2Ef3Gh4Ij5Kl6Mn7Op8Qr9St0Uv", "openai"),
        ("sk_live_Ab1Cd2Ef3Gh4Ij5Kl6Mn7Op8", "stripe"),
        ("xoxb-123456789012-AbCdEfGhIjKlMnOpQrStUvWx", "slack"),
        ("AIzaSyAbCdEfGhIjKlMnOpQrStUvWxYz01234567", "google"),
        ("N7vQ2mX9cL4pR8sT1wY5zA6bD3fG0hJ2kM9nP4q", "high-entropy"),
    ],
    ids=[
        "github-classic",
        "github-fine-grained",
        "aws-access-key",
        "bearer",
        "jwt",
        "private-key",
        "openai",
        "stripe",
        "slack",
        "google",
        "high-entropy",
    ],
)
def test_credential_like_values_are_not_promoted_or_recallable(client, credential, event_id):
    from sqlalchemy import func, select

    import app.main
    from app.models import Episode, ProvenanceLink

    login(client)
    response = client.post(
        "/api/chat/messages",
        json={
            "content": f"I deployed credential-canary with {credential}",
            "event_id": f"credential-{event_id}",
        },
        headers=csrf(client),
    )
    assert response.status_code == 201

    with app.main.SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Episode)) == 0
        assert db.scalar(select(func.count()).select_from(ProvenanceLink)) == 0
    if client.get("/api/history/recall", params={"q": "credential-canary"}).json():
        pytest.fail("credential-like chat was promoted into recall")


@pytest.mark.parametrize(
    "question",
    ["What have we been doing?"],
)
def test_chat_recall_is_chronological_sourced_and_uncertainty_aware(client, question):
    login(client)
    h = csrf(client)
    facts = [
        ("I submitted the launch plan.", "user"),
        ("You found the API documentation.", "assistant"),
        ("We designed the prototype.", "joint"),
        ("We only discussed deploying it.", "discussed_only"),
    ]
    for index, (content, _actor) in enumerate(facts):
        assert (
            client.post(
                "/api/chat/messages",
                json={"content": content, "event_id": f"fact-{index}"},
                headers=h,
            ).status_code
            == 201
        )

    recall_response = client.post(
        "/api/chat/messages",
        json={"content": question, "event_id": "recall-question"},
        headers=h,
    )
    assert recall_response.status_code == 201
    assert recall_response.json()["handled_by"] == "AgentRuntime.handle"
    answer = client.get("/api/chat/messages").json()[-1]["content"]
    assert "recorded claims, not independently verified facts" in answer
    assert [answer.index(summary) for summary, _ in facts] == sorted(
        answer.index(summary) for summary, _ in facts
    )
    for summary, actor in facts:
        line = next(line for line in answer.splitlines() if summary in line)
        assert f"[{actor}; source message:" in line
        assert "confidence " in line


@pytest.mark.parametrize("referent", ["this", "that"])
def test_ambiguous_assistant_recall_does_not_dump_unrelated_history(client, referent):
    login(client)
    h = csrf(client)
    for event_id, content in [
        ("unrelated-launch", "You told me about the launch checklist."),
        ("unrelated-api", "You found the API documentation."),
        ("unrelated-context", "Can you remind me what we were discussing?"),
    ]:
        client.post(
            "/api/chat/messages",
            json={"content": content, "event_id": event_id},
            headers=h,
        )

    client.post(
        "/api/chat/messages",
        json={
            "content": f"What did you already tell me about {referent}?",
            "event_id": f"ambiguous-{referent}",
        },
        headers=h,
    )

    answer = client.get("/api/chat/messages").json()[-1]["content"]
    assert "which topic" in answer.lower() or "enough context" in answer.lower()
    assert "launch checklist" not in answer
    assert "API documentation" not in answer


def test_demonstrative_assistant_recall_uses_a_unique_immediate_referent(client):
    login(client)
    h = csrf(client)
    for event_id, content in [
        ("referent-launch", "You told me about the launch checklist."),
        ("referent-api", "You found the API documentation."),
        ("referent-context", "Let's return to the launch checklist."),
    ]:
        client.post(
            "/api/chat/messages",
            json={"content": content, "event_id": event_id},
            headers=h,
        )

    client.post(
        "/api/chat/messages",
        json={"content": "What did you already tell me about that?", "event_id": "resolved-that"},
        headers=h,
    )

    answer = client.get("/api/chat/messages").json()[-1]["content"]
    assert "You told me about the launch checklist." in answer
    assert "API documentation" not in answer


def test_all_spec_recall_phrases_filter_history_without_contaminating_it(client):
    import app.main
    from app.agent import AgentRuntime
    from app.clock import FakeClock

    clock = FakeClock(datetime(2026, 9, 20, 9, tzinfo=timezone.utc))
    app.main.runtime = AgentRuntime(clock=clock)
    login(client)
    h = csrf(client)
    facts = [
        (
            "old-help",
            "You helped me archive old files.",
            datetime(2026, 9, 20, 9, tzinfo=timezone.utc),
        ),
        (
            "nebius-talk",
            "We only discussed Nebius project options.",
            datetime(2026, 9, 28, 9, tzinfo=timezone.utc),
        ),
        (
            "nebius-decision",
            "We decided the Nebius project should use a separate demonstrator.",
            datetime(2026, 9, 28, 10, tzinfo=timezone.utc),
        ),
        (
            "jev-start",
            "We started talking about Jev and possible collaborators.",
            datetime(2026, 9, 29, 9, tzinfo=timezone.utc),
        ),
        ("jev-later", "We discussed Jev again.", datetime(2026, 9, 30, 8, tzinfo=timezone.utc)),
        (
            "ip-talk",
            "We only discussed the IP issue.",
            datetime(2026, 9, 30, 9, tzinfo=timezone.utc),
        ),
        (
            "ip-conclusion",
            "We concluded the IP issue requires keeping FPC private.",
            datetime(2026, 9, 30, 10, tzinfo=timezone.utc),
        ),
        (
            "assistant-prior",
            "You told me about the launch checklist.",
            datetime(2026, 9, 30, 11, tzinfo=timezone.utc),
        ),
        (
            "user-tried",
            "I tested the deployment workflow.",
            datetime(2026, 9, 30, 12, tzinfo=timezone.utc),
        ),
    ]
    for event_id, content, when in facts:
        clock.set(when)
        assert (
            client.post(
                "/api/chat/messages",
                json={"content": content, "event_id": event_id},
                headers=h,
            ).status_code
            == 201
        )

    clock.set(datetime(2026, 9, 30, 15, tzinfo=timezone.utc))
    cases = [
        (
            "What have we been doing?",
            [content for _, content, _ in facts],
            [],
        ),
        (
            "What did we decide about the Nebius project?",
            ["We decided the Nebius project should use a separate demonstrator."],
            ["We only discussed Nebius project options.", "IP issue"],
        ),
        (
            "What have you helped me with this week?",
            ["You told me about the launch checklist."],
            ["You helped me archive old files.", "Nebius project"],
        ),
        (
            "When did we start talking about Jev?",
            ["We started talking about Jev and possible collaborators."],
            ["We discussed Jev again."],
        ),
        (
            "What did we conclude about the IP issue?",
            ["We concluded the IP issue requires keeping FPC private."],
            ["We only discussed the IP issue.", "Nebius project"],
        ),
        (
            "What did you already tell me about this?",
            ["Which topic do you mean?"],
            ["archive old files", "launch checklist", "Nebius project", "deployment workflow"],
        ),
        (
            "What have we tried?",
            ["We decided the Nebius project", "I tested the deployment workflow."],
            ["We only discussed Nebius project options.", "We only discussed the IP issue."],
        ),
    ]
    for index, (question, included, excluded) in enumerate(cases):
        response = client.post(
            "/api/chat/messages",
            json={"content": question, "event_id": f"spec-recall-{index}"},
            headers=h,
        )
        assert response.status_code == 201
        answer = client.get("/api/chat/messages").json()[-1]["content"]
        if "about this" not in question:
            assert "source" in answer
        assert all(text in answer for text in included)
        assert all(text not in answer for text in excluded)

    recalled = client.get(
        "/api/history/recall",
        params={"q": "archive Nebius Jev issue checklist deployment"},
    ).json()
    assert len(recalled) == len(facts)
    assert not any(item["summary"].startswith("What ") for item in recalled)


def test_chat_recall_includes_explicit_non_deleted_state_with_message_sources(client):
    login(client)
    h = csrf(client)
    for event_id, content in [
        ("state-commitment", "I need to finish the Nebius brief"),
        ("state-thread", "hang onto this idea: Jev interview series"),
    ]:
        assert (
            client.post(
                "/api/chat/messages",
                json={"content": content, "event_id": event_id},
                headers=h,
            ).status_code
            == 201
        )

    thread = client.get("/api/threads").json()[0]
    assert client.delete(f"/api/threads/{thread['id']}", headers=h).status_code == 204
    client.post(
        "/api/chat/messages",
        json={"content": "What have we been doing?", "event_id": "state-recall"},
        headers=h,
    )
    answer = client.get("/api/chat/messages").json()[-1]["content"]
    assert "finish the Nebius brief" in answer
    assert "source message:" in answer
    assert "Jev interview series" not in answer


def test_chat_recall_uses_corrected_history_and_excludes_deleted_history(client):
    login(client)
    h = csrf(client)
    for event_id, content in [
        ("stale", "I drafted the stale launch plan."),
        ("deleted", "You tested the discarded prototype."),
    ]:
        client.post(
            "/api/chat/messages", json={"content": content, "event_id": event_id}, headers=h
        )
    episodes = client.get(
        "/api/history/recall", params={"q": "stale discarded"}
    ).json()
    corrected, deleted = episodes
    assert (
        client.patch(
            f"/api/episodes/{corrected['id']}",
            json={"summary": "I drafted the corrected launch plan.", "version": 1},
            headers=h,
        ).status_code
        == 200
    )
    assert client.delete(f"/api/episodes/{deleted['id']}", headers=h).status_code == 204

    client.post(
        "/api/chat/messages",
        json={"content": "What have we tried?", "event_id": "recall-after-edits"},
        headers=h,
    )
    answer = client.get("/api/chat/messages").json()[-1]["content"]
    assert "I drafted the corrected launch plan." in answer
    assert "stale launch plan" not in answer
    assert "discarded prototype" not in answer


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


@pytest.mark.parametrize(
    "update",
    [
        "I haven't finished the frontend",
        "I haven’t finished the frontend",
        "I have not finished the frontend",
        "I didn't finish the frontend",
        "I did not finish the frontend",
        "The frontend is not finished",
    ],
)
def test_negated_completion_keeps_an_open_commitment_open(client, update):
    login(client)
    h = csrf(client)
    client.post(
        "/api/chat/messages",
        json={"content": "I need to finish the frontend", "event_id": "negated-open"},
        headers=h,
    )

    client.post(
        "/api/chat/messages",
        json={"content": update, "event_id": "negated-update"},
        headers=h,
    )

    assert client.get("/api/commitments").json()[0]["state"] == "open"


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


def test_today_and_bounded_tenant_scoped_journal_history(client):
    import app.main
    from app.agent import AgentRuntime
    from app.clock import FakeClock

    clock = FakeClock(datetime(2026, 9, 30, 8, tzinfo=timezone.utc))
    app.main.runtime = AgentRuntime(clock=clock)
    login(client, username="alice")
    h = csrf(client)
    client.post(
        "/api/chat/messages",
        json={"content": "I need to submit demo before Friday", "event_id": "commit"},
        headers=h,
    )
    assert client.post(
        "/api/events/scheduled",
        json={"event_id": "morning", "kind": "morning_briefing"},
        headers=h,
    ).status_code == 202
    today = client.get("/api/today").json()
    assert today["briefing"]["local_date"] == "2026-09-30"
    assert today["power_list"][0]["title"] == "submit demo"
    assert today["open_commitments"][0]["title"] == "submit demo"
    assert today["evening_reflection"]["status"] == "not_started"

    clock.set(datetime(2026, 9, 30, 20, tzinfo=timezone.utc))
    client.post(
        "/api/events/scheduled",
        json={"event_id": "evening", "kind": "evening_reflection"},
        headers=h,
    )
    reflection = "I didn't finish submit demo. Blocked by review."
    client.post(
        "/api/chat/messages",
        json={"content": reflection, "event_id": "reflection"},
        headers=h,
    )
    history = client.get("/api/history/journals", params={"q": "REVIEW", "limit": 10}).json()
    assert history["items"][0]["original_content"] == reflection
    assert history["has_more"] is False
    assert client.get("/api/history/journals", params={"q": "x" * 501}).status_code == 422
    assert client.get("/api/history/journals", params={"limit": 101}).status_code == 422

    client.post("/api/auth/logout", headers=h)
    login(client, username="bob")
    assert client.get("/api/today").json()["briefing"] is None
    assert client.get("/api/history/journals", params={"q": "review"}).json()["items"] == []


def test_today_caps_150_open_commitments_and_active_threads_with_stable_metadata(client):
    from sqlalchemy import select

    import app.main
    from app.models import Commitment, Thread, User

    login(client)
    now = datetime(2026, 9, 30, 8, tzinfo=timezone.utc)
    with app.main.SessionLocal.begin() as db:
        user = db.scalar(select(User).where(User.username == "owner"))
        db.add_all(
            [
                Commitment(
                    user_id=user.id,
                    title=f"commitment {index:03d}",
                    confidence=1,
                    derivation="test",
                    created_at=now + timedelta(seconds=index),
                )
                for index in range(150)
            ]
            + [
                Thread(
                    user_id=user.id,
                    title=f"thread {index:03d}",
                    confidence=1,
                    derivation="test",
                    created_at=now + timedelta(seconds=index),
                )
                for index in range(150)
            ]
        )

    payload = client.get("/api/today").json()
    assert len(payload["open_commitments"]) == 50
    assert len(payload["active_threads"]) == 50
    assert [item["title"] for item in payload["open_commitments"]] == [
        f"commitment {index:03d}" for index in range(50)
    ]
    assert [item["title"] for item in payload["active_threads"]] == [
        f"thread {index:03d}" for index in range(50)
    ]
    assert payload["collection_meta"] == {
        "open_commitments": {
            "limit": 50,
            "returned_count": 50,
            "total_count": 150,
            "has_more": True,
        },
        "active_threads": {
            "limit": 50,
            "returned_count": 50,
            "total_count": 150,
            "has_more": True,
        },
    }


def test_missed_scheduled_trigger_uses_validated_intended_date_and_is_logically_idempotent(
    client,
):
    from sqlalchemy import func, select

    import app.main
    from app.agent import AgentRuntime
    from app.clock import FakeClock
    from app.models import DailyBriefing

    app.main.runtime = AgentRuntime(
        clock=FakeClock(datetime(2026, 10, 1, 0, 30, tzinfo=timezone.utc))
    )
    login(client)
    headers = csrf(client)
    first = client.post(
        "/api/events/scheduled",
        json={
            "event_id": "missed-morning-1",
            "kind": "morning_briefing",
            "intended_local_date": "2026-09-30",
        },
        headers=headers,
    )
    duplicate = client.post(
        "/api/events/scheduled",
        json={
            "event_id": "missed-morning-2",
            "kind": "morning_briefing",
            "intended_local_date": "2026-09-30",
        },
        headers=headers,
    )

    assert first.status_code == 202
    assert first.json()["idempotent"] is False
    assert duplicate.status_code == 202
    assert duplicate.json()["idempotent"] is True
    with app.main.SessionLocal() as db:
        briefing = db.scalar(select(DailyBriefing))
        assert briefing.local_date.isoformat() == "2026-09-30"
        assert db.scalar(select(func.count()).select_from(DailyBriefing)) == 1


def test_scheduled_trigger_rejects_future_stale_and_non_daily_intended_dates(client):
    import app.main
    from app.agent import AgentRuntime
    from app.clock import FakeClock

    app.main.runtime = AgentRuntime(
        clock=FakeClock(datetime(2026, 10, 1, 12, tzinfo=timezone.utc))
    )
    login(client)
    headers = csrf(client)
    for event_id, kind, intended_date in [
        ("future", "morning_briefing", "2026-10-02"),
        ("stale", "evening_reflection", "2026-09-29"),
        ("foreign-kind", "dormancy_scan", "2026-10-01"),
    ]:
        response = client.post(
            "/api/events/scheduled",
            json={
                "event_id": event_id,
                "kind": kind,
                "intended_local_date": intended_date,
            },
            headers=headers,
        )
        assert response.status_code == 422
