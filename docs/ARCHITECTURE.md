# Architecture

## Milestone 1 boundary

One FastAPI service and one Next.js app use PostgreSQL as production authority. SQLite is limited to isolated API tests. There is no broker, vector database, or agent framework. Conversation segmentation is internal; the UI exposes one continuing relationship.

`AgentRuntime.handle(RuntimeEvent)` is the only event entry point for both user messages and scheduled events. Plain deterministic extraction proposes state; the runtime validates and persists proposals, messages, provenance, events, and skill runs in one transaction. Model proposals never receive an ORM session. `ModelRouter` is a protocol ready for a future Nebius/Nemotron adapter; deterministic replies must be explicitly configured for development/test and are not live model output.

All durable records are UUID-owned by a user and tenant filters are mandatory. Mutable threads, commitments, and episodes carry optimistic versions. Derived state includes confidence, derivation, and `ProvenanceLink`. Recall is explicit SQL over non-deleted episodes and preserves `user`, `assistant`, `joint`, or `discussed_only` attribution; it does not infer authorship and does not use embeddings.

PostgreSQL is migrated with Alembic. The initial migration reflects the complete M1 schema: User, server Session, internal ConversationSession, Message, Thread, Commitment, Episode/links, AgentEvent, ProvenanceLink, and SkillRun.

Milestones 2–6 (briefings, polished Today/Threads/History, external discovery, vocabulary loops, and autonomous actions) are out of scope.
