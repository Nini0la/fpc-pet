import json
from datetime import timedelta

import pytest
from sqlalchemy import select
from test_postgres_quality import csrf
from test_postgres_quality import pg_client as pg_client
from test_postgres_quality import postgres_url as postgres_url
from test_semantic_conversation import NOW, act
from test_semantic_conversation import scene as scene

from app.context import build_context
from app.intentions import stated_reason
from app.models import Commitment, DailyBriefing, User
from app.persistence import append_message, get_or_create_conversation


@pytest.mark.parametrize("quote", ["Yes, that's why.", "   "])
def test_short_confirmation_requires_actual_words_without_repeating_the_inference(
    pg_client, scene, quote
):
    main, gateway = scene
    act(
        pg_client,
        gateway,
        "infer",
        "Save the essay, no check-ins.",
        "create_commitment",
        {"title": "Essay", "purpose": "Make an impression", "followup_enabled": False},
    )
    with main.SessionLocal() as db:
        row = db.scalar(select(Commitment))
        identifier, version = row.id, row.version
        assert row.intention_context["purpose"]["basis"] == "inferred"
    act(
        pg_client,
        gateway,
        "confirm",
        "Yes, that's why.",
        "update_commitment",
        {
            "id": identifier,
            "version": version,
            "intentions": [
                {
                    "field": "purpose",
                    "text": "Make an impression",
                    "basis": "confirmed",
                    "source_quote": quote,
                }
            ],
        },
    )
    with main.SessionLocal() as db:
        row = db.get(Commitment, identifier)
        if not quote.strip():
            assert row.intention_context["purpose"]["basis"] == "inferred"
            assert not stated_reason(row)
            return
        assert stated_reason(row) == "Make an impression"
        assert row.intention_context["purpose"]["confirmed_from_basis"] == "inferred"
        assert row.intention_context["purpose"]["source_quote"] == "Yes, that's why."


def test_fabricated_explicit_reason_is_rejected(pg_client, scene):
    main, gateway = scene
    answer = act(
        pg_client,
        gateway,
        "fake",
        "Save an essay commitment.",
        "create_commitment",
        {
            "title": "Essay",
            "purpose": "Become famous",
            "intentions": [
                {
                    "field": "purpose",
                    "text": "Become famous",
                    "basis": "user_stated",
                    "source_quote": "Become famous",
                }
            ],
        },
    )
    assert "verbatim" in answer["content"]
    with main.SessionLocal() as db:
        assert not db.scalar(select(Commitment))


def test_foreign_intention_source_is_rejected_and_never_recalled(pg_client, scene):
    main, gateway = scene
    with main.SessionLocal.begin() as db:
        other = User(username="other")
        db.add(other)
        db.flush()
        session = get_or_create_conversation(db, other.id)
        message = append_message(
            db,
            user_id=other.id,
            conversation_id=session.id,
            role="user",
            actor="user",
            content="Private cosmos fellowship motive",
            created_at=NOW,
        )
        source = message.id
    act(
        pg_client,
        gateway,
        "foreign",
        "Save an essay.",
        "create_commitment",
        {
            "title": "Essay",
            "intentions": [
                {
                    "field": "purpose",
                    "text": "Private cosmos fellowship motive",
                    "basis": "user_stated",
                    "source_quote": "Private cosmos fellowship motive",
                    "source_message_id": source,
                }
            ],
        },
    )
    with main.SessionLocal() as db:
        owner = db.scalar(select(User).where(User.username == "owner"))
        assert not db.scalar(select(Commitment))
        data = build_context(db, owner.id, "cosmos fellowship motive", now=NOW).payload
        assert "Private cosmos fellowship motive" not in json.dumps(data)


def test_briefing_is_bounded_natural_and_uses_only_attributed_motivation(pg_client, scene):
    main, gateway = scene
    act(
        pg_client,
        gateway,
        "explicit",
        "Save Essay because I want thoughtful feedback. No check-ins.",
        "create_commitment",
        {
            "title": "Essay",
            "purpose": "I want thoughtful feedback",
            "next_action": "Draft the introduction",
            "followup_enabled": False,
        },
    )
    act(
        pg_client,
        gateway,
        "hypothesis",
        "Save a second task, no check-ins.",
        "create_commitment",
        {"title": "Second task", "purpose": "Win prestige", "followup_enabled": False},
    )
    calls = len(gateway.calls)
    for _ in range(2):
        assert pg_client.post(
            "/api/events/scheduled",
            headers=csrf(pg_client),
            json={"event_id": "morning", "kind": "morning_briefing"},
        ).is_success
    assert len(gateway.calls) == calls
    with main.SessionLocal() as db:
        briefing = db.scalar(select(DailyBriefing))
        assert "I want thoughtful feedback" in briefing.content
        assert "Draft the introduction" in briefing.content
        assert "Win prestige" not in briefing.content
        assert briefing.content.count("Essay") == 1
        assert "/100" not in briefing.content and "inactive" not in briefing.content
        assert briefing.power_list[0]["score"] is not None  # Diagnostics retained, not narrated.
        assert len(list(db.scalars(select(DailyBriefing)))) == 1


def test_forgotten_source_cannot_be_reused_as_intention_evidence(pg_client, scene):
    main, gateway = scene
    with main.SessionLocal.begin() as db:
        owner = db.scalar(select(User))
        session = get_or_create_conversation(db, owner.id)
        message = append_message(
            db,
            user_id=owner.id,
            conversation_id=session.id,
            role="user",
            actor="user",
            content="An old private reason",
            created_at=NOW - timedelta(days=1),
        )
        source = message.id
        owner.conversation_recall_after = NOW
    main.runtime.clock.set(NOW + timedelta(minutes=1))
    act(
        pg_client,
        gateway,
        "old",
        "Save an essay",
        "create_commitment",
        {
            "title": "Essay",
            "intentions": [
                {
                    "field": "purpose",
                    "text": "An old private reason",
                    "basis": "user_stated",
                    "source_quote": "An old private reason",
                    "source_message_id": source,
                }
            ],
        },
    )
    with main.SessionLocal() as db:
        assert not db.scalar(select(Commitment))


def test_motivation_retrieval_keeps_goal_and_evidence_within_record_budget(pg_client, scene):
    main, gateway = scene
    fields = {
        "purpose": "Qualify for the fellowship",
        "completion_criteria": "Submit the essay and references",
        "timing_reason": "The application closes Friday",
        "consequences": "A late application will not be reviewed",
        "dependency": "Ask my referee for a letter",
        "change_reason": "The panel extended the deadline",
    }
    act(
        pg_client, gateway, "rich-goal", "; ".join(fields.values()), "create_commitment",
        {
            "title": "Application", "purpose": fields["purpose"],
            "completion_criteria": fields["completion_criteria"],
            "next_action": "Outline the essay", "followup_enabled": False,
            "intentions": [
                {"field": field, "text": value, "basis": "user_stated", "source_quote": value}
                for field, value in fields.items()
            ],
        },
    )
    with main.SessionLocal() as db:
        owner = db.scalar(select(User))
        bundle = build_context(db, owner.id, "fellowship", now=NOW)
        assert db.scalar(select(Commitment)) is not None
        record = next((r for r in bundle.payload["records"] if r["type"] == "commitment"), None)
        assert record is not None, bundle.manifest
        assert record["title"] == "Application"
        assert record["purpose"] == fields["purpose"]
        assert record["next_action"] == "Outline the essay"
        assert record["intention_context"]["purpose"]["basis"] == "user_stated"
        assert record["sources"]
        assert len(json.dumps(record)) <= 1500
        assert len(json.dumps(bundle.payload)) <= 12000
