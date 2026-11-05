"""Real PostgreSQL/context/runtime/worker journeys; scripted model and Telegram transport."""

import json
from datetime import timedelta

from sqlalchemy import select
from test_assistance import reply, send, tool
from test_postgres_quality import csrf
from test_postgres_quality import pg_client as pg_client
from test_postgres_quality import postgres_url as postgres_url
from test_semantic_conversation import NOW, act
from test_semantic_conversation import scene as scene

from app.agent import AgentRuntime
from app.clock import FakeClock
from app.commitments import describe, utc
from app.context import build_context
from app.gateway import GatewayError
from app.intentions import project, stated_reason
from app.models import (
    Commitment,
    CommitmentRevision,
    ConversationProposal,
    JournalEntry,
    Message,
    ReflectionPrompt,
    ReminderPlan,
    ScheduledAction,
    Thread,
    User,
)
from app.scheduler import tick

ESSAY = ("I need to write an essay for Cosmos Institute and it's better "
         "I finish that before Wednesday next week.")


def context(gateway):
    return json.loads(gateway.calls[-1]["messages"][1]["content"].split("\n", 1)[1])


def test_failed_mention_is_retrieved_without_creating_a_commitment(pg_client, scene):
    main, gateway = scene
    gateway.scripts.append(GatewayError("invalid_response"))
    failure = send(pg_client, "essay", ESSAY, allow_memory_write=False)
    assert "message is still in the conversation" in failure["content"]
    with main.SessionLocal() as db:
        source = db.scalar(select(Message).where(Message.content == ESSAY)).id
        assert db.scalar(select(Commitment)) is None
    for n in range(3):
        gateway.scripts.append(reply("We can discuss that."))
        send(pg_client, f"interruption-{n}", f"Unrelated conversation {n}")
    gateway.scripts.append(
        reply("You mentioned an essay for Cosmos Institute. It wasn't saved as a commitment.")
    )
    answer = send(pg_client, "recall", "Did I say anything about writing an essay?")
    evidence = context(gateway)
    assert any(
        m["id"] == source and "Cosmos Institute" in m["content"]
        for m in evidence["conversation_mentions"]
    )
    assert all(m["id"] != source for m in evidence["recent_conversation"])
    assert len(json.dumps(evidence)) <= 12000 and len(evidence["conversation_mentions"]) <= 3
    assert "wasn't saved" in answer["content"]
    with main.SessionLocal() as db:
        assert not db.scalar(select(Commitment)) and not db.scalar(select(ReminderPlan))


def test_unrelated_correction_does_not_erase_mentions_but_deletion_respects_forgetting(
    pg_client, scene
):
    main, gateway = scene
    gateway.scripts.append(reply("We can talk about the essay."))
    send(pg_client, "essay", ESSAY)
    with main.SessionLocal.begin() as db:
        owner = db.scalar(select(User))
        row = Thread(
            user_id=owner.id, title="Unrelated garden", description="old", derivation="fixture"
        )
        db.add(row)
        db.flush()
        identifier = row.id
    assert pg_client.patch(
        f"/api/threads/{identifier}",
        headers=csrf(pg_client),
        json={"version": 1, "title": "Unrelated garden", "description": "new"},
    ).is_success
    gateway.scripts.append(reply("You mentioned the essay."))
    send(pg_client, "recall", "Did I mention Cosmos Institute?")
    assert any("essay" in m["content"] for m in context(gateway)["conversation_mentions"])
    assert pg_client.delete(
        f"/api/threads/{identifier}?version=2", headers=csrf(pg_client)
    ).is_success
    with main.SessionLocal() as db:
        owner = db.scalar(select(User))
        data = build_context(db, owner.id, "Cosmos essay", now=NOW).payload
        assert data["conversation_mentions"] == []


def test_reflection_write_survives_response_failure_and_can_be_explained(pg_client, scene):
    main, gateway = scene
    assert pg_client.post(
        "/api/events/scheduled",
        headers=csrf(pg_client),
        json={"event_id": "reflection", "kind": "evening_reflection"},
    ).is_success
    with main.SessionLocal() as db:
        prompt = db.scalar(select(ReflectionPrompt))
        identifier, version = prompt.id, prompt.version
    gateway.scripts.extend(
        [
            reply(
                "",
                tool(
                    "manage_workflow",
                    {
                        "kind": "reflection",
                        "id": identifier,
                        "version": version,
                        "action": "respond",
                        "summary": "The owner reported a tiring day.",
                    },
                    "write",
                ),
                tool("get_commitments", {}, "read"),
            ),
            GatewayError("unavailable"),
        ]
    )
    answer = send(pg_client, "tiring", "Tiring day.", allow_memory_write=True)
    assert "reflection for" in answer["content"] and "Activity updated" not in answer["content"]
    assert identifier not in answer["content"] and "Server receipts" not in answer["content"]
    with main.SessionLocal() as db:
        assert db.scalar(select(JournalEntry)).original_content == "Tiring day."
        assert db.get(ReflectionPrompt, identifier).workflow_state == "completed"
    gateway.scripts.append(reply("Activity updated."))  # Bad wording must be grounded, not echoed.
    explained = send(pg_client, "explain", "What activity was updated?")
    assert "reflection" in explained["content"] and "Tiring day" in explained["content"]
    outcome = context(gateway)["recent_operations"][0]
    assert outcome["response_status"] == "failed" and outcome["persisted_turn"]
    assert outcome["operation_outcomes"][0]["current_record"]["journal_id"]


def test_rejected_write_does_not_claim_success_or_create_activity(pg_client, scene):
    main, gateway = scene
    message = act(
        pg_client,
        gateway,
        "denied",
        "Please save this",
        "create_commitment",
        {"title": "Essay"},
        allowed=False,
    )
    assert "permission" in message["content"] and "Saved" not in message["content"]
    with main.SessionLocal() as db:
        assert db.scalar(select(Commitment)) is None


def test_tracking_acceptance_plus_read_retains_schedule_question_and_ordered_goal(pg_client, scene):
    main, gateway = scene
    plan = {
        "title": "Acceptable submission",
        "purpose": "Reach approximately 90% readiness",
        "next_action": "Finish product path",
        "completion_criteria": "Finish product path, then record demo video",
    }
    act(
        pg_client,
        gateway,
        "offer",
        "I need the product path then a video to reach 90% readiness.",
        "propose_action",
        {"title": "Track submission", "tool_name": "create_commitment", "arguments": plan},
    )
    with main.SessionLocal() as db:
        p = db.scalar(select(ConversationProposal))
        identifier, version = p.id, p.version
    gateway.scripts.extend(
        [
            reply(
                "",
                tool(
                    "resolve_proposal",
                    {"reference": identifier, "version": version, "action": "execute"},
                    "accept",
                ),
                tool("get_commitments", {}, "list"),
            ),
            reply("Your submission is the only open commitment here."),
        ]
    )
    answer = send(
        pg_client,
        "accept",
        "That would be nice. Btw do I have any hanging commitments?",
        allow_memory_write=True,
    )
    assert "No automatic check-in" in answer["content"] and "when or how often" in answer["content"]
    assert "only open commitment" in answer["content"]
    with main.SessionLocal() as db:
        c = db.scalar(select(Commitment))
        cid = c.id
        assert (
            c.purpose == plan["purpose"]
            and not c.followup_enabled
            and c.next_relevant_moment is None
        )
        pending = db.scalar(
            select(ConversationProposal).where(ConversationProposal.state == "needs_clarification")
        )
        pid, pv = pending.id, pending.version
    act(
        pg_client,
        gateway,
        "cadence",
        "Check in every 20 minutes.",
        "resolve_proposal",
        {"id": pid, "version": pv, "action": "execute", "changes": {"followup_minutes": 20}},
    )
    with main.SessionLocal() as db:
        c = db.get(Commitment, cid)
        assert c.followup_enabled and utc(c.next_relevant_moment) == NOW + timedelta(minutes=20)
        version = c.version
    act(
        pg_client,
        gateway,
        "step",
        "I finished product path; next is the video.",
        "update_commitment",
        {"id": cid, "version": version, "next_action": "Record demo video"},
    )
    with main.SessionLocal() as db:
        c = db.get(Commitment, cid)
        assert c.state == "open" and c.completion_criteria == plan["completion_criteria"]
        assert c.purpose == plan["purpose"]


def test_explicit_motive_correction_preserves_provenance_and_does_not_reschedule(pg_client, scene):
    main, gateway = scene
    act(
        pg_client,
        gateway,
        "capture",
        "Track the essay because I want to qualify for the fellowship. Check in every 20 minutes.",
        "create_commitment",
        {
            "title": "Essay",
            "purpose": "I want to qualify for the fellowship",
            "followup_enabled": True,
            "followup_minutes": 20,
        },
    )
    with main.SessionLocal.begin() as db:
        c = db.scalar(select(Commitment))
        cid, version = c.id, c.version
        assert c.intention_context["purpose"]["basis"] == "user_stated"
        assert c.intention_context["purpose"]["source_message_id"]
        c.followup_count = 1
        due = utc(c.next_relevant_moment)
    main.runtime.clock.set(NOW + timedelta(minutes=5))
    reason = "I want feedback on my ideas"
    act(
        pg_client,
        gateway,
        "correct",
        "Actually, I want feedback on my ideas.",
        "update_commitment",
        {
            "id": cid,
            "version": version,
            "purpose": reason,
            "intentions": [
                {"field": "purpose", "text": reason, "basis": "confirmed", "source_quote": reason}
            ],
        },
    )
    with main.SessionLocal() as db:
        c = db.get(Commitment, cid)
        assert c.purpose == reason and c.intention_context["purpose"]["basis"] == "confirmed"
        assert utc(c.next_relevant_moment) == due and c.followup_count == 1
        revisions = list(
            db.scalars(select(CommitmentRevision).where(CommitmentRevision.commitment_id == cid))
        )
        assert any(
            r.snapshot["purpose"] == "I want to qualify for the fellowship" for r in revisions
        )
        assert (
            describe(c, db.get(User, c.user_id), db, NOW)["attention_context"][
                "intervention_policy"
            ]["minutes"]
            == 20
        )
    worker = AgentRuntime(clock=FakeClock(due))
    assert tick(main.SessionLocal, worker)["executed"] == 1
    assert tick(main.SessionLocal, worker)["executed"] == 0
    with main.SessionLocal() as db:
        action = db.scalar(select(ScheduledAction).where(ScheduledAction.state == "succeeded"))
        text = db.get(Message, action.message_id).content
        assert reason in text and "qualify for the fellowship" not in text


def test_inferred_reason_stays_inferred_and_missing_reason_stays_unknown(pg_client, scene):
    main, gateway = scene
    act(
        pg_client,
        gateway,
        "inferred",
        "Save an essay commitment. No check-ins.",
        "create_commitment",
        {"title": "Essay", "purpose": "Impress the panel", "followup_enabled": False},
    )
    act(
        pg_client,
        gateway,
        "unknown",
        "Save Call Jolly. No check-ins.",
        "create_commitment",
        {"title": "Call Jolly", "followup_enabled": False},
    )
    with main.SessionLocal() as db:
        inferred = db.scalar(select(Commitment).where(Commitment.title == "Essay"))
        unknown = db.scalar(select(Commitment).where(Commitment.title == "Call Jolly"))
        assert project(inferred)["purpose"]["basis"] == "inferred" and not stated_reason(inferred)
        assert not unknown.purpose and "purpose" not in unknown.intention_context


def test_reminder_reason_survives_timing_clarification_and_simple_reminders_need_no_reason(
    pg_client, scene
):
    main, gateway = scene
    reason = "I need to confirm the arrangements for tomorrow"
    answer = act(
        pg_client,
        gateway,
        "reason",
        f"Remind me to call Jolly because {reason}.",
        "schedule_reminder",
        {
            "topic": "Call Jolly",
            "intentions": [
                {"field": "reason", "text": reason, "basis": "user_stated", "source_quote": reason}
            ],
        },
    )
    assert "When" in answer["content"]
    with main.SessionLocal() as db:
        p = db.scalar(select(ConversationProposal))
        pid, version = p.id, p.version
    act(
        pg_client,
        gateway,
        "when",
        "In 35 minutes.",
        "resolve_proposal",
        {
            "id": pid,
            "version": version,
            "action": "execute",
            "changes": {"when": {"kind": "after", "seconds": 2100}},
        },
    )
    simple = act(
        pg_client,
        gateway,
        "simple",
        "Remind me to stretch in 35 minutes.",
        "schedule_reminder",
        {"topic": "Stretch", "when": {"kind": "after", "seconds": 2100}},
    )
    assert "why" not in simple["content"].lower() and "?" not in simple["content"]
    with main.SessionLocal() as db:
        plan = db.scalar(select(ReminderPlan).where(ReminderPlan.topic == "Call Jolly"))
        assert stated_reason(plan) == reason
        assert (
            db.scalar(select(ReminderPlan).where(ReminderPlan.topic == "Stretch")).intention_context
            == {}
        )


def test_related_motivation_is_labeled_and_not_applied_to_unrelated_commitments(pg_client, scene):
    main, gateway = scene
    act(
        pg_client,
        gateway,
        "project",
        "Save Career project because I want meaningful work.",
        "save_project",
        {"title": "Career", "description": "Career direction", "why": "I want meaningful work"},
    )
    with main.SessionLocal() as db:
        parent = db.scalar(select(Thread))
        parent_id = parent.id
    gateway.scripts.append(
        reply(
            "",
            tool(
                "create_commitment",
                {
                    "title": "Interview practice",
                    "project_id": parent_id,
                    "purpose": "I want meaningful work",
                    "followup_enabled": False,
                    "intentions": [
                        {"field": "purpose", "text": "I want meaningful work", "basis": "derived"}
                    ],
                    "response_text": "Saved.",
                },
            ),
        )
    )
    send(
        pg_client,
        "child",
        "Save interview practice in Career.",
        active_thread_id=parent_id,
        allow_memory_write=True,
    )
    with main.SessionLocal() as db:
        child = db.scalar(select(Commitment).where(Commitment.title == "Interview practice"))
        assert project(child, db)["purpose"]["basis"] == "derived"
        child.related_thread_id = None
        assert project(child, db)["purpose"]["basis"] == "stale_derived"
        db.rollback()
    act(
        pg_client,
        gateway,
        "unrelated",
        "Save Call Jolly. No check-ins.",
        "create_commitment",
        {"title": "Call Jolly", "followup_enabled": False},
    )
    assert pg_client.patch(
        f"/api/threads/{parent_id}",
        headers=csrf(pg_client),
        json={"version": 1, "title": "Career", "why": "A different direction"},
    ).is_success
    with main.SessionLocal() as db:
        child = db.scalar(select(Commitment).where(Commitment.title == "Interview practice"))
        assert child.intention_context["purpose"]["basis"] == "derived"
        assert project(child, db)["purpose"]["basis"] == "stale_derived"
        assert not db.scalar(select(Commitment).where(Commitment.title == "Call Jolly")).purpose


def test_change_reason_is_evidenced_and_previous_cause_is_not_assumed_for_later_changes(
    pg_client, scene
):
    main, gateway = scene
    act(
        pg_client,
        gateway,
        "save",
        "Save Submit essay, no check-ins.",
        "create_commitment",
        {"title": "Submit essay", "followup_enabled": False},
    )
    with main.SessionLocal() as db:
        row = db.scalar(select(Commitment))
        identifier, version = row.id, row.version
    act(
        pg_client,
        gateway,
        "delay",
        "The deadline moved to 7 November at 6pm because the train was cancelled.",
        "update_commitment",
        {
            "id": identifier,
            "version": version,
            "deadline": {"kind": "local", "date": "2026-11-07", "at": "18:00"},
            "intentions": [
                {
                    "field": "change_reason",
                    "text": "the train was cancelled",
                    "source_quote": "the train was cancelled",
                    "basis": "user_stated",
                    "category": "obstacle",
                }
            ],
        },
    )
    with main.SessionLocal() as db:
        row = db.get(Commitment, identifier)
        version = row.version
        assert row.intention_context["change_reason"]["basis"] == "user_stated"
        assert (
            "07 Nov 2026 at 18:00 WAT"
            in describe(row, db.get(User, row.user_id))["deadline_display"]
        )
    act(
        pg_client,
        gateway,
        "next",
        "Next step: outline the essay.",
        "update_commitment",
        {"id": identifier, "version": version, "next_action": "Outline the essay"},
    )
    with main.SessionLocal() as db:
        assert "change_reason" not in db.get(Commitment, identifier).intention_context
        assert any(
            "change_reason" in r.snapshot.get("intention_context", {})
            for r in db.scalars(
                select(CommitmentRevision).where(CommitmentRevision.commitment_id == identifier)
            )
        )
