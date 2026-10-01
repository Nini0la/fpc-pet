# Implementation status — Milestone 3

## TDD evidence

M3 was implemented in vertical RED → GREEN slices. Representative observed failures before implementation:

| Slice | RED | GREEN |
|---|---|---|
| Temporal schema and parsing | `Reminder` import missing; normalized fields absent | commitment timing/effort fields, Reminder model, explicit weekday/ISO parsing, ambiguity, timezone and end-of-local-day policy pass |
| Runtime extraction | title retained date/effort prose and ambiguity was lost | chat persists normalized deadline, granularity, source phrase, effort, and clarification; named follow-up effort updates use CAS |
| Urgency | Monday/Thursday policy and exact factors absent | deterministic low/medium/high score exposes deadline, effort, slack, importance, inactivity, blockers, and stored availability |
| Prospective runtime | `commitment_check` returned no surfaced count and wrote nothing | no-op then surfacing produces one atomic same-chat Reminder/message/Episode/event/skill/provenance bundle |
| Suppression/replies | completion timestamp absent and generic `that` resolution ignored surfacing | terminal/deleted/ambiguous records are suppressed; unique latest surfaced commitment completes; tied candidates ask clarification |
| API/scheduling | Today had no urgency; intended window inputs were ignored | Today urgency, bounded tenant Reminder API, and validated timezone-aware catch-up windows pass |
| Migration | `reminders` table absent at Alembic head | explicit reversible `0004` upgrade/downgrade passes on SQLite and PostgreSQL |
| Concurrency | no M3 race coverage | real PostgreSQL proves one reminder under concurrent scans and suppression when completion wins the row-lock race |

Tests were written and observed failing before their corresponding behavior. Documentation followed behavioral implementation.

## Delivered

- Commitment temporal/effort/importance/relevance/surfacing/ambiguity/dependency/availability/thread/completion fields without filling unknown values.
- Tenant-owned Reminder with reason code, factor-only metadata, lifecycle/retry state, commitment/thread/message/event links, and one-per-window/policy uniqueness.
- Bounded explicit weekday, `next weekday`, ISO date/time, numeric-date ambiguity, and word/digit effort parsing using injected time and IANA timezone. Date-only deadlines preserve granularity/source and use local 23:59:59 for urgency.
- Interpretable `m3-v1` urgency/slack service. Advancing Monday to Thursday increases urgency solely as deadline slack shrinks.
- `ProspectiveReminderSkill` and periodic `commitment_check` through `AgentRuntime.handle`; authoritative row refresh immediately precedes surfacing.
- Atomic proactive message, Reminder, Episode, SkillRun, AgentEvent, provenance, and exact true-factor explanation in the persistent chat.
- PostgreSQL row locking, uniqueness, event fingerprints, bounded scan/retry, duplicate-scan safety, and completion-wins-race suppression.
- “Actually, I finished that already” resolves only a uniquely most-recently surfaced commitment, records `completed_at`, and prevents future reminders; tied candidates receive clarification.
- Live urgency in Today plus bounded, tenant-scoped `/api/reminders`; scheduled commitment checks validate aware intended instants and a 1–1440 minute catch-up window.
- Explicit reversible Alembic `0004`; documentation updated for M3. No M4/M5/optional work was started.

## Verification

- M3 focused SQLite/API/migration tests pass.
- Real PostgreSQL focused concurrency tests pass, including concurrent duplicate scans and completion-vs-scan suppression.
- Full PostgreSQL-enabled backend run: `122 passed`, with zero skips. A separate real-PostgreSQL migration/race command passed all `3` targeted upgrade/downgrade, duplicate-scan, and completion-wins-race tests.
- Final `make check`: backend `99 passed, 23 skipped` when `POSTGRES_TEST_URL` is not exported; Ruff and mypy pass; frontend `6 passed`, npm audit reports `0 vulnerabilities`, ESLint and TypeScript pass, and the production build succeeds.

## Known limits

The parser is intentionally bounded, not general natural-language date understanding. Numeric slash dates remain ambiguous. Availability contributes only when already stored; M3 does not add calendar integration. Retry fields and reconciliation state are bounded, but external job orchestration remains deployment-owned. Today UI remains the minimal M2 surface consuming the expanded API; full UX polish remains M5. The deterministic model adapter remains development/test-only.
