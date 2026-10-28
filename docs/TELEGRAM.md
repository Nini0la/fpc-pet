# Telegram — private Milestone 1 owner trial

This is an owner-authorized messaging extension to the existing Mica runtime, not a multi-user
release or a new agent. Discord is still unimplemented. WhatsApp delivery stays disabled.

## Connect once

1. Open the authenticated web app at **http://localhost:3000**.
2. In **Today → Telegram → Open Telegram**, select the permissions you want:
   - Allow linked DMs to save/update memories, projects and commitments.
   - Deliver enabled personal check-ins/routines to your Telegram DM.
3. Create a private linking invitation, open its Telegram link and press **Start** within five
   minutes. Do not share that invitation. The bot acknowledges the connection and its permissions.
4. Talk naturally in the bot's private DM. Web Chat and Telegram share the same conversation,
   personality, authoritative records and Azure runtime. Visible web Chat/Today refresh periodically.

The invitation is single-use, stored only as a hash, and available only to the existing web `owner`.
It binds a numeric Telegram user/private-chat ID; display names are not identities. Group messages,
bot-authored messages and unlinked users are ignored without personal replies or model calls.
Other web test identities cannot generate links. No new Mica accounts are provisioned by Telegram.

Permission defaults are off. The Telegram memory grant is explicitly ongoing until revoked,
unlike the per-message web checkbox. Incoming messages retain their arrival-time write permission;
later enabling it does not authorize old queued requests. Current permission is rechecked too.

`/status` shows permissions; `/stop` pauses proactive Telegram delivery. Web routines have separate
settings and can continue saving in-app messages. Use ordinary conversation to pause/complete a
named commitment, or revoke the entire connection from Today. Relinking invalidates older codes,
queued inputs and deliveries. Opting into proactive messages never sends the old chat backlog.

## Tight trial checklist

1. **Remember:** track one real task, explicitly requesting check-ins every 15 minutes.
2. **Follow up:** close Telegram/web; check that one DM arrives after the scheduled time.
3. **Adapt:** change its deadline or availability; verify the revised plan.
4. **Stop:** pause it, then mark it complete; future check-ins stop.
5. **Continuity:** return later and ask about the task; inspect the same record in the web app.

Keep the Mac awake and logged in. Personal autonomy and that commitment's follow-ups must be
enabled, and quiet hours still apply. Text messages are supported, up to 4,000 characters.

## Runtime and delivery guarantees

- `app.telegram_worker` long-polls Telegram using an outbound HTTPS connection; no public webhook
  or inbound web port is needed. `TELEGRAM_BOT_TOKEN` stays in the ignored private `.env`.
  The bot verified during setup is **@QwenErringBot**; its backend is Mica's existing Azure runtime.
- Migration `0013` adds four empty tables: bot cursor/heartbeat, owner connection, durable incoming
  messages and outgoing deliveries. Existing personal rows are not rewritten.
- A PostgreSQL session advisory lock permits one poller/sender per bot. Telegram update IDs and
  AgentRuntime event keys deduplicate incoming work. Inbox processing, shared conversation/tool
  writes and queued reply parts commit atomically. At most three processing attempts are allowed.
- Explicit provider rate-limit rejection can retry the saved reply, respecting retry-after and
  a maximum of three sends. A timeout or crash during a send is **uncertain**, not blindly retried:
  Telegram's send API does not provide our own end-to-end idempotency key. Inspect the saved web
  reply and Telegram before making a new request. `sent` means Telegram accepted it, not read.
- Scheduled in-app effects are projected to the opted-in private DM. Delivery rechecks link,
  owner, plan version/status, preferences, availability and quiet hours. Changed/completed plans,
  revoked links and check-ins older than two hours are cancelled, not delivered as stale nudges.
- Normal web replies are not broadcast to Telegram. Telegram replies remain visible in web Chat.
  Long replies split into bounded plain-text parts, without HTML/Markdown parsing or link previews.
- There is a 20-message pending queue and 60 accepted messages/hour for this private trial.
  Unsupported attachment-only messages receive a text-only instruction from the linked bot.
- Token-bearing URLs/provider bodies are excluded from error logs. Delivery metadata is available
  in Today; no bot token, linking-code hash or private message body is returned by that status API.

## Deployment / disable / recovery

Back up the personal database and private configuration, stop writers, apply `0013`, then deploy
the matching backend/frontend/personal worker and a supervised Telegram worker. Use an absolute
environment path from a pinned release checkout:

```sh
uv run --no-sync --env-file /Users/niniola/Projects/fpc-pet/.env alembic upgrade 0013
uv run --no-sync --env-file /Users/niniola/Projects/fpc-pet/.env python -m app.telegram_worker
```

The worker checks bot identity and refuses an existing webhook rather than deleting someone else's
integration. `--once` performs one polling/processing/delivery iteration. The regular personal
scheduler continues to run separately with `--personal-only`; Telegram does not run WhatsApp work.

Disable via Today → Telegram → Disconnect and stop `com.mica.telegram`. For application rollback,
stop Telegram and point the other services back to `.local/releases/m1-final/` (`acaa10c`); the
additive Telegram tables can remain so history/evidence is preserved. The old runtime ignores them.
Only if a schema rollback is specifically needed, stop all new services first and back up before
`alembic downgrade 0012`: this deletes Telegram links/inbox/outbox evidence, but preserves shared
chat, original memories and commitments. Re-upgrading requires relinking. Never run the Telegram
worker against a downgraded schema.

See `IMPLEMENTATION_STATUS.md` for actual test and deployment results. Owner acceptance of
Milestone 1 remains pending; the feature branch is not merged.
