# Adaptive Assistance Slice

**Provider update:** Azure OpenAI GPT-5.4 is now connected and live-verified with synthetic
project/idea capture, cross-session recall, correction and feedback flows. Configuration and
observed usage are in [AZURE_OPENAI.md](AZURE_OPENAI.md). Statements below about unavailable
credentials record the original implementation handoff; they no longer describe the local
provider setup. A comparative live evaluation and real-user quality study remain outstanding.

This is the first contextual creative workflow on top of Continuity, not the complete Mystery
Pet specification. No proprietary FPC or MindGauntlet code is included.

## Reconciliation

| Existing component | Reused responsibility | Extension | Trade-off |
| --- | --- | --- | --- |
| Thread | Ongoing subject and editable state | Project/idea kind, parent project, why, epistemic status, revisions | No parallel Project/Idea database; simple one-level project links |
| Commitment and urgency | Explicit intentions, timing, completion, explainable resurfacing | Authorized creation tool and association to a project | Existing deterministic timing parser; automatic delivery remains absent |
| Episode and JournalEntry | Experiences, decisions, verbatim reflection | Evidence in bounded context; invalidated journal-derived episodes after source correction/deletion | No broad semantic consolidation or contradiction detector |
| Message and AgentRuntime | Persistent interaction, ordered atomic pairs, replay safety | Bounded contextual skill with native tool calls | Conversation lock remains held during model calls |
| ProvenanceLink and CAS | Sources, confidence, safe corrections | Revision snapshots and current-version retrieval | Model summaries remain inferences unless grounded in exact user wording or confirmed by the user |
| AgentEvent and SkillRun | Audit ingress and execution | AssistanceRun, explicit feedback, evidence-backed GrowthEvent | These are outcomes/observations, not a learned psychological model |
| User | Tenant and preferences | Pet name, temperament and transient-context cutoff | Existing fixed-owner access-code authentication remains |

## What Works

With a configured tool-capable provider, a user can discuss an idea, explicitly permit its
capture, save a project and linked idea, return later, select that project or refer to it by
name, and ask for further help using current records. The user can inspect/correct those
records in Threads and inspect WHY/WHAT/HOW in Chat's companion panel.

Tools are `save_project`, `save_idea`, `update_thread`, `create_commitment`, and
`retrieve_context`. Saving a project and then a linked idea in separate messages is the
recommended walkthrough: the second turn has the real project ID. Native tool proposals are
validated with strict schemas, an allowlist, tenant ownership, retrieved/newly-created target
IDs, and expected versions. There is no SQL, arbitrary URL, external communication, deletion,
or recursive agent tool. No tools accept an authoritative user ID.

The per-message permission starts unchecked and resets after sending. Retries preserve both
the permission and event ID. In live mode, pending journal/vocabulary capture also requires
the permission; without it the pending capture remains unconsumed. Chat itself is always
persisted. Deterministic development mode preserves the shipped explicit-phrase extraction
and daily-loop behavior; this mode is not an LLM demo.

Each contextual response has an AssistanceRun recording evidence references, intervention
type, policy reason, tool outcomes and model usage. Provider failures produce an honest
persisted response, with completed actions listed separately. Retrying the same accepted event
does not invoke the provider or tools again; a new message is required for a new attempt.

Feedback is explicit: acknowledged, completed, helpful or unhelpful. Completed means
**user-reported outcome**, not a causal claim or automatic commitment completion. Missing
feedback remains unknown. An unhelpful verdict on the same context changes a later interaction
to `clarify_support`; it asks which form of help is wanted rather than repeating a suggestion.
The negative feedback remains available after that clarification, even if the next run is
unreviewed. This is a deterministic policy, not generalized learning.

Growth taxonomy separates understanding, judgement, capacity, relationship and human
empowerment. This slice emits only helpfulness-reported and outcome-reported milestones,
each referencing explicit feedback. It never emits demonstrated-improvement assessments or XP.

## Context and Privacy

Retrieval uses lexical word matching, current versions, project/idea/commitment associations,
recency, and relevant explicit feedback. No vectors or new retrieval infrastructure.

- Serialized context: at most 12,000 characters, 12 included records, and 1,500 characters per record.
- Candidate retrieval: bounded per source type; exact matches rank before SQL limits.
- Recent conversation: up to four messages, strictly after the latest memory-mutation cutoff.
- Diagnostics: IDs, versions, source references, inclusion/exclusion reasons and approximate size.
- No prompts, tool arguments, hidden reasoning or copied raw context in assistance diagnostics.

Important memory mutations advance `User.context_reset_at`. Older messages remain visible
in Chat but cannot be replayed into subsequent model context. This intentionally sacrifices
some short-term conversational detail after a correction. Migration initializes existing users'
cutoff so pre-upgrade erased facts cannot re-enter through recent transcripts. New users start
without a cutoff. Current structured records override recent conversation; old revisions are
inspectable but never retrieval candidates.

Thread deletion scrubs its text and revision snapshots. Journal correction/deletion invalidates
directly derived episodes. These controls do not erase the separately retained source chat,
database backups, or independent memories that happen to contain similar text. There is no
account export/deletion or arbitrary semantic erasure engine in this milestone.

All mutating API requests acquire the existing tenant conversation lock before reading or
changing memory. This serializes corrections/deletions against in-flight generation. After a
native correction, the second model call is rebuilt from current state, not the old prompt.
The original conversation idempotency and transaction-contiguous message ordering remain.

## Runtime and Cost

An ordinary contextual turn makes one model call. A tool-assisted turn makes at most two calls
and executes at most two tools. An explicit-feedback clarification makes zero model calls.
Output defaults to 600 tokens per call, configurable up to 1,200. Each provider call has a
maximum 15-second wall-clock deadline, enforced by a killable Python worker process, including
DNS and body reads. The operation checks a 35-second execution budget before further work.
HTTP redirects and automatic retries are disabled. Response bytes are bounded.

Worker credentials travel over stdin, never command arguments. Subprocess startup adds latency
but avoids non-cancellable network work holding a conversation transaction indefinitely. This
small prototype retains the database lock while waiting. An outbox/worker split with stale-context
validation is the next scalability step, not an implied property of this implementation.

Provider-reported input/output tokens, model ID and latency are recorded. Optional per-million
input/output prices produce estimated USD cost. Missing prices/usage are `null`, not zero.
Timeouts may have incurred provider cost even when usage is unavailable. A database failure
after an external call can roll back its local audit and a later retry can incur another charge;
external inference is not transactionally exactly-once. No subscriptions, billing, rate limiter
or per-user daily spending budget has been added.

## Run and Try

Use the root README's database/backend/frontend commands with the environment variables in
`.env.example`. Migrate to `0009`. For real conversation set `MODEL_MODE=live` and configure
`MODEL_BASE_URL`, `MODEL_API_KEY`, and `MODEL_NAME` on the backend. Never put a key in a
`NEXT_PUBLIC_*` variable. Missing live settings fail startup instead of silently using a stub.

1. Sign in with the configured private access code. Name the pet in Chat's companion panel.
2. Ask: "Save a project called Melody: a story about a musician losing melody recognition."
   Enable the per-message save permission before sending.
3. Select Melody as active context. Discuss the idea, then permit saving a specific linked idea.
4. Reload and ask to continue Melody. Inspect context references and server receipts.
5. Correct a detail in Threads, then ask again. Inspect the new version; old text should not
   be replayed from recent chat. Revision history is available at `/api/threads/{id}/revisions`.
6. Mark assistance unhelpful. Ask about the same project again and observe the clarification.
7. Report helpfulness/completion and inspect the evidence-linked milestone. It is not proof
   that the model improved or caused the outcome.

The existing Today controls invoke daily/reminder-capable runtime paths manually. This slice
does not install a scheduler. A saved commitment is not advertised as a delivered notification.
No background unsolicited intervention has been added, so quiet-hour handling is not fabricated.

## Verification and Evaluation

From `backend`:

```bash
uv run pytest -q
uv run ruff check app tests
uv run mypy app
uv run python -m app.evaluate
```

PostgreSQL tests recreate schema: use **only a disposable database**, never personal data.
Set `POSTGRES_TEST_URL` to enable migrations, concurrency and tenant-constraint tests. On slow
container storage, run `tests/test_migrations.py`, `tests/test_context_postgres.py`, and
`tests/test_postgres_quality.py` separately; repeated schema creation can take several minutes.

From `frontend`: `npm test -- --maxWorkers=1 --testTimeout=30000`, `npm run lint`,
`npm run typecheck`, `npm run build`, and `npm run audit:ci`.

`uv run python -m app.evaluate` performs offline retrieval checks over six synthetic histories.
`uv run python -m app.evaluate --live` explicitly sends those synthetic cases to the configured
provider. Both conditions use the same model/output budget, one call per scenario and no tools:
12 calls total. It records expected/forbidden string checks, source mentions, cost, latency and
answers for manual review. Correction evaluation includes the actual context-reset behavior.
These heuristics are not a scientific correctness or intervention-quality score; human review
is required. No live evaluation or benefit over the baseline is claimed without results.

### Recorded Validation

- Backend regression suite: 394 non-PostgreSQL tests, 31 PostgreSQL quality tests, and 18
  migration/context-locking tests passed in separate batches (443 total, no skipped tests).
- Frontend: 48 component/layout tests passed; ESLint, TypeScript and production build passed.
- Backend Ruff and mypy passed. Scoped audit: no production findings; the previously documented
  five development-tooling findings remain accepted, not resolved by this milestone.
- Real Chromium browser smoke at 1280x900 and 390x844 passed with the real FastAPI/PostgreSQL
  stack in deterministic mode: login, onboarding, pet rename/reload, idea capture, context
  inspection, immediate Threads refresh and usable mobile Send. No horizontal page overflow.
- Browser testing found and then verified fixes for mobile navigation covering Send, stale
  Threads after chat saves, and a loading request replacing an unsaved pet-name draft.
- No real provider credentials were available. Provider tests used scripted replies and a
  loopback HTTP server, including slow response/DNS deadline tests. No Safari/physical-iPhone
  behavior, live creative quality, or improvement over the baseline has been established.

## Deliberate Gaps and Next Experiments

No autonomous scheduler/delivery, public registration, data export/account erasure, broad
world-model consolidation, relationship graph, deep reasoning route, social bridge, computer
control, or paid progression. The complete accountability scenario is still partial.

Next: run real-provider/user evaluation; finish one reliable opt-in reminder delivery path;
then improve context/feedback policy from measured failures rather than adding more abilities.
