"""Optional intention annotations; current what/why/next-action fields stay authoritative."""

import hashlib
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from .history import SharedHistoryRecallSkill
from .models import Message, ProvenanceLink, Thread, User


class IntentionNote(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: Literal[
        "why",
        "purpose",
        "completion_criteria",
        "timing_reason",
        "consequences",
        "dependency",
        "change_reason",
        "reason",
    ]
    text: str = Field(min_length=1, max_length=1000)
    basis: Literal["user_stated", "derived", "inferred", "confirmed"] = "inferred"
    source_message_id: str | None = None
    source_quote: str | None = Field(default=None, max_length=1000)
    category: (
        Literal[
            "new_priority",
            "obstacle",
            "reestimate",
            "changed_circumstances",
            "loss_of_relevance",
            "dependency_completed",
        ]
        | None
    ) = None


class CommitmentIntentionNote(IntentionNote):
    field: Literal[
        "purpose", "completion_criteria", "timing_reason", "consequences", "dependency",
        "change_reason",
    ]


class ThreadIntentionNote(IntentionNote):
    field: Literal["why"]


class ReminderIntentionNote(IntentionNote):
    field: Literal["reason", "timing_reason", "consequences", "change_reason"]


def fingerprint(value):
    return hashlib.sha256(value.encode()).hexdigest()


def normalize(value):
    return " ".join(value.casefold().split())


def annotate(
    db,
    owner,
    notes,
    source_id,
    now,
    scalars,
    *,
    existing=None,
    parent_id=None,
    trusted=False,
    allowed=None,
    previous_scalars=None,
):
    """Validate evidence, keeping inferred/derived statements separate from user assertions."""
    from .commitments import utc

    result = dict(existing or {})
    fields = allowed or {
        "purpose",
        "completion_criteria",
        "timing_reason",
        "consequences",
        "dependency",
        "change_reason",
    }
    explicit = {note.field: note for note in notes}
    if len(explicit) != len(notes) or set(explicit) - fields:
        raise ValueError("Use one supported intention note per field.")
    for field, value in scalars.items():
        if value is None or field not in fields:
            continue
        if not value and field not in explicit:
            result.pop(field, None)
            continue
        previous = result.get(field, {})
        if field not in explicit and previous.get("value_hash") == fingerprint(value):
            continue
        if field not in explicit:
            message = db.get(Message, source_id) if source_id else None
            stated = bool(
                message
                and message.user_id == owner
                and message.role == "user"
                and value
                and normalize(value) in normalize(message.content)
            )
            explicit[field] = IntentionNote(
                field=field,
                text=value,
                basis="confirmed" if trusted else "user_stated" if stated else "inferred",
                source_quote=value if stated else None,
            )
    for field, note in explicit.items():
        if not normalize(note.text):
            raise ValueError("An intention note needs meaningful text.")
        if field in scalars and scalars[field] is not None and note.text != scalars[field]:
            raise ValueError("The intention note must match the current plan field.")
        message_id = note.source_message_id or source_id
        message = db.scalar(
            select(Message).where(
                Message.id == message_id, Message.user_id == owner, Message.role == "user"
            )
        )
        user = db.get(User, owner)
        if message and user and user.conversation_recall_after:
            if utc(message.created_at) <= utc(user.conversation_recall_after):
                message = None
        data = {
            "basis": note.basis,
            "source_message_id": message.id if message else None,
            "source_at": utc(message.created_at).isoformat() if message else now.isoformat(),
            "updated_at": now.isoformat(),
            "value_hash": fingerprint(note.text),
        }
        if trusted and note.basis != "derived":
            data.update(
                basis="inferred" if note.basis == "inferred" else "confirmed",
                source_type="owner_control",
                source_message_id=None,
            )
        elif note.basis in {"user_stated", "confirmed"}:
            if (
                not message
                or not normalize(note.source_quote or "")
                or not SharedHistoryRecallSkill().allows_episodic_content(message.content)
            ):
                raise ValueError("A stated or confirmed reason needs the owner's actual words.")
            confirming_existing = (
                note.basis == "confirmed"
                and message.id == source_id
                and (
                    (existing or {}).get(field, {}).get("value_hash") == fingerprint(note.text)
                    or (previous_scalars or {}).get(field) == note.text
                )
            )
            if normalize(note.source_quote) not in normalize(message.content) or (
                normalize(note.text) not in normalize(note.source_quote) and not confirming_existing
            ):
                raise ValueError(
                    "Use the owner's verbatim reason, or label the interpretation inferred."
                )
            data["source_quote"] = note.source_quote
            if confirming_existing:
                data["confirmation_of_prior_value"] = True
                data["confirmed_from_basis"] = (
                    (existing or {}).get(field, {}).get("basis", "legacy_unattributed")
                )
        elif note.basis == "derived":
            parent = (
                db.scalar(
                    select(Thread).where(
                        Thread.id == parent_id, Thread.user_id == owner, Thread.deleted.is_(False)
                    )
                )
                if parent_id
                else None
            )
            if (
                field not in {"purpose", "why"}
                or not parent
                or parent.kind != "project"
                or normalize(note.text) != normalize(parent.why)
            ):
                raise ValueError(
                    "Derived purpose must reference this commitment's linked project reason."
                )
            data.update(
                related_thread_id=parent.id,
                related_thread_version=parent.version,
                related_why_hash=fingerprint(parent.why),
            )
        elif message is None:
            raise ValueError("An inferred intention needs an owned source message.")
        if field not in {"why", "purpose", "completion_criteria"}:
            data["text"] = note.text
        if note.category:
            data["category"] = note.category
            data["category_basis"] = "model_interpretation"
        result[field] = data
    return result


def link_evidence(db, record, now):
    for field, evidence in (record.intention_context or {}).items():
        if evidence.get("updated_at") != now.isoformat():
            continue
        basis = evidence["basis"]
        db.add(
            ProvenanceLink(
                user_id=record.user_id,
                target_id=record.id,
                source_type="thread"
                if basis == "derived"
                else evidence.get("source_type", "message"),
                source_id=evidence.get("related_thread_id")
                if basis == "derived"
                else evidence.get("source_message_id"),
                confidence=1.0 if basis in {"user_stated", "confirmed"} else 0.5,
                derivation=f"intention:{field}:{basis}",
                metadata_only=True,
                created_at=now,
            )
        )


def project(record, db=None):
    """A stale annotation cannot certify a later scalar edit or a changed parent."""
    context = {}
    stored = record.intention_context or {}
    for field, data in stored.items():
        value = getattr(record, field, data.get("text", ""))
        item = {
            **{
                k: v
                for k, v in data.items()
                if k not in {"value_hash", "related_why_hash", "source_quote"}
            },
            "text": value,
        }
        if data.get("value_hash") != fingerprint(value):
            item["basis"] = "unknown"
        if data.get("basis") == "derived" and db is not None:
            parent = db.scalar(
                select(Thread).where(
                    Thread.id == data.get("related_thread_id"),
                    Thread.user_id == record.user_id,
                    Thread.deleted.is_(False),
                )
            )
            current_parent = getattr(record, "related_thread_id", None) or getattr(
                record, "parent_thread_id", None
            )
            if (
                not parent
                or parent.id != current_parent
                or fingerprint(parent.why) != data.get("related_why_hash")
            ):
                item["basis"] = "stale_derived"
        context[field] = item
    for field in ("purpose", "why", "completion_criteria"):
        value = getattr(record, field, "")
        if value and field not in context:
            context[field] = {"text": value, "basis": "legacy_unattributed"}
    return context


def stated_reason(record):
    for field in ("purpose", "why", "reason"):
        evidence = project(record).get(field, {})
        if evidence.get("basis") in {"user_stated", "confirmed"}:
            return evidence.get("text", "")
    return ""


def context_notes(record, db=None):
    return {
        field: {
            k: v
            for k, v in note.items()
            if k != "text" or field not in {"why", "purpose", "completion_criteria"}
        }
        for field, note in project(record, db).items()
    }


def reason_phrase(record, timezone_name):
    from datetime import datetime
    from zoneinfo import ZoneInfo

    reason = stated_reason(record)
    if not reason:
        return ""
    for note in project(record).values():
        if note.get("text") == reason and note.get("basis") in {"user_stated", "confirmed"}:
            if not note.get("source_at"):
                return ""
            stamp = datetime.fromisoformat(note["source_at"]).astimezone(ZoneInfo(timezone_name))
            quote = reason[:250] + ("…" if len(reason) > 250 else "")
            return f"Your reason, recorded {stamp.strftime('%d %b %Y')}: “{quote}”."
    return ""


def attention_context(record, now):
    from .prospective import urgency_for

    urgency = urgency_for(record, now)
    return {
        "importance": {"recorded_level": record.importance},
        "time_constraints": {
            k: urgency.factors[k] for k in ("deadline_hours", "effort_minutes", "slack_hours")
        },
        "blockers": record.dependencies,
        "inactivity": {
            "days_since_record_update": urgency.factors["inactivity_days"],
            "meaning": "No recorded update; not evidence of procrastination or failure.",
        },
        "intervention_policy": {
            "enabled": record.followup_enabled,
            "minutes": record.followup_minutes,
            "maximum": record.max_followups,
        },
        "policy_boundary": "Importance and urgency do not authorize additional interventions.",
    }
