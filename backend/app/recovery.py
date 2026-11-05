"""Recover failed turns through existing messages, operation evidence and proposals."""

from sqlalchemy import select

from .commitments import utc
from .history import SharedHistoryRecallSkill
from .models import AssistanceRun, ConversationProposal, Message, ProvenanceLink, User

UNFINISHED = {"failed", "limited", "rejected", "awaiting_clarification"}


def request_evidence(db, owner, source, *, include_text=True):
    if source is None or source.user_id != owner or source.role != "user":
        return None
    user = db.get(User, owner)
    if (user.conversation_recall_after
            and utc(source.created_at) <= utc(user.conversation_recall_after)):
        return None
    if not SharedHistoryRecallSkill().allows_episodic_content(source.content):
        return None
    response = db.scalar(select(Message).where(
        Message.user_id == owner, Message.conversation_id == source.conversation_id,
        Message.ordinal == source.ordinal + 1, Message.role == "assistant",
    ))
    run = db.scalar(select(AssistanceRun).where(
        AssistanceRun.user_id == owner, AssistanceRun.message_id == response.id,
    )) if response else None
    if (not run or run.execution_status not in UNFINISHED
            or run.trace_status == "cleared_by_memory_deletion"):
        return None
    handled = bool(db.scalar(select(ProvenanceLink.id).where(
        ProvenanceLink.user_id == owner, ProvenanceLink.source_type == "request_recovery",
        ProvenanceLink.source_id == source.id,
    ).limit(1)))
    pending = list(db.scalars(select(ConversationProposal).where(
        ConversationProposal.user_id == owner, ConversationProposal.source_message_id == source.id,
        ConversationProposal.state.in_(["proposed", "needs_clarification", "paused"]),
    ).order_by(ConversationProposal.created_at).limit(3)))
    effects = handled or any(
        r.get("status") in {"saved", "updated", "proposed", "needs_clarification"}
        for r in run.tool_results or [])
    return {
        "source_message_id": source.id, "source_at": utc(source.created_at).isoformat(),
        "response_status": run.execution_status, "effects_recorded": effects,
        "pending_proposals": [{"id": p.id, "version": p.version, "title": p.title,
                               "tool_name": p.tool_name, "state": p.state} for p in pending],
        **({"text": source.content[:1000], "excerpt": len(source.content) > 1000}
           if include_text else {}),
        "recovery_rule": "Use pending proposals; never repeat recorded effects. "
                         "With no effect, an owner-requested retry may use request_source_id. "
                         "The current write grant is still required.",
    }


def preceding_source(db, owner, response_id):
    response = db.get(Message, response_id)
    if response is None or response.user_id != owner:
        return None
    return db.scalar(select(Message).where(
        Message.user_id == owner, Message.conversation_id == response.conversation_id,
        Message.ordinal == response.ordinal - 1, Message.role == "user",
    ))


def recovery_source(db, owner, identifier, context, event_id):
    views = [r.get("source_request") for r in context.get("recent_operations", [])]
    views += [r.get("recovery") for r in context.get("conversation_mentions", [])]
    selected = next((r for r in views if r and r["source_message_id"] == identifier), None)
    if selected is None or selected["effects_recorded"] or selected["pending_proposals"]:
        raise ValueError("Use the pending proposal or outcome; don't repeat completed work.")
    source = db.get(Message, identifier)
    evidence = request_evidence(db, owner, source)
    if evidence is None:
        raise ValueError("That earlier request is not available for recovery.")
    prior = db.scalar(select(ProvenanceLink.id).where(
        ProvenanceLink.user_id == owner, ProvenanceLink.source_type == "request_recovery",
        ProvenanceLink.source_id == identifier,
        ProvenanceLink.derivation != f"recovery:{event_id}",
    ).limit(1))
    if prior:
        raise ValueError("That request already has recorded effects; use its remaining proposals.")
    return source


def record_recovery(db, owner, result, source, authorization_source, event_id, now):
    if result.get("id") and result.get("status") in {
        "saved", "updated", "proposed", "needs_clarification",
    }:
        for kind, identifier, derivation in (
            ("request_recovery", source.id, f"recovery:{event_id}"),
            ("message", authorization_source, "recovery-authorized-by-current-turn"),
        ):
            db.add(ProvenanceLink(user_id=owner, target_id=result["id"], source_type=kind,
                source_id=identifier, confidence=1.0, derivation=derivation, created_at=now))
        result["recovery_source_id"] = source.id


def retain_failed_call(db, owner, name, arguments, result, source, now, allowed_fields):
    from .continuation import PROPOSABLE, save_proposal

    if (name not in PROPOSABLE or result.get("status") != "rejected"
            or result.get("reason") not in {
                "tool_failed", "invalid_arguments", "clarification_required", "ambiguous_deadline",
                "followup_schedule_required", "time_limit",
            }):
        return result
    values = {k: v for k, v in arguments.items() if k not in {"response_text", "request_source_id"}}
    # Do not preserve rejected attribution or malformed identities as future model evidence.
    if values.get("intentions") or any(
        key.endswith("_id") and isinstance(value, str) and not value.strip()
        for key, value in values.items()
    ):
        return result
    if (set(values) - set(allowed_fields)
            or not SharedHistoryRecallSkill().allows_episodic_content(str(values))):
        return result
    title = values.get("title") or values.get("topic") or "Your unfinished request"
    if not isinstance(title, str):
        return result
    proposal = save_proposal(db, owner, name, title[:500], values, source, now,
                             state="needs_clarification")
    if proposal.get("kind") != "proposal":
        return result
    return {**proposal, "execution": result,
            "question": result.get("question") or "I've kept this request, but it hasn't run. "
                        "Would you like to clarify it or try it again?"}
