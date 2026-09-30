from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Episode


class SharedHistoryRecallSkill:
    """Deterministic recall over explicit, non-deleted episode records."""

    _questions = {
        "what have we been doing",
        "what have you helped me with",
        "what have we tried",
    }

    def matches(self, text: str) -> bool:
        normalized = re.sub(r"[^a-z0-9' ]", "", " ".join(text.lower().split()))
        return normalized in self._questions

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

    def answer(self, db: Session, user_id: str) -> str:
        episodes = db.scalars(
            select(Episode)
            .where(Episode.user_id == user_id, Episode.deleted.is_(False))
            .order_by(Episode.created_at, Episode.id)
        ).all()
        if not episodes:
            return (
                "I don’t have any non-deleted episode records to answer from yet. "
                "I won’t invent a shared history."
            )
        lines = [
            "Here’s the explicit history, oldest first. These are recorded claims, "
            "not independently verified facts:"
        ]
        for episode in episodes:
            lines.append(
                f"- [{episode.actor}; source {episode.source}; "
                f"confidence {episode.confidence:.2f}] {episode.summary}"
            )
        return "\n".join(lines)
