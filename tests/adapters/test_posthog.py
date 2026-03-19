import hashlib
import hmac
import json
from pathlib import Path

import pytest

from heartbeat_gateway.adapters.posthog import PostHogAdapter
from heartbeat_gateway.config.schema import GatewayConfig, PostHogWatchConfig, WatchConfig

FIXTURES = Path(__file__).parent.parent / "fixtures"
SECRET = "test-posthog-secret"

THRESHOLD_PAYLOAD: dict = {
    "type": "insight_threshold_alert",
    "insight": {"id": "insight-001", "name": "Daily Active Users"},
    "threshold": {"value": 1000, "type": "below"},
    "current_value": 450,
    "project_id": "proj-001",
    "timestamp": "2024-01-15T08:00:00Z",
}

ERROR_SPIKE_PAYLOAD: dict = {
    "type": "error_spike",
    "event": "Exception",
    "count": 250,
    "threshold": 50,
    "project_id": "proj-001",
    "timestamp": "2024-01-15T09:00:00Z",
}

FEATURE_FLAG_PAYLOAD: dict = {
    "event": "$feature_flag_called",
    "properties": {"$feature_flag": "new-dashboard", "$feature_flag_response": True},
    "project_id": "proj-001",
    "timestamp": "2024-01-15T10:00:00Z",
}


def make_config(**posthog_kwargs) -> GatewayConfig:
    return GatewayConfig(
        workspace_path=Path("/tmp"),
        soul_md_path=Path("/tmp/SOUL.md"),
        llm_api_key="test",
        watch=WatchConfig(posthog=PostHogWatchConfig(**posthog_kwargs)),
    )


def sign(payload: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


@pytest.fixture
def pageview_payload() -> dict:
    return json.loads((FIXTURES / "posthog_pageview.json").read_text())


class TestPostHogAdapterNormalize:
    def test_normalizes_threshold_breach(self) -> None:
        adapter = PostHogAdapter(make_config())
        event = adapter.normalize(THRESHOLD_PAYLOAD, {})
        assert event is not None
        assert event.source == "posthog"
        assert event.event_type == "insight.threshold"
        assert event.metadata["insight_name"] == "Daily Active Users"
        assert event.metadata["current_value"] == 450
        assert event.metadata["threshold_value"] == 1000

    def test_normalizes_error_spike(self) -> None:
        adapter = PostHogAdapter(make_config())
        event = adapter.normalize(ERROR_SPIKE_PAYLOAD, {})
        assert event is not None
        assert event.event_type == "error.spike"

    def test_normalizes_feature_flag(self) -> None:
        adapter = PostHogAdapter(make_config())
        event = adapter.normalize(FEATURE_FLAG_PAYLOAD, {})
        assert event is not None
        assert event.event_type == "feature_flag.new-dashboard"
        assert event.metadata["flag_key"] == "new-dashboard"

    def test_pageview_returns_none(self, pageview_payload: dict) -> None:
        adapter = PostHogAdapter(make_config())
        assert adapter.normalize(pageview_payload, {}) is None

    def test_unrecognized_event_returns_none(self) -> None:
        adapter = PostHogAdapter(make_config())
        assert adapter.normalize({"event": "$autocapture", "project_id": "p"}, {}) is None

    def test_condense_threshold_le_240_chars(self) -> None:
        adapter = PostHogAdapter(make_config())
        assert len(adapter.condense(THRESHOLD_PAYLOAD)) <= 240

    def test_condense_error_spike_le_240_chars(self) -> None:
        adapter = PostHogAdapter(make_config())
        assert len(adapter.condense(ERROR_SPIKE_PAYLOAD)) <= 240

    def test_condense_threshold_content(self) -> None:
        adapter = PostHogAdapter(make_config())
        result = adapter.condense(THRESHOLD_PAYLOAD)
        assert "Daily Active Users" in result
        assert "450" in result


class TestPostHogAdapterSignature:
    def test_valid_signature_passes(self) -> None:
        adapter = PostHogAdapter(make_config(secret=SECRET))
        raw = json.dumps(THRESHOLD_PAYLOAD).encode()
        sig = sign(raw, SECRET)
        assert adapter.verify_signature(raw, {"posthog-signature": sig}) is True

    def test_invalid_signature_returns_false(self) -> None:
        adapter = PostHogAdapter(make_config(secret=SECRET))
        raw = json.dumps(THRESHOLD_PAYLOAD).encode()
        assert adapter.verify_signature(raw, {"posthog-signature": "badsig"}) is False

    def test_no_secret_always_passes(self) -> None:
        adapter = PostHogAdapter(make_config())
        raw = json.dumps(THRESHOLD_PAYLOAD).encode()
        assert adapter.verify_signature(raw, {}) is True
