from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .clock import Clock, SystemClock
from .daily import EveningReflectionSkill, MorningBriefingSkill
from .history import SharedHistoryRecallSkill
from .models import AgentEvent, Commitment, Episode, Message, ProvenanceLink, SkillRun, Thread
from .persistence import MutationResult, atomic_update
from .runtime import DeterministicModel, StateExtractor, StateProposal


@dataclass(frozen=True)
class RuntimeEvent:
    external_id: str
    kind: str
    content: str | None = None
    conversation_id: str | None = None


class IdempotencyConflict(Exception):
    pass


class ConcurrentMutation(Exception):
    pass


class AgentRuntime:
    """The single entry point for reactive and scheduled events."""

    def __init__(
        self, model: DeterministicModel | None = None, clock: Clock | None = None
    ) -> None:
        self.extractor = StateExtractor()
        self.model = model or DeterministicModel()
        self.clock = clock or SystemClock()
        self.history = SharedHistoryRecallSkill(self.clock)
        self.morning = MorningBriefingSkill()
        self.evening = EveningReflectionSkill()

    @staticmethod
    def _fingerprint(user_id: str, event: RuntimeEvent) -> str:
        relevant = {
            "content": event.content,
            "kind": event.kind,
            "user_id": user_id,
        }
        canonical = json.dumps(relevant, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()

    @staticmethod
    def _idempotent_result(prior: AgentEvent, fingerprint: str) -> dict[str, Any]:
        if not hmac.compare_digest(prior.request_fingerprint, fingerprint):
            raise IdempotencyConflict("Idempotency key already used for different input")
        return {"idempotent": True, "handled_by": "AgentRuntime.handle"}

    @staticmethod
    def _next_message_ordinal(db: Session, conversation_id: str) -> int:
        current = db.scalar(
            select(func.max(Message.ordinal)).where(Message.conversation_id == conversation_id)
        )
        return (current or 0) + 1

    def handle(self, db: Session, user_id: str, event: RuntimeEvent) -> dict[str, Any]:
        fingerprint = self._fingerprint(user_id, event)
        prior = db.scalar(
            select(AgentEvent).where(
                AgentEvent.user_id == user_id, AgentEvent.external_id == event.external_id
            )
        )
        if prior:
            return self._idempotent_result(prior, fingerprint)
        recorded = AgentEvent(
            user_id=user_id,
            external_id=event.external_id,
            kind=event.kind,
            request_fingerprint=fingerprint,
            created_at=self.clock.now(),
        )
        try:
            with db.begin_nested():
                db.add(recorded)
                db.flush()
        except IntegrityError:
            db.expire_all()
            prior = db.scalar(
                select(AgentEvent).where(
                    AgentEvent.user_id == user_id,
                    AgentEvent.external_id == event.external_id,
                )
            )
            if prior is None:
                raise
            return self._idempotent_result(prior, fingerprint)
        logical_idempotent = False
        reflection_handled = False
        if event.kind == "user_message" and event.content and event.conversation_id:
            user_message = Message(
                user_id=user_id,
                conversation_id=event.conversation_id,
                role="user",
                actor="user",
                content=event.content,
                ordinal=self._next_message_ordinal(db, event.conversation_id),
                created_at=self.clock.now(),
            )
            db.add(user_message)
            db.flush()
            reflection_handled = self.evening.capture_if_pending(
                db,
                user_id,
                recorded.id,
                user_message.id,
                event.content,
                self.clock.now(),
                self.history.allows_episodic_content(event.content),
            )
            recalling_history = self.history.matches(event.content)
            episode_actor = self.history.actor_for(event.content)
            if not recalling_history and episode_actor is not None:
                episode = Episode(
                    user_id=user_id,
                    summary=" ".join(event.content.strip().split()),
                    actor=episode_actor,
                    confidence=0.9,
                    derivation="explicit-chat-episode-v1",
                    source=f"message:{user_message.id}",
                    created_at=self.clock.now(),
                )
                db.add(episode)
                db.flush()
                db.add(
                    ProvenanceLink(
                        user_id=user_id,
                        target_id=episode.id,
                        source_type="message",
                        source_id=user_message.id,
                        confidence=episode.confidence,
                        derivation=episode.derivation,
                    )
                )
            proposal = (
                StateProposal("none")
                if reflection_handled
                else self.extractor.extract(event.content)
            )
            target: Commitment | Thread | None = None
            if proposal.kind == "commitment":
                target = Commitment(
                    user_id=user_id,
                    title=proposal.title or "",
                    deadline_hint=proposal.deadline_hint,
                    effort_minutes=proposal.effort_minutes,
                    confidence=proposal.confidence,
                    derivation=proposal.derivation,
                    created_at=self.clock.now(),
                )
            elif proposal.kind == "thread":
                target = Thread(
                    user_id=user_id,
                    title=proposal.title or "",
                    confidence=proposal.confidence,
                    derivation=proposal.derivation,
                    created_at=self.clock.now(),
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
                    state = "abandoned" if state == "abandon" else state
                    outcome = atomic_update(
                        db,
                        type(target),
                        target.id,
                        user_id,
                        target.version,
                        {"state": state},
                    )
                    if outcome is not MutationResult.UPDATED:
                        raise ConcurrentMutation(outcome.value)
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
            if reflection_handled:
                reply = "Thanks — I’ve carried that into tomorrow."
            elif recalling_history:
                reply = self.history.answer(
                    db,
                    user_id,
                    event.content,
                    conversation_id=event.conversation_id,
                    current_message_id=user_message.id,
                )
            elif proposal.kind == "clarification":
                reply = "What should I remind you about?"
            else:
                reply = self.model.respond(event.content)
            db.add(
                Message(
                    user_id=user_id,
                    conversation_id=event.conversation_id,
                    role="assistant",
                    actor="assistant",
                    content=reply,
                    ordinal=self._next_message_ordinal(db, event.conversation_id),
                    created_at=self.clock.now(),
                )
            )
        elif event.kind == "morning_briefing":
            logical_idempotent = not self.morning.run(
                db, user_id, recorded.id, self.clock.now()
            )
        elif event.kind == "evening_reflection":
            logical_idempotent = not self.evening.start(
                db, user_id, recorded.id, self.clock.now()
            )
        db.add(
            SkillRun(
                user_id=user_id,
                event_id=recorded.id,
                skill_name=(
                    self.evening.name
                    if event.kind == "evening_reflection" or reflection_handled
                    else self.morning.name
                    if event.kind == "morning_briefing"
                    else "shared-history-recall"
                    if event.kind == "user_message"
                    and event.content
                    and self.history.matches(event.content)
                    else "state-extraction"
                    if event.kind == "user_message"
                    else "scheduled-event"
                ),
                outcome="duplicate" if logical_idempotent else "handled",
                created_at=self.clock.now(),
            )
        )
        db.commit()
        return {"idempotent": logical_idempotent, "handled_by": "AgentRuntime.handle"}
