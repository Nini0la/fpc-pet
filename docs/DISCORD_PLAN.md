# Discord Integration — Saved Plan

Status: parked for later; no Discord adapter has been implemented.

## Goal

Private Discord DMs reach the same agent, personal state, tools and conversation used by the
web app. WhatsApp can later use the same channel boundary. Replies return to the originating
channel rather than being broadcast to every linked account.

## Implementation Order

1. Create a Discord application/bot and configure its server-side token. Use a small Python
   Gateway worker with only the intents and permissions needed for private DMs.
2. Add secure linking: an authenticated web user generates a short-lived, one-use code and
   sends `/link <code>` to the bot. Map Discord user IDs, never display names, to application
   users. Show and revoke the connection from web settings.
3. Route linked DMs into the existing AgentRuntime. Ignore bot-authored messages, preserve
   tenant isolation and execution limits, split long replies, suppress unintended mentions,
   and provide typing/error feedback.
4. Implement explicit `/remember <message>` permission for structured memory writes on that
   operation. Ordinary DMs may discuss/retrieve context but cannot authorize memory tools.
   Conversation retention remains distinct from structured-memory permission.
5. Persist incoming-message and outgoing-delivery state. Use namespaced Discord message IDs
   for idempotency. Retry delivery of the saved answer without repeating inference or writes.
6. Label message origins in the web conversation and poll while visible so external messages
   appear without manual reload. Refresh affected context views.
7. Verify one complete real DM workflow after simulated-event and failure-path tests.

## Acceptance Checks

- Link, DM, receive an Azure response, and see the exchange on the web.
- Save an idea in Discord; inspect it on the web.
- Correct a fact on the web; Discord uses the corrected version.
- Duplicate incoming events do not repeat processing or side effects.
- A failed outbound send retries delivery rather than recreating records.
- Unlinked users cannot access personal context; revoking the connection stops access.

## Scope and Operating Requirements

Start with private DMs, account linking, shared context/history, write permissions, delivery
recovery and web synchronization. Server conversations, attachments, voice, automatic
notifications, WhatsApp and broadcasting are deferred.

The Gateway worker must remain running. Local testing works while the computer/app is on;
reliable access while the computer is off requires hosting. The user will need to create the
Discord application and place its token in server configuration, not in chat or source control.
