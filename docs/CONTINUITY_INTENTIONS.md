# Continuity, truthful effects and intention evidence

Development work, November 1, 2026. Branch `feat/continuity-intentions`, parent `ea9b74c`.
Milestone 1 remains **Implemented, tested but not fully confirmed**.

## Scope and boundaries

The resumed work follows this order:

1. Reconcile source, deployed releases and the suspended corrections stash; investigate actual
   recall and unexplained-activity incidents.
2. Repair conversation/effect evidence and consequential conversational corrections.
3. Extend existing intention fields with optional, source-bearing annotations.
4. Use that evidence in bounded accountability and daily routines; verify integrated behavior.

This uses the existing AgentRuntime, native tools, PostgreSQL, Context Builder, permissions,
version checks, scheduler, leases and outbox. A conversational mention does not itself authorize
creating a commitment. A saved commitment does not itself authorize an invented reminder cadence.
No additional agent framework, goal graph, automatic research or outside-app activity inference
was introduced. Existing goal-aware Tavily behavior remains available where configured.

### Source and deployment ledger

| Surface | Revision/schema at investigation | Role |
| --- | --- | --- |
| Development | parent `ea9b74c`; new local `0015` | Current uncommitted implementation |
| Private owner trial | `25f8959`, `0014` | Existing Telegram/web owner runtime |
| Separate judge service | `60bd905`, `0014` | Synthetic submission demonstration |
| Suspended stash | `ee097774a2ac1f0203fe5df4f89447eba5ed48b9` | Retained; selectively reimplemented |

The production incident investigation was read-only. Original personal inputs and full traces
remain in `.local/rollouts/continuity-intentions/production-incidents.json`, excluded from Git.
The live verification below uses fictional/synthetic data rather than replaying those records.

## What changed

### A. Recall and correction boundaries

`app/continuity.py` retrieves bounded owner-authored lexical matches from existing Message rows.
`app/context.py` selects at most two historical excerpts and two recent operation summaries,
alongside four recent messages, within the existing 12,000-character total context budget.
Each evidence section is capped at 2,500 characters. Historical source timestamps are retained.
No match means insufficient retrieved evidence, not proof the owner never mentioned something.

`context_reset_at` still excludes old recent turns after corrections. The new
`conversation_recall_after` independently bounds historical retrieval: unrelated corrections do
not erase all earlier mentions. Sources linked to corrected/deleted records are excluded from
historical matching. Deletion retains the existing conservative global forgetting behavior,
including clearing private captured traces and pending proposal contents. Migration backfills the
new cutoff from existing resets to preserve legacy privacy boundaries.

The existing correction evaluation fixture lacked original-message provenance. It now links the
old venue utterance to the corrected record, as actual capture/correction does. Tests continue to
assert that the old venue is absent; unrelated historical recall has its own positive regression.
Unlinked historical assertions are not proof of current facts; current authoritative records
override transcript evidence. Retrieval is lexical, English-token-oriented and bounded, not an
exhaustive semantic memory search.

Purpose, completion criteria, next action and intention metadata now participate in commitment
selection, including the final commitment query rather than only project-link discovery.
Optional diagnostics are compacted before they can crowd a goal out of its 1,500-character record
budget. Evidence basis remains attached to retained scalar fields; omitted detail is labeled and
full selected provenance remains in the manifest/inspector.

### B. What actually changed

Recent persisted AssistanceRun outcomes are resolved against currently owned records. Reflection
evidence identifies the activity, local date, current journal entry and saved text. A failed model
response does not imply that a prior successful tool write was rolled back.

`app/presentation.py` renders validated outcomes with natural names and timing, not UUID/version
receipts. Final wording inputs omit technical identifiers; the private inspector still records
the exact tool inputs/results. If a generated response exposes known identifiers, the application
renders the structured outcome instead of blindly deleting substrings. Reflection acknowledgements
name the actual operation and date. A no-op workflow start reports existing state.

Saved-only, scheduled, disabled, paused, closed, exhausted and unclear-deadline states are distinct.
Missing-cadence proposals retain the question and the fact that declining should close the
proposal while keeping the commitment. Short acceptance plus a read request is explicitly modeled
as two ordered native calls in one response; the second model call is for wording, not more tools.
Exact owner-scoped IDs in a generic reference field are accepted before title matching; provided
versions and foreign-owner rejection still apply.

### C. Existing fields plus optional evidence

| Existing authority | Optional annotation fields |
| --- | --- |
| Thread `why`, description, next action | `why` |
| Commitment title, `purpose`, `completion_criteria`, next action, constraints, availability, deadline | `purpose`, `completion_criteria`, `timing_reason`, `consequences`, `dependency`, `change_reason` |
| ReminderPlan topic and finite timing policy | `reason`, `timing_reason`, `consequences`, `change_reason` |

New `intention_context` JSON lives on those existing records. It records evidence basis, source
message/time, update time, field-value hash and supporting quote or linked project where relevant.
The actual scalar remains authoritative. Tools advertise only fields their validator supports.

- **User-stated:** verbatim reason and supporting quote occur in an owned user message. A wider
  quote may contain the exact reason; paraphrases must remain inferred.
- **Inferred:** a model interpretation tied to an owned source; never upgraded to an owner fact
  merely because it was stored.
- **Derived:** exact reason from the linked project, explicitly labeled. Changing that reason or
  removing/changing the relationship makes the projection stale.
- **Confirmed:** an explicit owner edit or a source-bearing confirmation of the unchanged prior
  value. Short confirmation interpretation remains the model's responsibility; the backend checks
  owned source, nonempty verbatim quote and unchanged prior value.
- Existing unattributed values stay **legacy_unattributed**; missing reasons stay unknown.

Commitment revisions retain prior scalar values and annotations. A new change does not silently
inherit the previous change reason; category labels such as obstacle or new priority are marked
as model interpretations. Existing ProvenanceLink records connect annotations to their evidence.
Simple reminders require no reason. Credential-like, foreign or forgotten sources cannot certify
a newly stated intention. Source validation establishes provenance, not independent truth or
semantic entailment of every model interpretation.

### D. Bounded follow-through

Reason-only edits preserve cadence, follow-up count and due time while invalidating stale-version
actions. Only explicit/confirmed reasons appear in deterministic check-ins and reminders, dated
so an old relative phrase is not misread as today's timing.

Morning briefing text uses compact ranked work, next actions, absolute deadlines and attributed
reasons/reflection where available. Existing diagnostic scores remain inspectable. Importance,
deadline pressure, blockers and intervention authorization remain separate; no extra escalation
or observation of off-app progress is inferred from inactivity. This is not a full adaptive
Eren/Scribe implementation.

## Verification

Run from `backend/` with an expendable local PostgreSQL test database:

```bash
POSTGRES_TEST_URL=postgresql+psycopg:///mica_autonomy_test uv run pytest -q --tb=short
uv run ruff check app tests
uv run mypy app
```

Final result: **624 passed in 132.70s**, Ruff passed, mypy passed for 44 modules.
Frontend: `npm test` (**69 passed**) and `npm run typecheck` passed.

Key regression files: `test_continuity_intentions.py`, `test_intention_evidence.py`,
`test_intention_migration.py`, `test_telegram.py`, `test_semantic_conversation.py`, and existing
context/assistance/evaluation tests. PostgreSQL effects, worker replay and ownership checks are
real; scripted model and Telegram transport tests are labeled as such.

### Loss-aware migration rehearsal

The ordinary suite runs the SQLite rehearsal. For PostgreSQL, use a **fresh empty local** database
whose name ends in `_smoke_test`:

```bash
createdb mica_intention_migration_fresh_smoke_test
DATABASE_URL=postgresql+psycopg:///mica_intention_migration_fresh_smoke_test uv run python tests/test_intention_migration.py
```

Observed on `mica_intention_migration_20261101_smoke_test`: two `0014 → 0015 → 0014` cycles,
all original columns unchanged, initial empty annotations and legacy cutoff backfill verified,
annotation loss on downgrade explicit. This used synthetic legacy data, not a production restore.

### Actual Nebius/API/worker journey

```bash
createdb mica_continuity_fresh_smoke_test
DATABASE_URL=postgresql+psycopg:///mica_continuity_fresh_smoke_test uv run alembic upgrade head
DATABASE_URL=postgresql+psycopg:///mica_continuity_fresh_smoke_test MICA_CONTINUITY_ACCEPTANCE=1 uv run python tests/live_nebius_acceptance.py
```

Credentials are read from ignored private configuration and only Nebius credentials reach the
loopback API. The worker has no model credentials and is network-guarded. Delivery is in-app;
no actual Telegram/WhatsApp sends occur. The initial failure and four interruptions are injected
fixtures; all subsequent conversation interpretation uses real Nebius calls.

Passing evidence: `.local/rollouts/nebius-acceptance/20261101T213559Z/results.json`, with companion
network audit. Database `mica_continuity_4096_v3_20261101_smoke_test`, schema `0015`.

| Check | Observed result |
| --- | --- |
| Failed input, interruption, recall | Original mention recovered outside recent window; no commitment fabricated; replay idempotent |
| Reflection and explanation | Journal persisted; later answer identified its activity, date and current content |
| Proposal plus compound acceptance/read | Pending offer persisted; one commitment created and read in the same turn |
| No cadence invented | Saved-only state and question; explicit decline closed pending proposal |
| Meaning survives correction | Corrected explicit reason with old revision retained; prototype completion advanced to video without closing the whole goal |
| Deadline | Persisted `2026-11-07T18:00:00+00:00` |
| Actual independent worker | API stopped, one reminder delivered; lag **3.3272s**, one attempt |
| Replay/restart | Repeat sweep executed zero; restarted API inspector showed succeeded action |
| Provider/network | **13 Nebius calls**, zero Azure calls, zero worker inference calls |

Model `nvidia/Nemotron-3.5-Super-VL`, reasoning `low`, ceiling **4,096 tokens**, 15s/call and
two calls/turn. Totals: **209,299 input**, **8,240 output**, **$0.0702057** estimated uncached
list price, not an invoice and not total experimentation cost. The gateway's default remains 600;
the larger allowance is an explicit configuration. Tests reject a Nebius ceiling above 4,096.

### Failed attempts are part of the evidence

All November 1 synthetic attempts remain under the same ignored acceptance directory. They
include low-reasoning `output_limit` at 2,400 tokens; disabled-reasoning missed proposal/acceptance
or workflow IDs; unsupported intention fields in proposals; an ID placed in the reference field;
and a declined cadence question remaining pending. These findings informed schema, context,
prompt and reference-resolution repairs. Two runs stopped on overly narrow harness wording
assertions despite valid mention recall; that check now verifies mention evidence and absence of
an actual commitment rather than requiring extra unsolicited wording. One run stopped because
4,096 exceeded the then-configured gateway ceiling, before inference; the explicit bounded
gateway allowance and its boundary test were subsequently updated.

The latest passing trajectory is not a statistical reliability claim. Some successful compound
answers still repeat their confirmation/question. A model can choose conservative saved-only
parameters instead of asking about cadence, or fail to preserve a perfectly isolated first step.
These are remaining quality/longitudinal acceptance issues, not hidden by the passing run.

## Rollout and rollback

`0015` is additive: optional recall cutoff plus non-null JSON annotations defaulting to `{}`.
It preserves existing scalar fields and does not backfill guesses about historical motivation.

For an owner-authorized release: take a fresh schema/data backup using the PostgreSQL 18 tools,
stop affected writers/workers, rehearse against an isolated restore, upgrade to `0015`, start the
matching code, verify owner controls and a bounded local/authorized-channel trajectory, then
resume the single scheduler. Select the tested inference allowance explicitly; the private
1,200-token configuration is not evidence of this new 4,096-token profile working in production.

Prefer a code rollback with additive columns retained. A schema downgrade removes annotations
and the separate recall cutoff. Export/back up first; original scalar reasons and operational
records remain, but annotation evidence cannot be recreated by re-upgrading. Original context
reset behavior remains in the old release. Do not restore a stale local database over Neon.

No deployment or production schema change was performed in this development verification.
The stable judge and private trial retain their respective releases and configuration. Owner
trial, conversational polish and longitudinal reliability remain explicit acceptance gates.
