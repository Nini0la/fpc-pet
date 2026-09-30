# Architecture

## Milestone 2 boundary

One FastAPI service and one Next.js app use PostgreSQL as production authority. SQLite remains limited to isolated API/unit tests. There is no broker, vector database, graph orchestration engine, or private FPC machinery. Conversation segmentation is internal; chat, morning briefings, and evening check-ins share one continuing relationship.

`AgentRuntime.handle(RuntimeEvent)` is the only event entry point for user and scheduled events. `MorningBriefingSkill` and `EveningReflectionSkill` are thin deterministic skills called by that runtime. A transaction records the `AgentEvent`, `SkillRun`, proactive/user messages, journal/state mutations, Episodes, and provenance together. Request fingerprints bind the user, event kind/payload/date, and normalized conversation target for user messages: the same idempotency key replays only for the same target and conflicts if retargeted. Model proposals never receive an ORM session. `ModelRouter` remains the future live-provider boundary; deterministic replies are explicitly development/test-only.

### Daily loop

`User.timezone` plus an injected timezone-aware clock and `zoneinfo` determine local dates, including DST transitions. `DailyBriefing` persists the rendered briefing, named non-empty sections, structured Power List, source event, policy version, and chat message. A unique `(user_id, local_date, policy_version)` constraint is the logical morning idempotency authority. `ReflectionPrompt` applies the same pattern to evening check-ins and tracks `awaiting`/`completed` state. The authenticated scheduled-event boundary accepts `intended_local_date` only for morning/evening events and only for the current or immediately previous user-local day; this supports a missed-trigger catch-up without reassigning the record to execution day. Repeated catch-up triggers for that intended day do not duplicate proactive messages.

The M2 `m2-v1` Power List is intentionally simple and replaceable. It scores currently open commitments and active threads using available deadline hints, explicit importance words, user priority, inactivity, recent promises, and IDs explicitly marked unfinished in yesterday's journal. It returns at most three deterministic selections with observable reasons. Schedule-slack/effort optimization remains M3.

An evening answer is stored unchanged in `JournalEntry.original_content`, with optional summary and structured supported changes, source message/event, UTC timestamps, and the matched prompt's local date. The answer binds to the user's most recent awaiting prompt created within the preceding 12 hours, so midnight and DST crossings preserve the prompted day. Extraction is clause-aware but narrow: exact normalized subjects, explicit contrast/negation, safe action/article normalization, and `it` only when one supported subject appeared in the immediately preceding clause. Ambiguous references cause no mutation. Structured updates and sourced Episodes occur in the same transaction. The following morning excludes completed commitments and boosts still-open items explicitly marked unfinished.

### Persistence and APIs

All durable records are UUID-owned by a user and tenant filters are mandatory. The current product model has exactly one persistent `ConversationSession` per user, enforced by a unique `user_id`. Creation is conflict-safe, and every message append locks that tenant-scoped conversation row before allocating the next ordinal. A unique `(conversation_id, ordinal)` constraint is the final ordering authority, so concurrent proactive and user-message transactions remain in one chat with distinct, strictly increasing, transaction-contiguous ordinals. Mutable threads, commitments, and episodes retain versioned correction/deletion behavior. Derived state has confidence, derivation, and `ProvenanceLink`; audit rows store observable action/reason metadata, not hidden chain-of-thought or prompts.

`GET /api/today` returns only the authenticated user's local-day briefing, Power List, resurfaced items, reflection state, and stable oldest-first slices of open commitments and active threads. Each state slice is capped at 50; `collection_meta` supplies `limit`, `returned_count`, `total_count`, and `has_more`. Persisted briefing collection sections are also capped at 50 and include equivalent metadata for commitments and threads. `GET /api/history/journals` is tenant-scoped with bounded query, limit, and offset. The Next.js page renders a minimal Today surface alongside chat; full navigation/polish remains M5.

PostgreSQL is migrated with explicit Alembic revisions. `0001` is the M1 foundation; `0002` adds timezone/priority/message-order fields and daily briefings, reflection prompts, and journal entries. Reversible `0003` consolidates any pre-existing per-user conversations, deterministically renumbers their messages, and adds the conversation and ordinal uniqueness constraints.

## Deferred

M3 schedule slack and urgency scans, M4 vocabulary, M5 full Today/Threads/History polish, M6 discovery/integrations, and a production model adapter are out of scope.
