from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True)
class StateProposal:
    kind: Literal["commitment", "thread", "transition", "clarification", "none"]
    title: str | None = None
    deadline_hint: str | None = None
    effort_minutes: int | None = None
    transition: str | None = None
    confidence: float = 0.0
    derivation: str = "deterministic-explicit-phrase-v1"


class ModelRouter(Protocol):
    def respond(self, text: str) -> str: ...


class DeterministicModel:
    """Explicit development/test adapter; never presented as a live model."""

    def respond(self, text: str) -> str:
        return "I’ll carry that forward." if text.strip() else "What would you like to discuss?"


class StateExtractor:
    def extract(self, text: str) -> StateProposal:
        normalized = " ".join(text.strip().split())
        lower = normalized.lower()
        if lower == "remind me about that":
            return StateProposal("clarification", confidence=1.0)
        transitions = {
            "finished": "complete",
            "abandon": "abandon",
            "reactivate": "reactivate",
            "dormant": "dormant",
        }
        completion_negated = re.search(
            r"\b(?:not|never|haven't|hasn't|hadn't)(?:\s+\w+){0,3}\s+finished\b",
            lower.replace("’", "'"),
        )
        for needle, state in transitions.items():
            if needle in lower and not (state == "complete" and completion_negated):
                return StateProposal(
                    "transition", title=normalized, transition=state, confidence=0.95
                )
        if lower.startswith("i'm considering ") or lower.startswith("i’m considering "):
            return StateProposal("thread", normalized.split(" ", 2)[2], confidence=0.9)
        if lower.startswith("hang onto this idea"):
            title = normalized.split(":", 1)[-1].strip()
            return StateProposal("thread", title, confidence=1.0)
        if lower.startswith("i need to ") or (lower.startswith("send ") and " before " in lower):
            body = normalized[10:] if lower.startswith("i need to ") else normalized
            deadline = None
            match = re.search(r"\bbefore ([A-Za-z]+)", body, re.I)
            if match:
                deadline = match.group(1)
                body = body[: match.start()].rstrip(" ;,")
            effort = None
            effort_match = re.search(r"(?:takes?|about) (\d+) hours?", normalized, re.I)
            if effort_match:
                effort = int(effort_match.group(1)) * 60
            return StateProposal("commitment", body, deadline, effort, confidence=0.95)
        return StateProposal("none")
