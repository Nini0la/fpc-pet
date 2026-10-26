# Personal Mica — Milestone 1 controlled rollout, 2026-10-26

Owner authorization: deploy Milestone 1, preserve existing records/settings, keep WhatsApp
delivery disabled, do not merge the branch or begin Milestone 2 before owner acceptance.

## Release and preflight

- Branch `feat/functional-autonomy`; initial implementation `8b7ed1c291e93056f3c362b745fbe33d8865be23`,
  followed by rollout fixes `a750646` and **`acaa10c379ff00e151068a12635ac81438718c4b`**, the deployed
  application revision. All are pushed to origin as single-parent commits, not branch merges.
- GitHub CI runs `40356768901`, `40363868186`, `40365221852`: passed. Final verification: **526 backend**,
  65 frontend,
  12 bridge tests; real Azure/API/worker/Chromium acceptance on the isolated stack.
- Personal stack before rollout: API/worker `cef953f`, frontend `d58b2ef`, PostgreSQL
  `mystery_pet` at schema `0011`. Original services were stopped before backup, including
  the WhatsApp bridge and responsibility worker.
- Final immutable release checkout: `.local/releases/m1-final/` at `acaa10c`. Dependencies installed from lockfiles;
  production frontend built for `http://localhost:8000`, not the isolated smoke port.
- Previous source checkouts retained at `.local/releases/previous-api/` (`cef953f`) and
  `.local/releases/previous-frontend/` (`d58b2ef`).

## Backup and tested recovery

Private artifacts are under `/Users/niniola/Projects/fpc-pet/.local/rollouts/20261026-m1/`.
The directory is mode 0700 and excluded from Git; database/config archives are mode 0600.

| Artifact | SHA-256 |
| --- | --- |
| `mystery_pet-0011.dump` (custom-format `pg_dump`) | `8e8a1dc866b78b9f7b1bba52a7837f8a18dcb6bb216189336b6989c01d8270fd` |
| `private-config-and-bridge.tgz` (private `.env` and paired bridge state) | `7dd98a7882346303697cf477e76e62daf85af6ac642371f20cc0c3abcbec3e00` |
| `mystery_pet-0012-verified.dump` (post-verification checkpoint) | `5bba45c4506626420f7629d2d481cdc0bed216658195aeb9cd40af98a3056112` |

The dump was restored successfully using `pg_restore --exit-on-error --no-owner --no-acl`
into **`mica_recovery_20261026`**. Content-free per-column fingerprints verified all **100 original
rows** with no differences. On that restored copy, `0011 → 0012 → 0011` succeeded, with every
original row/column unchanged apart from the expected Alembic version. No source-table deletion
or content rewriting is performed by the upgrade.

The previous `cef953f` API was actually started on port 8013 against the restored/downgraded copy.
Owner authentication succeeded; all 26 owner chat messages, the existing owner commitment,
companion profile, preferences, Threads and History were accessible. The recovery API was then
stopped. The copied database stays available locally for recovery; it is never wired to a worker
or external channel.

### Migration review

`0012` adds default-off user opt-ins, quiet hours and scheduler metadata; adds plan/follow-up
fields with compatible defaults to Commitments; extends the state constraint with `paused`;
and creates action/revision tables with tenant-aware foreign keys and unique action keys.
PostgreSQL DDL is transactional. Existing conversation, project, memory and personality columns
are not rewritten. Old commitments do not silently opt into autonomous follow-ups.

Downgrade is intentionally lossy for **new autonomy-only** data: it drops action/revision history
and the new settings/plan fields, and maps `paused` to legacy `waiting`. Therefore a database
backup/switch is the verified full recovery path. Stop all writers before any schema downgrade.

## Deployment procedure and service management

Local LaunchAgents use `RunAtLoad` and `KeepAlive` to supervise processes independently of a browser
or terminal session. They run while this macOS user is logged in; a sleeping/offline machine cannot
execute scheduled work. All listeners bind to `127.0.0.1`; the existing private development auth
configuration and owner identity are retained.

- `~/Library/LaunchAgents/com.mica.api.plist`: committed release API, port 8000.
- `~/Library/LaunchAgents/com.mica.frontend.plist`: matching Next production build, port 3000.
- `~/Library/LaunchAgents/com.mica.worker.plist`: `app.scheduler --personal-only`.
- API/worker receive blank channel configuration overrides. WhatsApp bridge/responsibility worker
  stay stopped; paired credentials are preserved in place and backed up.
- Logs: `.local/rollouts/20261026-m1/{api,frontend,worker}.log`.
- Private root `.env` supplies existing database/Azure/auth settings; no secrets are embedded in
  the LaunchAgents. No injected clock is used on the personal deployment.

With writers stopped and backup/recovery verified, from the committed release's `backend/`:

```sh
uv run --no-sync --env-file /Users/niniola/Projects/fpc-pet/.env alembic upgrade 0012
```

Verify original-row fingerprints, disable channel accounts, then bootstrap each matching service:

```sh
launchctl bootstrap gui/501 /Users/niniola/Library/LaunchAgents/com.mica.api.plist
launchctl bootstrap gui/501 /Users/niniola/Library/LaunchAgents/com.mica.frontend.plist
launchctl bootstrap gui/501 /Users/niniola/Library/LaunchAgents/com.mica.worker.plist
```

Inspect with `launchctl print gui/501/com.mica.api` (and `.frontend`/`.worker`). Restart a service
using `launchctl kickstart -k gui/501/com.mica.worker`. Stop services using `launchctl bootout`
with the corresponding label. Keep the three services pinned to the same release path when
performing a later authorized deployment.

## Exact previous-version recovery

1. Stop new writers/UI:
   ```sh
   launchctl bootout gui/501/com.mica.worker
   launchctl bootout gui/501/com.mica.api
   launchctl bootout gui/501/com.mica.frontend
   ```
2. Preserve the post-rollout database with another custom-format dump before changing anything.
   Do not overwrite `mystery_pet-0011.dump`. The new database contains post-backup conversations
   and evidence that are not in the pre-rollout snapshot.
3. Restore the verified pre-rollout snapshot into a **new** database (the name must be unused):
   ```sh
   createdb mica_restore_0011
   pg_restore --exit-on-error --no-owner --no-acl --dbname=mica_restore_0011 \
     /Users/niniola/Projects/fpc-pet/.local/rollouts/20261026-m1/mystery_pet-0011.dump
   ```
   This avoids dropping/overwriting `mystery_pet`; its post-rollout records remain recoverable.
   Verify all original fingerprints with the private `verify_database.py` helper against
   `postgresql+psycopg:///mica_restore_0011` and `original-rows.json`.
4. Start the retained `cef953f` backend with that restored database. From
   `.local/releases/previous-api/backend/`, use the verified compatible backend interpreter:
   ```sh
   DATABASE_URL=postgresql+psycopg:///mica_restore_0011 \
   CHANNEL_BRIDGE_URL= CHANNEL_ACCOUNT_ID= CHANNEL_BRIDGE_TOKEN= \
   /Users/niniola/miniforge3/bin/uv run --no-sync --env-file /Users/niniola/Projects/fpc-pet/.env \
     /Users/niniola/Projects/fpc-pet/.local/releases/8b7ed1c/backend/.venv/bin/python \
     -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
   ```
   For supervised recovery, point the API LaunchAgent at that previous backend working directory
   and explicitly override `DATABASE_URL` to the restored DB before bootstrapping it again.
5. The previous frontend's locked dependencies and production build were also prepared and verified
   during rollout. From `.local/releases/previous-frontend/frontend/`, start the retained build:
   ```sh
   /Users/niniola/.local/bin/node node_modules/next/dist/bin/next start --hostname 127.0.0.1 --port 3000
   ```
   If it needs rebuilding, run `npm ci` and build with `NEXT_PUBLIC_API_URL=http://localhost:8000`.
   Point the frontend
   LaunchAgent to that retained checkout/build for supervised recovery. Verify owner login,
   historical chat, commitments and companion settings as in the completed recovery rehearsal.
6. Leave the new personal scheduler, old responsibility worker and WhatsApp bridge stopped on the
   previous version. Restoring a backup does not authorize external sends. Do not restore bridge
   credentials over the working files unless needed; the private archive is retained for that case.

The alternative `alembic downgrade 0011` preserves post-rollout ordinary records but loses the
autonomy-only data described above. Prefer the tested separate-database restore until the owner
chooses how to retain/reconcile newer records. No branch merge is required for either recovery path.

## Post-deployment evidence

### Completed checks

- Personal migration reached `0012`; original-row comparison immediately after migration showed
  **100 original rows preserved, no differences**. A later comparison after live conversations
  again preserved all original content, excluding only deliberate preference/version/context-cursor,
  conversation-activity and channel-enabled metadata changes. All original messages, Threads,
  commitments, provenance, responsibility records and personality values remain intact.
- Backend, frontend and worker are pinned to `acaa10c`. The release worktree is clean. API/Next
  listen on loopback 8000/3000. LaunchAgents are valid and running; browser checks see a recent worker
  heartbeat. The bridge listener on 8081 is stopped, both channel accounts are disabled, channel
  settings are blank in the supervised processes, and there are **zero channel-message rows**.
- Real mobile Chromium against `http://localhost:3000` passed owner login, historical chat, History,
  autonomy controls, current plan/correction evidence, in-app execution evidence and layout checks,
  with zero page errors. This browser was closed before the unattended check-in test.
- The clearly named **Rollout validation presentation** was created through ordinary chat, with
  source evidence and an exclusive tomorrow-before-21:00 UTC deadline. Quiet hours temporarily
  covering the current hour deferred its check outside that interval. Only the validation plan
  and explicitly enabled preferences were exercised; original commitments were not changed.
- Live correction moved its deadline to Thursday 2026-10-29 18:00 UTC. Unavailable evenings were
  recorded through 2026-11-01, preserved the purpose, replaced the evening next action and moved the
  next check to the following morning. An explicit conversational reversal of this temporary
  restriction restored a 15-minute cadence for a real-clock check-in.
- Morning briefing and evening reflection each produced one actual owner-visible in-app output
  without a browser-driven request. Repeated scheduling recorded `routine_already_generated`
  skips rather than duplicate outputs. Temporary near-term routine times were used for verification;
  the owner's stored routine times are restored after the check-in test.

### Failures found and handled

1. Azure final-response generation returned `unavailable` on **two turns after their tool writes
   had succeeded** (initial creation and deadline correction). The original server receipts and
   durable records accurately reported the saved actions. Creation was not replayed and no duplicate
   commitment was created. Subsequent replanning/availability responses were delivered normally.
   The configured bounded gateway/provider availability remains a limitation; do not interpret a
   failed final wording call as evidence that the preceding write failed.
2. With another commitment present, an ID-only tool proposal was rejected even though the owner
   explicitly named the full title. Fixed in `a750646`: backend validation accepts the full named
   title while still rejecting unnamed/ambiguous references and duplicate titles. Regression tests
   cover both positive and negative cases; the real correction then updated the intended record.
3. A positive availability correction was intercepted by an awaiting evening reflection and saved
   as a journal entry instead of changing the plan. Fixed in `acaa10c`: availability/plan corrections
   bypass reflection capture. The regression exercises this exact pending-reflection case; live
   availability restoration then updated the existing record. The test journal/related evidence is
   retained transparently; there were no pre-existing journals to overwrite.

The full backend suite after both fixes passed **526 tests in 95.62s**, plus Ruff and mypy.
Final GitHub CI also passed. The runtime fixes and their regression tests were committed and pushed
before deploying the matching final release.

### Actual unattended check-in and OS-process recovery: PASS

The validation commitment's persisted check was due **2026-10-26 17:23:45 UTC**. The monitor stopped
the regular worker, API and frontend. A separate real-clock worker committed its claim and was
terminated with **actual `SIGKILL`** before executing the effect. Database evidence at that point:

```text
action 5a19e625-a581-4588-9532-90039e241855
state executing; attempt_count 1; message_id null; source_event_id null
lease_until 2026-10-26 17:24:53.462835 UTC
```

After restarting only the personal worker, the expired claim recovered at
**17:24:59.024782 UTC**, while the API and frontend were still absent:

```text
same action 5a19e625-a581-4588-9532-90039e241855
state succeeded; attempt_count 2
message 8c8e3c84-0732-40bc-b0ae-7e7dc40f3a97
source event 0f866522-f108-4554-b7d9-e5756f83e564
```

Two further actual worker subprocess sweeps left exactly one check-in effect. The API/frontend
were restarted; “Actually, I've finished the Rollout validation presentation” then produced a
successful Azure `update_commitment` receipt, version **5**, state **completed**, no next check.
The commitment has five source-linked revisions. No clock injection, fake delivery or external
channel was involved in this personal-stack check.

Final persisted outcomes: one successful personal check-in, one successful morning briefing,
one successful evening reflection, and one duplicate-suppression skip for each daily routine.
There are zero outbound/inbound channel-message records and zero enabled channel accounts.
The final preservation comparison again passed for every original record/content field; only
authorized metadata changes were excluded as documented above. A final real-browser check passed
after service recovery, and a second custom-format database dump preserves the verified `0012`
state/evidence separately from the untouched pre-rollout backup.

Private reproducible evidence/helpers are retained alongside the backup: `original-rows.json`,
`verify_database.py`, `recovery_smoke.py`, `personal_validation.py`, `crash_after_claim.py`,
`watch_personal.py`, `watch.log`, `restart-proof.json`, `browser_personal.mjs`, and a private
`launchagents-final.tgz` service-config archive. Do not publish these owner-specific artifacts.

### Current owner configuration / acceptance

- Open **http://localhost:3000** using the existing private access code.
- Personal check-ins, morning briefing and evening reflection are enabled. Per-commitment follow-up
  authorization is still required; the original commitments remain opted out.
- Original timezone **UTC**, morning time **11:58**, evening time **20:00**, companion name and
  temperament are preserved. Quiet hours are **21:00–08:00 UTC**. Today's routines already ran
  during validation, so they will not deliver twice; normal-time recurrence resumes tomorrow.
- Services are supervised independently of browser windows, while this Mac is awake and the user
  session is logged in. Frontend/backend/worker all run the clean `acaa10c` release checkout.
- The temporary validation commitment remains visibly completed; its journal/action/revision
  evidence is retained. No original conversation or memory was removed.
- Run the real owner capture → unattended check-in → correction/replan → completion trial. For a
  short trial, explicitly request in-app check-ins every 15 minutes and close the browser while
  leaving the Mac awake. Approval remains the owner's decision, separate from these agent-run checks.

Owner acceptance remains pending; the branch is not merged and Milestone 2 is not started.
