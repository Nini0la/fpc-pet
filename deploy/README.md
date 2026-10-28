# Temporary owner-only Modal trial

`modal_trial.py` runs the existing personal scheduler and Telegram adapter against the owner's
hosted PostgreSQL database. No public web endpoint, new identity provider, GPU or new model is used.
The web UI can still run locally against the same hosted database when the Mac is on.

Runtime secrets and the 46-hour trial window are separate Modal Secrets. Start disabled, verify
the image and restored database, stop local writers, then activate a fixed UTC start/end window.
The worker refuses work outside that window. A separate expiry function stops this app, not other
workspace apps. Resource/concurrency limits apply specifically to this deployment; no existing
workspace-wide budgets or unrelated apps are modified.

The exported requirements are generated from the existing lockfile:

```sh
# From backend/
uv export --frozen --no-dev --no-emit-project --no-hashes --format requirements-txt \
  --output-file ../deploy/requirements.txt
```

Keep `TELEGRAM_BOT_TOKEN`, database URLs, Azure keys and runtime/window JSON files outside Git.
The deployment image copies only application code and locked requirements, never `.env` or backups.

The active trial and exact expiry/recovery instructions are recorded in `docs/MODAL_TRIAL.md`.
Changing a Modal Secret does not necessarily restart warm containers: the identical deployment
may be skipped. For a deliberate window activation, stop/redeploy only `mica-owner-trial`, then
verify `inspect_runtime` reports the intended active window. Do not reset the window for routine fixes.
