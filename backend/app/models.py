from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def uid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Owned:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Session(Base):
    __tablename__ = "auth_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    csrf_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ConversationSession(Owned, Base):
    __tablename__ = "conversation_sessions"
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_conversation_sessions_user_id"),
    )


class Message(Owned, Base):
    __tablename__ = "messages"
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversation_sessions.id"))
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    actor: Mapped[str] = mapped_column(String(20))
    ordinal: Mapped[int] = mapped_column(Integer, default=0)
    __table_args__ = (
        CheckConstraint("role in ('user','assistant','system')"),
        UniqueConstraint("conversation_id", "ordinal", name="uq_messages_conversation_ordinal"),
    )


class Thread(Owned, Base):
    __tablename__ = "threads"
    title: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(20), default="active")
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    derivation: Mapped[str] = mapped_column(String(100))
    version: Mapped[int] = mapped_column(Integer, default=1)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (CheckConstraint("state in ('active','dormant','abandoned')"),)


class Commitment(Owned, Base):
    __tablename__ = "commitments"
    title: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(20), default="open")
    deadline_hint: Mapped[str | None] = mapped_column(Text, nullable=True)
    effort_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_granularity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    due_source_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_effort_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    importance: Mapped[int] = mapped_column(Integer, default=0)
    next_relevant_moment: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_surfaced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ambiguity: Mapped[str] = mapped_column(String(50), default="none")
    dependencies: Mapped[list] = mapped_column(JSON, default=list)
    available_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    related_thread_id: Mapped[str | None] = mapped_column(
        ForeignKey("threads.id"), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confidence: Mapped[float] = mapped_column(Float)
    derivation: Mapped[str] = mapped_column(String(100))
    version: Mapped[int] = mapped_column(Integer, default=1)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (
        CheckConstraint(
            "state in ('open','in_progress','waiting','complete','completed','cancelled',"
            "'abandoned','dormant')"
        ),
        CheckConstraint("importance between 0 and 3"),
        CheckConstraint("estimated_effort_minutes is null or estimated_effort_minutes >= 0"),
    )


class Reminder(Owned, Base):
    __tablename__ = "reminders"
    commitment_id: Mapped[str] = mapped_column(
        ForeignKey("commitments.id", ondelete="CASCADE"), index=True
    )
    thread_id: Mapped[str | None] = mapped_column(ForeignKey("threads.id"), nullable=True)
    policy_version: Mapped[str] = mapped_column(String(30))
    relevance_window: Mapped[str] = mapped_column(String(80))
    reason_code: Mapped[str] = mapped_column(String(50))
    reason_metadata: Mapped[dict] = mapped_column(JSON)
    state: Mapped[str] = mapped_column(String(20), default="pending")
    surfaced_message_id: Mapped[str | None] = mapped_column(
        ForeignKey("messages.id"), nullable=True
    )
    source_event_id: Mapped[str | None] = mapped_column(
        ForeignKey("agent_events.id"), nullable=True
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "commitment_id",
            "relevance_window",
            "policy_version",
            name="uq_reminder_commitment_window_policy",
        ),
        CheckConstraint("state in ('pending','surfaced','suppressed','failed')"),
        CheckConstraint("attempt_count between 0 and 3"),
    )

    def __init__(self, **kwargs):
        kwargs.setdefault("attempt_count", 0)
        super().__init__(**kwargs)


class Episode(Owned, Base):
    __tablename__ = "episodes"
    summary: Mapped[str] = mapped_column(Text)
    actor: Mapped[str] = mapped_column(String(30))
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    derivation: Mapped[str] = mapped_column(String(100), default="user-authored")
    source: Mapped[str] = mapped_column(String(200), default="explicit episode")
    version: Mapped[int] = mapped_column(Integer, default=1)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (CheckConstraint("actor in ('user','assistant','joint','discussed_only')"),)


class EpisodeThread(Base):
    __tablename__ = "episode_threads"
    episode_id: Mapped[str] = mapped_column(
        ForeignKey("episodes.id", ondelete="CASCADE"), primary_key=True
    )
    thread_id: Mapped[str] = mapped_column(
        ForeignKey("threads.id", ondelete="CASCADE"), primary_key=True
    )


class AgentEvent(Owned, Base):
    __tablename__ = "agent_events"
    external_id: Mapped[str] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(50))
    request_fingerprint: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), default="handled")
    __table_args__ = (UniqueConstraint("user_id", "external_id"),)


class ProvenanceLink(Owned, Base):
    __tablename__ = "provenance_links"
    target_id: Mapped[str] = mapped_column(String(36), index=True)
    source_type: Mapped[str] = mapped_column(String(30))
    source_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    confidence: Mapped[float] = mapped_column(Float)
    derivation: Mapped[str] = mapped_column(String(100))
    metadata_only: Mapped[bool] = mapped_column(Boolean, default=False)


class SkillRun(Owned, Base):
    __tablename__ = "skill_runs"
    event_id: Mapped[str] = mapped_column(ForeignKey("agent_events.id"))
    skill_name: Mapped[str] = mapped_column(String(100))
    outcome: Mapped[str] = mapped_column(String(30))


class DailyBriefing(Owned, Base):
    __tablename__ = "daily_briefings"
    local_date: Mapped[date] = mapped_column(Date)
    policy_version: Mapped[str] = mapped_column(String(30))
    content: Mapped[str] = mapped_column(Text)
    sections: Mapped[dict] = mapped_column(JSON)
    power_list: Mapped[list] = mapped_column(JSON)
    message_id: Mapped[str | None] = mapped_column(ForeignKey("messages.id"), nullable=True)
    source_event_id: Mapped[str] = mapped_column(ForeignKey("agent_events.id"))
    __table_args__ = (
        UniqueConstraint(
            "user_id", "local_date", "policy_version", name="uq_daily_briefing_policy"
        ),
    )


class JournalEntry(Owned, Base):
    __tablename__ = "journal_entries"
    local_date: Mapped[date] = mapped_column(Date)
    original_content: Mapped[str] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    structured_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    source_message_id: Mapped[str] = mapped_column(ForeignKey("messages.id"))
    source_event_id: Mapped[str] = mapped_column(ForeignKey("agent_events.id"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    __table_args__ = (
        UniqueConstraint("user_id", "local_date", name="uq_journal_entries_user_date"),
    )


class ReflectionPrompt(Owned, Base):
    __tablename__ = "reflection_prompts"
    local_date: Mapped[date] = mapped_column(Date)
    policy_version: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20), default="awaiting")
    message_id: Mapped[str | None] = mapped_column(ForeignKey("messages.id"), nullable=True)
    source_event_id: Mapped[str] = mapped_column(ForeignKey("agent_events.id"))
    journal_entry_id: Mapped[str | None] = mapped_column(
        ForeignKey("journal_entries.id"), nullable=True
    )
    __table_args__ = (
        UniqueConstraint(
            "user_id", "local_date", "policy_version", name="uq_reflection_prompt_policy"
        ),
        CheckConstraint("status in ('awaiting','completed')"),
    )
