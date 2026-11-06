# Implementation Status

## Owner-requested Azure provider restoration — November 5, 2026, 23:55 UTC

At the owner's request, switched the active Telegram runtime back to Azure GPT-5.4.
This was a provider-only change on the existing pinned `25f8959` release and schema `0014`;
the reliability candidate has **not** been promoted.

- Provider: `azure_openai`; deployment `edge-imci-gpt-5-4`.
- Actual deployed connectivity call returned `gpt-5.4-2026-03-05`.
- Active Modal app ID: `ap-Xpdsih9CiLibRuXhCLM2dP`; both worker heartbeats resumed.
- Profile: reasoning `none`, 1,200 output tokens, 15-second per-call limit.
- Acquired the bot's existing PostgreSQL advisory lock, verified no processing inputs or sending
  deliveries, stopped the owner app, replaced its runtime Secret and redeployed the pinned source.
- Database, owner identity, Telegram connection/generation/grants and quiet hours were preserved.
  The existing December 31 cutoff was retained byte-for-byte; no historical window was restored.
- The cloud worker delivered the service-update notice through the existing outbox:
  Telegram provider message **169**, delivery `f15dc688-99c3-4686-a757-08d22f118a12`.
- Private rollback/configuration and preflight/delivery evidence are under
  `.local/rollouts/owner-reliability/` (`owner-runtime-before-azure.json`,
  `azure-runtime-candidate.json`, `azure-restore-preflight.json`, `azure-restore-delivery.json`).
  No credentials are included in this report. The canary is stopped; the judge deployment was
  not changed. The optional local web/API provider configuration was not changed by this
  Telegram-only restoration.

The alternate canary model was `nvidia/nemotron-3-super-120b-a12b`, the text-only Nemotron 3
Super model, distinct from `nvidia/Nemotron-3.5-Super-VL`. Its responsive serving path did not
resolve all compound-request behavior. The latest candidate canary revision was `9c7fc22`;
additional batch-action work is uncommitted and still requires acceptance. Provider restoration
does not establish completion of the reliability mission or the broader autonomy milestone.

## Reliability and controlled owner release — November 5, 2026 (in progress)

The owner authorized diagnosis, implementation, commits, a controlled Telegram trial and
promotion after the trial passes. The isolated judge deployment is excluded from changes.

Verified baseline: continuity/intention work committed as `971c1d4` on
`feat/continuity-intentions`; **624 backend / 69 frontend** tests passed again, with Ruff,
mypy (44 modules), TypeScript and ESLint. The suspended correction stash remains retained.
The owner cloud runtime is still `25f8959`, schema `0014`, Nebius Super-VL, with healthy
Telegram/scheduler heartbeats and its existing December 31 cutoff. The judge's read-only
status reports `60bd905`, active, external messaging disabled.

Read-only owner-scoped diagnosis (private artifacts in `.local/rollouts/owner-reliability/`):
- Nine retained failed turns; the reported Nebius examples failed on the initial call with
  `invalid_response`, a 1,200-token cap, low reasoning, and no tool execution. Historical
  traces do not retain sufficient provider diagnostics to assert the exact finish reason.
- The Samuel commitment contains relative timing only in its title, recorded October 23;
  `due_at`, `deadline_hint` and `due_source_text` are null. It has no authorized monitoring.
  Its title must not be rendered as a current structured deadline.
- The product/submission completion was recorded on November 3. That unrelated change
  advanced the legacy global context reset. The conservative `0015` backfill would therefore
  suppress the earlier essay mention during rollout. No deletion tombstones, deleted memory
  rows or cleared-by-deletion traces exist for this owner; upgrade handling needs a guarded
  distinction between legacy corrections and actual forgetting.
- Only one Telegram bot credential is configured. A canary can use an isolated database and
  authenticated replay ingress with actual owner-DM delivery, without competing for the
  production bot's update cursor. Replayed inputs must be labeled synthetic; genuine owner
  Telegram conversations remain a separate acceptance observation.

Implementation sequence: improve bounded provider diagnostics; reproduce the owner's cases;
repair partial-effect/recovery and temporal/lifecycle gaps using existing messages, runs and
proposals; rehearse migrations and rollback; commit a tested release; deploy the controlled
canary; promote only after its gates pass; record deployed evidence and owner handoff.

Candidate verification: **634 backend tests passed in 165.26s; 70 frontend tests passed**;
Ruff, mypy (45 modules), TypeScript, ESLint and the Next.js production build passed.
New coverage includes rollback of a failing tool while preserving an earlier successful tool,
retained pending requests, source-linked retries without duplicate effects, three-intent handling,
historical title timing across dates/timezones, retrospective/idempotent completion and date-only
reminders refusing a guessed clock. Migration `0016` releases a legacy recall reset only with
positive matching correction/completion evidence and no durable deletion indicators; unknown or
forgotten histories keep the stricter boundary. Its upgrade/downgrade policy is regression-tested.

Fresh provider probes retained in the private rollout directory show contextual low/minimal
reasoning requests reaching the 15-second deadline, while disabling reasoning returned usable
responses for the greeting, follow-up, compound and relationship examples. One date request still
timed out. These observations do not retroactively establish the old `invalid_response` finish
reason. The compound replay produced **three native tool calls**, demonstrating why the former
two-call turn limit rejected otherwise interpretable work. The candidate permits four calls,
retains two inference calls and the existing wall-clock bounds, and records allowlisted finish,
token/reasoning counts, HTTP status and failure-stage metadata without reasoning text or secrets.

The controlled canary uses a separate database and does not poll Telegram updates. Its replay
ingress is explicitly synthetic; its Nebius calls, scheduler, outbox and labeled owner-DM delivery
are real. The candidate no-reasoning profile is subject to these deployed gates before promotion.

## Owner-trial incomplete-response incident — November 2, 2026

An owner-supplied Telegram screenshot showed an explicit November 7 reminder request and a later
ordinary greeting both receiving the generic incomplete-response fallback. A read-only,
owner-scoped inspection of the authoritative schema-`0014` database confirmed the corresponding
assistant runs at **2026-11-01 17:32:13 UTC** and **19:43:57 UTC**. Both failed on their first
inference call with `invalid_response`, executed zero tools and persisted no matching reminder
plan. The requested reminder therefore must not be represented as scheduled.

Two later owner turns at **2026-11-02 03:44 UTC** completed successfully, including one validated
workflow update. This rules out a continuous Telegram, database or worker outage, but does not by
itself establish provider reliability. The deployed `25f8959` gateway maps several invalid or
empty completion shapes to the same `invalid_response` code, so the retained trace cannot prove
the provider finish reason. The development branch now distinguishes output-limit and filtered
responses. Its retained real-provider attempts exhausted a 2,400-token allowance, while the
documented integrated trajectory passed with a bounded 4,096-token allowance; this makes the
owner trial's 1,200-token ceiling a leading explanation, not a confirmed historical cause.

No production data, model configuration, deployment, scheduler or external message was changed
during this diagnosis. The live reminder remains absent. A production correction still requires
an owner-authorized, backed-up rollout of a tested release/profile and a fresh channel-level
verification; the existing uncommitted schema-`0015` work was not deployed as an incident hotfix.

## Continuity and intention evidence — November 1, 2026

**Development status:** implemented and locally verified on `feat/continuity-intentions`, based
on `ea9b74c`; changes are uncommitted and undeployed. Milestone 1 remains **Implemented, tested
but not fully confirmed**. Full scope, limitations, reproduction and rollback:
[`CONTINUITY_INTENTIONS.md`](CONTINUITY_INTENTIONS.md).

### Reconciled baseline and incident findings

- Private owner runtime is the pinned `25f8959` release, schema `0014`; the separate judge
  runtime is `60bd905`, schema `0014`. Development `ea9b74c` includes the judge/Tavily source and
  documentation updates. The suspended corrections stash `ee097774a2ac1f0203fe5df4f89447eba5ed48b9`
  was inspected and selectively reimplemented; it is still retained.
- Read-only incident inspection established that the essay utterance **was persisted** despite
  an initial provider `invalid_response` and no tool executions. Later context contained only
  recent messages and saved records, so the model lacked the older mention. The historical trace
  does not establish that failure's provider finish reason.
- The unexplained activity acknowledgement corresponded to a **real reflection/journal write**.
  A generic receipt obscured the effect, and later context did not expose the persisted operation.
  Private original records remain in ignored `.local/rollouts/continuity-intentions/`.

### Implemented behavior

- Bounded, owner-scoped historical mentions and recent persisted-operation evidence; mentions are
  explicitly distinguished from saved commitments and completed actions. Corrections exclude linked
  obsolete sources; deletion advances a separate forgetting cutoff. The correction evaluation
  fixture now retains original-message provenance, matching a real corrected record.
- Structured natural confirmations, reflection explanations, absolute deadline projections and
  honest monitoring status. Technical IDs/versions remain in the inspector rather than final
  wording context. Model failure acknowledges that the user's message survived.
- Optional evidence annotations beside existing why/purpose/completion fields, plus reason,
  timing reason, consequences, dependency and change reason where supported. Owner quotes,
  inferred/derived/confirmed distinctions, revision history and stale-parent checks are retained.
  Reason-only changes preserve authorized cadence and existing due work timing.
- Compact motivation-aware context selection and briefings. Regression work caught and fixed
  both purpose-only retrieval missing the commitment and metadata crowding out meaningful text.
- Real inference exposed mismatched intention field schemas, ambiguous ID-in-reference handling,
  missing compound-call sequencing, and an unresolved cadence question after declining check-ins.
  Schemas now advertise supported fields; exact owned references retain version/isolation checks;
  pending cadence context names the decision and cancellation path.

### Verification and qualification

- **624 backend tests passed in 132.70s**, including PostgreSQL runtime/worker journeys, scripted
  Telegram replay, correction/forgetting, rejection, provenance, cadence and revision checks.
  `uv run ruff check app tests` and `uv run mypy app` passed (44 modules).
- **69 frontend tests** and TypeScript passed. No frontend source changes were needed.
- Two **PostgreSQL** `0014 → 0015 → 0014` cycles on a fresh isolated database preserved all legacy
  columns; the same loss-aware rehearsal passes on SQLite. Downgrade deliberately loses the new
  annotations/cutoff, not the original scalar fields.
- **Integrated live pass**, `.local/rollouts/nebius-acceptance/20261101T213559Z/results.json`:
  actual HTTP API, PostgreSQL `0015`, real `nvidia/Nemotron-3.5-Super-VL`, native tool calls,
  independent worker, API stop/restart and inspector verification. Failed input and four intervening
  messages were explicitly injected synthetic fixtures; subsequent interpretation was real Nebius.
  Verified older mention recall without a fabricated task; actual reflection write/explanation;
  offer → compound acceptance/read; declined check-ins closing the pending proposal; reason and
  next-step correction retaining the overall goal and old revision; exact November 7, 18:00 UTC
  deadline; and browser/API-independent one-time delivery with no duplicate on a repeat sweep.
- Passing profile: **low reasoning, 4,096-token ceiling, 15s/call, at most two calls/turn**.
  **13 actual calls**, 209,299 input / 8,240 output tokens, **$0.0702057** uncached estimate for
  this passing run only. Worker inference and Azure calls: **zero**. Reminder delivery lag:
  **3.3272s**; action `d5dbdeef-c54a-481f-b213-0738bc99d173`, one attempt, repeat sweep executed zero.
- Earlier attempts are retained, including `output_limit` at 2,400 tokens, disabled-reasoning
  missed actions, schema/reference failures, and overly strict harness wording checks. A proposed
  4,096 configuration was initially rejected by the existing cap before any inference; the
  development gateway now explicitly permits this bounded opt-in allowance and rejects 4,097.
  Defaults and deployed configurations were not changed. This is one successful integrated
  trajectory, **not a reliability percentage or proof of production acceptance**.

Remaining: successful compound replies can still duplicate confirmations/questions; conservative
saved-only choices can bypass asking for a cadence; retrieval remains lexical and bounded;
paraphrase/short-confirmation interpretation remains model-dependent. General adaptive Eren/Scribe
behavior and longitudinal owner acceptance remain outside this completed verification slice.
Private and judge deployments retain their existing code/configuration/schema; production rollout
requires its own backup, migration and owner-trial decision.

## Submission provenance clarification

The owner clarified that the original working repository was created for Mica itself, rather
than for an unrelated pre-existing application. GitHub reports its creation as September 30,
2026; the earliest recorded specification/implementation commits are also September 30, within
the August 26–October 30 eligibility period. The submission repository was created October 30.
Updated the public README and its source copy with this distinction, a dated development outline,
links to original commit history, and an explicit explanation of how hosted Token Factory
inference avoided GPU/model-server setup and accelerated integration. Corrected the accompanying
Devpost draft's ambiguous pre-existing-prototype wording. Documentation-only; `git diff --check`
is the relevant verification, with no application or deployment change.

## Final hackathon submission mission — October 30, 2026

**Final engineering handoff:** Gates A, B and C passed on the deployed judge service; Gate D's
public code/docs/testing/video-support package is prepared. Public repository:
**https://github.com/Nini0la/mica**, MIT license detected, main branch. Deployed public runtime
**`60bd9059234eb369f12bc15309982c704308d712`**, CI passed:
https://github.com/Nini0la/mica/actions/runs/41053817189. The development source is preserved on
`feat/functional-autonomy` (`191f32d`, then bounded-budget/security-fixture correction `51949cb`).

Final verification at 12:02 UTC confirmed public HTTPS, the exact Nebius/NVIDIA provider/model,
fresh-browser authentication, create/amend, source-bearing research commitment and browser-closed
reminder delivery. Action `b89b6819-af65-4a7c-84be-3545743f94e6` delivered once; Tavily Search
`835b67d3-a1f6-49fa-a2e1-c64d85469510` and Extract `bb4458ab-4dae-4a30-8cba-83575eaa0f6f`
were genuine runtime calls. Final dataset is `mica_judge_submission`; engineering data is retained
in `mica_judge_demo`. Private table reads remain denied to the restricted judge role. Live origin,
CSRF, unauthenticated access and external-action blocking checks passed.

At 12:16 UTC, the final `60bd905` deployment additionally passed a fresh-browser check showing
`nebius` and the exact NVIDIA model in the existing Context Inspector. This change added a
provider label to the previously verified backend-identical `a10ecc6` release. Provider/model,
cutoff, scheduler heartbeat and disabled external messaging were reconfirmed from live health.

**604 backend tests**, **69 frontend tests**, lint/type checks, audit, static build and public CI
passed. The final judge profile uses a bounded **2,400-token** Nebius output allowance: a verified
research tool-selection turn used 1,402 output tokens, exceeding the earlier 1,200 ceiling. The
15-second call deadline and two-call/turn limit remain. The private owner trial stays on its
previous pinned release/configuration and was checked healthy at 12:01 UTC.

Publication used an allowlisted clean snapshot (169 audited source/doc files plus a source manifest),
excluding private environments, rollout/financial records, original specification ZIP and unrelated
product materials/history. Exact configured-secret comparison found no matches. GitHub initially
flagged synthetic Stripe/Slack credential-detection fixtures; these were assembled at runtime,
their 11 security tests passed, and a new clean root commit was published without bypassing push
protection, amending the rejected snapshot or force-pushing. The rejected local snapshot is retained.

Judge credentials and full browser/security reports are in ignored `.local/rollouts/judge-demo/`.
Public handoff material is in `docs/submission/` and at the public repository root. **Video recording,
public YouTube upload and final Devpost submission remain the owner's outstanding actions.**

Official rules verified at https://nebiusglobalaihackathon.devpost.com/rules:
deadline **18:00 WAT / 17:00 UTC October 30**; judging ends **December 23, 20:00 UTC**.
The current mission is the owner's explicitly authorized isolated public judge demonstration
and submission package, not a Milestone 2 expansion or owner acceptance of Milestone 1.

### Preservation and gate status

- Suspended conversational-quality changes are preserved in stash
  **`ee097774a2ac1f0203fe5df4f89447eba5ed48b9`**, including the new untracked regression test in
  its third-parent tree. No verified runtime feature was discarded. The judge work started from
  the deployed/verified `25f8959` baseline. Completed acceptance harnesses and prior uncommitted
  deployment evidence are retained. Deferred scope is in `docs/submission/POST_SUBMISSION_BACKLOG.md`.
- **Gate A passed:** real Nemotron conversation, model-selected commitment creation/amendment,
  persisted reminder and browser-independent worker delivery. Actual provider/model identity is
  in the existing trace; no Azure fallback is used by the judge instance.
- **Gate B passed:** deployed same-origin HTTPS static Next.js + FastAPI on Modal at
  https://nini-adegboyega--mica-demo.us-east.modal.run. Fresh Chromium login, context, create/amend,
  reminder, 65-second browser closure and fresh-session delivery inspection passed. Restricted
  `mica_judge` database role was denied private-table access with SQLSTATE `42501`. No personal
  Telegram credentials/links or unrestricted external actions are attached.
- **Gate C passed:** real Tavily Search/Extract through `research_goal` from the deployed Mica
  runtime, context-influenced query, original source links, explicit unknowns, then a model-created
  commitment retaining the chosen source and verification next action. Detailed request IDs and
  caveats are in `docs/submission/EVIDENCE.md`. An initial missing runtime `httpx` dependency and
  overly long/mixed-source synthesis were corrected; evidence-only synthesis excludes old research
  replies and preserves the same NVIDIA model/provider.
- **Gate D package prepared:** MIT license, curated public README, setup/deployment/recovery, judge
  instructions, official rules, Devpost text and a 2:50 video sequence are prepared under
  `docs/submission/`. A clean public source snapshot was audited to exclude personal rollout
  artifacts, billing records, credentials and the original specification ZIP.

**Checks:** 603 backend tests passed in 123.87s, Ruff/mypy passed (41 modules); 69 frontend tests,
ESLint, TypeScript, dependency audit and static production build passed. Live browser evidence is
retained privately under `.local/rollouts/judge-demo/` (`gate-b-results.json`, `gate-c-results.json`,
screenshots). The engineering database is preserved; `mica_judge_submission` has been provisioned
with a fresh synthetic seed for final publication. One scheduler per active judge deployment;
private owner deployment remains independent on Nemotron with its December 31 cutoff.

The owner still must record/upload the public YouTube video and submit Devpost. Neither task
has been represented as complete. Final public revision, health and handoff follow below.

## Owner-authorized cutoff extended to December 31 — 2026-10-30

At the owner's explicit request, extended the active trial cutoff to
**December 31, 2026 at 09:54:34 UTC**, retaining the existing time of day and original
October 28 start. Updated both the end and explicit authorization bound in the private window
Secret, then stopped/redeployed the same pinned Nemotron release to refresh the containers.

- Active app: **`ap-UiUS2EBdamKGyGCdV92nUI`**, `mica-owner-trial`.
- Revision: `25f89598e9a7ed0e4afbe8a509968688f20da81f`, schema `0014`.
- Cloud inspection confirmed `active=true`, end `2026-12-31T09:54:34+00:00`, provider `nebius`,
  model `nvidia/Nemotron-3.5-Super-VL`, owner present and Telegram linked.
- Direct guard checks passed: active one second before the new cutoff, inactive at the cutoff
  and afterward. This was a timing-configuration update; no application source change or migration.
- Previous app `ap-DKr0Mueb5LthiJdkrrD21n` is stopped. The old timing configuration is retained
  privately at `.local/rollouts/modal-trial/window-before-dec31.json`.

The expiry checker continues to stop this Modal app at the configured end. Historical November 3
dates and window hashes below describe prior authorizations and must not be used to undo this
extension during a provider rollback.

## Live owner trial switched to Nemotron — 2026-10-30 08:57 UTC

At the owner's explicit request to try the Nemotron experience, switched the cloud Telegram
runtime and optional local web/API to **Nebius Token Factory / `nvidia/Nemotron-3.5-Super-VL`**.
The active settings are reasoning **low**, output cap **1,200**, timeout **15 seconds** and
uncached cost estimates **$0.30/M input / $0.90/M output**. There is no automatic Azure fallback.

- **Pinned deployed revision:** `25f89598e9a7ed0e4afbe8a509968688f20da81f` (runtime `8e25def`).
  Local release: `.local/releases/nebius-owner-trial/`; frontend rebuilt successfully.
- **Active Modal app:** `ap-DKr0Mueb5LthiJdkrrD21n` (`mica-owner-trial`). Previous Azure app
  `ap-5vkZd5oyjoX90MIqXLnosu` is stopped. Fresh containers loaded the new runtime Secret.
- Authenticated cloud inspection confirmed `provider=nebius`, the exact configured model, schema
  `0014`, owner present/Telegram linked and advancing Telegram/scheduler heartbeats. A real call
  from the deployed image returned **`nvidia/Nemotron-3.5-Super-VL`**; bot identity/webhook and
  database checks passed. At 09:00 UTC, delivery counts remained 28 sent with no reported
  failed/uncertain state. No artificial owner Telegram input was injected.
- The cloud runtime Secret contains only the selected Nebius inference credentials; Azure keys
  are absent. Root `.env` selects Nebius and retains Azure configuration for manual rollback.
- **Trial end unchanged:** November 3, 2026, 09:54:34 UTC. Window-file SHA-256 before/after:
  `25bfd607e298a8d2d55208806d7a9b74814c7e6892cff3fe86fe623b56fde23f`.
- This was a configuration/release change, with no schema migration. Existing Telegram identity,
  link generation, write/proactive permissions and proactive-since timestamp were verified
  unchanged. Local authenticated API/continuations and frontend HTTP checks passed.
  Local background workers remain disabled; WhatsApp remains disabled.

Private rollback/evidence: `.local/rollouts/nebius-cutover/` contains `pre-nebius.env`,
`azure-runtime-secret.json`, the original window, original LaunchAgent plists, link snapshot,
`configuration-results.json` and `verification-results.json`. To revert, stop this cloud app,
restore the selected Azure runtime settings and local environment from those private backups,
then redeploy/restart the corresponding pinned services. Keep Neon and the existing window;
no database downgrade or history replacement is needed.

**Owner action:** send a new message to the existing `@QwenErringBot` chat. No relinking/reset is
needed. New Telegram turns now select Nemotron; owner assessment of the experience remains open.
Milestone 1 remains **implemented, tested but not fully confirmed**.

## Requested three-interaction Nemotron proof — PASS (2026-10-30 08:22 UTC)

Ran real contextual conversation, model-generated commitment creation, and a 30-second reminder
through the actual Mica HTTP app, fresh local PostgreSQL and a separate real scheduler process.
Exact requested/returned model: **`nvidia/Nemotron-3.5-Super-VL`**, provider **Nebius Token Factory**.
The reminder was delivered to **in-app chat** with the API stopped, 3.877 seconds after its due
instant. The subsequent worker sweep produced no duplicate. The API was restarted to verify
the persisted delivery in the existing inspector.

Four model calls (one context-setting turn plus the three requested interactions) used **49,854
input tokens and 1,282 output tokens**. Authenticated model metadata supplied rates of $0.30/M
input and $0.90/M output; the **uncached list-price estimate is $0.01611**, not an invoice debit.
Model-call latencies: **2.199, 3.031, 2.604 and 2.732 seconds**.

Provider traces and an opt-in subprocess network audit confirm **four Nebius inference requests,
zero Azure requests and zero worker inference calls**. Azure configuration was absent from the
test processes; the worker had no model credentials and external connections were blocked.
No production data or provider configuration was changed. This is real inference/application
execution with synthetic test inputs; it does not claim production Telegram delivery.

Full receipts, exact IDs, cost source, reproducible commands and private artifact references:
[NEBIUS_ACCEPTANCE.md](NEBIUS_ACCEPTANCE.md). Acceptance harness:
`backend/tests/live_nebius_acceptance.py`. Actual run, Ruff, mypy and diff whitespace checks passed.
Milestone 1 remains **implemented, tested but not fully confirmed**. The owner trial still used
Azure at the time of this isolated proof; the later live cutover is recorded above.

## Nebius/Nemotron integration — implemented and live-tested in isolation (2026-10-30)

**Published implementation:** `8e25def6f541af6274fc395a8e6fc585e97bd702` on
`feat/functional-autonomy`. GitHub CI passed for backend and frontend, including dependency
audits, lint/type checks and the frontend build:
https://github.com/Nini0la/fpc-pet/actions/runs/40995602852.

The owner prioritized Nebius Token Factory + NVIDIA Nemotron after requesting publication of
the pending state. That documentation was committed/pushed as `442cb0f`. **Milestone 1 remains
implemented, tested but not fully confirmed; Milestone 2 has not started.** Hermes follows as a
separate runtime-integration workstream.

### Implemented integration

- `PROVIDER=nebius` selects the existing gateway, shared conversational runtime, domain tools,
  PostgreSQL persistence, scheduler and trace machinery. No model download, GPU, schema migration
  or second runtime is introduced.
- Explicit `NEBIUS_API_KEY`/`NEBIUS_MODEL` configuration, official endpoint default, isolated
  reasoning/price settings, bearer auth, bounded requests and native tool calls. No credential,
  model or price fallback to Azure. `store=false` and `service_tier=default` are explicit.
- Nebius nullable tool-call responses are accepted; truncated/filtered or reasoning-only empty
  outputs are rejected. Local tool-schema definitions are inlined for nested-object visibility.
  Model output types and domain validation remain strict.
- `app.nebius_check` provides authenticated model discovery and a maximum two-call synthetic
  text/native-tool preflight. `tests/live_semantic_smoke.py` now supports both providers and saves
  separate, uniquely named private reports including model/token/latency evidence.
- Cloud preparation supports `refresh --provider nebius` (or `azure_openai` rollback), exports
  only the selected provider settings, and preserves the authorized trial window. Authenticated
  runtime inspection and response traces identify the provider/model.
- Actual transcript review found a correct persisted schedule accompanied by a stale predicted
  next-check time. Reminder acknowledgements now rely on backend-grounded schedule receipts;
  a regression test deliberately supplies a wrong model date and verifies it is not shown.

### Tests and real-service evidence

**585 backend tests passed in 183.59s** after the final reminder-wording fix; Ruff and mypy
passed (39 app modules). The new provider tests use a **fake model HTTP endpoint** with the real
subprocess transport, PostgreSQL/runtime, worker and duplicate-event checks. Cloud Secret preparation
is tested against temporary files, including unchanged window bytes and credential separation.
Frontend code was unchanged; frontend tests/build were rerun by the passing CI above rather than
repeated locally.

Credentials were initially absent, then authenticated discovery succeeded during this session.
The list included Lightning, Super-VL, Ultra and the retiring Nano/Super IDs. Both Lightning and
Super-VL passed the real two-call native-tool preflight. No operational tool was executed by that
preflight. The selected integrated candidate is:

```dotenv
PROVIDER=nebius
NEBIUS_MODEL=nvidia/Nemotron-3.5-Super-VL
NEBIUS_REASONING_EFFORT=low
MODEL_MAX_OUTPUT_TOKENS=1200
MODEL_TIMEOUT_SECONDS=15
```

Against the fresh local `mica_nebius_verified_smoke_test` database at schema `0014`, the real
Nebius API completed all six scenarios through the actual HTTP app, including two unrelated
turns and an API restart before proposal acceptance, retained missing-time clarification,
one-time/480-second recurring plans and two real worker sweeps producing exactly two due effects
with no duplicates. The exact punctuationless interruption also passed, with no vocabulary grading.
The 11 main turns plus one variant used **12 inference calls**, **154,967 input tokens** and
**4,421 output tokens** total. Main-run call latency ranged from **2.680 to 7.340 seconds**.
Prices were not configured, so dollar cost is **unknown**, not zero. These totals exclude earlier
candidate/debug runs and preflights.

Private successful reports:
- `.local/rollouts/semantic-integration/live-nebius-results-4120a2cc.json`
- `.local/rollouts/semantic-integration/live-nebius-variant-09a9240f.json`

The main functional smoke preceded the final grounded-confirmation change; its stale-time wording
is retained in that report. The targeted transport/application regression verifies the correction,
and the variant plus full regression suite ran on the final source. All live inputs were synthetic
in isolated local databases; channel credentials were blank. No production conversation was sent
to Nebius and no production Telegram send was used for this integration test.

### Failures retained and current limits

- Lightning initially stringified a nested time object; inlining schema references improved that
  case, but its next run attempted the wrong immediate update instead of staging the requested offer.
- Super-VL with reasoning disabled omitted the requested persistent vocabulary start. Low reasoning
  plus clearer activity/tool instructions progressed farther; subsequent failures exposed a string
  `"None"` and an omitted proposal `action` field. Explicit JSON/target-schema instructions addressed
  these without relaxing validation or inventing missing user details.
- One run stopped solely because an otherwise supportive response lacked `?`. The harness now
  retains wording for human review and checks nonempty output/no quiz pivot instead of punctuation;
  persistence, timing, proposal execution and duplicate-effect assertions remain intact.
- Failed private reports are retained as `live-nebius-results-026e3761.json`, `aea5b4a7.json`,
  `07f52608.json`, `48dcc181.json`, `01d37482.json`, and `e77ce8c8.json` (same full filename prefix).
  A passing run does not erase these failures or establish longitudinal reliability.

**Deployment state:** the owner trial remains on the previously deployed Azure revision `c4137ec`
with the November 3 cutoff. Nebius integration has not been activated in that trial. The next gate
is controlled deployment of the tested profile and owner-channel verification, with Azure retained
for rollback. Setup, model deprecation details and reproduction commands: [NEBIUS.md](NEBIUS.md).

## Owner-authorized Edge IMCI artifact cleanup — 2026-10-30 02:20–02:21 UTC

The owner explicitly authorized clearing the two previously inspected heavy artifact volumes.
Removed all contents while retaining the named volumes in environment `main`:

- `edge-imci-routing-matrix-v1-artifacts`: **280.052 GiB**, 44 root entries;
  fresh recursive listing verified zero entries at **02:20:08 UTC**.
- `edge-imci-finetune-artifacts`: **204.061 GiB**, 91 root entries;
  fresh recursive listing verified zero entries at **02:21:30 UTC**.

Combined with the earlier Foundry cleanup, approximately **1,494.394 GiB** of logical contents
were removed. The pre-cleanup inventory implies approximately **160.167 GiB** remains in other
volumes; this is an estimate from that inventory, not a fresh account-wide scan. Other volumes,
Mica, and Neon were not modified. External checkpoint copies were not inspected or changed.
The pre-deletion container inventory showed only Mica running. Billing reductions remain subject
to Modal's documented post-deletion delay and have not yet been verified.

## Owner-authorized Modal cache cleanup — 2026-10-30 02:08 UTC

The owner explicitly requested clearing `fpc-foundry-models`. Removed all 17 root entries
from that volume in environment `main`, including model caches, vLLM cache and lock/metadata
files. Pre-deletion metadata totaled **1,010.281 GiB**. A fresh recursive listing at
**02:08:31 UTC** returned **zero entries**; the empty named volume itself was retained.
The two Edge IMCI artifact volumes were not changed: their possible removal remains undecided.
Mica mounts no Modal persistent volume, and its deployment/database were not modified.
Billing reductions are not yet verified; Modal documents up to four days of post-deletion
storage billing. The earlier inventory and costs below are historical pre-cleanup evidence.

## Modal cost audit — read-only, 2026-10-30 approximately 01:34 UTC

Owner reported approximately $35 of monthly Modal usage. Queried authenticated
`modal billing summary --for 2026-10 --json`, resource-level app reports, current rates,
app/container inventory and volume metadata. The account summary attributed approximately
**$91.27 gross to volumes**, with **$56.49 free-storage adjustment**, leaving approximately
**$34.78 storage usage before credits**. Deployed-app compute was approximately **$0.72**;
the app report identified Mica deployments and their shutdown probe. Account credits applied
were approximately **$35.51** and the billing summary reported **$0.00 billed cost** at inspection.
This is a current API snapshot, not a final monthly invoice or a statement about remaining credits.

Mica's complete October 29 UTC compute usage was **$0.45697565**. At similar activity this is
roughly $0.46/day or $14 per 30 days, excluding separately billed Azure/Neon and changes in workload.
Mica uses no Modal persistent volumes or GPUs. The only running container at initial inspection
belonged to Mica; deployed older apps had zero containers, which does not eliminate storage costs.
Metadata inventory found 21 pre-Mica volumes created in August/September, totaling approximately
1,655 GiB of logical file sizes. Logical sizes identify cleanup candidates, not exact per-volume
billed bytes or historical charges. No files, apps, budgets or billing settings were changed.

Private reproducible report and helper: `.local/rollouts/modal-trial/billing-audit-20261030.json`
and `billing_audit.py`. The app report omits volume attribution; storage totals come from the
workspace summary. SDK daily reports omit the incomplete current day, so their app totals can
lag the current summary. Review retained model/artifact volumes before any cleanup; deleting a
volume requires a separate decision about preserving its contents. Modal documents up to four
days of continued storage billing after deletion. No application tests apply to this audit.

Follow-up metadata inspection at 01:44 UTC identified the largest volume (`fpc-foundry-models`)
as model-download cache layout plus vLLM cache: approximately 703.77 GiB under GLM-5.3,
155.44 GiB under DeepSeek-V4-Flash-0731, 89.47 GiB under Mistral-Small-3.2-24B, and smaller
Qwen/Granite/Phi caches. The two owner-selected Edge IMCI artifact volumes contain trained
outputs: routing has 44 top-level run directories and 618 checkpoint directories; finetuning
has 91 top-level directories and 150 checkpoint directories, with model/adapter weights,
optimizer state and evaluation files. Backup availability and deployed dependencies have not
been established for deletion. No deletion was performed. Detailed metadata-only evidence:
`.local/rollouts/modal-trial/large-volume-details-20261030.json`.

## Current milestone status and owner-directed next focus

**Milestone 1: Implemented, tested but not fully confirmed.** This is the owner's requested
status. The deployed implementation and recorded checks below stand; real-world confirmation
and owner acceptance remain open. **Milestone 2 has not started.**

The owner has requested bringing **Nebius Token Factory and Hermes Agent** forward from the
infrastructure roadmap. Repository review found an existing high-level direction in
`MICA_TARGET.md` §5: a swappable inference provider, NVIDIA Nemotron via Nebius, and evaluation
of Hermes as a runtime/execution component with explicit ownership boundaries. It did **not**
establish a detailed Hermes integration design or verified Nebius deployment.

Current implementation has a generic OpenAI-compatible gateway (`backend/app/gateway.py`) in
addition to Azure, but the cloud preparation path explicitly selects Azure. No Hermes runtime
integration or live Nebius validation is recorded. Those are starting points, not completed work.

Next integration planning should establish:

1. **Nebius inference:** verify the current endpoint, available model/tool-call capabilities and
   configuration against the existing gateway; define bounded live tests and compare the same
   conversational/autonomy scenarios with the Azure baseline.
2. **Hermes runtime:** inspect the intended Hermes Agent project's current APIs and execution model;
   decide which responsibility it owns within Mica. Specify tool access, conversation/context flow,
   persistence, restart behavior and tracing without competing schedulers or duplicate action owners.
3. **Integrated proof:** preserve Neon as operational authority and reuse validated Mica domain
   operations, permissions, action/outbox evidence and owner controls. Verify continuity, corrections,
   interruption/acceptance, unattended work and duplicate recovery before a runtime cutover.

These are planning requirements, not claims that either integration is implemented or deployed.
This status/documentation update changed no application behavior and required no application test run;
`git diff --check` is the documentation verification.

## Semantic release deployed; extended owner trial active — 2026-10-29

**Application revision:** `c4137ec503c5a6a3b75974c5a2e044b4e4088cd7`, pushed on
`feat/functional-autonomy` and deployed to Modal plus the optional local API/frontend.
**Schema:** `0014`. **Active Modal app:** `ap-5vkZd5oyjoX90MIqXLnosu` (`mica-owner-trial`).
**Authorized window:** original start **2026-10-28 11:54:34 UTC**, extended end
**2026-11-03 09:54:34 UTC**. The prior Modal app `ap-1yObYNST6QMQ207oajaSga` is stopped.

- GitHub CI passed for the deployed revision (backend, frontend, dependency checks and build):
  https://github.com/Nini0la/fpc-pet/actions/runs/40853857079.
  Local verification: **571 backend tests**, **69 frontend tests**, Ruff/mypy, frontend lint/type
  checks/build, eight rendered architecture diagrams and the real-Azure semantic smoke described below.
- Stopped cloud/local writers and took a fresh PostgreSQL 18 backup before migration:
  `.local/rollouts/semantic-integration/production-pre-0014.dump`, SHA-256
  `1993f059ae7d984a7f7e413afb65874ba490e9c6ff1532b16951b17e667f87e2`.
  Migration preserved all original columns of **316 pre-migration rows**, verified before writers
  restarted. Private manifest/results: `production-original-rows.json`, `cutover-results.json`.
- The first migration attempt timed out because the private verifier retained a read transaction
  that blocked DDL. It rolled back; verification confirmed original data unchanged. Switching the
  verifier to autocommit released those table locks, and the retry succeeded using the original
  preserved backup. This was a rollout-helper issue, not an application schema failure.
- Runtime and explicitly extended window Secrets were updated while the app was stopped, then
  fresh containers deployed. Authenticated cloud inspection confirmed the exact revision, schema,
  active owner link, new cutoff and advancing scheduler/Telegram heartbeats. A real Azure connectivity
  probe and Telegram identity/webhook checks passed inside the deployed image.
- Optional local API/frontend use the pinned release `.local/releases/semantic-owner-final/`.
  Both HTTP services and authenticated `/api/continuations` passed. The fallback worker/Telegram
  LaunchAgents also point to this release but remain **disabled** while Modal is active.
  WhatsApp remains disabled; no public endpoint or multi-user access was added.

### Actual deployed reminder delivery

A clearly labeled **synthetic authenticated API turn**, not a fabricated incoming Telegram update,
requested one reminder after 30 seconds. The deployed Azure path used one inference call; the
cloud worker independently executed and forwarded it through the existing owner Telegram link:

- Plan: `623215b3-2468-412e-8a99-33124f0eb5f7` — one-time, now completed.
- Scheduled action: `2a416394-0223-4c0f-848e-2cf918eb0a53` — succeeded, one attempt.
- Telegram delivery: `56facd56-7255-4990-9a9d-2baa6ba820de` — sent, one attempt,
  provider message **44**. This proves Telegram acceptance, not that the owner read it.
- No additional effect appeared after another worker sweep. The scheduled message's existing
  Context Inspector returned the action and provider evidence. The test initially queried the
  creation acknowledgement instead; correcting the read-only inspector target verified the already
  delivered message without sending another test reminder.
- Private evidence: `.local/rollouts/semantic-integration/live-rollout-results.json`.
  At 10:10 UTC inspection showed **17 sent deliveries**, current heartbeats and no reported failed
  or uncertain delivery states.

**Remaining human gate:** a new owner-sent Telegram conversation should exercise disclosure,
short recurring check-ins, interrupted proposal acceptance, and pause/cancel on this deployed
revision. Those semantic cases passed real Azure in isolation; the live deployed check above proves
outbound reminder delivery, not all incoming Telegram scenarios. Owner acceptance is pending;
the branch remains unmerged and Milestone 2 has not started.

## Owner-authorized publication and trial extension — 2026-10-29

The owner explicitly requested **commit, push and deploy**, and extended the trial to November 3.
Retaining the existing time of day, the authorized new cutoff is **2026-11-03 09:54:34 UTC**.
Deployment/application of the new cutoff completed as recorded above. The original
start remains 2026-10-28 11:54:34 UTC; the branch must remain unmerged.

`cloud_trial.window` retains the default 46-hour limit unless the private window configuration
contains an explicit `MICA_TRIAL_AUTHORIZED_END_AT`. The configured end cannot exceed that bound;
naive/malformed timestamps fail closed and the cutoff remains exclusive. `prepare_trial.py extend
--end-at ...` preserves the existing start and requires an explicit later timestamp. This is an
operator configuration change, not permission obtainable through conversation/tool arguments.
After this addition: **571 backend tests passed in 106.38s**, Ruff and mypy passed. Tests cover
the exact November 3 bound, missing authorization, invalid bounds and overrun rejection.

## Semantic conversation integration — pre-deployment verification (2026-10-29)

**Source at verification:** working-tree changes based on `84c710d`, subsequently released as `c4137ec`.
**Pre-deployment production:** read-only Modal inspection at approximately 04:49 UTC confirmed revision `8b8bb7b`,
schema `0013`, active owner link, current Telegram/scheduler heartbeats and 16 sent deliveries.
At that inspection, the trial still ended **2026-10-30 09:54:34 UTC**. The following results describe the new source,
not the old bot inspected at that time. Subsequent deployment evidence is recorded above;
full owner-channel semantic acceptance and owner approval remain pending.

### Implemented behavior

- The existing Azure conversational turn interprets live messages and chooses tools. Pending
  reflection/vocabulary records no longer consume arbitrary replies through ordered keyword gates.
  Ordinary conversation needs no tool call. Structured writes still require backend validation,
  owner scope, current permission, versions and domain preconditions.
- Migration `0014` adds durable proposals and separate one-time/recurring reminder plans, workflow
  state/version fields, original Telegram message timestamps and reminder-plan action references.
  Proposals retain parameters across clarification, unrelated conversation and process restart;
  execution, amendment, pause/resume and cancellation have persisted state and provenance.
- One-time reminders and finite recurring check-ins use the existing scheduler/action/outbox path.
  Structured times resolve against the source message timestamp and stored timezone. Rate limits,
  quiet hours, availability, cancellation and stale-action checks remain deterministic.
- Existing Today controls and Context Inspector expose plans, proposals, selected conversational
  state, tool receipts, state transitions and current action/Telegram delivery evidence.
- `deploy/prepare_trial.py refresh` prepares only the runtime Secret input. It leaves the existing
  trial-window file untouched, avoiding a new 46-hour authorization window during a code update.

### Verification on the current source

| Check | Result |
| --- | --- |
| `uv run ruff check app tests ../deploy` | Passed |
| `uv run mypy app` | Passed, 38 source files |
| `POSTGRES_TEST_URL=postgresql+psycopg:///mica_autonomy_test uv run pytest -q --tb=short` | **567 passed in 104.94s** |
| Frontend `npm run typecheck` and `npm run lint` | Passed |
| `npm test -- --maxWorkers=1 --testTimeout=30000` | **69 passed**, 12 files |
| Frontend `npm run build` | Passed, Next.js 16.4.3 |
| Current architecture diagrams | **8 parsed and rendered**, Mermaid 12.2.0; 17 source references checked |
| `git diff --check` | Passed |

The PostgreSQL regression suite includes proposal/plan permission and ownership checks, stale
versions, interruption/resumption, clarification timing, DST behavior, rate safeguards, claimed-action
pause/resume, older proposal lookup, duplicate events and crash-stage recovery. Automated Telegram
transport tests use fakes and do not establish delivery of the new implementation to the real bot.

**Fresh real-Azure run:** created and migrated the isolated local database
`mica_semantic_final_smoke_test`, then ran from `backend/`:

```sh
DATABASE_URL=postgresql+psycopg:///mica_semantic_final_smoke_test uv run alembic upgrade head
DATABASE_URL=postgresql+psycopg:///mica_semantic_final_smoke_test uv run python -m tests.live_semantic_smoke
DATABASE_URL=postgresql+psycopg:///mica_semantic_final_smoke_test MICA_VARIANT_ONLY=1 uv run python -m tests.live_semantic_smoke
```

The main harness requires a fresh database and refuses non-`*_smoke_test` targets. It starts an
actual HTTP API on loopback port 8014, uses Azure with synthetic test conversation and a controlled
clock, restarts the API, and invokes the real scheduler as a separate process. Telegram and WhatsApp
credentials are blank in the test process. All six acceptance cases passed:

1. “Not so great” received a natural follow-up without an unsolicited vocabulary answer capture.
2. Both punctuated and exact punctuationless “You’re not gonna ask how my day went” interrupted
   vocabulary naturally, with no grading/write tool call.
3. “Remind me to look for Pelumi Buari at 3pm.” saved a one-time reminder for the next 15:00
   Africa/Lagos occurrence (14:00 UTC) without requesting an unnecessary date.
4. “Could you pls remnd me to focus every 8min ?” saved a finite 480-second recurring plan.
5. An offered 15-minute alternative survived two unrelated turns and an API restart;
   “OK do that thanks” executed the stored proposal and updated the existing plan to 900 seconds.
6. “Remind me to stretch.” retained a clarification request; “15min from now” completed its
   timing from the clarification message. Two real worker sweeps created exactly two due effects
   total, with no duplicate on the second sweep and the one-time plan completed.

Each observed conversational turn used **one inference call**. Private reports are
`.local/rollouts/semantic-integration/live-azure-results.json` and `live-azure-variant.json`.
These are real Azure/application/worker results with synthetic inputs, not owner-sent Telegram turns.

### Migration and remaining rollout gate

A prior real-data rehearsal restored a PostgreSQL 18 dump into the separate hosted database
`mica_semantic_recovery`. Upgrade `0013 → 0014`, downgrade and re-upgrade preserved all original
columns of **316 original rows**. Private evidence: `precheck-0013.dump`,
`recovery-original-rows.json` and `rehearse.py` under `.local/rollouts/semantic-integration/`.
The working PostgreSQL 18 clients are in `.local/tools/pg18/bin/`.

This is preservation evidence for pre-existing data, not a lossless rollback of new features:
`0014` downgrade removes proposals, reminder plans and their scheduled actions/Telegram delivery
records, drops new workflow/timestamp fields, and clamps sub-15-minute legacy commitment cadence
back to 15 minutes. Back up the current authoritative database before any rollback.

Before production migration: quiesce writers, take a fresh PostgreSQL 18 backup and row manifest,
pin the verified application source, migrate Neon, deploy matching backend/worker/frontend,
and verify preservation, runtime identity and actual owner-channel behavior. Preserve the trial
cutoff and owner permissions. See [MODAL_TRIAL.md](MODAL_TRIAL.md#semantic-integration-update-procedure).
No merge, owner acceptance or Milestone 2 completion is implied by these checks.

## Conversation/autonomy architecture map — historical pre-integration audit

Inspected the actual `feat/functional-autonomy` repository at `84c710d` (application revision
`8b8bb7b`) and added [the baseline lifecycle map](architecture/CONVERSATION_AND_AUTONOMY_BASELINE.md). The map covers
normal web/Telegram messages, pending reflection/vocabulary workflows, model/tool execution,
clarification, autonomous scheduling, interruption/resumption, transport recovery and the separate
implemented-but-disabled delegated responsibility path. The original audit is retained separately;
`ARCHITECTURE.md` now links to the updated semantic map and identifies older descriptions as historical.

Verified architectural distinctions:

- Web and ordinary Telegram DMs share `AgentRuntime.handle`, domain logic, owner conversation and
  PostgreSQL state, but use different instances, permission sources and transaction/delivery wrappers.
- Live routing uses ordered conditions/regexes plus pending-row selection; `StateExtractor` is the
  no-gateway development path, not a universal live intent classifier. Pending skills read their
  own state instead of always going through the model context builder.
- No generic clarification continuation, workflow stack or checkpointed LLM program is implemented.
  Clarification answers are new turns. Pending domain rows, explicit commitment resume and crash
  recovery are distinct mechanisms with different eligibility and retry rules.
- Tool rejection/provider failure does not necessarily mean no earlier write committed. Event,
  model, workflow, in-app effect and external delivery statuses are separate evidence layers.
- Manual scheduled-event APIs, lifecycle controls, adapter commands and responsibility callbacks
  must not all be drawn as equivalent calls through AgentRuntime. The accepted `dormancy_scan`
  event currently has no work handler.

Validation: **12 Mermaid diagrams parsed and rendered with Mermaid 12.2.0 in headless Chromium**;
**58 local source/document references** and their line ranges checked; **12 explicitly named test
references** and the document's heading links checked. A sequence-diagram punctuation parse issue
was corrected before the final successful render. Rendered artifacts and the checker are retained
in the temporary `opencode/mica-architecture-check/` tooling directory, outside the repository.
No application tests were added or rerun for this documentation-only audit, and no live messages,
data mutations, service restarts or deployment changes were performed. Existing test sources and
the earlier recorded acceptance results are cited without representing them as new test runs.

## Initial 46-hour Modal trial — historical cutover, laptop-independent operation verified

**Deployed revision:** `8b8bb7b`. **Window:** 2026-10-28 11:54:34 UTC through
2026-10-30 09:54:34 UTC. Modal app `mica-owner-trial`, current ID `ap-1yObYNST6QMQ207oajaSga`.
Full evidence, controls, costs and recovery: [MODAL_TRIAL.md](MODAL_TRIAL.md).

- All **227 pre-cutover records** restored to Neon with exact original-field fingerprints.
  Hosted PostgreSQL is now authoritative; the frozen local DB and a custom dump are retained.
- Local background workers are stopped and disabled. Optional local API/frontend now use Neon,
  but Telegram/scheduling remain available with the Mac off. No public web/multi-user access was added.
- Actual cloud-generated morning briefing at **11:58:14 UTC**, accepted by Telegram as message **22**,
  while all local application services were stopped. Subsequent real owner DM/Azure reply succeeded
  at **12:08:49 UTC**; ongoing conversations also succeeded.
- Explicit cloud worker-container termination recovered automatically with persisted state/link/cursor.
  Post-restart status showed 9 accepted Telegram deliveries and no failed/uncertain delivery state.
- Automatic app shutdown tested independently; runtime model/send guards enforce the exact 46-hour
  cutoff. Shutdown leaves Neon data intact. WhatsApp remains disabled; the branch is unmerged.
- **545 backend tests**, lint/type checks and deployed-revision GitHub CI passed:
  https://github.com/Nini0la/fpc-pet/actions/runs/40682756247.

### Preparation record

The owner approved CPU-only Modal hosting plus hosted PostgreSQL so Telegram/autonomy can operate
with the Mac off for 46 hours. Existing Modal workspace authentication is available; the owner
provided a new direct SSL Neon connection in the ignored `.env`. Connectivity passed and the target
public schema was confirmed empty before the migration described above.

- Added a bounded, timezone-aware 46-hour authorization window, plus model/send guards after expiry.
  `deploy/modal_trial.py` reuses the current scheduler and Telegram runtime in one capped CPU worker
  with a separate expiry function. No public web endpoint or multi-user access is added.
- Expiry was tested on a disposable Modal app: it successfully stopped itself using the CLI and
  container identity. The first probe lacked CLI dependencies; installing the pinned Modal SDK
  resolved that. Probe app `ap-SNHPsvStC1DlG6paKzqR1l` is stopped; unrelated workspace apps were untouched.
- Runtime/credential and trial-window Secrets are separate. The expiry function receives only the
  window, not database/Azure/Telegram credentials. No workspace-wide budget or plan was changed.
- Requirements are exported from the existing lockfile. Guards fail closed on disabled, malformed,
  naive-time, premature or expired windows and reject durations longer than 46 hours.
- Verification: **545 backend tests passed in 90.53s**, Ruff and mypy passed (34 app modules).
  Cloud image, restored-data integrity, real cloud Azure/Telegram access, cutover and restart were
  subsequently verified as recorded above.

## Telegram owner-trial extension — deployed, linked and live DM replies verified

The owner explicitly requested Telegram access for the Milestone 1 trial. This remains owner-only;
no multi-user rollout, Discord adapter, WhatsApp send authorization or Milestone 2 work is included.
See [TELEGRAM.md](TELEGRAM.md) for linking, permissions, the short test checklist and rollback.

- Added `0013` with empty bot/link/inbox/outbox tables; original records are untouched.
- `app/telegram.py` reuses AgentRuntime and PostgreSQL transactions, with single-use linking,
  per-connection write/proactive grants, input deduplication, bounded retry, saved reply delivery,
  stale-action suppression and uncertain-send handling. `telegram_worker.py` uses a per-bot
  PostgreSQL advisory lock and outbound long polling. Tokens never enter safe error messages.
- Today → Telegram provides linking, permission/revocation controls and delivery evidence.
  Visible web Chat/Today now refresh to show external conversation updates.
- Real Telegram `getMe` succeeded for **@QwenErringBot**; no webhook was configured. No bot token
  was displayed or committed. No live DM was sent before owner linking.
- PostgreSQL/fake-transport acceptance: shared chat/tool writes, unattended forwarding, duplicate
  updates, private-only/owner-only linking, expiration/replacement/replay of codes, write-permission
  boundaries, completion/revocation/stop cancellation, quiet hours/stale checks, uncertain sends,
  explicit rate-limit retry and concurrent-worker exclusion all passed.
- Full regressions: **540 backend tests passed in 97.55s**, Ruff/mypy passed (33 app modules).
  **67 frontend tests passed**, with lint/type checks. Migration upgrade/downgrade preserves old
  records and personality settings. These automated Telegram deliveries use a fake transport;
  separate live account-linking and DM results are recorded below.

### Personal deployment — 2026-10-28

- Initial Telegram revision `81a1aeb`, followed by routing fix **`b2cf3c9`**, committed/pushed on
  `feat/functional-autonomy` and deployed from the clean `.local/releases/telegram-owner-final/`
  checkout. This supersedes the `acaa10c` runtime
  described in the earlier rollout record below; Milestone 1 owner acceptance is still pending.
- Personal DB is at **0013**. Its pre-upgrade custom dump was restored to `mica_telegram_recovery`;
  `0012 → 0013 → 0012` preserved all **207 original rows**. The actual upgrade also preserved every
  original row/field. Post-startup comparison ignores only the normal autonomy heartbeat timestamp.
- Backup/config artifacts: restricted, ignored `.local/rollouts/telegram-owner-trial/`.
  `mystery_pet-0012.dump` SHA-256:
  `4596b5a1d746150ee3d60e08348c7074c33c9ee18bb42c966e50e05a972756a0`.
- Matching API/frontend/personal worker are supervised alongside **`com.mica.telegram`**.
  Real long polling is active for @QwenErringBot, with a recent persisted heartbeat and no worker
  errors observed. The owner completed authenticated linking and granted memory/proactive delivery
  permissions. No other Telegram user is trusted. WhatsApp accounts remain disabled.
- Real mobile Chromium against the deployed app passed owner login, Telegram panel/bot identity,
  recent heartbeat, default-off permissions, enabled invitation control and no horizontal overflow
  or page errors. The browser check did not create or consume a linking code on the owner's behalf.
- Final production build passed. GitHub CI for the deployed revision passed:
  https://github.com/Nini0la/fpc-pet/actions/runs/40672129160.
- Rollback: stop the Telegram worker, point the other LaunchAgents back to the retained
  `.local/releases/m1-final/` (`acaa10c`) and restart them; the additive Telegram tables can remain
  to preserve evidence. See `TELEGRAM.md` for optional schema downgrade and the linking/test guide.

### Live linking and final routing check

- The owner linked their private Telegram account through the one-use invitation. Both memory
  updates and proactive Telegram delivery are explicitly enabled. The link survives worker/API
  restart and remains visible with its permissions in the web app.
- Real Telegram transport evidence: **two incoming messages processed successfully**, **two Azure
  contextual-assistance turns delivered**, and **four bot deliveries accepted by Telegram**
  (including connection/command acknowledgements). No failed/uncertain deliveries were present at
  verification. Real check-in arrival on Telegram remains part of the owner's leisure trial;
  automated scheduled forwarding, quiet-hour/cancellation and retry tests use fake transport.
- Fixed a shared-runtime edge case where a pending daily prompt could consume a greeting, question
  or explicit tracking request. These now reach normal contextual assistance. Three added regressions
  verify that the pending reflection stays awaiting and no spurious journal is created.
- Final regressions: **543 backend tests passed in 115.97s**, Ruff/mypy passed; **67 frontend tests**
  and the production build passed. Real mobile browser verification after the final restart confirms
  the linked account, granted permissions, worker heartbeat and valid layout.
- The owner asked about a possible 46-hour Modal deployment. Only pricing was researched; no Modal
  or hosted-PostgreSQL deployment was performed. The current service still depends on the Mac being
  awake and logged in. Cloud deployment would require moving the authoritative database as well as
  the workers; Azure inference remains separate usage.

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
