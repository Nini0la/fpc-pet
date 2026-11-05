"""Isolated owner trial: replayed Telegram ingress, real inference/outbox/delivery.

Never polls Telegram updates, so the active owner deployment keeps its cursor.
Authenticated Modal RPC only; every actual DM is labeled as a controlled trial.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parents[1]
app = modal.App("mica-owner-canary")
image = (modal.Image.debian_slim(python_version="3.11")
         .pip_install_from_requirements(str(ROOT / "deploy/requirements.txt"))
         .add_local_dir(str(ROOT / "backend/app"), "/opt/mica/backend/app", copy=True)
         .env({"PYTHONPATH": "/opt/mica/backend"}))
runtime_secret = modal.Secret.from_name("mica-owner-canary-runtime")
window_secret = modal.Secret.from_name("mica-owner-canary-window")


def guarded_sessions():
    from sqlalchemy.engine import make_url

    from app.cloud_trial import active

    assert os.getenv("MICA_OWNER_CANARY") == "1"
    assert make_url(os.environ["DATABASE_URL"]).database.startswith("mica_owner_canary_")
    assert active(), "Canary window is inactive"
    from app.main import SessionLocal

    return SessionLocal


def transport():
    from app.cloud_trial import TrialTelegram
    from app.telegram_transport import TelegramError

    class CanaryTelegram(TrialTelegram):
        def updates(self, offset):
            return []  # Explicitly no getUpdates call; production owns inbound polling.

        def send(self, peer_id, content):
            if str(peer_id) != os.environ["MICA_CANARY_PEER_ID"]:
                raise TelegramError("canary_recipient_rejected")
            return super().send(peer_id, "[Mica controlled trial — replayed input]\n" + content)

    return CanaryTelegram(os.environ["TELEGRAM_BOT_TOKEN"])


@app.function(image=image, secrets=[runtime_secret, window_secret], schedule=modal.Period(seconds=15),
              timeout=240, cpu=(0.25, 1.0), memory=(512, 1024), max_containers=1,
              scaledown_window=30, retries=0)
def worker():
    from app.agent import AgentRuntime
    from app.cloud_trial import TrialGateway, active
    from app.scheduler import tick
    from app.telegram_worker import run_once

    if not active():
        return {"status": "inactive"}
    sessions = guarded_sessions()
    scheduled = tick(sessions, AgentRuntime())
    processed = run_once(sessions, AgentRuntime(gateway=TrialGateway.from_env()), transport(),
                         os.environ["TELEGRAM_BOT_TOKEN"].split(":", 1)[0])
    return {"scheduled": scheduled, "processed": processed, "polls_telegram": False}


@app.function(image=image, secrets=[runtime_secret, window_secret], timeout=90,
              cpu=(0.25, 1.0), memory=(512, 1024), max_containers=1,
              scaledown_window=10, retries=0)
def replay(case: str, content: str, source_at: str | None = None, fault: str | None = None):
    """Synthetic Telegram fixture, not a claim the owner sent a real incoming DM."""
    import re

    from sqlalchemy import func, select, text

    from app.agent import AgentRuntime
    from app.cloud_trial import TrialGateway
    from app.gateway import GatewayError
    from app.models import AgentEvent, TelegramBot, TelegramConnection, TelegramInput, User
    from app.telegram import ingest, process_one

    assert re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", case)
    assert content.strip() and len(content) <= 4000
    assert fault in {None, "initial_provider_failure", "final_provider_failure"}
    sessions = guarded_sessions()
    bot_id = os.environ["TELEGRAM_BOT_TOKEN"].split(":", 1)[0]
    with sessions.kw["bind"].connect() as lock:
        if not lock.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": int(bot_id)}):
            return {"busy": True}
        try:
            with sessions.begin() as db:
                owner = db.scalar(select(User).where(User.username == "owner"))
                prior = db.scalar(select(AgentEvent).where(
                    AgentEvent.user_id == owner.id, AgentEvent.external_id == f"canary:{case}"))
                if prior:
                    return {"case": case, "update_id": int(prior.request_fingerprint),
                            "replayed": True, "ingress": "synthetic"}
                assert not db.scalar(select(func.count()).select_from(TelegramInput).where(
                    TelegramInput.state.in_(["pending", "processing"])))
                link = db.scalar(select(TelegramConnection).where(TelegramConnection.user_id == owner.id))
                assert link.linked and link.peer_id == os.environ["MICA_CANARY_PEER_ID"]
                bot = db.get(TelegramBot, bot_id)
                number = bot.next_update_id + 1
                now = datetime.now(timezone.utc)
                sent = datetime.fromisoformat(source_at) if source_at else now
                assert sent.tzinfo is not None
                ingest(db, bot, [{"update_id": number, "message": {
                    "message_id": number, "date": int(sent.timestamp()), "text": content,
                    "from": {"id": int(link.peer_id), "is_bot": False},
                    "chat": {"id": int(link.peer_id), "type": "private"},
                }}], now)
                db.add(AgentEvent(user_id=owner.id, external_id=f"canary:{case}",
                                  kind="canary_fixture", request_fingerprint=str(number)))
            if fault:
                class FaultGateway(TrialGateway):
                    calls = 0
                    fault_injected = False

                    def complete(self, messages, tools):
                        self.calls += 1
                        if ((fault == "initial_provider_failure" and self.calls == 1)
                                or (fault == "final_provider_failure" and self.calls == 2)):
                            self.fault_injected = True
                            raise GatewayError("unavailable")
                        return super().complete(messages, tools)

                fault_gateway = FaultGateway.from_env()
                process_one(sessions, AgentRuntime(gateway=fault_gateway), bot_id)
                from app.models import AssistanceRun

                with sessions.begin() as db:
                    event = db.scalar(select(AgentEvent).where(
                        AgentEvent.external_id == f"telegram:{bot_id}:{number}"))
                    run = db.scalar(select(AssistanceRun).where(AssistanceRun.event_id == event.id))
                    run.policy = {**run.policy, "acceptance_injected_fault":
                                  fault if fault_gateway.fault_injected else None}
            return {"case": case, "update_id": number, "ingress": "synthetic", "fault": fault}
        finally:
            lock.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": int(bot_id)})


@app.function(image=image, secrets=[runtime_secret, window_secret], timeout=60,
              cpu=(0.125, 0.5), memory=(256, 512), max_containers=1,
              scaledown_window=10, retries=0)
def inspect(case: str | None = None):
    from sqlalchemy import select, text

    from app.commitments import describe
    from app.continuation import plan_data, proposal_data
    from app.models import (
        AgentEvent, AssistanceRun, Commitment, ConversationProposal, JournalEntry,
        Message, ReminderPlan, ScheduledAction, TelegramDelivery, TelegramInput, User,
    )

    sessions = guarded_sessions()
    with sessions() as db:
        owner = db.scalar(select(User).where(User.username == "owner"))
        result = {"revision": os.getenv("MICA_DEPLOYED_REVISION"),
                  "schema": db.scalar(text("select version_num from alembic_version")),
                  "model": os.getenv("NEBIUS_MODEL"), "reasoning": os.getenv("NEBIUS_REASONING_EFFORT"),
                  "max_tokens": os.getenv("MODEL_MAX_OUTPUT_TOKENS"), "ingress": "synthetic_replay",
                  "delivery": "actual_owner_telegram_dm", "polls_telegram": False,
                  "commitments": [describe(r, owner, db) for r in db.scalars(select(Commitment))],
                  "plans": [plan_data(r, db) for r in db.scalars(select(ReminderPlan))],
                  "proposals": [proposal_data(r) for r in db.scalars(select(ConversationProposal))],
                  "journals": [{"id": j.id, "content": j.corrected_content or j.original_content}
                               for j in db.scalars(select(JournalEntry))],
                  "actions": [{"id": a.id, "kind": a.kind, "state": a.state,
                               "plan_id": a.reminder_plan_id, "commitment_id": a.commitment_id,
                               "message_id": a.message_id, "due_at": str(a.due_at),
                               "completed_at": str(a.completed_at)}
                              for a in db.scalars(select(ScheduledAction))],
                  "deliveries": [{"id": d.id, "message_id": d.message_id, "action_id": d.action_id,
                                   "state": d.state, "provider_message_id": d.provider_message_id}
                                  for d in db.scalars(select(TelegramDelivery))]}
        if case:
            marker = db.scalar(select(AgentEvent).where(AgentEvent.external_id == f"canary:{case}"))
            if marker is None:
                return {**result, "case": None}
            update_id = int(marker.request_fingerprint)
            incoming = db.scalar(select(TelegramInput).where(TelegramInput.update_id == update_id))
            bot_id = os.environ["TELEGRAM_BOT_TOKEN"].split(":", 1)[0]
            event = db.scalar(select(AgentEvent).where(
                AgentEvent.external_id == f"telegram:{bot_id}:{update_id}"))
            run = db.scalar(select(AssistanceRun).where(AssistanceRun.event_id == event.id)) if event else None
            message = db.get(Message, run.message_id) if run and run.message_id else None
            result["case"] = {"name": case, "input_state": incoming.state if incoming else None,
                              "run_id": run.id if run else None, "status": run.execution_status if run else None,
                              "message_id": message.id if message else None,
                              "response": message.content if message else None,
                              "trace": run.context_trace if run else None}
        return result


stop_image = modal.Image.debian_slim(python_version="3.11").pip_install("modal==1.5.4")


@app.function(image=stop_image, secrets=[window_secret], schedule=modal.Period(minutes=1),
              timeout=45, cpu=(0.125, 0.25), memory=(128, 256), max_containers=1, retries=0)
def expire():
    import subprocess
    import sys

    if datetime.now(timezone.utc) < datetime.fromisoformat(os.environ["MICA_TRIAL_END_AT"]):
        return {"status": "not_expired"}
    identifier = os.environ.get("MODAL_APP_ID") or app.app_id
    assert identifier
    result = subprocess.run([sys.executable, "-m", "modal", "app", "stop", identifier, "--yes"],
                            capture_output=True, timeout=30)
    assert result.returncode == 0, "Canary expiry failed"
