from __future__ import annotations

import importlib
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.agent import AgentRuntime, IdempotencyConflict, RuntimeEvent
from app.models import (
    AgentEvent,
    Base,
    Commitment,
    ConversationSession,
    DailyBriefing,
    Episode,
    Message,
    ProvenanceLink,
    Thread,
    User,
)
from app.persistence import MutationResult, atomic_update


@pytest.fixture()
def postgres_url() -> str:
    url = os.getenv("POSTGRES_TEST_URL")
    if not url:
        pytest.skip("POSTGRES_TEST_URL is required for PostgreSQL integration tests")
    return url


@pytest.fixture()
def pg_sessions(postgres_url: str):
    engine = create_engine(postgres_url)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    try:
        yield sessions
    finally:
        engine.dispose()


def seed_owned(session_factory, model, **values):
    with session_factory.begin() as db:
        owner = User(username="owner")
        stranger = User(username="stranger")
        db.add_all([owner, stranger])
        db.flush()
        item = model(user_id=owner.id, **values)
        db.add(item)
        db.flush()
        return owner.id, stranger.id, item.id


@pytest.mark.parametrize(
    ("model", "values", "changed"),
    [
        (Thread, {"title": "thread", "derivation": "test"}, {"title": "changed"}),
        (
            Commitment,
            {"title": "commitment", "confidence": 1.0, "derivation": "test"},
            {"title": "changed"},
        ),
        (Episode, {"summary": "episode", "actor": "user"}, {"summary": "changed"}),
    ],
)
def test_atomic_update_rejects_stale_and_cross_tenant_sessions(
    pg_sessions, model, values, changed
):
    owner_id, stranger_id, item_id = seed_owned(pg_sessions, model, **values)
    first = pg_sessions()
    stale = pg_sessions()
    try:
        first_version = first.get(model, item_id).version
        stale_version = stale.get(model, item_id).version
        assert (
            atomic_update(first, model, item_id, owner_id, first_version, changed)
            is MutationResult.UPDATED
        )
        first.commit()

        assert (
            atomic_update(stale, model, item_id, owner_id, stale_version, changed)
            is MutationResult.CONFLICT
        )
        stale.rollback()
        assert (
            atomic_update(stale, model, item_id, stranger_id, first_version + 1, changed)
            is MutationResult.NOT_FOUND
        )
    finally:
        first.close()
        stale.close()


@pytest.mark.parametrize(
    ("model", "values", "redaction_field"),
    [
        (Thread, {"title": "thread", "derivation": "test"}, "title"),
        (
            Commitment,
            {"title": "commitment", "confidence": 1.0, "derivation": "test"},
            "title",
        ),
        (Episode, {"summary": "episode", "actor": "user"}, "summary"),
    ],
)
def test_atomic_soft_delete_allows_only_one_concurrent_session(
    pg_sessions, model, values, redaction_field
):
    owner_id, _, item_id = seed_owned(pg_sessions, model, **values)
    first = pg_sessions()
    stale = pg_sessions()
    try:
        version = first.get(model, item_id).version
        assert stale.get(model, item_id).version == version
        deletion = {"deleted": True, redaction_field: "[deleted]"}
        assert (
            atomic_update(first, model, item_id, owner_id, version, deletion)
            is MutationResult.UPDATED
        )
        first.commit()
        assert (
            atomic_update(stale, model, item_id, owner_id, version, deletion)
            is MutationResult.NOT_FOUND
        )
    finally:
        first.close()
        stale.close()


def seed_runtime(pg_sessions):
    with pg_sessions.begin() as db:
        user = User(username="runtime-owner")
        db.add(user)
        db.flush()
        conversation = ConversationSession(user_id=user.id)
        commitment = Commitment(
            user_id=user.id,
            title="file taxes",
            confidence=1.0,
            derivation="test",
        )
        db.add_all([conversation, commitment])
        db.flush()
        return user.id, conversation.id


def test_runtime_transition_uses_atomic_cas(pg_sessions, monkeypatch):
    import app.agent

    user_id, conversation_id = seed_runtime(pg_sessions)
    rendezvous = Barrier(2)
    real_atomic_update = atomic_update

    def synchronized_update(*args, **kwargs):
        rendezvous.wait(timeout=10)
        return real_atomic_update(*args, **kwargs)

    monkeypatch.setattr(app.agent, "atomic_update", synchronized_update)

    def handle(event_id: str):
        with pg_sessions() as db:
            return AgentRuntime().handle(
                db,
                user_id,
                RuntimeEvent(event_id, "user_message", "I finished file taxes", conversation_id),
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(handle, "a"), pool.submit(handle, "b")]
        outcomes = [future.exception() or future.result() for future in futures]

    assert sum(isinstance(outcome, app.agent.ConcurrentMutation) for outcome in outcomes) == 1
    with pg_sessions() as db:
        commitment = db.scalar(select(Commitment).where(Commitment.user_id == user_id))
        assert (commitment.state, commitment.version) == ("complete", 2)


def test_concurrent_duplicate_ingress_is_conflict_safe(pg_sessions):
    user_id, conversation_id = seed_runtime(pg_sessions)
    rendezvous = Barrier(2)

    def handle():
        with pg_sessions() as db:
            rendezvous.wait(timeout=10)
            return AgentRuntime().handle(
                db,
                user_id,
                RuntimeEvent("duplicate", "user_message", "Hello there!", conversation_id),
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [future.result() for future in [pool.submit(handle), pool.submit(handle)]]

    assert sorted(result["idempotent"] for result in results) == [False, True]
    with pg_sessions() as db:
        assert db.scalar(select(func.count()).select_from(AgentEvent)) == 1
        assert db.scalar(select(func.count()).select_from(Message)) == 2


def test_concurrent_morning_triggers_create_one_logical_briefing(pg_sessions):
    from app.clock import FakeClock

    user_id, _ = seed_runtime(pg_sessions)
    rendezvous = Barrier(2)
    clock = FakeClock(datetime(2026, 9, 30, 8, tzinfo=timezone.utc))

    def handle(event_id: str):
        with pg_sessions() as db:
            rendezvous.wait(timeout=10)
            return AgentRuntime(clock=clock).handle(
                db, user_id, RuntimeEvent(event_id, "morning_briefing")
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(handle, "am-1"), pool.submit(handle, "am-2")]
        results = [future.result() for future in futures]

    assert sorted(result["idempotent"] for result in results) == [False, True]
    with pg_sessions() as db:
        assert db.scalar(select(func.count()).select_from(DailyBriefing)) == 1
        proactive = db.scalars(select(Message).where(Message.role == "assistant")).all()
        assert len(proactive) == 1
        assert "Power List" in proactive[0].content


def test_idempotency_key_reuse_with_different_fingerprint_conflicts(pg_sessions):
    user_id, conversation_id = seed_runtime(pg_sessions)
    with pg_sessions() as db:
        runtime = AgentRuntime()
        runtime.handle(
            db,
            user_id,
            RuntimeEvent("reused", "user_message", "Hello there!", conversation_id),
        )
    with pg_sessions() as db, pytest.raises(IdempotencyConflict):
        AgentRuntime().handle(
            db,
            user_id,
            RuntimeEvent("reused", "user_message", "Different content", conversation_id),
        )
    with pg_sessions() as db, pytest.raises(IdempotencyConflict):
        AgentRuntime().handle(db, user_id, RuntimeEvent("reused", "dormancy_scan"))


@pytest.fixture()
def pg_client(postgres_url: str, monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    monkeypatch.setenv("ACCESS_CODE", "correct horse battery staple")
    monkeypatch.setenv("SESSION_SECRET", "s" * 32)
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://testserver")
    import app.main

    app.main.engine.dispose()
    importlib.reload(app.main)
    Base.metadata.drop_all(app.main.engine)
    Base.metadata.create_all(app.main.engine)
    with TestClient(app.main.app) as client:
        yield client
    app.main.engine.dispose()


def login(client):
    return client.post(
        "/api/auth/login",
        json={"access_code": "correct horse battery staple", "username": "owner"},
        headers={"origin": "http://testserver"},
    )


def csrf(client):
    return {"origin": "http://testserver", "x-csrf-token": client.cookies.get("csrf_token")}


@pytest.mark.parametrize(
    ("path", "valid_payload", "invalid_payload"),
    [
        (
            "/api/chat/messages",
            {"content": "x" * 4000, "event_id": "message-max"},
            {"content": "x" * 4001, "event_id": "message-over"},
        ),
        (
            "/api/episodes",
            {"summary": "x" * 1000, "actor": "user"},
            {"summary": "x" * 1001, "actor": "user"},
        ),
    ],
)
def test_postgres_create_boundaries_return_validation_not_server_errors(
    pg_client, path, valid_payload, invalid_payload
):
    assert login(pg_client).status_code == 200
    headers = csrf(pg_client)
    assert pg_client.post(path, json=valid_payload, headers=headers).status_code == 201
    assert pg_client.post(path, json=invalid_payload, headers=headers).status_code == 422


def test_postgres_extracted_titles_and_correction_boundaries_are_contained(pg_client):
    assert login(pg_client).status_code == 200
    headers = csrf(pg_client)
    response = pg_client.post(
        "/api/chat/messages",
        json={"content": "I need to " + "x" * 3990, "event_id": "long-title"},
        headers=headers,
    )
    assert response.status_code == 201
    commitment = pg_client.get("/api/commitments").json()[0]
    assert len(commitment["title"]) == 3990
    assert pg_client.patch(
        f"/api/commitments/{commitment['id']}",
        json={"title": "x" * 500, "version": commitment["version"]},
        headers=headers,
    ).status_code == 200
    assert pg_client.patch(
        f"/api/commitments/{commitment['id']}",
        json={"title": "x" * 501, "version": commitment["version"] + 1},
        headers=headers,
    ).status_code == 422


def test_postgres_credential_like_chat_stays_out_of_episodic_memory(pg_client):
    import app.main

    assert login(pg_client).status_code == 200
    headers = csrf(pg_client)
    for index, credential in enumerate(
        [
            "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij",
            "N7vQ2mX9cL4pR8sT1wY5zA6bD3fG0hJ2kM9nP4q",
        ]
    ):
        response = pg_client.post(
            "/api/chat/messages",
            json={
                "content": f"I deployed pg-credential-canary-{index} with {credential}",
                "event_id": f"pg-credential-{index}",
            },
            headers=headers,
        )
        assert response.status_code == 201

    with app.main.SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Episode)) == 0
        assert db.scalar(select(func.count()).select_from(ProvenanceLink)) == 0
    assert pg_client.get(
        "/api/history/recall", params={"q": "pg-credential-canary"}
    ).json() == []
