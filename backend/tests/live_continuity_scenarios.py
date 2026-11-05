"""Synthetic continuity extension to live_nebius_acceptance; never uses owner conversations.

Enable with MICA_CONTINUITY_ACCEPTANCE=1. Failure and interruptions are explicitly injected;
subsequent recall, reflection, proposal acceptance and intention changes use the real HTTP API
and real configured Nebius gateway. No external channel credentials are supplied by the harness.
"""

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agent import AgentRuntime, RuntimeEvent
from app.clock import FakeClock
from app.gateway import GatewayError
from app.models import (
    AssistanceRun,
    Commitment,
    CommitmentRevision,
    ConversationProposal,
    JournalEntry,
    Message,
    ReflectionPrompt,
    User,
)
from app.persistence import append_message, get_or_create_conversation


class InjectedFailure:
    def complete(self, messages, tools):
        raise GatewayError("invalid_response")


def initial_context(turn):
    messages = turn["inspection"]["trace"]["calls"][0]["request"]["messages"]
    return json.loads(messages[1]["content"].split("\n", 1)[1])


def exercise(client, engine, turn, report):
    evidence = report["continuity"] = {
        "failure_fixture": "Injected invalid_response, not an observed Nebius failure",
        "interruption_fixture": "Four seeded synthetic messages; no model calls",
        "checks": [],
    }
    now = datetime.now(timezone.utc)
    essay = (
        "I need to write an essay for the fictional Aurora Institute, "
        "ideally before Wednesday next week."
    )
    with Session(engine) as db:
        owner = db.scalar(select(User))
        conversation = get_or_create_conversation(db, owner.id)
        event = RuntimeEvent(
            external_id="synthetic-failed-essay", kind="user_message", content=essay,
            conversation_id=conversation.id,
        )
        runtime = AgentRuntime(
            gateway=InjectedFailure(), clock=FakeClock(now - timedelta(minutes=5)),
        )
        runtime.handle(db, owner.id, event)
        assert runtime.handle(db, owner.id, event)["idempotent"]
        source = db.scalar(select(Message).where(Message.content == essay))
        source_id = source.id
        run = db.scalar(select(AssistanceRun))
        assert run.execution_status == "failed" and not run.tool_results
        assert db.scalar(select(func.count()).select_from(Commitment)) == 0
        evidence["failed_source_id"] = source_id
        for ordinal, (role, content) in enumerate([
            ("user", "I took a short walk."), ("assistant", "How was the walk?"),
            ("user", "Quiet and refreshing."), ("assistant", "Welcome back."),
        ]):
            append_message(
                db, user_id=owner.id, conversation_id=conversation.id, role=role, actor=role,
                content=content, created_at=now - timedelta(minutes=4 - ordinal),
            )
        db.commit()
    recall = turn("historical_mention", "Did I say anything about writing an essay?")
    context = initial_context(recall)
    assert any(m["id"] == source_id for m in context["conversation_mentions"])
    assert all(m["id"] != source_id for m in context["recent_conversation"])
    assert "aurora" in recall["response"].lower()
    assert "mentioned" in recall["response"].lower() or "you said" in recall["response"].lower()
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(Commitment)) == 0
    evidence["checks"].append("failed utterance recovered without a fabricated commitment")

    response = client.post("/api/events/scheduled", json={
        "event_id": "synthetic-reflection", "kind": "evening_reflection",
    })
    assert response.is_success
    reflection = turn("reflection_capture", "Tiring day. Please put that in my reflection.")
    assert "reflection" in reflection["response"].lower()
    assert "activity updated" not in reflection["response"].lower()
    with Session(engine) as db:
        journal = db.scalar(select(JournalEntry))
        assert journal and "Tiring day" in journal.original_content
        assert db.scalar(select(ReflectionPrompt)).workflow_state == "completed"
        evidence["journal_id"] = journal.id
    explanation = turn("reflection_explanation", "What activity was updated, and what changed?")
    assert "reflection" in explanation["response"].lower()
    assert "tiring" in explanation["response"].lower()
    assert any(
        (outcome.get("current_record") or {}).get("activity") == "reflection"
        for operation in initial_context(explanation)["recent_operations"]
        for outcome in operation["operation_outcomes"]
    )
    evidence["checks"].append("reflection write explained using persisted operation evidence")

    turn(
        "tracking_offer",
        "I want to finish the prototype, then record the video for a project called Aurora demo. "
        "The goal is a complete submission. This matters because I want feedback on my ideas. "
        "Please offer to track this as one commitment; ask me before saving it.",
    )
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(Commitment)) == 0
        assert db.scalar(select(ConversationProposal).where(
            ConversationProposal.tool_name == "create_commitment",
            ConversationProposal.state == "proposed",
        ))
    accepted = turn(
        "accept_and_read", "That would be nice. Btw do I have any hanging commitments?",
    )
    with Session(engine) as db:
        item = db.scalar(select(Commitment))
        assert item and "aurora" in item.title.lower()
        cid = item.id
        assert not item.followup_enabled and item.next_relevant_moment is None
        assert "video" in (item.completion_criteria + item.next_action).lower()
        assert item.intention_context["purpose"]["basis"] in {"user_stated", "inferred"}
        evidence["commitment_id"] = cid
    executions = accepted["inspection"]["trace"]["tool_executions"]
    assert any(t["name"] == "resolve_proposal" for t in executions)
    assert any(t["name"] == "get_commitments" for t in executions)
    with Session(engine) as db:
        pending_cadence = bool(db.scalar(select(ConversationProposal).where(
            ConversationProposal.state == "needs_clarification",
        )))
    evidence["cadence_question_retained"] = pending_cadence
    if pending_cadence:
        assert "when or how often" in accepted["response"]
    turn("cadence_declined", "No automatic check-ins for Aurora demo. Just keep the commitment.")
    with Session(engine) as db:
        assert not db.get(Commitment, cid).followup_enabled
        assert not db.scalar(select(ConversationProposal).where(
            ConversationProposal.state == "needs_clarification",
        ))
    evidence["checks"].append("compound acceptance plus read; no invented monitoring cadence")

    new_reason = "I want to test whether the explanation is clear"
    corrected = turn(
        "purpose_and_plan_correction",
        f"For Aurora demo, correct my reason to: {new_reason}. "
        "The prototype is finished; the next step is recording the video, "
        "not completing the whole commitment. Set the deadline to 7 November 2026 at 18:00 UTC.",
    )
    with Session(engine) as db:
        item = db.get(Commitment, cid)
        assert item.state in {"open", "in_progress"}
        assert "video" in item.next_action.lower()
        assert item.purpose.casefold().rstrip(".") == new_reason.casefold()
        assert item.intention_context["purpose"]["basis"] in {"confirmed", "user_stated"}
        assert item.due_at == datetime(2026, 11, 7, 18, tzinfo=timezone.utc)
        revisions = list(db.scalars(select(CommitmentRevision).where(
            CommitmentRevision.commitment_id == cid,
        )))
        assert any("feedback" in r.snapshot.get("purpose", "").lower() for r in revisions)
        assert cid not in corrected["response"]
        evidence["final_commitment"] = {
            "title": item.title, "purpose": item.purpose, "next_action": item.next_action,
            "completion_criteria": item.completion_criteria, "due_at": item.due_at.isoformat(),
            "intention_context": item.intention_context,
        }
    evidence["checks"].append("reason correction retains revisions and ordered remaining step")
