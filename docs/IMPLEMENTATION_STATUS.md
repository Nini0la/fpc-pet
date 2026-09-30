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

Tests were written and observed failing before the corresponding runtime/UI behavior. Documentation followed the behavioral work.

## Delivered

- `JournalEntry`, `DailyBriefing`, and `ReflectionPrompt` persistence with ownership, provenance, policy/date uniqueness, source links, UTC timestamps, local date, structured state, and verbatim reflection retention.
- Unified morning/evening events through `AgentRuntime.handle`, thin daily skills, proactive messages in the same chat, AgentEvents, SkillRuns, Episodes, and audit provenance.
- Interpretable deterministic `m2-v1` Power List over current state; no empty vocabulary/discovery placeholders and no M3 slack overbuild.
- Explicit evening extraction boundaries for completion, unfinished work, priority changes, new commitments/threads, blockers, and outcomes; unsupported prose is retained but not promoted.
- Next-morning continuity: completed work stays out; explicitly unfinished open work resurfaces with a ranking boost.
- Tenant-scoped bounded Today and journal-history APIs plus minimal Today rendering.
- Injected clock, IANA timezones/`zoneinfo`, DST coverage, catch-up idempotency, and real PostgreSQL concurrent-trigger coverage.
- Explicit Alembic `0002` upgrade and downgrade; CI already runs the full PostgreSQL suite.

## Final verification

- `POSTGRES_TEST_URL=… make check` passed: backend `82 passed` against PostgreSQL 16, Ruff clean, mypy clean; frontend `6 passed`, npm audit `0 vulnerabilities`, ESLint clean, TypeScript clean, and Next.js 16.3.7 production build successful.
- Focused real-PostgreSQL M2 quality suite: `14 passed`, including concurrent same-day morning triggers producing exactly one logical briefing/proactive message.
- Real-PostgreSQL Alembic cycle succeeded: `upgrade head` (`0001` → `0002`), `downgrade 0001`, then `upgrade head` again.

## Known limits

M2 remains intentionally deterministic. Deadline hints are not normalized dates; M3 owns effort/slack and generalized urgency scans. The reflection grammar is narrow and explicit rather than open-ended language understanding. Vocabulary/discovery are omitted because M4/M6 data does not exist. Today UI is minimal; full navigation, journal correction/deletion UX, and polish remain M5. The deterministic model adapter remains development/test-only and no live Nebius/Nemotron claim is made.
