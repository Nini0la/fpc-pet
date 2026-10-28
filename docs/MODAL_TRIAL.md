# Owner-only 46-hour cloud trial

- **Application revision:** `8b8bb7bc0701d7e6da5575759875923e17c9c3f3`
- **Start:** 2026-10-28 11:54:34 UTC
- **End:** 2026-10-30 09:54:34 UTC
- **Modal app:** `mica-owner-trial`, active app ID `ap-1yObYNST6QMQ207oajaSga`
- **Dashboard:** https://modal.com/apps/nini-adegboyega/main/deployed/mica-owner-trial

The existing Telegram adapter and personal scheduler now run in Modal against the owner's direct
SSL Neon PostgreSQL connection. Azure remains the inference provider. The Mac can be off during
the trial. Telegram remains owner-only and WhatsApp remains disabled. No public web endpoint or
multi-user release was introduced; the optional local web UI/API use the same hosted database.

## Cutover and preservation

- The hosted database was verified empty before restore. Local API/frontend and both workers were
  stopped after checking that no Telegram processing/sends were in flight.
- A custom-format pre-cloud dump was restored to Neon. Every field of all **227 existing rows**
  matched the original fingerprints. This includes conversations, memories, commitments, personality,
  permissions, Telegram identity, inbox/outbox and update cursor. Schema remains `0013`.
- Private backup: `.local/rollouts/modal-trial/mystery_pet-pre-cloud.dump`, SHA-256
  `84cb7f0c583bbe13fd744cdee16c2d386dc1bc21815ae019d5cc178714289e34`.
  The original local database is retained untouched. Secrets, original `.env`, fingerprints and
  migration helpers remain under that ignored, restricted private rollout directory.
- Root `.env` now points `DATABASE_URL` to hosted PostgreSQL. **Neon is authoritative from cutover
  onward.** Do not overwrite it with the older local database: subsequent phone conversations and
  actions exist in Neon.
- Local `com.mica.telegram` and `com.mica.worker` LaunchAgents are booted out and disabled, including
  automatic restart at login. The local web/API were later restarted as optional clients of Neon;
  turning the Mac off only removes that local dashboard, not Telegram/autonomous operation.

## Actual cloud verification

- Disabled preflight, executed inside the Modal image: Neon `SELECT 1`, Telegram bot identity and
  webhook check, and an actual `gpt-5.4-2026-03-05` Azure response all passed before activation.
- With all local application services stopped, Modal generated the scheduled morning briefing at
  **2026-10-28 11:58:14.927009 UTC** and Telegram accepted it with provider message ID **22**.
  Scheduled action: `65a313d1-b437-4cce-a994-d4425fca18a7`.
- The owner sent a new DM after cutover; cloud AgentRuntime processed it at **12:08:49 UTC** and
  delivered the Azure-generated reply through Telegram. Later ordinary conversations also succeeded.
- The running worker container was explicitly stopped. Modal replaced it automatically, the
  persisted heartbeat resumed, and the migrated link/cursor/conversation remained available.
  At the post-restart check there were **9 accepted Telegram deliveries**, with no failed or
  uncertain deliveries reported. Legitimate owner conversations increased shared history to 62
  messages; this is live activity, not a frozen acceptance count.
- All **545 backend tests**, Ruff and mypy passed. GitHub CI passed for the deployed revision:
  https://github.com/Nini0la/fpc-pet/actions/runs/40682756247.

## Expiry and cost controls

- One scheduled worker, one maximum container, CPU request/limit **0.25/1 physical core**, memory
  request/limit **512/1024 MiB**, no GPU. It runs the deterministic scheduler then polls Telegram;
  the model is invoked only for incoming owner conversation, not continuous reasoning.
- The separate expiry function is capped at one small container, receives only timing configuration
  and stops **this app** when the window expires. Expiry checks run every minute; model/send guards
  reject new requests after the exact cutoff even before the stop completes.
- Auto-stop was tested with a disposable Modal app and its own container identity. The first probe
  lacked CLI dependencies; the pinned full Modal SDK image fixed that, and the probe stopped itself.
  No full workspace credential was copied into the shutdown function.
- Updating a Secret alone did not refresh an already-warm container, and identical `modal deploy`
  was skipped. Activation therefore used a stop/redeploy of only this app, which loaded the new
  window. Do not reset the trial start/end merely to deploy a fix.
- No unrelated Modal apps, workspace-wide budgets or billing plan settings were changed.
  At published rates, a continuously used 1-core/1-GiB worker is about **$2.54 for 46 hours**;
  actual requested baseline is smaller. Expiry/inspection/build overhead is additional. Existing
  Modal credits may cover compute; Azure tokens and the database account's own allowances are
  separate. This is a bounded resource/time configuration, not a guaranteed invoice amount.
- At expiry, the bot stops until explicitly resumed. **The Neon database is not deleted.**

## Stop / resume / recovery

To stop cloud activity early:

```sh
modal app stop mica-owner-trial --yes
```

To return to the Mac, first stop the cloud app (or confirm automatic expiry), then retain the current
hosted `DATABASE_URL` and enable/start the local workers:

```sh
launchctl enable gui/501/com.mica.worker
launchctl enable gui/501/com.mica.telegram
launchctl bootstrap gui/501 /Users/niniola/Library/LaunchAgents/com.mica.worker.plist
launchctl bootstrap gui/501 /Users/niniola/Library/LaunchAgents/com.mica.telegram.plist
```

The existing local API/frontend can continue against Neon. If they are not running, bootstrap their
corresponding `com.mica.api.plist` and `com.mica.frontend.plist`. Check service state before bootstrap
to avoid treating “already loaded” as a failure. Do not run a second Telegram poller against an old
forked database.

For complete disaster recovery, the pre-cloud dump can be restored into a separate local database,
but it is a **point-in-time fallback**, not a copy of later cloud activity. Preserve/export the Neon
database first when possible. Neon runs PostgreSQL 18; use a PostgreSQL 18-or-newer `pg_dump` client
for future logical backups of it (the Mac's original client is version 14). Returning local workers
to the same Neon database avoids any reverse migration or loss of trial conversations.

Any extension beyond this window requires a new explicit authorization. The feature branch remains
unmerged, Milestone 1 owner acceptance remains pending, and Milestone 2 has not started.

## Short owner trial checklist

1. Track one real task and request a check-in every 15 minutes.
2. Close Telegram/the laptop; confirm one check-in arrives after its scheduled time.
3. Change the task's deadline or availability and check the revised plan.
4. Pause it, then complete it; verify future check-ins stop.
5. Return later and ask about it; check that Mica remembers the current state.

Quiet hours remain 21:00–08:00 UTC. `/stop` pauses proactive Telegram DMs. No relinking is needed.
