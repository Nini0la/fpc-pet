"""Prepare private Modal Secret JSON. Never prints a credential or connection URL.

Run with the backend environment, from the repository root. Output is ignored .local state.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def private_json(path, values):
    with open(path, "w", encoding="utf-8") as stream:
        os.chmod(path, 0o600)
        json.dump(values, stream, indent=2)


def main():
    from app.cloud_trial import window as valid_window
    from app.gateway import OpenAICompatibleGateway

    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=["prepare", "activate", "refresh", "extend"])
    parser.add_argument("--end-at", help="Explicit owner-authorized timezone-aware trial cutoff")
    args = parser.parse_args()
    state = ROOT / ".local/rollouts/modal-trial"
    if not state.is_dir():
        raise SystemExit("Create the private rollout directory first")
    os.chmod(state, 0o700)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    window = {
        "MICA_TRIAL_ACTIVE": "1" if args.operation == "activate" else "0",
        "MICA_TRIAL_START_AT": now.isoformat(),
        "MICA_TRIAL_END_AT": (now + timedelta(hours=46)).isoformat(),
    }
    if args.operation == "extend":
        if not args.end_at:
            raise SystemExit("extend requires the owner's explicit --end-at cutoff")
        window = json.loads((state / "window-secret.json").read_text())
        previous = valid_window(window)
        end = datetime.fromisoformat(args.end_at)
        if not previous or end.tzinfo is None or end <= max(now, previous[1]):
            raise SystemExit("Extension must be later than the valid existing cutoff and now")
        window["MICA_TRIAL_END_AT"] = end.isoformat()
        window["MICA_TRIAL_AUTHORIZED_END_AT"] = end.isoformat()
        if not valid_window(window):
            raise SystemExit("Invalid extended window")
    elif args.end_at:
        raise SystemExit("--end-at is only valid with extend")
    if args.operation in {"prepare", "refresh"}:
        values = {
            key: value for key, value in dotenv_values(ROOT / ".env").items() if value is not None
        }
        url = make_url(values["MICA_CLOUD_DATABASE_URL"]).set(drivername="postgresql+psycopg")
        if (
            not url.host
            or "-pooler" in url.host
            or url.query.get("sslmode")
            not in {
                "require",
                "verify-ca",
                "verify-full",
            }
        ):
            raise SystemExit("A direct SSL hosted PostgreSQL URL is required")
        gateway = OpenAICompatibleGateway.from_env(values)
        if gateway.provider != "azure_openai":
            raise SystemExit("This trial retains the existing Azure provider")
        revision = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
        runtime = {
            "APP_ENV": "production",
            "MODEL_MODE": "live",
            "PROVIDER": "azure_openai",
            "DATABASE_URL": url.render_as_string(hide_password=False),
            "ACCESS_CODE": values["ACCESS_CODE"],
            "SESSION_SECRET": values["SESSION_SECRET"],
            "ALLOWED_ORIGINS": values["ALLOWED_ORIGINS"],
            "AZURE_OPENAI_ENDPOINT": gateway.base_url,
            "AZURE_OPENAI_API_KEY": gateway.api_key,
            "AZURE_OPENAI_DEPLOYMENT": gateway.model,
            "AZURE_OPENAI_API_VERSION": gateway.api_version,
            "MODEL_MAX_OUTPUT_TOKENS": str(gateway.max_output_tokens),
            "MODEL_TIMEOUT_SECONDS": str(gateway.timeout_seconds),
            "TELEGRAM_BOT_TOKEN": values["TELEGRAM_BOT_TOKEN"],
            "CHANNEL_BRIDGE_URL": "",
            "CHANNEL_ACCOUNT_ID": "",
            "CHANNEL_BRIDGE_TOKEN": "",
            "MICA_DEPLOYED_REVISION": revision,
        }
        if gateway.reasoning_effort:
            runtime["MODEL_REASONING_EFFORT"] = gateway.reasoning_effort
        for key in (
            "MODEL_INPUT_COST_PER_MILLION",
            "MODEL_OUTPUT_COST_PER_MILLION",
            "MICA_MIN_CHECKIN_SECONDS",
            "MICA_REMINDERS_PER_HOUR",
            "MICA_REMINDERS_PER_DAY",
        ):
            if key in values:
                runtime[key] = values[key]
        backup = state / "pre-cloud.env"
        if not backup.exists():
            shutil.copyfile(ROOT / ".env", backup)
            os.chmod(backup, 0o600)
        private_json(state / "runtime-secret.json", runtime)
    if args.operation != "refresh":
        private_json(state / "window-secret.json", window)
    print(
        json.dumps(
            {
                "operation": args.operation,
                "window": window if args.operation != "refresh" else "unchanged",
                "secrets": "written only to private ignored rollout files",
            }
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        raise SystemExit("Trial preparation failed: " + type(error).__name__) from None
