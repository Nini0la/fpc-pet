from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.cloud_trial import TrialGateway, TrialTelegram, active, window
from app.gateway import GatewayError, OpenAICompatibleGateway
from app.telegram_transport import TelegramError, TelegramTransport

NOW = datetime(2026, 10, 28, 12, tzinfo=timezone.utc)


def settings():
    return {
        "MICA_TRIAL_ACTIVE": "1",
        "MICA_TRIAL_START_AT": NOW.isoformat(),
        "MICA_TRIAL_END_AT": (NOW + timedelta(hours=46)).isoformat(),
    }


def test_trial_window_is_bounded_and_exclusive():
    values = settings()
    assert active(values, NOW)
    assert active(values, NOW + timedelta(hours=45, minutes=59))
    assert not active(values, NOW - timedelta(seconds=1))
    assert not active(values, NOW + timedelta(hours=46))
    assert not active(values | {"MICA_TRIAL_ACTIVE": "0"}, NOW)
    assert not active({}, NOW)
    assert window(values | {"MICA_TRIAL_END_AT": (NOW + timedelta(hours=47)).isoformat()}) is None
    assert window(values | {"MICA_TRIAL_START_AT": "2026-10-28T12:00:00"}) is None


def test_expired_trial_never_calls_model_or_telegram(monkeypatch):
    monkeypatch.setenv("MICA_TRIAL_ACTIVE", "0")
    with patch.object(TelegramTransport, "send") as send:
        with pytest.raises(TelegramError, match="trial_expired"):
            TrialTelegram("unused").send("123", "should not leave")
        send.assert_not_called()
    with patch.object(OpenAICompatibleGateway, "complete") as model:
        gateway = TrialGateway(base_url="https://example.com/v1", api_key="test", model="test")
        with pytest.raises(GatewayError):
            gateway.complete([], [])
        model.assert_not_called()
