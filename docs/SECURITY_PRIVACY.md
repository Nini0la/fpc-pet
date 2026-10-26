# Security and privacy

## Operational Communications

Drafting a responsibility does not authorize contact. A separate session/CSRF-protected action
binds approval to the exact displayed scope and version; workers recheck scope, state, recipient,
sender identity, opt-outs, deadlines and quiet hours. External replies cannot authorize tools or
expand the contact plan. Reported completion is not owner-verified completion.

The Baileys bridge has a separate bearer-authenticated service boundary and private persistent
session storage. It checks the paired number against the configured assistant number and the
sender address supplied by the authorized core. Pairing data and credentials are not logged.
Uncertain sends stop for review rather than being blindly replayed. Communication transcripts,
approval snapshots and external evidence are retained as operational records, separate from
derived-memory deletion; comprehensive communications erasure is not implemented yet.
See [OPERATIONS.md](OPERATIONS.md) for setup and failure/recovery limits.

## Private Response Context Inspection

New contextual responses retain exact model-input snapshots for the owning user's inspector.
These raw inputs are stored separately from metadata-only diagnostics and are not exported to
an external observability service or used as memory retrieval sources. Transport credentials
are excluded; personal text supplied to the model is retained. The dedicated endpoint is
tenant-scoped and non-cacheable. Users can clear individual snapshots. Deleting retained memory
conservatively clears all raw snapshots for that account; corrections preserve historical
snapshots. See [RESPONSE_CONTEXT.md](RESPONSE_CONTEXT.md) for the full retention boundaries.

## Contextual Slice Amendment

The live gateway adds an external data boundary: bounded relevant personal context and the
current message are sent to the configured provider. Review that provider's retention policy
before using real personal data. Server credentials are never exposed to the frontend.

Per-turn UI permission gates live memory tools and pending journal/vocabulary capture. Tools
are schema-validated and tenant-scoped with no external side effects. Existing deterministic
development extraction is preserved, not silently advertised as a live model. Conversation
storage itself is separate from permission to promote structured memory.

Memory mutations cut off pre-mutation chat from future model prompts. Corrections serialize
with generation using the tenant conversation lock; the post-tool prompt uses refreshed state.
Thread revisions are scrubbed on deletion, and corrected/deleted journals invalidate their
directly derived episodes. Source chat and backups remain separate retention surfaces.
The full controls, cost risks and intentionally missing account-erasure/export features are
listed in [MYSTERY_PET_SLICE.md](MYSTERY_PET_SLICE.md). Earlier M5 notes below are historical
where they refer to the absence of a provider or to scrubbed thread fields.

- Identity is derived only from an opaque random HttpOnly session cookie. Clients never send authoritative user IDs. Production resolves the fixed `owner`; the username selector exists only in development/test for isolation testing. Session and CSRF values are hashed; cookies are SameSite=Strict and Secure in production.
- Login compares the environment access code in constant time. Mutations require an exact allowlisted Origin plus double-submit CSRF. CORS uses exact configured origins, never wildcard credentials.
- Production fails closed when required secrets/configuration are absent. Access codes, auth headers, raw prompts, chain-of-thought, and secrets are excluded from events and logs. Audit metadata contains observable actions/reasons only.
- Every Today, vocabulary item/attempt, reminder, journal, briefing, reflection, message, state, Episode, event, skill-run, and provenance query is server-user scoped. Foreign-user IDs remain indistinguishable from missing IDs. Journal search text is parameterized and bounded to 500 characters; pagination is capped at 100 rows and offset 10,000.
- Journal entries deliberately retain the user's original evening answer verbatim. This is visible product data with indefinite active-record retention by default, not hidden memory. Operators must define backup retention/erasure before handling sensitive data.
- Episodic memory capture remains default-deny. Greetings, ordinary questions, unsupported implications, and credential-like content are not promoted. The existing GitHub/AWS/bearer/JWT/private-key/API-key/high-entropy screening also gates reflection-derived Episodes. Raw chat/journal retention is distinct from promotion and follows the documented retention policy.
- Evening extraction only changes supported explicit state. It does not infer completion, blockers, commitments, or priorities from ambiguous prose. Journal, state, Episode, provenance, event, and skill-run writes share one transaction.
- Runtime ingress idempotency keys are fingerprint-bound to tenant, kind, and payload. Separate database uniqueness constraints enforce one logical briefing and reflection prompt per tenant/local date/policy. PostgreSQL row locking and uniqueness make concurrent repeated scheduled triggers safe and prevent duplicate proactive messages.
- Reminder uniqueness binds tenant, server-selected commitment, relevance window, and policy version. Model/user payloads never select ownership IDs. A commitment row is locked and refreshed immediately before surfacing; completion/cancellation/deletion suppresses output. Reminder audit metadata stores only policy factors and IDs, never raw source messages or secrets.
- User-local dates use a server-stored IANA timezone, a timezone-aware injected clock, and `zoneinfo`; clients cannot assert the authoritative user or local date. Invalid/unconfigured users default to `UTC` at creation.
- API text and identifiers are bounded. SQLAlchemy parameterizes queries. Errors are generic. React renders all content as escaped text, uses no `dangerouslySetInnerHTML`, accepts no user-authored destination URLs, and stores no auth token in localStorage.
- Corrections use tenant-scoped versioned compare-and-swap and content-free audit metadata.
  Journal correction preserves the verbatim original in `original_content` and stores the
  user-visible correction separately. Deletion scrubs retained journal content and leaves
  only a content-free tombstone. Raw chat is retained separately: deleting a derived memory
  does not delete the source transcript. Backups remain subject to operator rotation.
- Vocabulary answers are bounded to 1,000 characters and sentences to 500. Attempts store visible prompts/answers only, never hidden reasoning. Vocabulary deletion scrubs the word, definition, example, sentences, prompts, and answers while retaining a content-free metadata audit tombstone; database backups remain subject to operator retention.
- This is an original narrow continuity prototype; it does not expose, implement, or claim proprietary FPC internals.

Known M5 limits: one shared environment access code, no rate limiter, no field encryption,
no key-rotation UI, literal SQL substring search, conservative rather than comprehensive
DLP, and no production model provider. Put production behind TLS and a trusted reverse
proxy.

Accepted development-tooling risk: `eslint-config-next@16.4.0` currently reaches
`braces@3.0.3` through `fast-glob` and `micromatch`; npm reports the unpatched
GHSA-vfj7-8cjw-p6xm stack-exhaustion advisory. The affected chain is not a production
dependency and receives only repository-controlled lint globs, so forced downgrade is
not justified. The production dependency audit is clean; monitor for a patched upstream
release.
