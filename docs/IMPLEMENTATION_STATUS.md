# Implementation status — Milestone 1

## TDD evidence (actual runs)

| Slice | RED | GREEN |
|---|---|---|
| State extraction boundaries | `uv run pytest tests/test_extraction.py -q` → import failed: `No module named app` | same command → `5 passed` |
| Auth/chat/tenancy/provenance/idempotency/recall | `uv run pytest tests/test_api.py -q` → `No module named app.main` (7 errors) | same command → `7 passed` |
| Lifecycle transitions | focused test → expected `open != complete` failure | focused test → `1 passed` |
| Commitment/episode correction and deletion | focused test → expected route `404` | focused test → `1 passed` |
| Escaped chat rendering and bounded input affordance | `npm test` → XSS rendering passed; capacity assertion failed (`Unable to find ... 0 / 4000`) | `npm test` → `2 passed` |
| Controllable time | focused clock test → `No module named app.clock` | focused clock test → `1 passed` |
| Production model safety | focused config test → production imported with deterministic mode | focused config test → `1 passed`, deterministic production rejected |
| Pronoun completion / abandonment | focused API test → recent commitment remained `open` | focused API test → `1 passed` |
| Imperative deadline extraction | focused extractor test → `none != commitment` | focused extractor test → `1 passed` |
| Server-derived production identity | focused security test → `No module named app.security` | focused security test → `1 passed`; client username forced to `owner` |
| Chat-created shared history and conversational recall | focused E2E tests → `5 failed` (zero Episodes; canned reply) | focused E2E tests → `5 passed`; actor-attributed Episodes and sourced recall across auth sessions |
| Recall intent facets and history contamination | focused seven-phrase E2E test → failed at missing injected clock (`unexpected keyword argument 'clock'`) | focused E2E tests → `2 passed`; all seven spec questions filter by topic, actor, decision, chronology, and week while recall turns create no Episodes |
| Explicit state in shared-history recall | focused E2E test → commitment absent from recall despite its message provenance | focused E2E test → `1 passed`; non-deleted commitments/threads join chronology with message sources while deleted state stays excluded |
| Negated completion boundaries | focused extractor/API tests → `8 failed, 4 passed`; “haven’t/not finished” incorrectly completed the open commitment | focused positive/negative lifecycle tests → `14 passed`; common apostrophe and expanded negations stay open while explicit completion still works |
| Ambiguous demonstrative recall | focused `this`/`that` E2E test → `2 failed`; response dumped both unrelated assistant records | focused tests → `3 passed`; unresolved demonstratives request a topic and disclose no unrelated history, while a unique immediate referent filters the answer |
| Fresh-login history hydration | focused component test → failed to find the prior message after login | focused component test → `3 passed`; successful login fetches and renders existing chronological messages immediately |
| Deployment-selected migration target | focused migration test → ignored `DATABASE_URL` and failed against the unavailable PostgreSQL ini target; async SQLite URL failed on missing `aiosqlite` | focused migration tests → `2 passed`; environment URL overrides the local Compose fallback, supported async forms use sync drivers, secrets stay out of output, and isolated SQLite upgrade/downgrade succeeds |
| M1 quality/security hardening | focused privacy, concurrency, idempotency, PostgreSQL boundary, and migration tests failed on permissive Episode capture, application-only version checks, duplicate unique races, varchar overflow, and metadata-driven migration | focused tests pass with default-deny Episode capture, tenant-scoped atomic CAS, request fingerprints/savepoint race recovery, Text-backed narrative fields, and explicit Alembic operations |

Tests were added before their corresponding runtime behavior. Configuration and documentation were added after behavioral slices. The persistence regression opens a fresh SQLAlchemy session against the same durable database after the request transaction.

Dependency security was checked after upgrading Next/React/Vitest and the lint stack: `npm audit --json` reported 0 vulnerabilities (including 0 high/critical), and the regenerated lockfile is committed.

## Delivered

Secure opaque sessions/CSRF, tenant scoping, persistent chat, deterministic explicit state extraction and transitions, idempotent unified runtime, chat-created explicit attributed history, facet-filtered conversational shared-history recall, recall-contamination prevention, provenance, correction/deletion, M1 schema/migration, minimal login/chat UI, compose/Make/CI, and security/architecture docs.

## Final verification

`make check` passed with PostgreSQL integration enabled: backend `56 passed`, Ruff clean, mypy clean; frontend `3 passed`, npm audit `0 vulnerabilities`, ESLint clean, TypeScript clean, and Next.js 16.3.7 production build successful. PostgreSQL 16 exercised real concurrent sessions, duplicate ingress races, and input boundaries. The explicit Alembic initial migration also completed upgrade/downgrade cycles against both isolated SQLite and PostgreSQL databases.

## Known limits

This is M1 only. General deterministic response text is a test/development stub. Deadline strings are not normalized dates. Shared-history intent parsing is a small deterministic grammar for the documented recall facets rather than open-ended language understanding; conversational recall uses explicit, non-deleted Episode and state evidence with message provenance. The history API remains lexical. Scheduled events enter the runtime but M2 proactive policies are absent. Fast isolated tests use SQLite, while concurrency, migration, and length-boundary regressions also run against PostgreSQL 16.
