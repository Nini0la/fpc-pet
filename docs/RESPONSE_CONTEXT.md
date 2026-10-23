# Inspecting the Context Behind a Response

In **History**, click an assistant response or **View context**. The same button appears
under assistant messages in **Chat**. The inspector starts on the call that produced the
final model text, with other calls available in order.

## What Is Captured

New contextual turns capture inputs at the gateway boundary, before each model call:

- The actual provider JSON request body: messages in original order, model/deployment,
  tool schemas, output limit and configured reasoning effort where applicable.
- Explicit section labels for your message, system instructions, assembled personal context
  and tool receipts. These labels are attached by the application, not guessed from content.
- Included/excluded record references, versions and selection reasons.
- The returned model text and requested tool calls, excluding hidden reasoning fields.
- Actual backend tool arguments and results, associated with the requesting call.
- Reported tokens, latency, cost when configured, and safe error codes for failed attempts.

The gateway uses the same request-body builder for inspection and HTTP transport. Credentials,
HTTP authorization headers, cookies and endpoint secrets are not part of the captured body.
Test/alternative gateways without a request-body builder are explicitly labeled as gateway
inputs rather than claiming to show a provider-specific wire request.

## Reading a Tool-Assisted Response

1. **Call 1** contains the initial context and available tools. Its output may be a tool call.
2. **Tool execution** records what the backend actually did and returned.
3. **Call 2** receives fresh current state and server receipts. The inspector shows this
   new context separately; it does not pretend that the first prompt was reused.
4. **Selected assistant response** is what appeared in chat. It may include deterministic
   receipts appended after generation. **Model output before application formatting** shows
   the model's own returned text.

Our runtime rebuilds the second request after tools. A tool's full return object may not be
sent verbatim: a smaller receipt plus refreshed state can be used instead. The UI distinguishes
execution evidence from the exact tool-results message included in model input. It also shows
actual message roles; assembled context and receipts currently use the `user` role.

The selected inputs are evidence for investigating a response, not proof of causal influence,
access to a model's hidden reasoning, or visibility into provider-internal processing.
Character-based token estimates are labeled separately from provider-reported usage.

## Historical Accuracy

Snapshots are stored on the existing AssistanceRun linked to the exact assistant Message.
They are immutable with respect to later memory corrections and are never retrieval sources.
Inspecting a response does not invoke the model or rebuild context from today's records.

- Older responses without snapshots show **Context was not recorded**. No retrospective
  reconstruction is presented as the original input.
- A new deterministic feedback-policy response records **No model call** and its policy.
- Legacy deterministic skills without an AssistanceRun are labeled as uncaptured, not assigned
  an invented model context.
- Failed provider attempts show the prepared inputs and safe failure code, without claiming
  that the provider processed them successfully.

## Storage, Access and Deletion

This adds a private raw-content storage surface, separate from metadata-only general diagnostics.
It is kept in the application's database, not exported to Langfuse, Phoenix or another service.

- `GET /api/chat/messages/{message_id}/context` requires the owning user's session, returns
  `Cache-Control: no-store`, and does not expose foreign accounts' messages or traces.
- History lists and `/api/assistance` remain metadata-only with respect to model inputs.
- **Remove captured context** deletes the selected snapshot through a CSRF-protected DELETE
  endpoint, retaining the visible conversation and metadata audit.
- Deleting any retained thread, commitment, episode, journal or vocabulary memory clears
  **all raw response snapshots for that user**, not other users. This is deliberately
  conservative: copied recent-chat text can carry deleted facts without a direct record link.
- Correction retains old snapshots for historical analysis; corrected state controls future
  model requests. Snapshots are retained until explicit clearing or memory deletion; there
  is no automatic age-based expiry in this initial implementation.
- Source chat, external-provider retention and backups remain separate retention surfaces.

Snapshots commit with the conversation transaction. A process crash or database rollback can
still lose the trace of an already-incurred model call. This is not an independent telemetry
pipeline or a replacement for a full observability platform. Langfuse/Phoenix can be evaluated
later for aggregate tracing, experiments and operational dashboards; none is integrated here.

## Migration and Verification

Run `uv run alembic upgrade head` with the configured database environment. Revision **0010**
adds nullable private snapshots, capture status, and a tenant/message lookup index. Existing
runs remain explicitly `not_recorded`; downgrade discards snapshots but preserves base runs.

Tests cover request-body equality with actual transport, both tool-related contexts, correction
history, deletion scrubbing, idempotent replay, failed calls, deterministic responses, tenant
isolation, CSRF, legacy migration, loading/errors, escaping and access from both History/Chat.

Verification for this change: **465 backend tests passed** with a disposable PostgreSQL database
(zero skipped), **58 frontend tests passed**, and Ruff, mypy, ESLint, TypeScript and production
build passed. A real Azure GPT-5.4 two-call project-save flow was inspected in Chromium from both
Chat and History at desktop and 390px mobile widths, with no horizontal overflow or JS errors.
Only synthetic data was used for that live check.

The separate Discord integration plan is parked in [DISCORD_PLAN.md](DISCORD_PLAN.md).
