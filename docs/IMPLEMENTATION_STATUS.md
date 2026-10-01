# Implementation status — Milestone 3

## TDD evidence

M3 was implemented in vertical RED → GREEN slices. Representative observed failures before implementation:

| Slice | RED | GREEN |
|---|---|---|
| Temporal schema and parsing | `Reminder` import missing; normalized fields absent; invalid explicit ISO dates/clocks raised `ValueError` | commitment timing/effort fields, Reminder model, explicit weekday/ISO parsing, ambiguity, timezone and end-of-local-day policy pass; invalid recognized values preserve source, store no deadline, and clarify |
| Runtime extraction | title retained date/effort prose and ambiguity was lost | chat persists normalized deadline, granularity, source phrase, effort, and clarification; named follow-up effort updates use CAS |
| Urgency | Monday/Thursday policy and exact factors absent; inactivity used immutable creation time | deterministic low/medium/high score exposes deadline, effort, slack, importance, truthful `last_touched_at` inactivity, blockers, and stored availability |
| Prospective runtime | `commitment_check` returned no surfaced count and wrote nothing | no-op then surfacing produces one atomic same-chat Reminder/message/Episode/event/skill/provenance bundle |
| Suppression/replies | completion timestamp absent and generic `that` resolution ignored surfacing; unsurfaced records could be selected by fallback | terminal/deleted/ambiguous records are suppressed; only a unique latest surfaced active commitment completes; absent/tied candidates ask clarification without mutation |
| API/scheduling | Today had no urgency; intended window inputs were ignored | Today urgency, bounded tenant Reminder API, and validated timezone-aware catch-up windows pass |
| Migration | `reminders` table absent at Alembic head; M3-only states violated the restored M2 constraint on downgrade | explicit reversible `0004` backfills `last_touched_at`, applies the documented loss-aware state mapping, and passes real-data PostgreSQL downgrade/re-upgrade |
| Concurrency | no M3 race coverage | real PostgreSQL proves one reminder under concurrent scans and suppression when completion wins the row-lock race |
| M3 quality/security closure | unknown effort gained slack; fixed oldest-100 scans starved later rows; demonstrative/DST/effort bounds and tenant relationship enforcement were incomplete; scan/completion lock order could deadlock | unknown effort remains unknown, persistent keyset scanning is bounded and fair, all bounded demonstrative variants use unique surfaced resolution, wall times are fold/gap-safe, effort is bounded before conversion, conversation-first locking is race-tested, and composite tenant FKs reject cross-owner Reminder links |

Tests were written and observed failing before their corresponding behavior. Documentation followed behavioral implementation.

## Delivered

- Commitment temporal/effort/importance/relevance/surfacing/ambiguity/dependency/availability/thread/completion fields without filling unknown values.
- Tenant-owned Reminder with reason code, factor-only metadata, lifecycle/retry state, commitment/thread/message/event links, and one-per-window/policy uniqueness.
- Bounded explicit weekday, `next weekday`, ISO date/time, numeric-date ambiguity, and word/digit effort parsing using injected time and IANA timezone. Effort accepts 1 minute through 7 days and is rejected before unbounded integer conversion. Date-only deadlines preserve granularity/source and use local 23:59:59 for urgency; recognized invalid ISO dates/clocks and nonexistent/ambiguous local wall times preserve the original source, never guess `due_at`, and request clarification. Explicit UTC offsets disambiguate folds.
- Interpretable `m3-v1` urgency/slack service. `last_touched_at` is initialized/backfilled deterministically, refreshed by meaningful commitment mutations (including evening completion, explicit unfinished touches, and priority changes), and left unchanged by no-op extraction and read-only scans; advancing Monday to Thursday increases urgency solely as deadline slack shrinks.
- `ProspectiveReminderSkill` and periodic `commitment_check` through `AgentRuntime.handle`; authoritative state is selected under the conversation-first lock order and rechecked before surfacing.
- Atomic proactive message, Reminder, Episode, SkillRun, AgentEvent, provenance, and exact true-factor explanation in the persistent chat.
- Conversation-before-commitment PostgreSQL row locking, uniqueness, event fingerprints, bounded cursor-based fair scanning/retry, duplicate-scan safety, deterministic deadlock regression coverage, and completion-wins-race suppression. Retryable database conflicts roll back to a safe 409.
- Bounded “I finished/completed that” and “done with that” variants, with optional “already”, resolve only a uniquely most-recently surfaced active commitment, record `completed_at`, and prevent future reminders; absent or tied surfaced candidates receive clarification with no mutation.
- Live urgency in Today plus bounded, tenant-scoped `/api/reminders`; scheduled commitment checks validate aware intended instants and a 1–1440 minute catch-up window.
- Explicit reversible Alembic `0004` and `0005`, including deterministic M3→M2 state mapping, `last_touched_at` backfill, fair-scan cursor persistence, and composite tenant-aware Reminder relationships; documentation updated for M3. No M4/M5/optional work was started.

## Verification

- Updated M3/extraction/retry-conflict focus: `49 passed`.
- Real PostgreSQL blocker focus: `7 passed`, covering huge effort containment, deterministic conversation/commitment lock ordering, all four tenant-bound Reminder relationships, and preservation of existing valid rows through `0005` upgrade/downgrade/re-upgrade.
- Full PostgreSQL-enabled backend run: `156 passed`, zero skips, including real-data migration cycles, forced races, bounded fair scans, cross-tenant FK rejection, and completion-vs-scan suppression.
- Ruff and mypy pass. Frontend `6 passed`; npm audit reports `0 vulnerabilities`; ESLint, TypeScript, and the production build pass.

## Known limits

The parser is intentionally bounded, not general natural-language date understanding. Numeric slash dates remain ambiguous. Availability contributes only when already stored; M3 does not add calendar integration. Retry fields and reconciliation state are bounded, but external job orchestration remains deployment-owned. Today UI remains the minimal M2 surface consuming the expanded API; full UX polish remains M5. The deterministic model adapter remains development/test-only.
