# Personal autonomy — Milestone 1 runbook

## Owner experience

In **Today → Personal follow-through → Open autonomy controls**, enable in-app check-ins,
morning briefing and/or evening reflection. All three are off after migration. Choose routine
times outside quiet hours in the profile's timezone. Equal quiet start/end disables the quiet
interval. Worker heartbeat is shown separately from the opt-ins: settings alone do not run a worker.

With chat's memory-write permission enabled, ask to track a definite intention:

> I need to finish my presentation before 9pm tomorrow. Help me stay on track.

The backend resolves the relative deadline in your timezone and preserves an exclusive **before**
boundary. Ambiguous phrases such as “next Friday afternoon” request clarification. A commitment
must have its own follow-ups enabled as well as the global check-in preference. If global check-ins
are off, the commitment can still be saved, but the receipt says no automatic follow-up is scheduled.

Use ordinary corrections, completion statements, or the Today controls to revise, pause, resume,
cancel or explicitly reopen a commitment. Superseded pending/claimed work is cancelled. The current
purpose is preserved unless explicitly changed. Availability can exclude morning, afternoon,
evening or night, including “this week” with a stored expiry date. This is bounded rescheduling,
not a general-purpose planner.

Autonomous output is a **persisted Chat message**, visible on return. It is not a push notification
or external message. Today exposes the current plan/next check, correction sources and execution
history: action, subject version, due time, reason, attempts, event ID and verified message ID.
The UI shows the latest 100 personal commitments/actions. Delegated responsibilities retain their
separate scope-review and completion-verification controls.

## Authorized rollout

The implementation is verified in an isolated stack. The existing personal database/services were
not upgraded by this work. Rollout requires the owner's authorization and a coordinated deployment
of this branch's backend, frontend and migration. Stop the old API/workers, take the normal database
backup, then run from `backend/` using the existing private configuration:

```sh
uv run --env-file ../.env alembic upgrade head
# Start the API with the existing service manager/configuration.
uv run --env-file ../.env python -m app.scheduler --personal-only
```

Keep this worker supervised alongside the API. It wakes every 10 seconds, persists a heartbeat,
and never polls an LLM for routine scheduling. `--once --personal-only` runs one normal-clock sweep.
The existing responsibility worker can continue to own approved external-channel workflows.
Running the scheduler without `--personal-only` also invokes that existing worker when a channel
is configured; the documented personal deployment uses `--personal-only`.

Build/restart the frontend with `NEXT_PUBLIC_API_URL` pointing to the deployed API, not the isolated
smoke-test port. Both frontend and backend must come from the same committed revision of
`feat/functional-autonomy`. Never use `MICA_TEST_NOW` in a normal
deployment; the API rejects it outside `APP_ENV=test`. Worker `--at` additionally requires `--once`.

## Delivery and failure semantics

- PostgreSQL stores the authoritative plan, action keys, claims, revisions and results. Claims use
  `FOR UPDATE SKIP LOCKED`, a 60-second lease and a unique token. Work locks the same owner conversation
  as API mutations, then rechecks current state and versions before effects.
- In-app Message, Reminder, event, action outcome and next check commit in **one transaction**.
  A pre-commit crash leaves no visible effect; an expired claim can be retried. A post-commit retry
  observes the durable outcome. This guarantee applies to the in-app database effect, not to push
  transport, browser rendering or arbitrary external providers.
- Up to three attempts per action, with retry backoff of 60 then 120 seconds. Permanent failure stays
  visible in execution history and is not blindly replayed. Review/correct the plan to schedule new
  work. A planned check time by itself is not delivery evidence; inspect its action status.
- At most three personal check-ins per local day; each plan defaults to three total check-ins and
  a 24-hour interval (owner-configurable: 15 minutes–one week, at most ten). Quiet hours and blocked
  availability defer work. If there is no available slot in the bounded eight-day search, the action
  records a skip rather than inventing availability. There is a bounded 1,000-candidate scan per owner.
- Daily skills retain their once-per-owner/local-date deduplication, including manual generation.
  Enabling a routine does not replay a pre-opt-in backlog. Missing DST wall times are skipped with
  evidence; a repeated wall time has one local-date occurrence. Ambiguous *deadline* folds require
  explicit clarification/offset.
- Unknown/external action kinds in the personal scheduler are skipped as unauthorized. The existing
  bridge's uncertainty/no-blind-resend and reviewed recipient/scope rules remain in force.
- Model interpretation still uses the existing bounded Azure gateway (at most two calls/two tools).
  No general browser/email/calendar execution or new inference provider is introduced.

## Disable / rollback

Uncheck opt-ins in Today to cancel pending actions and remove planned checks. Pause/cancel a single
commitment for narrower control. Stop the personal worker to disable all unattended personal work.
Keep migration `0012` when disabling: it retains correction/execution evidence.

If a schema rollback is necessary, stop the new API/workers and back up first. From `backend/`,
`uv run --env-file ../.env alembic downgrade 0011` drops the new action/revision tables and autonomy
fields, preserving original commitments and converting `paused` to legacy `waiting`. That loses
autonomy-specific evidence/settings; restore the backup if those are needed. Re-upgrading defaults
all opt-ins to off. Run the matching old application only after the schema rollback.

## Reproduce acceptance

Automated tests are destructive **only to the explicitly supplied disposable test database**:

```sh
# backend/
POSTGRES_TEST_URL=postgresql+psycopg:///mica_autonomy_test uv run pytest -q
uv run ruff check app tests
uv run mypy app
# frontend/
npm test -- --maxWorkers=1 --testTimeout=30000
npm run typecheck
npm run lint
npm run audit:ci
# whatsapp-bridge/
npm test
npm audit --omit=dev
```

`tests/test_autonomy.py` uses real PostgreSQL/API/transactions and scripted model interpretations.
Its crash fixtures raise a `BaseException` at preparation, claim, pre-effect-commit and
post-effect-commit, then use fresh sessions/runtime and overlapping worker threads. They do not
claim an OS `SIGKILL` test. Existing bridge tests use isolated fake transport; no real sends occur.
`tests/test_autonomy_migration.py` adds legacy-default/pause rollback checks; existing PostgreSQL
migration/regression tests also upgrade/downgrade through `0012`.

The manual smoke uses real Azure, migrated PostgreSQL, HTTP API processes, fresh authenticated
sessions, actual one-shot worker subprocesses and optionally Chromium against a production Next build:

```sh
# Once, create an isolated database; the script requires a *_smoke_test name.
createdb mica_autonomy_smoke_test
# backend/
DATABASE_URL=postgresql+psycopg:///mica_autonomy_smoke_test uv run alembic upgrade head
# frontend/
NEXT_PUBLIC_API_URL=http://127.0.0.1:8012 npm run build
# backend/; Azure settings are read from the existing root .env/provider configuration.
DATABASE_URL=postgresql+psycopg:///mica_autonomy_smoke_test \
  uv run python tests/live_autonomy_smoke.py
```

For browser verification, install Playwright/Chromium in an isolated tools directory, set
`PLAYWRIGHT_MODULE_PATH` to its absolute `node_modules/playwright` path and add `--with-browser`
to the last command. Ports 8012/3002 must be free. The script creates synthetic data and terminates
its API/frontend children on exit; it does not wipe existing data or contact a third party. Every
worker subprocess includes `--personal-only`. It leaves synthetic evidence for inspection and
disables that test owner's routine/check-in opt-ins before completion.

See `IMPLEMENTATION_STATUS.md` for exact observed results and the remaining owner trial gate.
