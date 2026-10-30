# Mica — Product Target and Execution Charter

**Status:** Product intent / governing specification  
**Scope:** Mica (Mystery Pet), the personal AI assistant application  
**Owner:** Product owner  
**Operating principle:** Realize one verified target state at a time. Prefer finishing the behavioral loop to accumulating partially connected features.

## 1. Mission

Build Mica into an **ongoing, personal AI companion** that can understand what its owner is trying to accomplish, preserve relevant meaning across conversations, and make authorized progress without waiting for a new chat message.

Mica is not merely a chat UI, a reminders app, or a collection of autonomous demos. It should combine:

- **Conversation and relationship:** Natural, curious, context-aware interaction. The companion should be approachable, interested, and capable of initiative without being intrusive, manipulative, or needlessly verbose.
- **Persistent context:** Remember ongoing threads, projects, creative ideas, goals, preferences, constraints, decisions, and changes that actually matter. Recover this context selectively, not by dumping the entire transcript into prompts.
- **Active accountability:** Carry commitments forward, notice due or stalled work, check in appropriately, and revise plans when circumstances change.
- **Bounded execution:** Use authorized tools and reusable skills to take real actions; record what happened and avoid doing more than the owner authorized.
- **Owner control:** Allow the owner to inspect, correct, pause, or discontinue Mica's activities and stored records.

**North-star behavior:** The owner can express an intention once, revise it naturally over time, and rely on Mica to maintain a faithful, inspectable thread from original purpose through execution and eventual completion or cancellation.

## 2. The intended experience

Mica should:

1. **Notice meaning:** Distinguish idle discussion from an intention the owner wants tracked. Ask briefly when recording or acting would be ambiguous.
2. **Remember without requiring reconstruction:** On return, recover relevant prior decisions, current state, blockers, and context with provenance.
3. **Act between conversations:** On an authorized trigger, check due work and perform a useful follow-up or bounded action without requiring the owner to open chat.
4. **Adapt instead of nagging:** If a schedule changes, update the plan, preserve the underlying goal where still valid, and cancel superseded tasks.
5. **Communicate honestly:** Distinguish plans, intended actions, attempted actions, and verified completed actions. Never claim an email, message, task, or other effect happened without evidence.
6. **Respect attention:** Prefer meaningful interventions to generic repetitive reminders; account for quiet hours, user availability, priority, and previous responses.
7. **Support creativity and learning:** Maintain threads for ideas, writing, exploration, vocabulary and tutoring rather than treating every discussion as a task.
8. **Maintain a companion identity:** Preserve existing personality work, including warm, genuinely curious, sometimes childlike exploration where desired; do not confuse affection with fabricated feelings or intrusive follow-ups.

A good interaction should feel like continuing a shared effort, not restarting a session with a helpful stranger.

## 3. Functional model

### 3.1 Durable intention

An intention may include these fields, whether stored in existing structures or a modest extension:

- **What** the owner wants; **why** it matters; expected outcome or completion condition.
- Relevant constraints, preferences, approved action scope and availability.
- Related thread/project; milestones or next action when appropriate.
- Due date/time and timezone, if applicable; follow-up preference or cadence.
- Status (such as active, waiting, blocked, completed, cancelled) and last known progress.
- Source/provenance: which utterance, tool result or confirmed edit led to the record.
- Corrections and superseded information, without silently treating old assumptions as current.

These are **semantic requirements**, not a mandate to add a large new domain schema. Reuse existing Threads, Commitments, journal, provenance and context-builder machinery if possible. Structured operational facts must have one authoritative representation.

### 3.2 The operational loop

```text
Relevant event / scheduled wake-up / user message
                    ↓
Observe current authoritative state and selected context
                    ↓
Interpret changes, urgency, blockers and permitted actions
                    ↓
Decide whether an intervention or tool action is justified
                    ↓
Execute an authorized, bounded action (or intentionally do nothing)
                    ↓
Verify effects, persist evidence, update state
                    ↓
Schedule the next appropriate check / await a new event
```

**Always-on means availability and continuing responsibility, not a continuously running model.** Prefer event triggers, persisted schedules, and inexpensive deterministic checks. Invoke an LLM when interpretation, planning or wording truly benefits from one.

### 3.3 Authority boundaries

- **PostgreSQL** remains authoritative for user identity, operational state, commitments, project/thread records, actions, outcomes, scheduler entries, permissions, and audit data.
- **Conversation history** is evidence and context, not by itself proof of a current commitment.
- **LLM outputs** are proposals or interpretations; backend validation enforces structured writes, permissions, identity, time and state transitions.
- **Memory/context components** may summarize or retrieve meaning, but may not silently override the current authoritative operational state.
- **External actions** require prior permission appropriate to the action and channel; idempotency and delivery evidence are essential.

## 4. Starting point — reported, not yet independently verified

The supplied code-review report describes a Next.js UI; FastAPI backend; PostgreSQL storage for conversations, threads, commitments, journals, feedback and provenance; an `AgentRuntime` with Azure model integration and tools; deterministic briefing, reflection and vocabulary skills; and a newer responsibility worker/outbox/WhatsApp path.

It also reports important gaps:

- No complete goal hierarchy or systematic replanning.
- Chat creation of commitments exists, but natural-language deadline parsing and general conversational completion are incomplete.
- Daily briefing/reflection preferences are not yet connected to autonomous scheduling.
- Existing branch mismatch between frontend/personality and running operational backend.
- Tool scope is narrow; the system is not generally authorized for arbitrary browser/email/calendar/computer actions.
- Authentication is effectively single-owner, despite user-scoped database structures.

**Agent instruction:** Inspect the live repository and tests before assuming any item above is still true. Report discrepancies and base implementation on verified code, not on this description alone.

## 5. Delivery milestones

### Milestone 1 — Functional autonomy (current mission)

**Status:** Implemented, tested but not fully confirmed. Full owner confirmation remains pending.

**Outcome:** Mica can capture an intention in ordinary conversation, preserve it durably, act on a scheduled/event trigger without a new user message, incorporate corrections and completion, and record verifiable results.

- Use the existing application, Azure inference, database, worker and tools wherever feasible.
- Consolidate runtime/branch discrepancies relevant to this end-to-end behavior.
- Close the commitment lifecycle, scheduled daily support and accountability loop.
- Ensure explicit authorization, safe retries, inspection, pause/cancel and outcome evidence.

**Done when:** The documented end-to-end scenarios in `docs/milestones/01_AUTONOMY.md` pass in the actual deployed stack, including restart, changed circumstances, and duplicate-trigger tests.

### Milestone 2 — Intended companion experience

**Outcome:** Mica's conversational experience consistently supports continuity, curiosity, creative threads, teaching/helpfulness and context-sensitive accountability.

Work includes: relevance of recall, quality of questions, correction handling, appropriate intervention timing, avoiding unsolicited overreach, and owner-facing inspection/control. Review UX with real conversation transcripts and executable scenarios. **Do not implement this whole milestone during Milestone 1** except where minimal UI/control is required for functional proof.

### Milestone 3 — Intended infrastructure and proven reliability

**Outcome:** A swappable, instrumented runtime supporting production-quality longitudinal evaluation and the intended model/agent infrastructure.

- Preserve Azure as the known-cost development model initially.
- Keep a clean inference provider boundary so NVIDIA Nemotron via Nebius Token Factory can be integrated and verified later.
- Evaluate Hermes as a runtime/execution component and Letta as a memory/context component against demonstrated gaps. Introduce them only with explicit ownership boundaries and regression evidence. They are possible infrastructure, not already committed substitutions.
- Measure reliability on repeatable long-horizon scenarios: retrieval, intent drift, tool completion, authorization, retries, schedule adherence, recovery, and user corrections.
- For the hackathon build, actually run and show at least one qualifying NVIDIA open model invocation on Nebius; an Azure-only final demonstration is not enough for that technology requirement. Confirm the current competition rules independently at submission.

The original progression is **functional autonomy → desired experience → infrastructure and measured reliability**. Evaluation begins in Milestone 1; sophisticated longitudinal evaluation matures in Milestone 3.

**Owner-directed sequencing update:** bring forward Nebius Token Factory and Hermes Agent
integration planning while Milestone 1 remains implemented, tested but not fully confirmed.
The owner's subsequent implementation priority is **Nebius Token Factory + NVIDIA Nemotron
first**; see `docs/NEBIUS.md`. Hermes runtime work follows separately.
Milestone 2 has not started. The original roadmap established provider/runtime direction, not
a completed integration design. Define and verify the provider and runtime boundaries against
the current application before changing the deployed path. PostgreSQL remains authoritative for
operational state, permissions and effects; Azure remains the verified comparison baseline.
This is a scoped exception to the earlier Nebius/Hermes deferral, not acceptance of Milestone 1
or authorization to implement the whole of Milestones 2–3.

## 6. Non-negotiable design principles

1. **Behavior first, technology second.** Do not introduce a platform merely because its features overlap with something Mica has already implemented.
2. **One integrated path.** No competing experimental architectures or parallel alternative builds during the active milestone. Multiple implementation tasks are fine if they serve one design.
3. **Reuse before replace.** Preserve working threads, journal, creative work, personality and existing operational responsibilities. Avoid needless migrations.
4. **Meaning outranks transcript volume.** Context selection must prioritize current, relevant intentions and their provenance.
5. **State is inspectable.** A developer and eventually the owner must see why an action was due, what Mica decided, whether it ran, and what changed.
6. **Safe by default.** No unauthorized sends, invented completions, duplicate effects, exposed secrets, or cross-user data access.
7. **Model-budget awareness.** Retain Azure as the verified baseline and deterministic checks for routine scheduling. The owner-directed Nebius integration permits bounded provider tests; record usage and results rather than running uncontrolled evaluations.
8. **No silent claims.** Tests and reports must distinguish implemented, unit-tested, integration-tested and manually observed behaviors.
9. **Own the lifecycle.** If Mica creates a commitment, it must be able to edit, complete, pause, cancel, and follow through on it.
10. **Maintain real user control.** Existing single-owner authentication must not be presented as multi-user security. Keep the app private until proper identity and isolation are implemented and verified.

## 7. Agent working agreement

- Inspect repository architecture, existing tests, execution entry points and branches before making changes.
- Use `docs/milestones/01_AUTONOMY.md` as the active work contract. Do not silently extend scope into Milestones 2–3.
- Implement, run tests, fix failures, and record reproducible evidence in `docs/IMPLEMENTATION_STATUS.md`.
- Prefer a cohesive implementation over architectural essays or extended option studies.
- Don't declare acceptance merely because code was generated or mocks pass. Confirm actual backend persistence, scheduler invocation, real or isolated fake channel delivery, UI/state visibility, and failure/restart behavior.
- Report blockers briefly, with the exact failing test or unavailable dependency and the narrow next action needed.

## 8. Definition of product progress

Progress is measured by **owner-observable behavior and verified system effects**, not counts of endpoints, tools, files, or model calls.

A milestone is complete when the target experience has been exercised, verified, and documented. Until then, continue correcting the same milestone rather than advancing to a new one.
