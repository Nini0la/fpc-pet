"""Bounded conversation/effect evidence, using existing messages and operation records."""

import re

from sqlalchemy import case, func, select

from .history import SharedHistoryRecallSkill
from .models import (
    AssistanceRun,
    Commitment,
    ConversationProposal,
    JournalEntry,
    Message,
    ProvenanceLink,
    ReflectionPrompt,
    ReminderPlan,
    Thread,
    VocabularyAttempt,
)

_RECALL_WORDS = set(
    (
        "did say said anything something mention mentioned remember record earlier "
        "about writing updated activity"
    ).split()
)


def matching_mentions(db, owner, terms, recent_ids, cutoff):
    terms = [term for term in terms if len(term) >= 3 and term not in _RECALL_WORDS][:12]
    if not terms:
        return []
    score = sum(
        (
            case(
                (
                    func.lower(Message.content).regexp_match(
                        r"(^|[^a-z0-9_])" + re.escape(term) + r"([^a-z0-9_]|$)"
                    ),
                    1,
                ),
                else_=0,
            )
            for term in terms
        ),
        start=0,
    )
    query = select(Message, score.label("match_score")).where(
        Message.user_id == owner,
        Message.role == "user",
        Message.id.not_in(recent_ids),
        score > 0,
    )
    if cutoff:
        query = query.where(Message.created_at > cutoff)
    # Corrections invalidate sources of the corrected record, not unrelated conversations.
    for model in (Thread, Commitment, JournalEntry):
        corrected = select(model.id).where(
            model.user_id == owner, (model.version > 1) | model.deleted.is_(True)
        )
        excluded_sources = select(ProvenanceLink.source_id).where(
            ProvenanceLink.user_id == owner,
            ProvenanceLink.source_type == "message",
            ProvenanceLink.target_id.in_(corrected),
            ProvenanceLink.source_id.is_not(None),
        )
        query = query.where(Message.id.not_in(excluded_sources))
    candidates = db.execute(
        query.order_by(score.desc(), Message.created_at.desc(), Message.ordinal.desc()).limit(12)
    )
    result = []
    for message, _ in candidates:
        if not SharedHistoryRecallSkill().allows_episodic_content(message.content):
            continue
        positions = [message.content.casefold().find(term) for term in terms]
        pivot = min(p for p in positions if p >= 0)
        start = max(0, pivot - 160)
        result.append(
            {
                "id": message.id,
                "created_at": message.created_at.isoformat(),
                "role": "user",
                "content": message.content[start : start + 900],
                "excerpt": start > 0 or len(message.content) > 900,
                "evidence_kind": "conversational_mention_not_a_saved_commitment",
            }
        )
        from .recovery import request_evidence

        recovery = request_evidence(db, owner, message, include_text=False)
        if recovery:
            result[-1]["recovery"] = recovery
        if len(result) == 3:
            break
    return result


def current_target(db, owner, result):
    kind = result.get("kind")
    model = {
        "commitment": Commitment,
        "project": Thread,
        "idea": Thread,
        "thread": Thread,
        "reminder": ReminderPlan,
        "proposal": ConversationProposal,
    }.get(kind)
    if kind == "workflow":
        activity = result.get("transition", {}).get("type")
        model = (
            ReflectionPrompt
            if activity == "reflection"
            else VocabularyAttempt
            if activity == "vocabulary"
            else None
        )
    if model is None or not result.get("id"):
        return None
    row = db.scalar(select(model).where(model.user_id == owner, model.id == result["id"]))
    if row is None or getattr(row, "deleted", False):
        return {"record_available": False}
    data = {
        "id": row.id,
        "version": row.version,
        "kind": kind,
        "title": getattr(row, "title", getattr(row, "topic", "")),
        "state": getattr(row, "state", getattr(row, "workflow_state", None)),
    }
    if isinstance(row, ReflectionPrompt):
        data.update(
            activity="reflection", local_date=str(row.local_date), journal_id=row.journal_entry_id
        )
        journal = db.get(JournalEntry, row.journal_entry_id) if row.journal_entry_id else None
        if journal and journal.user_id == owner and not journal.deleted:
            data["current_reflection"] = (
                journal.corrected_content if journal.corrected_content is not None
                else journal.original_content
            )[:350]
    elif isinstance(row, VocabularyAttempt):
        data.update(activity="vocabulary", prompt=row.prompt[:200])
    elif isinstance(row, ConversationProposal) and row.result:
        data["executed_effect"] = current_target(db, owner, row.result)
    return data


def recent_operations(db, owner, cutoff):
    query = (
        select(AssistanceRun)
        .join(Message, Message.id == AssistanceRun.message_id)
        .where(
            AssistanceRun.user_id == owner,
            Message.user_id == owner,
            AssistanceRun.message_id.is_not(None),
            AssistanceRun.trace_status != "cleared_by_memory_deletion",
        )
    )
    if cutoff:
        query = query.where(AssistanceRun.created_at >= cutoff)
    entries = []
    for run in db.scalars(query.order_by(Message.ordinal.desc()).limit(12)):
        outcomes = []
        for result in run.tool_results or []:
            if result.get("status") == "read":
                continue
            outcomes.append(
                {
                    "tool": result.get("tool"),
                    "status": result.get("status"),
                    "reason": result.get("reason"),
                    "transition": result.get("transition"),
                    "current_record": current_target(db, owner, result),
                }
            )
        if outcomes or run.execution_status in {
            "failed", "limited", "rejected", "awaiting_clarification",
        }:
            from .recovery import preceding_source, request_evidence

            source_request = request_evidence(
                db, owner, preceding_source(db, owner, run.message_id))
            entries.append(
                {
                    "id": run.id,
                    "event_id": run.event_id,
                    "message_id": run.message_id,
                    "at": run.created_at.isoformat(),
                    "response_status": run.execution_status,
                    "persisted_turn": True,
                    "operation_outcomes": outcomes,
                    **({"source_request": source_request} if source_request else {}),
                    "failure": next((u.get("error") for u in reversed(run.usage or [])
                                     if u.get("error")), None),
                    "interpretation": "These outcomes belong to a persisted turn; "
                    "Current state may have changed. "
                    "Model response failure does not undo saved actions.",
                }
            )
        if len(entries) == 3:
            break
    return entries
