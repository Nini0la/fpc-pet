from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.agent import AgentRuntime, RuntimeEvent
from app.clock import FakeClock
from app.models import Base, DailyBriefing, Message, User, VocabularyAttempt, VocabularyItem


def sessions():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return sessionmaker(engine, expire_on_commit=False)


def owner(db, *, timezone_name="UTC"):
    user = User(username="vocab-owner", timezone=timezone_name)
    db.add(user)
    db.flush()
    return user.id


def test_day_one_morning_introduces_versioned_inchoate_in_existing_briefing():
    factory = sessions()
    clock = FakeClock(datetime(2026, 10, 1, 8, tzinfo=timezone.utc))
    with factory.begin() as db:
        user_id = owner(db)

    with factory() as db:
        AgentRuntime(clock=clock).handle(db, user_id, RuntimeEvent("m1", "morning_briefing"))

    with factory() as db:
        item = db.scalar(select(VocabularyItem))
        briefing = db.scalar(select(DailyBriefing))
        messages = db.scalars(select(Message)).all()
        assert item.normalized_word == "inchoate"
        assert item.display_word == "inchoate"
        assert item.definition == "only partly in existence; imperfectly formed"
        assert item.source == "continuity-curated-lexicon"
        assert item.policy_version == "vocab-v1"
        assert item.mastery_state == "new"
        assert item.next_review_at.replace(tzinfo=timezone.utc) == clock.now() + timedelta(days=1)
        assert briefing.sections["vocabulary"]["mode"] == "new"
        assert briefing.sections["vocabulary"]["word"] == "inchoate"
        assert "Word of the Day: inchoate" in messages[0].content
        assert len(messages) == 1


def test_weak_due_item_is_reviewed_before_introducing_another_word():
    factory = sessions()
    clock = FakeClock(datetime(2026, 10, 1, 8, tzinfo=timezone.utc))
    with factory.begin() as db:
        user_id = owner(db)
    with factory() as db:
        runtime = AgentRuntime(clock=clock)
        runtime.handle(db, user_id, RuntimeEvent("day1", "morning_briefing"))
    clock.set(datetime(2026, 10, 2, 8, tzinfo=timezone.utc))
    with factory() as db:
        AgentRuntime(clock=clock).handle(db, user_id, RuntimeEvent("day2", "morning_briefing"))
    with factory() as db:
        items = db.scalars(select(VocabularyItem)).all()
        latest = db.scalars(select(DailyBriefing).order_by(DailyBriefing.local_date.desc())).first()
        assert len(items) == 1
        assert latest.sections["vocabulary"]["mode"] == "review"
        assert latest.sections["vocabulary"]["reason"] == "weak word due for review"


def test_review_answer_is_graded_and_sentence_retained_with_interpretable_schedule():
    factory = sessions()
    clock = FakeClock(datetime(2026, 10, 1, 8, tzinfo=timezone.utc))
    with factory.begin() as db:
        user_id = owner(db)
    with factory() as db:
        runtime = AgentRuntime(clock=clock)
        runtime.handle(db, user_id, RuntimeEvent("morning", "morning_briefing"))
    clock.set(datetime(2026, 10, 1, 20, tzinfo=timezone.utc))
    with factory() as db:
        runtime = AgentRuntime(clock=clock)
        runtime.handle(db, user_id, RuntimeEvent("review", "vocabulary_review"))
        conversation_id = db.scalar(select(Message.conversation_id))
        runtime.handle(
            db,
            user_id,
            RuntimeEvent(
                "answer",
                "user_message",
                "only partly in existence; imperfectly formed. "
                "Sentence: The plan remained inchoate.",
                conversation_id,
            ),
        )
    with factory() as db:
        item = db.scalar(select(VocabularyItem))
        attempt = db.scalar(select(VocabularyAttempt))
        assert attempt.correct is True
        assert attempt.user_sentence == "The plan remained inchoate."
        assert item.recall_attempts == 1
        assert item.correct_recalls == 1
        assert item.user_sentences == ["The plan remained inchoate."]
        assert item.mastery_state == "developing"
        assert item.next_review_at.replace(tzinfo=timezone.utc) == clock.now() + timedelta(days=2)


def test_ambiguous_answer_is_ungraded_and_requests_clarification():
    factory = sessions()
    clock = FakeClock(datetime(2026, 10, 1, 8, tzinfo=timezone.utc))
    with factory.begin() as db:
        user_id = owner(db)
    with factory() as db:
        runtime = AgentRuntime(clock=clock)
        runtime.handle(db, user_id, RuntimeEvent("morning", "morning_briefing"))
        runtime.handle(db, user_id, RuntimeEvent("review", "vocabulary_review"))
        conversation_id = db.scalar(select(Message.conversation_id))
        runtime.handle(
            db,
            user_id,
            RuntimeEvent(
                "ambiguous", "user_message", "It is sort of beginning-ish", conversation_id
            ),
        )
    with factory() as db:
        attempt = db.scalar(select(VocabularyAttempt))
        assert attempt.correct is None
        assert db.scalars(select(Message).order_by(Message.ordinal)).all()[-1].content.startswith(
            "I’m not certain"
        )


def test_ambiguous_answer_can_be_explicitly_self_corrected():
    factory = sessions()
    clock = FakeClock(datetime(2026, 10, 1, 8, tzinfo=timezone.utc))
    with factory.begin() as db:
        user_id = owner(db)
    with factory() as db:
        runtime = AgentRuntime(clock=clock)
        runtime.handle(db, user_id, RuntimeEvent("morning", "morning_briefing"))
        runtime.handle(db, user_id, RuntimeEvent("review", "vocabulary_review"))
        conversation_id = db.scalar(select(Message.conversation_id))
        runtime.handle(
            db, user_id, RuntimeEvent("unclear", "user_message", "beginning-ish", conversation_id)
        )
        runtime.handle(
            db,
            user_id,
            RuntimeEvent(
                "correction",
                "user_message",
                "self-correction: only partly in existence; imperfectly formed",
                conversation_id,
            ),
        )
    with factory() as db:
        item = db.scalar(select(VocabularyItem))
        attempts = db.scalars(select(VocabularyAttempt)).all()
        assert len(attempts) == 1
        assert attempts[0].correct is True
        assert item.correct_recalls == 1


def test_evening_reflection_finishes_naturally_then_asks_active_recall_in_same_chat():
    factory = sessions()
    clock = FakeClock(datetime(2026, 10, 1, 8, tzinfo=timezone.utc))
    with factory.begin() as db:
        user_id = owner(db)
    runtime = AgentRuntime(clock=clock)
    with factory() as db:
        runtime.handle(db, user_id, RuntimeEvent("morning", "morning_briefing"))
    clock.set(datetime(2026, 10, 1, 20, tzinfo=timezone.utc))
    with factory() as db:
        runtime.handle(db, user_id, RuntimeEvent("evening", "evening_reflection"))
        conversation_id = db.scalar(select(Message.conversation_id))
        runtime.handle(
            db,
            user_id,
            RuntimeEvent("reflection", "user_message", "A calm day overall.", conversation_id),
        )
    with factory() as db:
        messages = db.scalars(select(Message).order_by(Message.ordinal)).all()
        assert messages[-1].content.startswith("Thanks — I’ve carried that into tomorrow.")
        assert "what does “inchoate” mean?" in messages[-1].content
        assert len({message.conversation_id for message in messages}) == 1


def test_mastery_retires_word_and_allows_next_curated_word():
    factory = sessions()
    clock = FakeClock(datetime(2026, 10, 1, 8, tzinfo=timezone.utc))
    with factory.begin() as db:
        user_id = owner(db)
    runtime = AgentRuntime(clock=clock)
    with factory() as db:
        runtime.handle(db, user_id, RuntimeEvent("morning", "morning_briefing"))
        conversation_id = db.scalar(select(Message.conversation_id))
    for index, day in enumerate((1, 3, 10, 17), start=1):
        clock.set(datetime(2026, 10, day, 20, tzinfo=timezone.utc))
        with factory() as db:
            runtime.handle(db, user_id, RuntimeEvent(f"review-{index}", "vocabulary_review"))
            runtime.handle(
                db,
                user_id,
                RuntimeEvent(
                    f"answer-{index}",
                    "user_message",
                    "only partly in existence; imperfectly formed",
                    conversation_id,
                ),
            )
    with factory() as db:
        inchoate = db.scalar(
            select(VocabularyItem).where(VocabularyItem.normalized_word == "inchoate")
        )
        assert inchoate.mastery_state == "mastered"
        assert inchoate.next_review_at is None

    clock.set(datetime(2026, 10, 17, 21, tzinfo=timezone.utc))
    with factory() as db:
        runtime.handle(
            db, user_id, RuntimeEvent("revisit", "user_message", "review inchoate", conversation_id)
        )
        runtime.handle(
            db, user_id, RuntimeEvent("lapse", "user_message", "I don't know", conversation_id)
        )
    with factory() as db:
        inchoate = db.scalar(
            select(VocabularyItem).where(VocabularyItem.normalized_word == "inchoate")
        )
        assert inchoate.mastery_state == "developing"

    clock.set(datetime(2026, 10, 18, 8, tzinfo=timezone.utc))
    with factory() as db:
        runtime.handle(db, user_id, RuntimeEvent("next-word", "morning_briefing"))
    with factory() as db:
        words = set(db.scalars(select(VocabularyItem.normalized_word)))
        assert words == {"inchoate", "lucid"}
