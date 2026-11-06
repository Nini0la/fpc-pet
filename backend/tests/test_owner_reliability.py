"""Owner scenarios through real PostgreSQL/runtime; scripted model, no external sends."""
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from test_assistance import reply, send, tool
from test_postgres_quality import pg_client as pg_client
from test_postgres_quality import postgres_url as postgres_url
from test_semantic_conversation import NOW, act
from test_semantic_conversation import scene as scene

from app.commitments import describe, utc
from app.context import build_context
from app.gateway import GatewayError
from app.models import (
    Commitment,
    ConversationProposal,
    JournalEntry,
    Message,
    ReflectionPrompt,
    ReminderPlan,
    User,
)
from app.presentation import confirmation


def test_failed_request_can_resume_without_retyping_or_duplicate_effects(pg_client, scene):
    main, gateway = scene
    original = "Can you remind me by the 7th of November to check my dad's mobile data?"
    gateway.scripts.append(GatewayError("output_limit"))
    send(pg_client, "failed", original, allow_memory_write=True)
    with main.SessionLocal() as db:
        source = db.scalar(select(Message).where(Message.content == original)).id
    main.runtime.clock.set(NOW + timedelta(minutes=2))
    answer = act(pg_client, gateway, "recover", "Try that again, one minute from now.",
        "schedule_reminder", {"topic": "Check dad's mobile data", "request_source_id": source,
                              "when": {"kind": "after", "seconds": 60, "anchor": "acceptance"}})
    assert "I'll remind you once" in answer["content"]
    with main.SessionLocal() as db:
        plan = db.scalar(select(ReminderPlan))
        assert utc(plan.due_at) == NOW + timedelta(minutes=3)
        assert plan.source_message_id == source
    act(pg_client, gateway, "duplicate", "Retry the mobile data request again.",
        "schedule_reminder", {"topic": "Check dad's mobile data", "request_source_id": source,
                              "when": {"kind": "after", "seconds": 60}})
    with main.SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(ReminderPlan)) == 1


def test_partial_tool_failure_preserves_first_effect_and_pending_second(
    pg_client, scene, monkeypatch,
):
    import app.assistance as assistance
    main, gateway = scene
    create = assistance.create_commitment
    def fail_second(db, owner, args, *a, **kw):
        if args.title == "World models":
            db.add(Commitment(user_id=owner, title="Must roll back",
                              confidence=1, derivation="test"))
            db.flush()
            raise RuntimeError("simulated tool failure")
        return create(db, owner, args, *a, **kw)
    monkeypatch.setattr(assistance, "create_commitment", fail_second)
    gateway.scripts.append(reply("", *[
        tool("create_commitment", {"title": title, "followup_enabled": False,
                                   "response_text": "Saved."}, title)
        for title in ("Cosmos draft", "World models")
    ]))
    body = "Save Cosmos draft and World models as two commitments, no check-ins."
    answer = send(pg_client, "partial", body, allow_memory_write=True)
    assert "Saved “Cosmos draft”" in answer["content"] and "didn't finish" in answer["content"]
    with main.SessionLocal() as db:
        assert [c.title for c in db.scalars(select(Commitment))] == ["Cosmos draft"]
        assert db.scalar(select(Message).where(Message.content == body))
        pending = db.scalar(select(ConversationProposal))
        identifier, version = pending.id, pending.version
    monkeypatch.setattr(assistance, "create_commitment", create)
    act(pg_client, gateway, "finish", "Please finish the remaining request.", "resolve_proposal",
        {"id": identifier, "version": version, "action": "execute"})
    act(pg_client, gateway, "replay", "Try that remaining request again.", "resolve_proposal",
        {"id": identifier, "version": version + 1, "action": "execute"})
    with main.SessionLocal() as db:
        assert sorted(c.title for c in db.scalars(select(Commitment))) == [
            "Cosmos draft", "World models"]


def test_three_intentions_can_be_preserved_without_automatic_commitments(pg_client, scene):
    main, gateway = scene
    gateway.scripts.append(reply("",
        tool("propose_action", {"title": "Cosmos first draft", "tool_name": "create_commitment",
             "arguments": {"title": "Cosmos first draft", "followup_enabled": False}}, "essay"),
        tool("schedule_reminder", {"topic": "Netball"}, "netball"),
        tool("propose_action", {"title": "World models", "tool_name": "create_commitment",
             "arguments": {"title": "World models", "followup_enabled": False}}, "world")))
    original = ("I have to write a first draft of my Cosmos essay today. "
                "Also I need to be reminded "
                "to go netball at 7. And also work on world models today as well.")
    answer = send(pg_client, "compound", original, allow_memory_write=True)
    assert "Netball" in answer["content"] and "Cosmos" in answer["content"]
    assert "World models" in answer["content"]
    with main.SessionLocal() as db:
        assert not db.scalar(select(Commitment)) and not db.scalar(select(ReminderPlan))
        assert db.scalar(select(func.count()).select_from(ConversationProposal)) == 3
        assert db.scalar(select(Message).where(Message.content == original))


def test_old_title_is_not_a_current_deadline_across_dates_and_timezones(pg_client, scene):
    main, _ = scene
    with main.SessionLocal.begin() as db:
        owner = db.scalar(select(User))
        owner.timezone = "America/Los_Angeles"
        item = Commitment(user_id=owner.id,
                          title="Reach out to Samuel's contact before 9pm tomorrow",
                          confidence=1, derivation="legacy", created_at=datetime(
                              2026, 10, 23, 0, 30, tzinfo=timezone.utc))
        db.add(item)
        db.flush()
        data = describe(item, owner, db, NOW)
        assert data["due_at"] is None and "historical wording" in data["deadline_display"]
        answer = confirmation({"status": "read", "context": {"commitments": [data]}})
        assert "22 Oct 2026" in answer and "No structured deadline" in answer
        later = describe(item, owner, db, NOW + timedelta(days=10))
        assert later["due_at"] is None and later["deadline_display"] == data["deadline_display"]


def test_retrospective_completion_is_reported_once_and_stops_followups(pg_client, scene):
    main, gateway = scene
    act(pg_client, gateway, "save",
        "Track the product video and submission, check in every minute.",
        "create_commitment", {"title": "Product video and submission", "followup_enabled": True,
                              "followup_minutes": 1})
    with main.SessionLocal() as db:
        row = db.scalar(select(Commitment))
        identifier, version = row.id, row.version
    phrase = "Oh I actually finished the product video and made that submission days ago."
    answer = act(pg_client, gateway, "done", phrase, "update_commitment",
        {"id": identifier, "version": version, "action": "complete",
         "completion_time_text": "days ago"})
    assert "days ago" in answer["content"] and "No further check-ins" in answer["content"]
    with main.SessionLocal() as db:
        row = db.get(Commitment, identifier)
        saved_version, completed_at = row.version, utc(row.completed_at)
        assert row.next_relevant_moment is None
        report = describe(row, db.get(User, row.user_id), db)["completion_report"]
        assert report["timing_text"] == "days ago"
    main.runtime.clock.set(NOW + timedelta(days=1))
    answer = act(pg_client, gateway, "already", phrase, "update_commitment",
        {"id": identifier, "version": saved_version, "action": "complete"})
    assert "already recorded as completed" in answer["content"]
    with main.SessionLocal() as db:
        row = db.get(Commitment, identifier)
        assert row.version == saved_version and utc(row.completed_at) == completed_at


def test_forgetting_blocks_failed_request_recovery(pg_client, scene):
    main, gateway = scene
    gateway.scripts.append(GatewayError("unavailable"))
    send(pg_client, "first", "Remind me about the private essay.", allow_memory_write=True)
    with main.SessionLocal.begin() as db:
        source = db.scalar(select(Message).where(Message.role == "user")).id
        owner = db.scalar(select(User))
        owner.context_reset_at = owner.conversation_recall_after = NOW
    main.runtime.clock.set(NOW + timedelta(minutes=1))
    act(pg_client, gateway, "old", "Try the earlier request.", "schedule_reminder",
        {"topic": "Private essay", "when": {"kind": "after", "seconds": 60},
         "request_source_id": source})
    with main.SessionLocal() as db:
        assert not db.scalar(select(ReminderPlan))
        owner = db.scalar(select(User))
        data = build_context(db, owner.id, "private essay", now=NOW + timedelta(minutes=1)).payload
        assert not data["conversation_mentions"]
        assert "Remind me about the private essay" not in json.dumps(data)


def test_date_only_request_does_not_authorize_a_guessed_clock(pg_client, scene):
    main, gateway = scene
    answer = act(pg_client, gateway, "date-only",
        "Can you remind me by the 7th of November to check my dad's mobile data?",
        "schedule_reminder", {"topic": "Check dad's mobile data",
        "when": {"kind": "local", "date": "2026-11-07", "at": "00:00"}})
    assert "What time" in answer["content"]
    with main.SessionLocal() as db:
        assert db.scalar(select(ReminderPlan)) is None
        pending = db.scalar(select(ConversationProposal))
        identifier, version = pending.id, pending.version
        assert pending.arguments["when"]["date"] == "2026-11-07"
        assert not pending.arguments["when"].get("at")
    act(pg_client, gateway, "guess-on-yes", "Yes", "resolve_proposal",
        {"id": identifier, "version": version, "action": "execute",
         "changes": {"when": {"kind": "local", "at": "09:00"}}})
    with main.SessionLocal() as db:
        assert db.scalar(select(ReminderPlan)) is None
    act(pg_client, gateway, "clock", "9 AM UTC please", "resolve_proposal",
        {"id": identifier, "version": version, "action": "execute",
         "changes": {"when": {"kind": "local", "at": "09:00", "timezone": "UTC"}}})
    with main.SessionLocal() as db:
        assert utc(db.scalar(select(ReminderPlan)).due_at) == datetime(
            2026, 11, 7, 9, tzinfo=timezone.utc)


def test_conversational_reflection_start_uses_actual_skill_prompt(pg_client, scene):
    main, gateway = scene
    answer = act(pg_client, gateway, "start-reflection", "Can we do my evening reflection?",
                 "manage_workflow", {"kind": "reflection", "action": "start"})
    assert answer["content"] == "How did things go today?"
    with main.SessionLocal() as db:
        prompt = db.scalar(select(ReflectionPrompt))
        identifier, version = prompt.id, prompt.version
    answer = act(pg_client, gateway, "tiring-day", "Tiring day.", "manage_workflow",
        {"kind": "reflection", "action": "respond", "id": identifier, "version": version,
         "summary": "The owner reported a tiring day."})
    assert "reflection for" in answer["content"]
    with main.SessionLocal() as db:
        assert db.scalar(select(JournalEntry)).original_content == "Tiring day."


def test_batched_reminder_retains_other_mentions_without_formal_capture(pg_client, scene):
    main, gateway = scene
    text = ("I have to write a first draft of my Cosmos essay today. Also I need to be reminded "
            "to go netball at 7. And also work on world models today as well.")
    answer = act(pg_client, gateway, "batch-mentions", text, "perform_actions", {
        "actions": [{"tool_name": "schedule_reminder", "arguments": {"topic": "Netball"}}],
        "mentions": ["write a first draft of my Cosmos essay today", "work on world models today"],
    })
    assert all(word in answer["content"] for word in ("Netball", "Cosmos", "world models"))
    with main.SessionLocal() as db:
        assert db.scalar(select(Commitment)) is None
        assert db.scalar(select(ReminderPlan)) is None
        assert db.scalar(select(func.count()).select_from(ConversationProposal)) == 1


def test_batch_cannot_exceed_budget_nest_or_self_approve(pg_client, scene):
    main, gateway = scene
    actions = [{"tool_name": "create_commitment", "arguments": {
        "title": f"Task {i}", "followup_enabled": False}} for i in range(4)]
    gateway.scripts.append(reply("", tool("perform_actions", {"actions": actions}, "batch"),
                                  tool("create_commitment", {"title": "Fifth"}, "fifth")))
    answer = send(pg_client, "over-budget", "Save five tasks", allow_memory_write=True)
    assert "limit was exceeded" in answer["content"]
    act(pg_client, gateway, "nested", "Save tasks", "perform_actions", {
        "actions": [{"tool_name": "perform_actions", "arguments": {"actions": actions}}]})
    act(pg_client, gateway, "approval", "Offer to track the essay, ask before saving.",
        "perform_actions", {"actions": [
            {"tool_name": "propose_action", "arguments": {"title": "Track essay",
                "tool_name": "create_commitment", "arguments": {"title": "Essay"}}},
            {"tool_name": "resolve_proposal", "arguments": {"reference": "Track essay",
                "action": "execute"}},
        ]})
    with main.SessionLocal() as db:
        assert db.scalar(select(Commitment)) is None
        assert db.scalar(select(ConversationProposal)).state == "proposed"


def test_proposal_accepts_advertised_target_response_metadata(pg_client, scene):
    main, gateway = scene
    act(pg_client, gateway, "offer-meta", "Offer to track revising my portfolio, ask first.",
        "propose_action", {"tool_name": "create_commitment", "title": "Track portfolio",
                           "arguments": {"title": "Revise portfolio", "response_text": ""}})
    with main.SessionLocal() as db:
        pending = db.scalar(select(ConversationProposal))
        assert pending and pending.state == "proposed"
        assert "response_text" not in pending.arguments
        assert db.scalar(select(Commitment)) is None
