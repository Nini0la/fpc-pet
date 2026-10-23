# Implementation Status

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
