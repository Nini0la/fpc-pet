from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .clock import Clock, SystemClock
from .models import Commitment, Episode, Message, ProvenanceLink, Thread


@dataclass(frozen=True)
class RecallIntent:
    topic: str | None = None
    actor: str | None = None
    decision: bool = False
    earliest_only: bool = False
    since: datetime | None = None
    exclude_discussed_only: bool = False
    needs_referent: bool = False


@dataclass(frozen=True)
class HistoryEvidence:
    summary: str
    actor: str
    confidence: float
    source: str
    created_at: datetime


class SharedHistoryRecallSkill:
    """Deterministic recall over explicit, non-deleted history evidence."""

    _decision_words = re.compile(r"\b(decid(?:e|ed)|conclud(?:e|ed)|agreed?|decision|conclusion)\b")
    _referent_stop_words = {
        "about",
        "already",
        "and",
        "did",
        "found",
        "from",
        "have",
        "lets",
        "return",
        "that",
        "the",
        "this",
        "to",
        "told",
        "what",
        "you",
    }

    def __init__(self, clock: Clock | None = None) -> None:
        self.clock = clock or SystemClock()

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"[^a-z0-9' ]", "", " ".join(text.lower().split())).strip()

    def parse(self, text: str) -> RecallIntent | None:
        normalized = self._normalize(text)
        match = re.fullmatch(r"what did we (decide|conclude) about (?:the )?(.+)", normalized)
        if match:
            return RecallIntent(topic=match.group(2), decision=True)

        match = re.fullmatch(r"when did we start talking about (?:the )?(.+)", normalized)
        if match:
            return RecallIntent(topic=match.group(1), earliest_only=True)

        match = re.fullmatch(r"what have you helped me with(?: (this week))?", normalized)
        if match:
            since = None
            if match.group(1):
                now = self.clock.now()
                since = (now - timedelta(days=now.weekday())).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
            return RecallIntent(actor="assistant", since=since)

        match = re.fullmatch(r"what did you already tell me about (.+)", normalized)
        if match:
            referent = match.group(1)
            return RecallIntent(
                topic=None if referent in {"this", "that"} else referent,
                actor="assistant",
                needs_referent=referent in {"this", "that"},
            )

        if re.fullmatch(r"what have we (?:been doing|tried)", normalized):
            return RecallIntent(exclude_discussed_only=normalized.endswith("tried"))
        return None

    def matches(self, text: str) -> bool:
        return self.parse(text) is not None

    def actor_for(self, text: str) -> str | None:
        lower = " ".join(text.lower().split())
        # State-setting utterances are represented by Thread/Commitment records,
        # not duplicated as claims that an episode already happened.
        if lower.startswith(("hang onto this idea", "i need to ")):
            return None
        discussed_markers = (
            "we only discussed ",
            "we discussed ",
            "we talked about ",
            "i'm considering ",
            "i’m considering ",
        )
        if lower.startswith(discussed_markers):
            return "discussed_only"
        if lower.startswith("we "):
            return "joint"
        if lower.startswith("you "):
            return "assistant"
        if lower.startswith("i ") or lower.startswith("i've ") or lower.startswith("i’ve "):
            return "user"
        return "discussed_only"

    @staticmethod
    def _topic_matches(summary: str, topic: str) -> bool:
        summary_words = set(re.findall(r"[a-z0-9]+", summary.lower()))
        topic_words = {
            word
            for word in re.findall(r"[a-z0-9]+", topic.lower())
            if word not in {"a", "an", "the", "about"}
        }
        return bool(topic_words) and topic_words.issubset(summary_words)

    @staticmethod
    def _utc_naive(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def _evidence(self, db: Session, user_id: str) -> list[HistoryEvidence]:
        episodes = list(
            db.scalars(
                select(Episode).where(
                    Episode.user_id == user_id, Episode.deleted.is_(False)
                )
            ).all()
        )
        states: list[Commitment | Thread] = list(
            db.scalars(
                select(Commitment).where(
                    Commitment.user_id == user_id, Commitment.deleted.is_(False)
                )
            ).all()
        )
        states.extend(
            db.scalars(
                select(Thread).where(Thread.user_id == user_id, Thread.deleted.is_(False))
            ).all()
        )
        state_ids = [state.id for state in states]
        sources: dict[str, str] = {}
        if state_ids:
            links = db.scalars(
                select(ProvenanceLink).where(
                    ProvenanceLink.user_id == user_id,
                    ProvenanceLink.target_id.in_(state_ids),
                    ProvenanceLink.source_type == "message",
                )
            ).all()
            sources = {
                link.target_id: f"message:{link.source_id}"
                for link in links
                if link.source_id is not None
            }
        evidence = [
            HistoryEvidence(
                episode.summary,
                episode.actor,
                episode.confidence,
                episode.source,
                episode.created_at,
            )
            for episode in episodes
        ]
        evidence.extend(
            HistoryEvidence(
                f"{type(state).__name__} ({state.state}): {state.title}",
                "user",
                state.confidence,
                sources.get(state.id, f"explicit {type(state).__name__.lower()}"),
                state.created_at,
            )
            for state in states
        )
        return sorted(
            evidence, key=lambda item: (self._utc_naive(item.created_at), item.source)
        )

    @classmethod
    def _referent_words(cls, text: str) -> set[str]:
        return {
            word
            for word in re.findall(r"[a-z0-9]+", text.lower())
            if len(word) > 2 and word not in cls._referent_stop_words
        }

    def _resolve_immediate_referent(
        self,
        db: Session,
        user_id: str,
        conversation_id: str,
        current_message_id: str,
        evidence: list[HistoryEvidence],
    ) -> list[HistoryEvidence]:
        previous = db.scalar(
            select(Message)
            .where(
                Message.user_id == user_id,
                Message.conversation_id == conversation_id,
                Message.role == "user",
                Message.id != current_message_id,
            )
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        if previous is None:
            return []
        context_words = self._referent_words(previous.content)
        matches = [
            item
            for item in evidence
            if len(context_words & self._referent_words(item.summary)) >= 2
        ]
        return matches if len(matches) == 1 else []

    def answer(
        self,
        db: Session,
        user_id: str,
        text: str,
        conversation_id: str | None = None,
        current_message_id: str | None = None,
    ) -> str:
        intent = self.parse(text)
        if intent is None:
            return "I couldn’t identify a supported shared-history recall intent."

        evidence = self._evidence(db, user_id)
        if intent.actor:
            evidence = [item for item in evidence if item.actor == intent.actor]
        if intent.needs_referent:
            evidence = (
                self._resolve_immediate_referent(
                    db, user_id, conversation_id, current_message_id, evidence
                )
                if conversation_id and current_message_id
                else []
            )
            if not evidence:
                return (
                    "I don’t have enough context to resolve that reference. "
                    "Which topic do you mean?"
                )
        if intent.since:
            since = self._utc_naive(intent.since)
            evidence = [
                item for item in evidence if self._utc_naive(item.created_at) >= since
            ]
        if intent.exclude_discussed_only:
            evidence = [item for item in evidence if item.actor != "discussed_only"]
        if intent.topic:
            evidence = [e for e in evidence if self._topic_matches(e.summary, intent.topic)]
        if intent.decision:
            evidence = [e for e in evidence if self._decision_words.search(e.summary.lower())]
        if intent.earliest_only and evidence:
            evidence = evidence[:1]

        if not evidence:
            return (
                "I couldn’t find enough evidence in the explicit, non-deleted history records "
                "that match that request. I won’t infer a shared history without a source."
            )
        lines = [
            "Here’s the explicit history, oldest first. These are recorded claims, "
            "not independently verified facts:"
        ]
        for item in evidence:
            lines.append(
                f"- [{item.actor}; source {item.source}; "
                f"confidence {item.confidence:.2f}] {item.summary}"
            )
        return "\n".join(lines)
