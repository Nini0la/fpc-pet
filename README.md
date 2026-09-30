# Continuity — Milestone 1

A narrow personal-AI prototype that carries explicit commitments, threads, and shared episodes forward through time. This repository intentionally does **not** reproduce or claim compatibility with proprietary FPC architecture.

## Run locally

1. Copy `.env.example` to `.env` and replace every secret. Never place `ACCESS_CODE` in frontend source or a `NEXT_PUBLIC_*` variable.
2. `docker compose up -d db`
3. `cd backend && uv sync --extra dev && set -a && source ../.env && set +a && uv run alembic upgrade head && uv run uvicorn app.main:app --reload`
4. `cd frontend && npm ci && npm run dev`

Alembic uses `DATABASE_URL` when it is set (converting supported async URL forms to synchronous migration drivers). If it is unset, `backend/alembic.ini` retains the local Compose PostgreSQL URL as a development fallback. Migration URLs are never logged by the Alembic configuration.

Production fails closed unless the database URL, access code, a 32+ character session secret, and exact CORS origins are present. Set `APP_ENV=production`; cookies are Secure in production. The deterministic adapter (`MODEL_MODE=deterministic`) is only a development/test response stub and is rejected in production. It is not an LLM and no live Nebius/Nemotron use is claimed. `ModelRouter` is the future provider boundary; M1 intentionally ships no production provider adapter, so run this milestone in development/test mode until one is added.

## Verify

`make check` runs backend tests/lint/types and frontend tests/lint/types/build.

See `docs/ARCHITECTURE.md`, `docs/SECURITY_PRIVACY.md`, and `docs/IMPLEMENTATION_STATUS.md`.
