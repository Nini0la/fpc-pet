# Implementation Status

## Milestone 01 — PERSONAL STACK DEPLOYED AND VERIFIED; OWNER ACCEPTANCE PENDING

**Current deployment:** `acaa10c379ff00e151068a12635ac81438718c4b` on
`feat/functional-autonomy`, pushed with initial implementation `8b7ed1c` and rollout fix `a750646`.
All commits are single-parent feature commits; no branch merge was performed. Full deployment,
backup hashes and exact previous-version restoration steps: [PERSONAL_ROLLOUT.md](PERSONAL_ROLLOUT.md).

Owner authorized the controlled personal rollout on 2026-10-26. The matching API, Next production
build and `app.scheduler --personal-only` now run from `.local/releases/m1-final/` under macOS
LaunchAgent supervision, on loopback ports 8000/3000. Personal PostgreSQL `mystery_pet` is at
**0012 (head)**. This supersedes the pre-rollout pending-deployment notes retained below.

### Personal-stack acceptance evidence

| Requirement | Observed result |
| --- | --- |
| Backup / usable recovery | Custom dump restored to `mica_recovery_20261026`; 100 original rows matched; real-data upgrade/downgrade rehearsal passed; previous `cef953f` API served original owner chat/commitment/profile/history |
| Preserve existing data/settings | All original content fingerprints preserved after migration and after validation; original companion name/temperament, timezone and routine times preserved |
| S1/S2 live conversation | One labelled validation commitment; correct exclusive deadline; ordinary correction to Thursday 18:00 UTC; Azure completion receipt at version 5 with no next check |
| S3 true unattended effect | One persisted in-app check-in with API/frontend stopped; actual scheduled real-clock worker effect at 17:24:59 UTC |
| S4 real crash / replay | Actual `SIGKILL` after committed claim; no effect before crash; expired lease recovered on attempt 2; two further worker sweeps produced no duplicate |
| S5 changed circumstances | Evening restriction preserved purpose and replanned to next morning; explicit later availability restoration reset the check safely |
| S6 routines | One unattended morning and one evening output; duplicate occurrences skipped; original 11:58/20:00 UTC times restored |
| S7 external boundary | Bridge/responsibility worker stopped; both channel accounts disabled; blank channel overrides in services; zero channel messages |
| S8/S9 integrated runtime/UI | Matching clean release; real mobile Chromium owner login, historical chat, History, controls, correction/action evidence, no page errors/overflow; verified again after recovery |

Final application verification: **526 backend tests passed in 95.62s**, Ruff and mypy passed;
**65 frontend / 12 bridge tests** passed; final production build passed. GitHub CI for `acaa10c`
passed: https://github.com/Nini0la/fpc-pet/actions/runs/40365221852.

Live action `5a19e625-a581-4588-9532-90039e241855` recovered to exactly one message
`8c8e3c84-0732-40bc-b0ae-7e7dc40f3a97`, source event `0f866522-f108-4554-b7d9-e5756f83e564`.
Validation commitment `0172a1ab-dc0d-4600-85ab-09a927924ccd` is completed, with five revisions.
Pre-rollout and post-verification database dumps, private config/bridge backup and detailed
evidence remain under ignored, restricted `.local/rollouts/20261026-m1/`.

### Findings during the controlled rollout

- Fixed an ID-only proposal being rejected despite the owner explicitly naming its full title
  when another commitment exists (`a750646`). Multi-commitment positive, unnamed-reference negative
  and duplicate-title negative regression cases pass.
- Fixed positive availability/plan corrections being consumed by an awaiting evening reflection
  (`acaa10c`). The exact pending-reflection regression passes; live plan restoration succeeded.
- Two Azure final wording calls returned `unavailable` after successful tool writes. Their receipts
  and persisted state stayed honest; creation was not retried or duplicated. Later conversational
  changes and completion delivered successfully. Provider final-response availability remains a
  known runtime limitation, not evidence that a saved write failed.

**Remaining gate:** the owner's real-world trial and approval. Check-ins and both routines are
enabled for that trial; original commitments retain default-off individual follow-ups. Today’s
routine outputs already exist from verification, so normal-time recurrence resumes tomorrow.
Keep the Mac awake/logged in for unattended work. WhatsApp delivery stays disabled. No Milestone 2
work or branch merge is authorized before owner acceptance.

## Isolated-stack verification — pre-rollout record

Governing documents: `MICA_TARGET.md` and `milestones/01_AUTONOMY.md`, read in full and copied
byte-for-byte from the supplied ZIP. No Milestone 2/3 implementation is authorized by this work.

### Verified starting point

- Inspected `feat/mystery-pet-context` at `d58b2ef` and `feat/operational-responsibilities` at
  `cef953f`. The former contains the new personality/security patches; the latter contains
  response inspection, delegated workflows, the worker and Baileys adapter. They diverged at
  `97c0dc7`; the current processes exposed the operational API while the checkout served the
  older frontend. The branch/runtime mismatch was real.
- `app/agent.py` uses one event ingress with per-user idempotency and ordered message writes.
  `app/assistance.py` provides Azure-backed tool calls, but its commitment tool only creates;
  there is no live conversational amend/complete/pause/resume/cancel tool.
- `app/prospective.py:parse_commitment_timing` handles ISO dates, weekdays and effort but not
  “before 9pm tomorrow” or weekday clocks. `next Friday afternoon` is currently reduced to a
  guessed date-only deadline instead of asking about the ambiguous time of day.
- `MorningBriefingSkill` / `EveningReflectionSkill` in `app/daily.py` are real persisted,
  idempotent handlers, but no worker invokes their stored times. The Power List still uses
  `deadline_hint` and creation-age proxies rather than the current urgency fields.
- `app/operations_worker.py` on the operational branch handles only a configured channel's
  delegated responsibilities. It has no owner commitment or daily-routine scheduler.
- PostgreSQL already owns commitments, threads, journals, provenance, feedback and operational
  messages. Existing single-owner production login deliberately resolves to `owner`
  (`app/security.py`); this remains a private application, not multi-user authentication.

Baseline commands (isolated native PostgreSQL test database, no personal-data mutation):

```text
createdb mica_autonomy_test
POSTGRES_TEST_URL=postgresql+psycopg:///mica_autonomy_test uv run pytest -q
  472 passed in 63.91s (initial mystery-pet-context branch)
npm test -- --maxWorkers=1 --testTimeout=30000
  48 passed (initial frontend)
```

### One implementation path

1. Consolidate the existing branches on `feat/functional-autonomy`, retaining the personality,
   patched frontend dependencies, response traces, responsibilities and authorization boundaries.
   Merge is prepared without creating a commit; no existing branch is overwritten.
2. Extend Commitment minimally for purpose, next action, timing bounds, constraints/availability,
   and opted-in follow-through. Add owner-scoped lifecycle tools and correction provenance.
3. Add a durable scheduled-action ledger with leases, bounded attempts and stable keys. In-app
   effects and authoritative state changes commit atomically; reuse existing daily skills and
   preserve the separate authorized responsibility/channel path.
4. Add explicit owner opt-ins and compact Today/history controls. New self-directed actions use
   in-app delivery; configured WhatsApp is not treated as permission to send.
5. Verify S1–S9 with injected clocks, PostgreSQL races/failure injection, and an isolated running
   Azure/API/worker smoke. Only then update the gate; owner real-world acceptance stays pending.

### Acceptance ledger

| Scenario | Status | Evidence |
| --- | --- | --- |
| S1 Natural intention | PASS: PostgreSQL/API fixture + live Azure | Exactly one presentation; `2026-10-27T20:00Z` exclusive boundary (before 21:00 Lagos), next check and message provenance; fresh session |
| S2 Updates/completion | PASS: fixture + live Azure | Thursday 18:00 Lagos correction; old actions cancelled; completed state and no future check; explicit reopen |
| S3 Unattended action | PASS: real worker subprocess | API/browser stopped during wake; one persisted in-app Message with event/action evidence; duplicate sweep adds nothing |
| S4 Restart/duplicates | PASS: PostgreSQL fault injection/concurrency | Four crash stages, new runtime/sessions and overlapping workers; one observable in-app effect; bounded retry/backoff; claimed-plan cancellation |
| S5 Meaningful replanning | PASS: fixture + live Azure | Purpose preserved; evenings blocked through 2026-11-01; next action/check replanned; old plan suppressed |
| S6 Daily routines | PASS: fixture + real worker subprocesses | Morning/evening each recur once on Oct 28/29; duplicate sweeps deduplicated; disabling stops next-day work |
| S7 Permission boundaries | PASS: deterministic/fake-channel tests | Unsupported external action records unauthorized skip; read-only chat cannot mutate; existing scope/bridge regressions pass |
| S8 Regressions/coherency | PASS on isolated integrated stack; personal rollout pending | 525 backend / 65 frontend / 12 bridge; migrations, type/lint/audits/build; real Chromium → Next 16.4.3 → current API/schema |
| S9 Inspection/controls | PASS: API + real mobile Chromium | Status/next check, correction sources, action history; reopen/pause/resume/cancel persisted across reload; no page errors or horizontal overflow |

### Implementation and observed proof (2026-10-26)

- Current branch: `feat/functional-autonomy`, based on `d58b2ef`, with the prepared merge of
  `cef953f`. No commit/push was requested or performed. The branch's source now combines personality,
  patched dependencies, raw response inspection, approved responsibilities and personal autonomy.
- Migration `0012` adds default-off preferences, modest Commitment plan/follow-up fields, versioned
  `CommitmentRevision` and durable `ScheduledAction`. Shared lifecycle validation is in
  `backend/app/commitments.py`; scheduler/policy/API are `scheduler.py`, `autonomy.py`,
  `autonomy_api.py`. Existing AgentRuntime/daily skills are used for actual effects.
- `frontend/app/autonomy.tsx` extends Today with opt-ins, quiet hours, plan correction, lifecycle
  controls and outcome history. Existing Chat displays actual unattended messages. See
  [AUTONOMY.md](AUTONOMY.md) for rollout, permission limits, retry semantics and rollback.

Final automatic checks:

```text
backend/: POSTGRES_TEST_URL=postgresql+psycopg:///mica_autonomy_test uv run pytest -q --tb=short
  525 passed in 78.44s
backend/: uv run ruff check app tests
  All checks passed
backend/: uv run mypy app
  Success: no issues found in 29 source files
backend/: DATABASE_URL=postgresql+psycopg:///mica_autonomy_smoke_test uv run alembic current
  0012 (head)
frontend/: npm test -- --maxWorkers=1 --testTimeout=30000
  65 passed, 10 files
frontend/: npm run typecheck; npm run lint; npm run audit:ci
  Passed; full dependency audit clean
frontend/: NEXT_PUBLIC_API_URL=http://127.0.0.1:8012 npm run build
  Next.js 16.4.3 production build passed
whatsapp-bridge/: npm test; npm audit --omit=dev
  12 passed; 0 vulnerabilities
repo/: git diff --check
  Passed
```

Live proof command (isolated migrated `mica_autonomy_smoke_test`, ports 8012/3002):

```sh
DATABASE_URL=postgresql+psycopg:///mica_autonomy_smoke_test \
PLAYWRIGHT_MODULE_PATH=/var/folders/2z/k510lmwj7g70_lk9nzmrw8jc0000gn/T/opencode/mystery-pet-smoke/node_modules/playwright \
uv run python tests/live_autonomy_smoke.py --with-browser
```

Observed output:

```text
Azure: gpt-5.4-2026-03-05
create_commitment saved version 1
fresh-session deadline retrieval: delivered, no state mutation
update_commitment updated version 2 (deadline)
update_commitment updated version 3 (availability)
update_commitment completed version 4; delivery none
Browser PASS: current state, corrections, reopen/pause/resume/cancel, in-app evidence, reload, mobile width
PASS: username autonomy-smoke-698a801b3769
commitment_id 15b23596-efd1-410d-a510-447bc2d3f76d
verified_effects 5; revisions 4 before browser controls; browser true; external_sends 0
```

The five effects are one check-in plus two morning and two evening outputs. Real Azure handled
the five conversational turns (nine bounded model calls total); deterministic scheduler decisions
used no inference. The smoke stops/restarts the actual API, authenticates a fresh client and invokes
fresh worker processes, including while the API/browser are absent. The browser uses the same
synthetic owner's real API/database records, not frontend mocks. Browser controls create additional
revisions and leave the synthetic commitment cancelled. All test-owner opt-ins end disabled.

Findings corrected during verification:

- Initial merged regression run: 493 passes, 13 old-contract failures (read receipts/tool lists,
  migration head, normalized deadline semantics). Updated assertions preserve their original
  regression purpose and test explicit new contracts; final full suite passes.
- First live S1 smoke asked for redundant confirmation and saved nothing. The prompt did not tell
  the model that available write tools signal the already-enabled UI permission. Clarified that
  authoritative rule and that a definite intention plus “help me stay on track” requests tracking;
  backend permission and ambiguity validation remain enforced. The final live capture passed.
- A subsequent smoke completed backend scenarios but the local cached Playwright package was
  incomplete. Reinstalled only in the temporary tools directory; Chromium launch and final real
  browser smoke passed. This was not treated as product acceptance before rerunning.

### Remaining gates and limits

- **Owner trial/approval and authorized personal-stack rollout are pending.** The personal
  `mystery_pet` database was not migrated and the existing API/paired WhatsApp processes were not
  restarted. The isolated integrated stack was verified and its test processes then stopped.
  The original personal runtime mismatch is therefore not claimed to be deployed away.
- Check-ins are in-app, not push/WhatsApp. Exactly-once evidence is for the transactional database
  effect. External-channel tests use fake transport; real recipient send/reply acceptance remains
  pending. Single-owner auth/privacy remains private; test usernames are not multi-user security.
- Date parsing deliberately asks about ambiguous dates/periods; constraints/replanning are bounded.
  The UI lists the latest 100 records and the scheduler has a bounded candidate scan. A permanently
  failed action needs inspection/plan correction rather than hidden unlimited retries.
- Do not reuse the smoke frontend build for personal deployment: rebuild with its correct API URL.
  Review migration/disable instructions in `AUTONOMY.md`, authorize rollout, then perform the real
  capture → unattended follow-up → correction → completion trial before accepting Milestone 1.

Owner trial and milestone approval: **pending**. No external third-party messages, Nebius
inference, Hermes or Letta are part of acceptance testing. Earlier sections below are historical
handoffs, not evidence that this new milestone is complete.

## Current: Operational Responsibilities

See [OPERATIONS.md](OPERATIONS.md). A deterministic delegation workflow extends Commitments,
with explicit external-contact authorization, durable scheduling and communication journals,
a channel-isolated Baileys service, and reported-vs-owner-verified completion. Migration `0011`
adds the operational records. Live pairing was subsequently verified against the dedicated
assistant account, with a recent worker heartbeat. The real recipient send/reply acceptance
test remains pending. General WhatsApp chat and automatic LLM retries are not implemented.
The earlier inspector work is preserved.

## Response-Level Context Inspection

History assistant responses and Chat expose a private **View context** inspector. New responses
capture actual model inputs per call, selected sources, tool execution evidence, model output,
and usage. Old uncaptured responses are explicitly marked unavailable. Migration `0010` reuses
AssistanceRun rather than creating a separate observability database. See
[RESPONSE_CONTEXT.md](RESPONSE_CONTEXT.md). Langfuse/Phoenix are not integrated.
The Discord plan is saved separately in [DISCORD_PLAN.md](DISCORD_PLAN.md).

## Contextual Mystery Pet Slice

The active milestone is documented in [MYSTERY_PET_SLICE.md](MYSTERY_PET_SLICE.md).
It adds a configurable provider, bounded context, authorized creative tools, revisions,
assistance feedback, evidence-linked milestones, pet presentation, and comparative evaluation.
Azure GPT-5.4 is now connected and the synthetic creative/correction workflow is live-verified;
see [AZURE_OPENAI.md](AZURE_OPENAI.md). Broad real-user quality remains unassessed.
Automated regression tests use test doubles and a loopback server. The complete automatic
accountability/reminder-delivery workflow remains deferred.

The following section records the earlier M5 handoff, not the current provider boundary.

## Historical Milestone 5

## Delivered

- Warm, mobile-first Next.js shell with Chat, Today, Threads, and History as the only product navigation. It includes semantic landmarks/headings/forms, a skip link, focus rings, 44px controls, reduced-motion support, long-content wrapping, and a desktop side rail that becomes a mobile bottom bar.
- Access-code login and first-run onboarding explain selective memory, inspect/correct/delete controls, session privacy, and the retention caveat. Users configure a validated IANA timezone and morning/evening times through tenant-scoped CAS preferences.
- Chat loads the newest bounded page in chronological order across login/reload/reconciliation,
  renders timestamps/proactive labels, safely reconciles optimistic messages from authoritative
  history, and exposes 401/network/server errors with retry. Accessible earlier-history loading
  prepends stable keyset pages without duplicates. It does not simulate streaming.
- Today presents only API-backed briefing, reason-bearing Power List, bounded urgent commitments, vocabulary state, resurfaced items, and reflection state. Morning/evening controls use the existing authorized idempotent event API.
- Threads filters active/exploring/waiting/dormant/completed/abandoned state and edits trimmed description, state, importance, deadline, next action, and watch fields using versioned CAS. Stale writes surface as conflicts.
- History provides a bounded/searchable tenant timeline of Episodes, journals, Threads, Commitments, observable AgentEvent metadata, vocabulary, and assistant messages. Actor attribution, provenance lookup, confirmation, and CAS deletion are visible; deleted records remain excluded.
- Reversible Alembic `0007` maps `exploring`/`waiting` to `active` and `completed` to
  `dormant` before restoring the M4 constraint. `0008` adds versioned journal controls.
- Chat retries preserve one event ID through uncertain delivery and reconcile accepted
  sends before replay. The latest-page response includes truthful count/continuation metadata,
  while the original forward collection contract remains compatible.
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
service at port 55432 completed with **196 passed, zero skipped**; this includes the
populated 0007 down/up cycle plus migration, race, API, latest/older chat pagination,
and tenant-isolation coverage. Ruff and mypy passed. Frontend verification completed
with **22 passed**, clean ESLint/TypeScript, a successful Next.js 16.4.0 production
build, and zero production dependency vulnerabilities.

## Handoff notes

The final M5 review blockers are resolved: journal search now uses only effective
(corrected-or-original) content; Threads and History load independently without false
empty states and retry only their own endpoint; provenance 401s expire the session,
while transient failures show an explicit retry. Browser screenshot dogfooding remains
unclaimed because the prior environment could not grant Chrome remote-debugging access.

The full development-dependency audit still reports five high findings through
`eslint-config-next -> fast-glob -> micromatch -> braces@3.0.3`. As of this verification,
3.0.3 is the newest `braces` release and no patched release exists. This is an accepted,
bounded tooling risk: the chain is development-only, receives repository-controlled lint
globs rather than user input, and is absent from the production dependency audit. Do not
apply npm's suggested forced downgrade to `eslint-config-next@14`; monitor for a patched
upstream release instead.
