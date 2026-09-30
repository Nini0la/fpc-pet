# Continuity — Milestone 2

A narrow personal-AI prototype that carries explicit commitments, threads, shared episodes, and a daily morning/evening loop forward through time. This repository intentionally does **not** reproduce or claim compatibility with proprietary FPC architecture.

## What M2 adds

- Scheduled `morning_briefing` and `evening_reflection` events enter the same `AgentRuntime.handle` path as chat.
- A deterministic, inspectable Power List ranks approximately three open commitments/threads using deadlines, explicit importance/user priority, inactivity, recent promises, and yesterday's explicitly unfinished work. Every selected item includes a reason.
- Morning briefings and evening prompts are proactive assistant messages in the same persistent chat.
- Evening answers are retained verbatim as tenant-owned journal entries. Only supported explicit completion, unfinished, priority, commitment/thread, blocker, and outcome language updates structured state; unsupported implications are not promoted.
- `/api/today` returns the current briefing, Power List, open commitments, resurfaced work, and reflection state. `/api/history/journals` provides bounded, tenant-scoped journal browse/search.
- `User.timezone`, an injected clock, and standard-library `zoneinfo` determine user-local dates. Database uniqueness makes repeated same-day triggers idempotent for policy `m2-v1`.

## Run locally

1. Copy `.env.example` to `.env` and replace every secret. Never place `ACCESS_CODE` in frontend source or a `NEXT_PUBLIC_*` variable.
2. `docker compose up -d db`
3. `cd backend && uv sync --extra dev && set -a && source ../.env && set +a && uv run alembic upgrade head && uv run uvicorn app.main:app --reload`
4. `cd frontend && npm ci && npm run dev`

Alembic uses `DATABASE_URL` when set and supports explicit upgrade/downgrade through M2. If unset, `backend/alembic.ini` retains the local Compose PostgreSQL URL as a development fallback. Migration URLs are never logged.

Production fails closed unless the database URL, access code, a 32+ character session secret, and exact CORS origins are present. Set `APP_ENV=production`; cookies are Secure in production. The deterministic adapter (`MODEL_MODE=deterministic`) is only a development/test response stub and is rejected in production. No live Nebius/Nemotron use is claimed yet.

## Verify

`make check` runs backend tests/lint/types and frontend tests/audit/lint/types/build. The PostgreSQL suite is enabled by setting `POSTGRES_TEST_URL`; CI runs it against PostgreSQL 16.

See `docs/ARCHITECTURE.md`, `docs/SECURITY_PRIVACY.md`, and `docs/IMPLEMENTATION_STATUS.md`.
