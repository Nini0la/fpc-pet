from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .clock import Clock, SystemClock
from .daily import EveningReflectionSkill, MorningBriefingSkill
from .history import SharedHistoryRecallSkill
from .models import (
    AgentEvent,
    Commitment,
    ConversationSession,
    Episode,
    ProvenanceLink,
    SkillRun,
    Thread,
)
from .persistence import MutationResult, append_message, atomic_update
from .runtime import DeterministicModel, StateExtractor, StateProposal


@dataclass(frozen=True)
class RuntimeEvent:
    external_id: str
    kind: str
    content: str | None = None
    conversation_id: str | None = None
    intended_local_date: date | None = None


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
    def _conversation_target(event: RuntimeEvent) -> str | None:
        return event.conversation_id if event.kind == "user_message" else None

    @staticmethod
    def _canonical_request(user_id: str, event: RuntimeEvent, *, include_target: bool) -> bytes:
        relevant = {
            "content": event.content,
            "intended_local_date": (
                event.intended_local_date.isoformat() if event.intended_local_date else None
            ),
            "kind": event.kind,
            "user_id": user_id,
        }
        if include_target:
            relevant["conversation_target"] = AgentRuntime._conversation_target(event)
        return json.dumps(relevant, sort_keys=True, separators=(",", ":")).encode()

    @staticmethod
    def _fingerprint(user_id: str, event: RuntimeEvent) -> str:
        digest = hashlib.sha256(
            AgentRuntime._canonical_request(user_id, event, include_target=True)
        ).digest()
        return "v2:" + base64.urlsafe_b64encode(digest).decode().rstrip("=")

    @staticmethod
    def _legacy_fingerprints(user_id: str, event: RuntimeEvent) -> tuple[str, ...]:
        later_digest = hashlib.sha256(
            AgentRuntime._canonical_request(user_id, event, include_target=False)
        ).hexdigest()
        if event.intended_local_date is not None:
            return (later_digest,)
        original_request = {
            "content": event.content,
            "kind": event.kind,
            "user_id": user_id,
        }
        original_canonical = json.dumps(
            original_request, sort_keys=True, separators=(",", ":")
        ).encode()
        return (later_digest, hashlib.sha256(original_canonical).hexdigest())

    @staticmethod
    def _idempotent_result(
        db: Session,
        prior: AgentEvent,
        user_id: str,
        event: RuntimeEvent,
        fingerprint: str,
    ) -> dict[str, Any]:
        if hmac.compare_digest(prior.request_fingerprint, fingerprint):
            return {"idempotent": True, "handled_by": "AgentRuntime.handle"}
        legacy_fingerprint = prior.request_fingerprint
        is_unversioned_sha256 = len(legacy_fingerprint) == 64 and all(
            character in "0123456789abcdef" for character in legacy_fingerprint
        )
        legacy_matches = (
            is_unversioned_sha256
            and prior.kind == event.kind
            and any(
                hmac.compare_digest(legacy_fingerprint, candidate)
                for candidate in AgentRuntime._legacy_fingerprints(user_id, event)
            )
        )
        if event.kind == "user_message":
            legacy_matches = legacy_matches and event.conversation_id is not None and db.scalar(
                select(ConversationSession.id).where(
                    ConversationSession.id == event.conversation_id,
                    ConversationSession.user_id == user_id,
                )
            ) is not None
        if not legacy_matches:
            raise IdempotencyConflict("Idempotency key already used for different input")
        prior.request_fingerprint = fingerprint
        db.commit()
        return {"idempotent": True, "handled_by": "AgentRuntime.handle"}

    def handle(self, db: Session, user_id: str, event: RuntimeEvent) -> dict[str, Any]:
        fingerprint = self._fingerprint(user_id, event)
        prior = db.scalar(
            select(AgentEvent).where(
                AgentEvent.user_id == user_id, AgentEvent.external_id == event.external_id
            )
        )
        if prior:
            return self._idempotent_result(db, prior, user_id, event, fingerprint)
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
            return self._idempotent_result(db, prior, user_id, event, fingerprint)
        logical_idempotent = False
        reflection_handled = False
        if event.kind == "user_message" and event.content and event.conversation_id:
            user_message = append_message(
                db,
                user_id=user_id,
                conversation_id=event.conversation_id,
                role="user",
                actor="user",
                content=event.content,
                created_at=self.clock.now(),
            )
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
            append_message(
                db,
                user_id=user_id,
                conversation_id=event.conversation_id,
                role="assistant",
                actor="assistant",
                content=reply,
                created_at=self.clock.now(),
            )
        elif event.kind == "morning_briefing":
            logical_idempotent = not self.morning.run(
                db,
                user_id,
                recorded.id,
                self.clock.now(),
                intended_local_date=event.intended_local_date,
            )
        elif event.kind == "evening_reflection":
            logical_idempotent = not self.evening.start(
                db,
                user_id,
                recorded.id,
                self.clock.now(),
                intended_local_date=event.intended_local_date,
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
