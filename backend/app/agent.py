from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import AgentEvent, Commitment, Message, ProvenanceLink, SkillRun, Thread
from .runtime import DeterministicModel, StateExtractor


@dataclass(frozen=True)
class RuntimeEvent:
    external_id: str
    kind: str
    content: str | None = None
    conversation_id: str | None = None


class AgentRuntime:
    """The single entry point for reactive and scheduled events."""

    def __init__(self, model: DeterministicModel | None = None) -> None:
        self.extractor = StateExtractor()
        self.model = model or DeterministicModel()

    def handle(self, db: Session, user_id: str, event: RuntimeEvent) -> dict[str, Any]:
        prior = db.scalar(
            select(AgentEvent).where(
                AgentEvent.user_id == user_id, AgentEvent.external_id == event.external_id
            )
        )
        if prior:
            return {"idempotent": True, "handled_by": "AgentRuntime.handle"}
        recorded = AgentEvent(user_id=user_id, external_id=event.external_id, kind=event.kind)
        db.add(recorded)
        db.flush()
        if event.kind == "user_message" and event.content and event.conversation_id:
            user_message = Message(
                user_id=user_id,
                conversation_id=event.conversation_id,
                role="user",
                actor="user",
                content=event.content,
            )
            db.add(user_message)
            db.flush()
            proposal = self.extractor.extract(event.content)
            target: Commitment | Thread | None = None
            if proposal.kind == "commitment":
                target = Commitment(
                    user_id=user_id,
                    title=proposal.title or "",
                    deadline_hint=proposal.deadline_hint,
                    effort_minutes=proposal.effort_minutes,
                    confidence=proposal.confidence,
                    derivation=proposal.derivation,
                )
            elif proposal.kind == "thread":
                target = Thread(
                    user_id=user_id,
                    title=proposal.title or "",
                    confidence=proposal.confidence,
                    derivation=proposal.derivation,
                )
            if target is not None:
                db.add(target)
                db.flush()
                db.add(
                    ProvenanceLink(
                        user_id=user_id,
                        target_id=target.id,
                        source_type="message",
                        source_id=user_message.id,
                        confidence=proposal.confidence,
                        derivation=proposal.derivation,
                    )
                )
            elif proposal.kind == "transition" and proposal.transition:
                words = {w.lower().strip(".,!?'\"") for w in event.content.split() if len(w) > 3}
                if proposal.transition == "complete":
                    candidates: list[Commitment | Thread] = list(
                        db.scalars(
                            select(Commitment)
                            .where(
                                Commitment.user_id == user_id,
                                Commitment.deleted.is_(False),
                            )
                            .order_by(Commitment.created_at)
                        )
                    )
                else:
                    candidates = list(
                        db.scalars(
                            select(Thread)
                            .where(Thread.user_id == user_id, Thread.deleted.is_(False))
                            .order_by(Thread.created_at)
                        )
                    )
                matches = [
                    item for item in candidates if words & {w.lower() for w in item.title.split()}
                ]
                if not matches and "that" in event.content.lower() and candidates:
                    matches = [candidates[-1]]
                if matches:
                    target = matches[-1]
                    state = "active" if proposal.transition == "reactivate" else proposal.transition
                    target.state = "abandoned" if state == "abandon" else state
                    target.version += 1
                    db.add(
                        ProvenanceLink(
                            user_id=user_id,
                            target_id=target.id,
                            source_type="message",
                            source_id=user_message.id,
                            confidence=proposal.confidence,
                            derivation="explicit-state-transition-v1",
                        )
                    )
            reply = (
                "What should I remind you about?"
                if proposal.kind == "clarification"
                else self.model.respond(event.content)
            )
            db.add(
                Message(
                    user_id=user_id,
                    conversation_id=event.conversation_id,
                    role="assistant",
                    actor="assistant",
                    content=reply,
                )
            )
        db.add(
            SkillRun(
                user_id=user_id,
                event_id=recorded.id,
                skill_name="state-extraction"
                if event.kind == "user_message"
                else "scheduled-event",
                outcome="handled",
            )
        )
        db.commit()
        return {"idempotent": False, "handled_by": "AgentRuntime.handle"}
