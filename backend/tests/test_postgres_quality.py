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
from app.clock import FakeClock
from app.models import (
    AgentEvent,
    Base,
    Commitment,
    ConversationSession,
    DailyBriefing,
    Episode,
    Message,
    ProvenanceLink,
    ReflectionPrompt,
    Reminder,
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


def test_runtime_transitions_are_serialized_by_conversation_lock(pg_sessions):
    user_id, conversation_id = seed_runtime(pg_sessions)
    rendezvous = Barrier(2)

    def handle(event_id: str):
        with pg_sessions() as db:
            rendezvous.wait(timeout=10)
            return AgentRuntime().handle(
                db,
                user_id,
                RuntimeEvent(event_id, "user_message", "I finished file taxes", conversation_id),
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(handle, "a"), pool.submit(handle, "b")]
        outcomes = [future.exception() or future.result() for future in futures]

    assert all(isinstance(outcome, dict) for outcome in outcomes)
    with pg_sessions() as db:
        commitment = db.scalar(select(Commitment).where(Commitment.user_id == user_id))
        assert (commitment.state, commitment.version) == ("complete", 3)


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


def test_simultaneous_morning_and_evening_share_one_ordered_conversation(pg_sessions):
    with pg_sessions.begin() as db:
        user = User(username="daily-race-owner", timezone="UTC")
        db.add(user)
        db.flush()
        user_id = user.id

    rendezvous = Barrier(2)

    def handle(event_id: str, kind: str):
        with pg_sessions() as db:
            rendezvous.wait(timeout=10)
            return AgentRuntime().handle(db, user_id, RuntimeEvent(event_id, kind))

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(handle, "simultaneous-morning", "morning_briefing"),
            pool.submit(handle, "simultaneous-evening", "evening_reflection"),
        ]
        outcomes = [future.exception() or future.result() for future in futures]

    assert all(isinstance(outcome, dict) for outcome in outcomes)
    with pg_sessions() as db:
        conversations = db.scalars(
            select(ConversationSession).where(ConversationSession.user_id == user_id)
        ).all()
        messages = db.scalars(
            select(Message).where(Message.user_id == user_id).order_by(Message.ordinal)
        ).all()
        assert len(conversations) == 1
        assert {message.conversation_id for message in messages} == {conversations[0].id}
        assert [message.ordinal for message in messages] == [1, 2]
        contents = {message.content for message in messages}
        assert "How did things go today?" in contents
        assert any(content.startswith("Good morning.") for content in contents)
        assert db.scalar(
            select(func.count()).select_from(DailyBriefing).where(DailyBriefing.user_id == user_id)
        ) == 1
        assert db.scalar(
            select(func.count())
            .select_from(ReflectionPrompt)
            .where(ReflectionPrompt.user_id == user_id)
        ) == 1


def test_simultaneous_user_messages_have_distinct_transactional_ordinals(pg_sessions):
    user_id, conversation_id = seed_runtime(pg_sessions)
    rendezvous = Barrier(8)

    def handle(index: int):
        with pg_sessions() as db:
            rendezvous.wait(timeout=10)
            return AgentRuntime().handle(
                db,
                user_id,
                RuntimeEvent(
                    f"simultaneous-message-{index}",
                    "user_message",
                    f"message {index}",
                    conversation_id,
                ),
            )

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(handle, index) for index in range(8)]
        outcomes = [future.exception() or future.result() for future in futures]

    assert all(isinstance(outcome, dict) for outcome in outcomes)
    with pg_sessions() as db:
        assert db.scalar(
            select(func.count())
            .select_from(ConversationSession)
            .where(ConversationSession.user_id == user_id)
        ) == 1
        messages = db.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id, Message.user_id == user_id)
            .order_by(Message.ordinal)
        ).all()
        assert [message.ordinal for message in messages] == list(range(1, 17))
        for offset in range(0, len(messages), 2):
            assert messages[offset].role == "user"
            assert messages[offset + 1].role == "assistant"


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


def test_idempotency_fingerprint_binds_normalized_conversation_target(pg_sessions):
    user_id, conversation_id = seed_runtime(pg_sessions)
    with pg_sessions.begin() as db:
        other_user = User(username="other-conversation-owner")
        db.add(other_user)
        db.flush()
        other_conversation = ConversationSession(user_id=other_user.id)
        db.add(other_conversation)
        db.flush()
        other_conversation_id = other_conversation.id

    event = RuntimeEvent("target-bound", "user_message", "Hello there!", conversation_id)
    with pg_sessions() as db:
        first = AgentRuntime().handle(db, user_id, event)
    with pg_sessions() as db:
        replay = AgentRuntime().handle(db, user_id, event)

    assert first["idempotent"] is False
    assert replay["idempotent"] is True
    with pg_sessions() as db, pytest.raises(IdempotencyConflict):
        AgentRuntime().handle(
            db,
            user_id,
            RuntimeEvent(
                "target-bound",
                "user_message",
                "Hello there!",
                other_conversation_id,
            ),
        )


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


def test_concurrent_daily_and_chat_requests_never_return_server_errors(pg_client):
    import app.main

    assert login(pg_client).status_code == 200
    headers = csrf(pg_client)
    daily_rendezvous = Barrier(2)

    def schedule(event_id: str, kind: str):
        daily_rendezvous.wait(timeout=10)
        return pg_client.post(
            "/api/events/scheduled",
            json={"event_id": event_id, "kind": kind},
            headers=headers,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        daily_responses = [
            future.result()
            for future in [
                pool.submit(schedule, "http-morning", "morning_briefing"),
                pool.submit(schedule, "http-evening", "evening_reflection"),
            ]
        ]
    assert [response.status_code for response in daily_responses] == [202, 202]

    chat_rendezvous = Barrier(4)

    def chat(index: int):
        chat_rendezvous.wait(timeout=10)
        return pg_client.post(
            "/api/chat/messages",
            json={"event_id": f"http-chat-{index}", "content": f"chat {index}"},
            headers=headers,
        )

    with ThreadPoolExecutor(max_workers=4) as pool:
        chat_responses = [future.result() for future in [pool.submit(chat, i) for i in range(4)]]
    assert [response.status_code for response in chat_responses] == [201] * 4

    with app.main.SessionLocal() as db:
        conversations = db.scalars(select(ConversationSession)).all()
        messages = db.scalars(select(Message).order_by(Message.ordinal)).all()
        assert len(conversations) == 1
        assert {message.conversation_id for message in messages} == {conversations[0].id}
        assert [message.ordinal for message in messages] == list(range(1, 11))


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


def test_concurrent_commitment_scans_create_one_reminder_and_message(pg_sessions):
    now = datetime(2026, 10, 1, 9, tzinfo=timezone.utc)
    with pg_sessions.begin() as db:
        user = User(username="reminder-race", timezone="UTC")
        db.add(user)
        db.flush()
        db.add(
            Commitment(
                user_id=user.id,
                title="finish evaluation",
                confidence=1,
                derivation="test",
                due_at=datetime(2026, 10, 2, 23, 59, tzinfo=timezone.utc),
                estimated_effort_minutes=180,
                importance=2,
                created_at=datetime(2026, 9, 24, 9, tzinfo=timezone.utc),
            )
        )
        user_id = user.id
    rendezvous = Barrier(2)

    def scan(event_id: str):
        with pg_sessions() as db:
            rendezvous.wait(timeout=10)
            return AgentRuntime(clock=FakeClock(now)).handle(
                db, user_id, RuntimeEvent(event_id, "commitment_check")
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [
            future.result()
            for future in [pool.submit(scan, "scan-a"), pool.submit(scan, "scan-b")]
        ]
    assert sorted(result["surfaced"] for result in results) == [0, 1]
    with pg_sessions() as db:
        assert db.scalar(select(func.count()).select_from(Reminder)) == 1
        assert db.scalar(select(func.count()).select_from(Message)) == 1


def test_completion_winning_scan_race_suppresses_stale_reminder(pg_sessions):
    now = datetime(2026, 10, 1, 9, tzinfo=timezone.utc)
    with pg_sessions.begin() as db:
        user = User(username="completion-race", timezone="UTC")
        db.add(user)
        db.flush()
        commitment = Commitment(
            user_id=user.id,
            title="finish evaluation",
            confidence=1,
            derivation="test",
            due_at=datetime(2026, 10, 2, 23, 59, tzinfo=timezone.utc),
            estimated_effort_minutes=180,
            importance=2,
            created_at=datetime(2026, 9, 24, 9, tzinfo=timezone.utc),
        )
        db.add(commitment)
        db.flush()
        user_id, commitment_id = user.id, commitment.id

    completion = pg_sessions()
    try:
        locked = completion.scalar(
            select(Commitment).where(Commitment.id == commitment_id).with_for_update()
        )
        rendezvous = Barrier(2)

        def scan():
            with pg_sessions() as db:
                rendezvous.wait(timeout=10)
                return AgentRuntime(clock=FakeClock(now)).handle(
                    db, user_id, RuntimeEvent("racing-scan", "commitment_check")
                )

        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(scan)
            rendezvous.wait(timeout=10)
            locked.state = "complete"
            locked.completed_at = now
            completion.commit()
            result = future.result(timeout=10)
        assert result["surfaced"] == 0
    finally:
        completion.close()
    with pg_sessions() as db:
        assert db.scalar(select(func.count()).select_from(Reminder)) == 0
        assert db.scalar(select(func.count()).select_from(Message)) == 0
