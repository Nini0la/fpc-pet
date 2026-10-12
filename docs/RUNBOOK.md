# Milestone 5 runbook

## Start

1. Copy `.env.example` to `.env`; set `APP_ENV`, `DATABASE_URL`, `ACCESS_CODE`, `SESSION_SECRET` (32+ characters), and exact `ALLOWED_ORIGINS`. Never use a `NEXT_PUBLIC_*` variable for a secret.
2. Start PostgreSQL: `docker compose up -d db`.
3. Backend: `cd backend && uv sync --extra dev && set -a && source ../.env && set +a && uv run alembic upgrade head && uv run uvicorn app.main:app --reload`.
4. Frontend: `cd frontend && npm ci && NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev`.

`NEXT_PUBLIC_API_URL` is an origin only; it must contain no credentials or sensitive query values. Production must use HTTPS and an exact frontend origin in `ALLOWED_ORIGINS`.

## Demo flow

1. Open the frontend, read the selective-memory and retention explanation, and sign in with the access code.
2. On first run set an IANA timezone plus morning/evening times.
3. In **Chat**, send an explicit commitment and an exploratory idea. Reload to verify chronology persists.
4. Open **Today** to inspect briefing reasons, urgency, vocabulary, resurfacing, and reflection state. Trigger only the offered morning/evening action; repeated requests are server-idempotent.
5. Open **Threads**, filter by state, inspect source metadata, edit fields, and save. A stale version displays a conflict instead of overwriting newer state.
6. Open **History**, search the bounded timeline, inspect actor/source, and correct or
   delete an editable memory through confirmation. Journal-memory deletion does not
   delete its separately retained raw chat source.
7. At 320px/390px widths, verify the primary nav is fixed at the bottom; at desktop widths it is a side rail. Keyboard through the skip link, navigation, forms, dialogs, and composer.

## Verification

- Full gate: `make check`.
- Backend with live PostgreSQL: set `POSTGRES_TEST_URL`, then `cd backend && uv run pytest -q`. Zero skips are expected when PostgreSQL is reachable.
- Migration smoke test: `cd backend && uv run alembic upgrade head`, then the migration test suite.
- Frontend: `cd frontend && npm test && npm run audit:ci && npm run lint && npm run typecheck && npm run build`.
- `npm run audit:ci` checks production and development dependencies. It fails on every
  advisory except the exact currently unpatched, development-only `braces@3.0.3`
  advisory chain documented in `docs/SECURITY_PRIVACY.md`; do not force npm's suggested
  Next.js ESLint downgrade.

## Operations and recovery

- HTTP 401: sign in again; never persist or reconstruct the session token client-side.
- HTTP 409: refetch the record and reapply the user’s intended edit; do not blind-retry stale CAS writes.
- HTTP 422: correct bounded text, time, timezone, state, or pagination input.
- Network/5xx: use the visible retry control. A pending chat send keeps the same event ID.
  If POST succeeded but history refresh failed, retry reconciles history first; otherwise
  replay of the same ID is server-idempotent.
- Bounded collection responses expose `X-Has-More` and an opaque `X-Next-Cursor`.
  Chat's `mode=latest` response also returns `items`, `has_more`, `older_cursor`, `limit`,
  and `returned_count`; continue older history with the returned cursor. Never construct or
  edit cursors client-side.
- The PostgreSQL migration suite destroys and recreates the configured test database's
  `public` schema; only point `POSTGRES_TEST_URL` at a disposable database.
- Before deleting data, explain that visible content is scrubbed/tombstoned while metadata-only audit rows and backups may remain under operator retention.
