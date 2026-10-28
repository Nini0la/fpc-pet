"""Two bounded CPU cron functions; all conversational state stays in PostgreSQL."""

from __future__ import annotations

import os
from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "mica-owner-trial"
app = modal.App(APP_NAME)
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install_from_requirements(str(ROOT / "deploy/requirements.txt"))
    .add_local_dir(str(ROOT / "backend/app"), "/opt/mica/backend/app", copy=True)
    .env({"PYTHONPATH": "/opt/mica/backend"})
)
stop_image = modal.Image.debian_slim(python_version="3.11").pip_install("modal==1.5.4")
runtime_secret = modal.Secret.from_name("mica-owner-trial-runtime")
window_secret = modal.Secret.from_name("mica-owner-trial-window")


@app.function(
    image=image,
    secrets=[runtime_secret, window_secret],
    schedule=modal.Period(seconds=15),
    timeout=240,
    cpu=(0.25, 1.0),
    memory=(512, 1024),
    max_containers=1,
    scaledown_window=30,
    retries=0,
)
def worker():
    from app.cloud_trial import TrialGateway, TrialTelegram, active

    if not active():
        return {"status": "inactive"}
    try:
        from app.agent import AgentRuntime
        from app.main import SessionLocal
        from app.models import TelegramBot
        from app.scheduler import tick
        from app.telegram_transport import configured_bot_id
        from app.telegram_worker import run_once

        bot_id = configured_bot_id()
        assert bot_id, "Telegram configuration missing"
        transport = TrialTelegram(os.environ["TELEGRAM_BOT_TOKEN"])
        with SessionLocal() as db:
            assert db.get(TelegramBot, bot_id), "Restored Telegram identity missing"
        # No model polling: the existing scheduler is deterministic.
        scheduled = tick(SessionLocal, AgentRuntime())
        if active():
            run_once(SessionLocal, AgentRuntime(gateway=TrialGateway.from_env()), transport, bot_id)
        return {"status": "ok", "scheduled": scheduled}
    except Exception as error:
        # Provider/database error representations can contain private connection data.
        print("Trial iteration failed:", type(error).__name__, flush=True)
        return {"status": "retry_on_next_sweep", "error_type": type(error).__name__}


@app.function(
    image=stop_image,
    secrets=[window_secret],
    schedule=modal.Period(minutes=1),
    timeout=45,
    cpu=(0.125, 0.25),
    memory=(128, 256),
    max_containers=1,
    scaledown_window=2,
    retries=0,
)
def expire():
    import subprocess
    import sys
    from datetime import datetime, timezone

    # Only timing configuration is mounted here, never Azure/Telegram/DB credentials.
    try:
        end = datetime.fromisoformat(os.environ["MICA_TRIAL_END_AT"])
        if end.tzinfo is None or datetime.now(timezone.utc) < end:
            return {"status": "not_expired"}
    except (KeyError, ValueError):
        return {"status": "invalid_window"}
    identifier = os.environ.get("MODAL_APP_ID") or app.app_id
    if not identifier:
        raise RuntimeError("Cannot identify this app for expiry")
    result = subprocess.run(
        [sys.executable, "-m", "modal", "app", "stop", identifier, "--yes"],
        capture_output=True,
        timeout=30,
    )
    if result.returncode:
        raise RuntimeError("Trial expiry stop request failed")


@app.function(
    image=image,
    secrets=[runtime_secret, window_secret],
    timeout=60,
    cpu=(0.125, 0.5),
    memory=(256, 512),
    max_containers=1,
    scaledown_window=2,
)
def inspect_runtime(probe_only: bool = False):
    """Authenticated Modal RPC only. Returns metadata, never credentials or chat bodies."""
    from sqlalchemy import func, select, text

    from app.cloud_trial import active, window
    from app.main import SessionLocal
    from app.models import Message, TelegramBot, TelegramConnection, TelegramDelivery, User

    bounds = window()
    with SessionLocal() as db:
        if probe_only:
            from app.gateway import OpenAICompatibleGateway
            from app.telegram_transport import TelegramTransport

            transport = TelegramTransport(os.environ["TELEGRAM_BOT_TOKEN"])
            identity = transport.call("getMe")
            assert str(identity["id"]) == os.environ["TELEGRAM_BOT_TOKEN"].split(":", 1)[0]
            assert not transport.call("getWebhookInfo").get("url")
            reply = OpenAICompatibleGateway.from_env().complete(
                [{"role": "user", "content": "Reply with only OK. Connectivity check."}], []
            )
            return {
                "database_connected": db.scalar(text("SELECT 1")) == 1,
                "bot_username": identity["username"],
                "model": reply.model,
                "model_responded": bool(reply.content),
                "active": active(),
            }
        owner = db.scalar(select(User).where(User.username == "owner"))
        bot = db.get(TelegramBot, os.environ["TELEGRAM_BOT_TOKEN"].split(":", 1)[0])
        linked = db.scalar(select(TelegramConnection).where(TelegramConnection.user_id == owner.id))
        return {
            "active": active(),
            "ends_at": bounds[1].isoformat() if bounds else None,
            "revision": os.environ.get("MICA_DEPLOYED_REVISION"),
            "schema": db.scalar(text("SELECT version_num FROM alembic_version")),
            "owner_present": bool(owner),
            "telegram_linked": bool(linked and linked.linked),
            "telegram_heartbeat": str(bot.heartbeat_at) if bot else None,
            "scheduler_heartbeat": str(owner.autonomy_heartbeat_at),
            "message_count": db.scalar(select(func.count()).select_from(Message)),
            "deliveries": dict(
                db.execute(
                    select(TelegramDelivery.state, func.count()).group_by(TelegramDelivery.state)
                ).all()
            ),
        }
