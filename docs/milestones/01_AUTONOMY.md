# Milestone 01 — Make Mica Genuinely Autonomous

**Status:** Implemented, tested but not fully confirmed

**Authority:** `docs/MICA_TARGET.md`  
**Development inference:** Existing Azure model provider  
**Objective:** Turn Mica's existing features into one reliable, event/schedule-driven loop that carries intentions from conversation to authorized follow-through.

**Owner status decision:** implementation and recorded tests are acknowledged; full real-world
confirmation and milestone acceptance remain pending. Milestone 2 has not started. See
`docs/IMPLEMENTATION_STATUS.md` for deployed evidence and the remaining confirmation gate.

**Owner-directed priority update:** Nebius Token Factory and Hermes Agent integration planning
is being brought forward from the infrastructure roadmap while this status remains open. This
supersedes the earlier blanket deferral of those two integrations below; it does not mark this
milestone accepted or start the Milestone 2 companion-experience scope. Azure remains the tested
baseline. Integration design, implementation and evidence must be recorded separately from the
existing Azure acceptance results.

## 0. Your assignment

You are the coding agent responsible for **implementing** this milestone, not proposing competing architectural approaches. Inspect the repository first; then modify the application, migrations, workers, frontend as needed, and tests until the behavior below is verified. Preserve useful existing functionality and avoid unrelated redesign.

**Definition of success in one sentence:** A user expresses a goal/commitment in ordinary chat; Mica records the right actionable state, initiates an appropriate unattended follow-up at the right time, updates that state when the user corrects or completes it, and survives restarts and retries without inventing or duplicating outcomes.

### Explicitly out of scope

- Switching development inference to Nebius/Nemotron. Avoid spending Nebius credits.
- Adding Hermes or Letta now without a demonstrated milestone-critical need.
- Replacing the entire existing agent architecture; writing an unrestricted general agent.
- Building a full enterprise goal planner, elaborate knowledge graph, broad computer-use/browser integration or multi-agent orchestration.
- Public multi-user release. Existing auth is reportedly single-owner and must stay private.
- Unprompted external WhatsApp/email actions beyond already authorized responsibility/channel workflows.
- Cosmetic redesign, new pet animation or feature-sprawl in tutoring and vocabulary.

If a requirement cannot be met without a significant design decision, choose the simplest safe integration consistent with the existing stack; document the tradeoff. Escalate only genuinely irreversible, unsafe or credential-blocked choices.

## 1. Verify the actual code first (short audit, then implement)

The prior implementation report is **provisional**. Confirm or correct these claims, identifying concrete modules and tests:

| Reported area | What to inspect |
|---|---|
| Next.js app (`Chat`, `Today`, `Threads`, `History`) | Frontend routes, API client, current branch/runtime deployed state |
| FastAPI `AgentRuntime` + Azure | Entry point, tool registry, context builder, prompt construction, auth boundary |
| PostgreSQL threads / commitments / provenance | Models, migrations, updates, timezone fields, data ownership |
| `backend/app/prospective.py` deadline parser | Supported date phrasing, error cases, validation and normalization |
| Deterministic morning/evening skills | Existing event handlers, preferences, ranking, journal/reflection persistence |
| Responsibility worker/outbox/WhatsApp bridge | Wake mechanism, due scans, locks, retries, idempotency, channels, failures |
| Personality/assistance split across branches | Which version runs, how prompts are assembled, regression risks |
| Single-owner authentication | Don't mistake testing usernames for secure multi-user identities |

Write a compact verified baseline into `docs/IMPLEMENTATION_STATUS.md`, with code references. **Do not stop at the audit** unless the repository or execution environment is actually unavailable.

## 2. Required behavior

### A. Close the conversation-to-state loop

Implement or repair backend-validated conversational operations to:

- Create and retrieve a goal/commitment associated with a thread or project when appropriate.
- Update its next action, deadline, importance, constraints, availability, blocker and follow-up preference, as supported by the existing schema.
- Mark it completed; pause, resume or cancel it; and revise/replan it after circumstances change.
- Distinguish a **discussion** from a **durable commitment**. Ask a concise clarification before persisting consequential ambiguous intentions or scheduling an unexpected intervention; honor existing tool/write permissions.
- Resolve ordinary language such as **“before 9pm tomorrow”** and **“next Friday afternoon”** against the user's configured timezone and a test-injected clock. When temporal meaning remains ambiguous, request clarification; don't persist a guessed precise instant.
- Make explicit statements such as **“I finished preparing the slides”** update the correct existing commitment after referent resolution (or briefly disambiguate).
- Create an auditable provenance trail for new facts and corrections; never silently rewrite the user's original purpose.

Reuse current Thread and Commitment models where possible. A large general goal graph is not required. If a tiny addition (e.g., intention summary, completion criteria, timezone, next-check metadata) is essential, add a backwards-compatible migration and tests.

**State invariants:**

- The database, not a model-generated summary, determines current status and due work.
- Completed/cancelled items must not generate fresh follow-ups.
- Editing a date or plan invalidates obsolete due work.
- The last accepted correction supersedes previous timing/constraints, retaining source evidence.
- LLM tool parameters must pass schema, ownership, permission and state-transition checks.

### B. Close the scheduler-to-action loop

Use the existing persisted worker/outbox patterns (or a minimal extension) to execute a durable, restart-safe loop:

```text
Schedule or relevant event
  → read due work and authoritative state
  → evaluate should-act policy (including permissions, quiet hours, status, frequency)
  → choose bounded action, with LLM if judgment is needed
  → perform authorized action or deliberately skip
  → persist decision, delivery evidence or failure, and state changes
  → persist next wake-up / no-next-action
```

Requirements:

- **Unattended:** Works without an open browser/chat session, provided the deployed backend and worker are running.
- **Persistent:** Due items and schedules survive process restarts and deployment restarts.
- **Idempotent:** Duplicate worker invocations, retries, process crashes or overlapping workers must not cause duplicate user-visible effects. Use stable action keys, database constraints/leases and a durable outbox as appropriate.
- **Finite and accountable:** Bound model calls, retry attempts, message frequency and action scope; record why a check led to an action or no action.
- **Timezone-aware:** Respect stored user timezone (default only if the existing product has a documented default), daylight-saving behavior when relevant, preferences and quiet hours.
- **Failure-aware:** Separate pending, executing, succeeded, failed/retryable and permanently failed where appropriate. Do not mark an action completed merely when the model requested it.
- **Owner-controlled:** Existing user settings or simple APIs must allow pausing/cancelling future nudges and viewing current next check.

Use deterministic rules for simple deadlines and due scans. The system should **not** continuously call an LLM or run a hidden infinite reasoning loop.

### C. Activate existing personal routines

Wire stored morning briefing and evening reflection preferences to autonomous daily triggers using the same scheduling system, **only when enabled by the owner**. Deduplicate per owner, routine and local date. Preserve existing content generation and journal behavior, improving only what is required to keep them consistent with current commitments and urgency.

If an actual outbound channel is not configured, create an **in-app activity/inbox record** visible on next login; do **not** claim a push notification or WhatsApp delivery happened. If a channel exists, only use it when authorized and capture a delivery attempt/result.

### D. Keep conversational identity and context coherent

- Resolve the reported frontend/backend branch mismatch so the app uses one coherent version of conversation, personality and tools.
- Feed the model relevant authoritative state: current goals, corrections, open commitments, prior interventions and latest outcomes; avoid flooding it with unrelated records.
- Preserve the intentional companion personality and existing creative Threads, journals, vocabulary, responsibilities and feedback paths.
- Never frame routine scheduling as an independent emotional desire by the companion. Natural curiosity is encouraged; made-up memory or action is not.

### E. Minimal inspection and manual controls

The owner and developer should be able to inspect at least:

- Current commitment/goal status, next action and next check time.
- History of autonomous wake-ups, decisions, tool/action attempts and verified outcomes.
- Whether an intervention was delivered, saved for in-app viewing, skipped or failed.
- The controls needed to pause/cancel follow-ups and correct a commitment.

Prefer extending existing Today/Threads/History surfaces and backend endpoints rather than adding a major dashboard. Logs must avoid secrets and unnecessarily exposing personal chat contents.

## 3. Interface and engineering guidance

These requirements define **behavior**, not a prescribed new framework. Follow established repository conventions and introduce the smallest abstractions required.

### Source-of-truth contract

- Operational facts, commitments, permission decisions, schedule, execution and outbox state live in PostgreSQL.
- Model prompts carry selected, provenance-aware context. They are not authoritative write stores.
- If using cached projections/context summaries, invalidate or refresh them on relevant writes.
- Add correlation IDs from conversational write → scheduler event → action attempt → outcome so an end-to-end trace can be reconstructed.

### Provider boundary

Retain the current Azure provider for all development and testing. Avoid broad refactoring, but ensure model calls go through a bounded, documented interface that could later accept another OpenAI-compatible provider. Do **not** implement Nemotron/Nebius integration in this milestone unless a separate explicit instruction supersedes this contract.

### Safety and permissions

- No external sends without owner/channel authorization; prefer in-app delivery for self-directed nudges when permissions are unclear.
- No implicit expansion from a narrowly authorized responsibility action to arbitrary messaging, browsing or account access.
- Avoid exposing one owner's private data to another. Do not assert multi-user support; current auth is reported to map production sessions to one owner.
- Store API keys in existing secret/env infrastructure; never log or commit secrets.
- For any user-controlled time/action input, validate server-side.
- Give the user a way to stop recurring work; cancellation must be enforced even if an older scheduled event later fires.

### Migration and rollback

Any schema or scheduler changes must use reversible or safely recoverable migrations, preserve existing data, and have a documented rollback/disable path. Do not modify deployed credentials or external communication integrations without necessary access and authorization.

## 4. Acceptance scenarios — executable, not aspirational

Build repeatable integration/E2E tests with a controlled clock and isolated database. At least one smoke test must exercise the actual configured app stack beyond unit mocks. Mock an external delivery provider to establish exactly-once **observable** delivery attempts, but separately label the test as mocked; test a real configured channel only when credentials/permission are available.

### S1 — Natural intention capture

**Given** a clean test user and the local clock fixed at Monday 2026-10-26, 10:00 Africa/Lagos,  
**when** the user says, “I need to finish my presentation before 9pm tomorrow. Help me stay on track,” and confirms tracking if needed,  
**then** Mica persists one appropriate commitment linked to the relevant thread (if applicable), an unambiguous due time of **2026-10-27 20:59 or a represented ‘before 21:00’ bound** in Africa/Lagos, the source utterance, and a scheduled next check. It communicates what was saved; do not round an exclusive bound to an unsupported exact timestamp. Verify retrieval from a fresh session.

### S2 — Ordinary-language updates and completion

**Given** an open commitment,  
**when** the user says, “Actually, the deadline moved to Thursday at 6pm,”  
**then** the authoritative due time changes to Thursday 2026-10-29 18:00 Africa/Lagos, old schedules no longer act, and correction provenance exists.  
**When** the user later says “I've finished the presentation,” **then** the correct commitment becomes completed, its future follow-ups stop, and a re-open path remains available if the user corrects that claim.

### S3 — True unattended action

**Given** the owner enabled check-ins and a tracked commitment has an authorized follow-up due,  
**when** the worker fires with no active user conversation/browser,  
**then** it evaluates state and creates exactly one owner-visible intervention in the configured delivery path (in-app or authorized channel), with an execution record, reason, attempt result and next check. A paused or cancelled commitment produces no intervention.

### S4 — Restart/retry/duplicate safety

**Given** an action becomes due,  
**when** the worker crashes after claiming or preparing it, restarts, and/or two worker instances process the same item,  
**then** there are no duplicate owner-visible effects, unfinished actions are safely reconciled or retried, and delivery statuses honestly reflect uncertainty. Test unique action IDs and failure injection at distinct stages. If exactly-once effects cannot be guaranteed for a provider, explicitly document the deduplication limits and choose safe at-most-once or reconciled semantics rather than making a false guarantee.

### S5 — Meaning survives a change of circumstances

**Given** a user goal with an evening study constraint,  
**when** the user later says, “Evenings are unavailable this week, but I still want to finish preparing for Friday,”  
**then** the system retains the goal, updates the active availability constraint, revises the next action/check, suppresses outdated reminders, and surfaces the changed plan without treating the original evening schedule as current.

### S6 — Daily routines actually recur

**Given** morning briefing and/or evening reflection is enabled with a configured local time,  
**when** the scheduled time arrives on two successive simulated days without new user messages,  
**then** the requested routine runs once per local day; its output includes current authoritative state; disabling the routine stops future delivery. If an outbound channel is unavailable, output remains in the in-app activity history and is not described as externally delivered.

### S7 — Permissions and non-actions

**Given** a request for an external message to a third party but no authority for that recipient/channel,  
**when** a scheduled action considers sending,  
**then** the action is blocked or sent for explicit approval, not sent automatically. Record this decision. Verify that merely seeing a WhatsApp bridge configured does not confer permission to message anyone.

### S8 — Regression and coherency

Existing chat, Threads/projects/ideas, journals/reflections, vocabulary, personality, feedback and any already authorized responsibilities still function after integration. The deployed frontend/backend agree on the same API/schema. Test migrating from existing records without loss.

### S9 — Observability and owner control

A developer can trace the originating utterance/structured change to scheduled check to decision to execution evidence; the owner can see the current status and next check, pause follow-ups, then resume without replaying cancelled work.

## 5. Required test coverage

At minimum, include:

- Unit tests for time parsing, inclusive/exclusive bounds, timezone conversion, ambiguous dates, status transitions and permission checks.
- Database integration tests for transactional state changes, stale-event cancellation, unique dedupe keys, worker leases/restarts and outbox outcomes.
- API/conversation tests for create, amend, complete, cancel, pause and disambiguate flows. Where model nondeterminism prevents a stable assertion, use deterministic tool-invocation fixtures plus a separate live-model smoke test.
- Scheduler tests with an injected clock; do not rely on real overnight waiting or `sleep()` for correctness.
- At least one application-level smoke test through the actual configured Azure path (or accurately report the credential blocker) and an actual running worker invocation.
- Regression tests preserving existing features and migration safety.

All tests should expose clear pass/fail criteria. A working UI click is not sufficient proof of persisted execution; a successful isolated unit test is not proof of the whole loop.

## 6. Execution protocol for the coding agent

1. **Inspect:** Read project guidance, app code, runtime branch, worker, DB and existing tests. Run a baseline test suite. Record verified findings.
2. **Select one implementation path:** Prefer existing app and worker patterns; add only the minimum primitives required. Write a brief implementation outline directly in the status file—not an architecture debate.
3. **Implement end-to-end:** Make one vertical slice work from conversational intent to persisted state to unattended due action to verified history; then extend to corrections, completion, routines and controls.
4. **Test and repair:** Run targeted tests continuously, full regressions before reporting, and failure-injection/restart scenarios.
5. **Prove:** Capture commands, relevant outputs, migration status, screenshots or trace references where useful, and precise paths/commit identifiers. Mark which tests used mocks and which used real services.
6. **Report:** Update `docs/IMPLEMENTATION_STATUS.md` with outcomes and remaining blockers. If some cases fail, continue repairing in this milestone; do not advance into the next one.

Do not perform destructive deployments, modify production data, send live third-party messages, publish the app or commit secrets to satisfy a test.

## 7. Completion gate

Milestone 1 is **ready for owner review** only when:

- [ ] S1–S3 pass end-to-end on the integrated app; no user input required at the time of a due follow-up.
- [ ] S4 restart/concurrency safety has explicit evidence and no duplicate externally visible effects in supported paths.
- [ ] S2/S5 correct state and old reminders are invalidated.
- [ ] S6 is scheduled, enabled/disabled and deduplicated per local day.
- [ ] S7 blocks unauthorized external actions.
- [ ] S8 regressions pass; branch/runtime discrepancies are resolved.
- [ ] S9 provides status, history and pause/cancel control.
- [ ] Current single-owner privacy is preserved; no new Nebius costs or unapproved external sends.
- [ ] Tests, limits and known defects are documented accurately in `docs/IMPLEMENTATION_STATUS.md`.

**Human acceptance:** The owner runs a short real-world trial of capture → unattended follow-up → correction → completion and approves this milestone. Only then start Milestone 2.

## 8. Final response contract

Return a compact completion report with:

1. **What is now possible** (observable behavior, not features listed in abstract).
2. **Tests and proof** (scenario identifiers, commands, results, whether external systems were mocked).
3. **Changes made** (major files/migrations, deployment configuration needed).
4. **Known failures and risks** (including permissions, time handling, delivery guarantees and auth limitations).
5. **Exact next action** to accept or correct Milestone 1.

Never write “all done” unless the acceptance gate is demonstrably met.
