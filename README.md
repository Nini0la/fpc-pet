# Continuity — Milestone 4

A narrow personal-AI prototype that carries explicit commitments, threads, shared episodes, and a daily morning/evening loop forward through time. This repository intentionally does **not** reproduce or claim compatibility with proprietary FPC architecture.

## What M4 adds

- A tenant-owned longitudinal vocabulary record and attempt history, backed by a versioned curated lexicon beginning with **inchoate**. Definitions and examples are source data, never model inventions.
- The deterministic `VocabularyLearningSkill` uses the same `AgentRuntime.handle` path as chat and scheduled events. Morning briefings contain one structured learning slot: the weakest due word wins; a new word appears only when no weak word is due.
- Evening reflection remains conversational, then asks a due active-recall question in the same chat. Exact normalized MVP grading supports bounded, audit-linked explicit self-correction of an ambiguous or incorrect latest attempt, optional sentence retention, and leaves ambiguous prose ungraded.
- An inspectable schedule advances correct recalls through new → developing → familiar → mastered, regresses incorrect recalls to developing, enforces the injected due instant for ordinary reviews, exposes the next review/reason, and retires mastered words from automatic deliberate review. `review <word>` is the explicit revisit override.
- `/api/vocabulary` and per-item attempts provide bounded tenant-scoped history; versioned correction and deletion immediately affect selection. Deletion scrubs vocabulary/attempt content and retains only metadata-only audit provenance.
- Today renders the current Word of the Day or due review. Alembic `0006` is reversible and enforces composite tenant ownership for attempts.

M1–M3 continuity behavior remains available:

- Scheduled `morning_briefing` and `evening_reflection` events enter the same `AgentRuntime.handle` path as chat.
- A deterministic, inspectable Power List ranks approximately three open commitments/threads using deadlines, explicit importance/user priority, inactivity, recent promises, and yesterday's explicitly unfinished work. Every selected item includes a reason.
- Morning briefings and evening prompts are proactive assistant messages in the same persistent chat.
- Evening answers are retained verbatim as tenant-owned journal entries. A clause-aware deterministic parser handles only explicit completion, unfinished, priority, commitment/thread, blocker, and outcome language; it resolves `it` only from one immediately preceding known subject and makes no mutation when the reference is ambiguous.
- `/api/today` returns the current briefing, Power List, resurfaced work, reflection state, and at most 50 open commitments and 50 active threads in stable order. `collection_meta` reports each collection's limit, returned and total counts, and `has_more`. Persisted briefing collections are also capped at 50. `/api/history/journals` provides bounded, tenant-scoped journal browse/search.
- `User.timezone`, an injected clock, and standard-library `zoneinfo` determine user-local dates. Scheduled daily events may carry `intended_local_date` for the current or immediately previous user-local day; other, future, and stale dates are rejected. Database uniqueness makes repeated triggers for the intended day idempotent for policy `m2-v1`.
- Explicit commitment dates/times and effort are normalized from bounded phrases using the user's IANA timezone and injected clock. Date-only deadlines retain their source phrase/granularity and use end-of-local-day for urgency; ambiguous numeric dates are retained as ambiguous and prompt for clarification.
- `commitment_check` enters the same runtime path and uses an inspectable `m3-v1` urgency/slack policy over deadline proximity, remaining effort, importance, inactivity, blockers, and stored availability. High-urgency work creates one tenant-owned Reminder and one explanatory message per commitment/relevance-window/policy.
- Reminder/message/Episode/event/skill-run/provenance writes are atomic. PostgreSQL row locks plus database uniqueness prevent duplicate concurrent surfacing; a completion that wins the row-lock race suppresses stale output. `/api/today` includes live urgency and `/api/reminders` provides bounded tenant-scoped inspection.

## Run locally

1. Copy `.env.example` to `.env` and replace every secret. Never place `ACCESS_CODE` in frontend source or a `NEXT_PUBLIC_*` variable.
2. `docker compose up -d db`
3. `cd backend && uv sync --extra dev && set -a && source ../.env && set +a && uv run alembic upgrade head && uv run uvicorn app.main:app --reload`
4. `cd frontend && npm ci && npm run dev`

Alembic uses `DATABASE_URL` when set and supports explicit upgrade/downgrade through M4 (`0006`). If unset, `backend/alembic.ini` retains the local Compose PostgreSQL URL as a development fallback. Migration URLs are never logged.

Production fails closed unless the database URL, access code, a 32+ character session secret, and exact CORS origins are present. Set `APP_ENV=production`; cookies are Secure in production. The deterministic adapter (`MODEL_MODE=deterministic`) is only a development/test response stub and is rejected in production. No live Nebius/Nemotron use is claimed yet.

## Verify

`make check` runs backend tests/lint/types and frontend tests/audit/lint/types/build. The PostgreSQL suite is enabled by setting `POSTGRES_TEST_URL`; CI runs it against PostgreSQL 16.

See `docs/ARCHITECTURE.md`, `docs/SECURITY_PRIVACY.md`, and `docs/IMPLEMENTATION_STATUS.md`.
