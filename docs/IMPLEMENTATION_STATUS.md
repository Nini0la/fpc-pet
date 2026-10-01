# Implementation status — Milestone 5

## Delivered

- Warm, mobile-first Next.js shell with Chat, Today, Threads, and History as the only product navigation. It includes semantic landmarks/headings/forms, a skip link, focus rings, 44px controls, reduced-motion support, long-content wrapping, and a desktop side rail that becomes a mobile bottom bar.
- Access-code login and first-run onboarding explain selective memory, inspect/correct/delete controls, session privacy, and the retention caveat. Users configure a validated IANA timezone and morning/evening times through tenant-scoped CAS preferences.
- Chat preserves server chronology across login/reload, renders timestamps/proactive labels, safely reconciles optimistic messages from authoritative history, and exposes 401/network/server errors with retry. It does not simulate streaming.
- Today presents only API-backed briefing, reason-bearing Power List, bounded urgent commitments, vocabulary state, resurfaced items, and reflection state. Morning/evening controls use the existing authorized idempotent event API.
- Threads filters active/exploring/waiting/dormant/completed/abandoned state and edits trimmed description, state, importance, deadline, next action, and watch fields using versioned CAS. Stale writes surface as conflicts.
- History provides a bounded/searchable tenant timeline of Episodes, journals, Threads, Commitments, observable AgentEvent metadata, vocabulary, and assistant messages. Actor attribution, provenance lookup, confirmation, and CAS deletion are visible; deleted records remain excluded.
- Reversible Alembic `0007` maps `exploring`/`waiting` to `active` and `completed` to
  `dormant` before restoring the M4 constraint. `0008` adds versioned journal controls.
- Chat retries preserve one event ID through uncertain delivery and reconcile accepted
  sends before replay. Collection reads are bounded and expose opaque keyset cursors.
- Timeline source projections are ordered before a global merge; event and assistant
  metadata participate in search, and actors come from record provenance semantics.
- Reusable dialogs trap Tab, close on Escape when allowed, focus their first control, and
  restore opener focus.

## TDD evidence

Milestone 5 used vertical RED → GREEN slices. The first backend run observed three expected failures: missing `/api/preferences`, missing thread detail fields, and missing `/api/history/timeline`; all three passed after minimal tenant-scoped implementations. The first frontend run failed module resolution for the not-yet-created Threads/History views; component and shell implementations then made the focused suite green. Subsequent full-suite failures exposed compatibility expectations and lint/type issues, which were corrected before final verification.

## Security posture

Production still fails closed without database URL, access code, 32+ character session secret, exact CORS origins, and a real model adapter. Session tokens remain HttpOnly cookies; mutations keep Origin and CSRF enforcement. React uses escaped text only, History excludes request fingerprints and hidden reasoning, all new reads/writes derive the tenant from the session, and all pages/fields are bounded.

## Known limits

- No live Nebius/Nemotron provider is claimed; deterministic mode remains development/test only.
- No M6 discovery, Jev, calendar, or external integrations were added.
- Backend chat is request/response, so the UI truthfully shows pending state rather than fake token streaming.
- Journal correction preserves the verbatim original while displaying corrected content;
  CAS deletion scrubs retained journal content to a content-free tombstone. Raw chat is a
  separate retention surface.
- Browser screenshots were not fabricated or added. Final visual dogfood is expected from the parent environment.

## Verification

See `docs/RUNBOOK.md` for commands. Final verification on the disposable PostgreSQL 16
service at port 55432 completed with **192 passed, zero skipped**; this includes the
populated 0007 down/up cycle plus migration, race, API, pagination, and tenant-isolation
coverage. Ruff and mypy passed. Frontend verification completed with **15 passed**, zero
high-severity audit findings, clean ESLint/TypeScript, and a successful production build.
