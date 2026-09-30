# Implementation status — Milestone 2

## TDD evidence

M2 was implemented in vertical RED → GREEN slices. Representative observed cycles:

| Slice | RED | GREEN |
|---|---|---|
| Local date and deterministic Power List | `app.daily` import failed; then expected rank order failed | DST-safe local dates and bounded ranked reasons passed |
| Morning runtime path | `DailyBriefing` model import failed | one structured briefing, same-chat proactive message, event/skill/Episode/provenance, and same-day logical idempotency passed |
| Evening loop | `JournalEntry` model import failed; then negated unfinished text was incorrectly completed by generic extraction | same-chat check-in, verbatim journal, explicit supported updates, sourced Episodes, and reflection close passed |
| Yesterday affects today | unfinished item lacked the expected boost/reason | completed work excluded and yesterday's unfinished open work resurfaced/ranked with reason |
| Today/History API | `/api/today` response lacked `briefing` (route absent) | tenant-scoped Today and bounded journal browse/search passed, including two-user isolation |
| M2 migration | upgraded schema lacked all daily-loop tables | explicit `0002` upgrade/downgrade passed |
| Today component | module resolution failed because `app/today.tsx` did not exist | briefing, Power List reasons, resurfacing, reflection state, and absent-section behavior passed |
| Authenticated Today hydration | UI could not find the Today heading | authenticated page fetches and renders Today beside persistent chat |
| Stable injected-clock chronology | shared-history recall selected the wrong same-timestamp message | persisted message ordinals restore deterministic same-chat order |
| Clause-aware evening extraction | the exact profiling/portfolio contrast completed the wrong item, and `finish the frontend` did not match `finished the frontend` | explicit clause boundaries, negation/contrast, unique immediate `it`, and safe action/article normalization pass; ambiguity is inert |
| Bounded Today/briefing state | 150 commitments and 150 threads were all returned and persisted | stable 50-item slices with totals and `has_more` pass for API and stored briefing sections |
| Midnight and catch-up dates | post-midnight and DST answers found no prompt; missed triggers were assigned to execution day | 12-hour latest-awaiting prompt binding and validated intended-day catch-up/idempotency pass |
| Concurrent chat authority | forced simultaneous morning/evening runs created two conversations and forced user-message runs reused ordinals | one DB-enforced conversation per user plus row-locked appends produce one chat and distinct, strictly increasing ordinals |
| Conversation-target idempotency | the same key and payload replayed when pointed at another conversation | same-target requests replay while a retargeted key conflicts |
| M2 concurrency migration | duplicate pre-existing conversations and ordinals survived at migration head | reversible `0003` consolidates conversations, renumbers messages, and applies both uniqueness constraints on SQLite and PostgreSQL |
| Legacy `0002` idempotency replay | the original three-field pre-v2 fingerprint returned 409 after migration while the later four-field fingerprint replayed | both historically emitted canonical schemas replay without duplicates, reject altered content/kind, non-null date mismatches, or foreign targets, and upgrade in place to target-bound v2 |

Tests were written and observed failing before the corresponding runtime/UI behavior. Documentation followed the behavioral work.

## Delivered

- `JournalEntry`, `DailyBriefing`, and `ReflectionPrompt` persistence with ownership, provenance, policy/date uniqueness, source links, UTC timestamps, local date, structured state, and verbatim reflection retention.
- Unified morning/evening events through `AgentRuntime.handle`, thin daily skills, proactive messages in the same chat, AgentEvents, SkillRuns, Episodes, and audit provenance.
- Interpretable deterministic `m2-v1` Power List over current state; no empty vocabulary/discovery placeholders and no M3 slack overbuild.
- Clause-aware evening extraction boundaries for completion, unfinished work, priority changes, new commitments/threads, blockers, and outcomes; unsupported or ambiguous prose is retained but not promoted.
- Next-morning continuity: completed work stays out; explicitly unfinished open work resurfaces with a ranking boost.
- Tenant-scoped bounded Today and journal-history APIs plus minimal Today rendering. Today and persisted briefing commitment/thread collections have a documented 50-item cap and explicit totals/`has_more` metadata.
- Injected clock, IANA timezones/`zoneinfo`, midnight and DST prompt binding, validated one-day intended-date catch-up, catch-up idempotency, and real PostgreSQL concurrent-trigger coverage.
- Explicit Alembic `0002` upgrade and downgrade; CI already runs the full PostgreSQL suite.
- Race-safe conversation get-or-create, tenant-scoped row-locked message appends, DB uniqueness for one conversation per user and `(conversation_id, ordinal)`, and conversation-target-bound request fingerprints.
- Explicit reversible Alembic `0003`, including deterministic cleanup of pre-constraint duplicate conversations/messages and a real PostgreSQL migration cycle.
- Versioned target-bound v2 request fingerprints with narrowly bounded compatibility for both pre-v2 schemas (original `content`/`kind`/`user_id` and later date-aware form) and upgrade-on-success.

## Final verification

- Full PostgreSQL-backed verification passed: backend `99 passed` against PostgreSQL 16, Ruff clean, mypy clean; frontend `6 passed`, npm audit `0 vulnerabilities`, ESLint clean, TypeScript clean, and Next.js 16.3.7 production build successful.
- Focused migration/PostgreSQL quality suite: `26 passed`, including forced simultaneous morning/evening and user-message requests with one conversation, strictly increasing transaction-contiguous ordinals, no HTTP 500s, and exact replay of both pre-v2 fingerprint formats.
- Real-PostgreSQL Alembic `0003` cycles succeeded for duplicate conversations and both historical legacy fingerprint fixtures; each replayed without duplicates, upgraded to v2 through downgrade/re-upgrade, and continued rejecting retargeting.

## Known limits

M2 remains intentionally deterministic. Deadline hints are not normalized dates; M3 owns effort/slack and generalized urgency scans. The reflection grammar is narrow and explicit rather than open-ended language understanding. Vocabulary/discovery are omitted because M4/M6 data does not exist. Today UI is minimal; full navigation, journal correction/deletion UX, and polish remain M5. The deterministic model adapter remains development/test-only and no live Nebius/Nemotron claim is made.
