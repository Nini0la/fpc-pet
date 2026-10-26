# Operational Responsibility Management — First Milestone

Branch: `feat/operational-responsibilities`. The prior response-inspector work is preserved.
This milestone implements a bounded delegation workflow, not a general autonomous business agent.

## Reconciliation and Plan

| Existing capability | Reuse / extension |
| --- | --- |
| Commitments | Canonical task title, deadline and completion; one Responsibility adds assignee and follow-through policy |
| Persistent conversation and locking | Important outcomes/escalations enter the same chat with ordered, tenant-owned messages |
| AgentEvent and provenance | Responsibility events link to the existing audit; drafts retain their user-message source |
| Live model and authorized tools | `draft_responsibility` captures a plan, never grants permission to contact someone |
| Context retrieval | Relevant commitments include responsibility state, assignee, report and verification status |
| User authorization / corrections | Session and CSRF guards; current plan hash and row version bind approval |
| Background event foundation | A separate durable responsibility worker processes due rows without an open browser |

New components are four relational tables (ChannelAccount, Responsibility, ChannelMessage,
ResponsibilityEvent), a small deterministic workflow/worker, and a separately running Node bridge.
The core uses a `CommunicationChannel` interface and generic message/receipt envelopes. Baileys
JIDs, sockets, credentials and connection events exist only inside `whatsapp-bridge/`.

## State and Authorization

1. A user asks in Chat or uses **Today → Delegated responsibilities** to create a draft.
2. The draft records an expected outcome, named assignee, recipient address, timezone-aware
   deadline, requested evidence, follow-up interval and maximum follow-ups.
3. The user reviews the initial and follow-up messages and explicitly authorizes external contact.
   The request must match both the row version and a hash of the displayed scope, including
   message bodies. Editing the underlying commitment invalidates old approval.
   After contact has occurred, a changed outcome needs a new responsibility rather than
   reusing an old reference that could misattribute the recipient's prior replies.
4. The worker persists an outbound message and dispatches it through the configured adapter.
5. Replies become agreement, progress, reported completion, blocker, opt-out, or unclear evidence.
6. Reported completion stops follow-ups and asks the owner to review evidence. Only an explicit
   owner verification with a review note completes the underlying Commitment.

Lifecycle: draft → active → completion_reported → verified, with paused, cancelled and escalated
branches. Verified means **verified by the owner**, not independently verified by a model.
Transport accepted/delivered/read states never mean the task is complete.

Each outbound message begins: “I'm [assistant], an AI assistant acting on behalf of [owner].”
The dedicated sender number must match both the paired account and the core's authorized sender
address. No personal-user impersonation, arbitrary external-send model tool, or automatic sharing
of the user's world model is provided.

## Durable Follow-Through

The Python worker polls every ten seconds, with bounded batches. PostgreSQL conversation-first
locking serializes approvals, revocations, inbound processing and competing workers. Due state
is rechecked after locking. It honors current user-timezone quiet hours, task deadlines, opt-outs
and approved follow-up limits. It checks current time per operation, not just once at process start.
The UI exposes a worker heartbeat; a paired WhatsApp account alone does not imply a running worker.

Default policy: follow up every 24 hours, at most twice, with quiet hours 21:00–08:00. The owner can
choose 60–10,080 minutes and 0–5 follow-ups. Equal quiet-hour endpoints disable the quiet interval.
An interval is not a guarantee of delivery time; disconnected channels, quiet hours and in-flight
network work can delay delivery. The worker escalates deadlines instead of starting new late sends.
Pause/cancel are monotonic revocations and are accepted even if a progress update made the displayed
version stale. Approval and verification still require the current version.

Routine agreement/progress and transport receipts remain in the responsibility timeline.
Meaningful updates reset the next follow-up interval rather than provoking an immediate reminder.
Blockers, ambiguous replies, delivery uncertainty, exhausted follow-ups, deadlines and completion reports
produce deduplicated attention updates in chat. Pausing/cancelling stops new contact; it cannot
recall a message already in flight. Replies to paused/closed tasks are retained without reactivating them.

## Baileys Service

Pinned dependency: `@whiskeysockets/baileys@7.0.0-rc14` (currently a release candidate).
Node **22.13+** is required for the built-in SQLite API; CI uses Node 24.

- Authentication credentials and Signal keys are persisted transactionally in SQLite, with
  Baileys' BufferJSON/protobuf codecs. This does not use the demo multi-file auth helper.
- The state database uses WAL/FULL synchronization and private file permissions. A renewable
  session lease prevents competing processes from opening the same account concurrently.
- Transient failures reconnect with bounded exponential delay. Logout/revoked/bad sessions
  require pairing again; connection replacement/forbidden states stop automatic reconnect.
- Pairing QR images are available only through authenticated, non-cacheable endpoints, never logs.
- Outgoing requests are content-bound to stable IDs and journaled **before** calling Baileys.
  Repeated requests return the existing outcome. A crash or timeout after dispatch becomes
  **uncertain**, not “definitely failed.” It is not automatically resent.
- Delivery receipts reconcile late outcomes, including the case where the core restarted before
  saving the bridge's response. Provider message IDs remain distinct from core message IDs.
- Incoming text is journaled before asynchronous address resolution. PN/LID mapping is confined
  to the adapter. Core forwarding is retried durably; acknowledged bodies are cleared from the
  forwarding journal while deduplication markers remain.
- Self-authored messages, groups, broadcasts and newsletters are ignored. Unsupported media and
  oversized replies produce review-needed notices rather than pretending their content was read.

No distributed exactly-once network delivery is claimed. Stable IDs, journaling and conservative
uncertainty prevent blind duplicate sends; an operator resolves ambiguous delivery before resuming.
Baileys/WhatsApp compatibility can change independently of this repository and must be live-tested
with the chosen number. The full library is loaded in tests, but the WhatsApp socket is simulated.

## Reply Interpretation and Boundaries

Messages include a responsibility reference and suggest AGREE, PROGRESS: …, DONE: …, BLOCKED: …,
or STOP. These have deterministic handling, including rejection of contradictory completion phrases.
Other text gets at most one call to the configured LLM using only the task and incoming reply;
it receives no tools or unrelated personal memories. Structured interpretation must cite an exact
substring of the reply. Failures/ambiguity escalate; reported completion still needs owner review.

Replies must match the configured channel and assignee, plus a quoted outbound message/reference
or an unambiguous contacted responsibility. Unmatched replies are visible for manual review rather
than assigned by guesswork. Unknown senders cannot instruct the owner agent or authorize actions.
STOP blocks future contact to that address on the channel, including newly drafted responsibilities.
An LLM interpretation is not guaranteed correct; original text and interpretation evidence remain visible.

## Local Setup

1. Load your root `.env` and migrate the backend through **0011**:
   ```bash
   # from backend/
   set -a; source ../.env; set +a
   uv run alembic upgrade head
   ```
2. In the web app, open **Today → Delegated responsibilities**. Register a **separate assistant
   WhatsApp number**, the name it represents, and quiet hours. Copy the displayed channel account ID.
3. From `backend/`, run:
   ```bash
   uv run python -m app.configure_operations --account-id YOUR_CHANNEL_ID
   ```
   This preserves existing settings, generates/reuses a random bridge secret, and writes the
   account binding, dedicated phone and private state path to the ignored root `.env`. It does
   not print secrets. Restart the API after reloading that file.
4. Run the bridge in another terminal:
   ```bash
   # from whatsapp-bridge/
   npm ci
   set -a; source ../.env; set +a
   npm start
   ```
5. Run the worker in another terminal:
   ```bash
   # from backend/
   set -a; source ../.env; set +a
   uv run python -m app.operations_worker
   ```
6. In Today, select **Pair / reconnect**. On the dedicated assistant phone open WhatsApp →
   Linked devices → Link a device and scan the QR. Confirm connection and worker status.
7. Create a short test responsibility for a consenting recipient. Review/authorize it, then have
   that person agree, provide progress and report DONE with evidence. Verify from the web app.

Keep the API, worker and bridge running for background operation. The browser can close, but
stopping the computer stops execution until services resume. Deployment should supervise these
processes and persist the bridge state volume. A lost state volume requires re-pairing and removes
transport deduplication evidence; preserve it alongside the core database during recovery.

## API / Service Boundary

- Session-scoped UI APIs: `/api/operations/channel`, `/api/responsibilities`, per-responsibility
  control/detail and delivery-review endpoints.
- Server-only inbound API: `/api/internal/channel-events`, requiring the configured bridge token
  and matching channel account ID. Browser authentication cannot substitute for this token.
- Private bridge API: `/v1/status`, `/v1/connect`, `/v1/disconnect`, `/v1/logout`, `/v1/messages`.
  Bindings default to loopback. Cross-host configurations require a trusted HTTPS endpoint.
- No API credentials, pairing data or message bodies are printed in service logs. Communication
  transcripts and approval snapshots are inspectable owner data, retained independently of raw chat
  and derived-memory deletion. Full communication erasure/retention controls remain future work.

## Validation and Remaining Work

Automated coverage includes approvals, changed scopes, cross-tenant references, concurrent workers,
duplicate inbound events, core interruption after dispatch, late receipts, quiet hours, deadlines,
follow-up limits, opt-outs, completion evidence, session persistence, QR/reconnect states, lease
ownership, HTTP authentication, inbound/outbound bridge contracts, and recovery after restart.

Validation completed for this slice:

- **488 backend tests passed**, including real PostgreSQL concurrency/tenant constraints,
  migrations, and the cross-service core/bridge HTTP test; zero skips in the full local run.
- **12 bridge tests passed**, using the real Baileys auth codecs with simulated socket events.
- **62 frontend tests passed**, plus ESLint, TypeScript, production build, Ruff and mypy.
- Bridge production dependency audit: zero findings. The frontend scoped audit passed after
  updating Vitest/Vite to patched compatible releases; the existing narrow braces waiver remains.
- Live Azure GPT-5.4 successfully invoked `draft_responsibility` in a browser walkthrough.
  Desktop and 390px mobile review/authorization views passed without overflow or JS errors.
  That synthetic draft was cancelled, and **no external WhatsApp messages were sent**.

The cross-service test runs actual FastAPI and Node HTTP services with real database persistence;
only the WhatsApp socket is simulated. Live QR pairing was subsequently completed and the bridge
reported a connected account matching the registered assistant number, with a recent worker
heartbeat and no reported connection error. **A real recipient send/reply acceptance test remains
pending.** Pairing alone does not verify message delivery or the whole responsibility workflow.

The current WhatsApp route handles responsibility replies, not general owner chat. Automatic
LLM-request retries are also not implemented; these are separate follow-up tasks.

V1 deliberately uses fixed, owner-reviewed contact templates, one recipient per responsibility,
text replies/link evidence, and owner verification. It does not independently open evidence URLs,
process attachments, make calls, negotiate changed deadlines, or send arbitrary model-written
external messages. Other transports can implement the same interface; none is installed yet.
