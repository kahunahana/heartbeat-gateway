import json
from pathlib import Path

import pytest

from heartbeat_gateway.adapters.amplitude import AmplitudeAdapter
from heartbeat_gateway.config.schema import AmplitudeWatchConfig, GatewayConfig, WatchConfig

FIXTURES = Path(__file__).parent.parent / "fixtures"


def make_config(**amplitude_kwargs) -> GatewayConfig:
    return GatewayConfig(
        workspace_path=Path("/tmp"),
        soul_md_path=Path("/tmp/SOUL.md"),
        llm_api_key="test",
        watch=WatchConfig(amplitude=AmplitudeWatchConfig(**amplitude_kwargs)),
    )


@pytest.fixture
def monitor_alert_payload() -> dict:
    return json.loads((FIXTURES / "amplitude_monitor_alert.json").read_text())


@pytest.fixture
def annotation_payload() -> dict:
    return json.loads((FIXTURES / "amplitude_annotation.json").read_text())


class TestAmplitudeAdapterSignature:
    def test_verify_always_true_no_secret(self, monitor_alert_payload: dict) -> None:
        # Amplitude does not sign webhook deliveries — permanent passthrough
        adapter = AmplitudeAdapter(make_config())
        raw = json.dumps(monitor_alert_payload).encode()
        assert adapter.verify_signature(raw, {}) is True

    def test_verify_always_true_with_any_headers(self, monitor_alert_payload: dict) -> None:
        # Passthrough regardless of headers present
        adapter = AmplitudeAdapter(make_config())
        raw = json.dumps(monitor_alert_payload).encode()
        assert adapter.verify_signature(raw, {"x-amplitude-secret": "anything"}) is True


class TestAmplitudeAdapterNormalize:
    def test_normalizes_monitor_alert(self, monitor_alert_payload: dict) -> None:
        adapter = AmplitudeAdapter(make_config())
        event = adapter.normalize(monitor_alert_payload, {})
        assert event is not None
        assert event.source == "amplitude"
        assert event.event_type == "monitor_alert"
        assert event.metadata["metric_header"] == "DAU Monitor - 2025-05-12"
        assert "850" in event.metadata["metric_body"]

    def test_empty_charts_returns_none(self) -> None:
        adapter = AmplitudeAdapter(make_config())
        payload = {"event_type": "monitor_alert", "charts": []}
        assert adapter.normalize(payload, {}) is None

    def test_normalizes_annotation(self, annotation_payload: dict) -> None:
        adapter = AmplitudeAdapter(make_config())
        event = adapter.normalize(annotation_payload, {})
        assert event is not None
        assert event.source == "amplitude"
        assert event.event_type == "chart.annotation"
        assert event.metadata["annotation_label"] == "Deploy v2.3.0"
        assert event.metadata["chart_name"] == "Daily Active Users"

    def test_unrecognized_event_returns_none(self) -> None:
        adapter = AmplitudeAdapter(make_config())
        payload = {"event_type": "something_else"}
        assert adapter.normalize(payload, {}) is None


class TestAmplitudeAdapterCondense:
    def test_condense_uses_header_not_what_happened(self, monitor_alert_payload: dict) -> None:
        adapter = AmplitudeAdapter(make_config())
        result = adapter.condense(monitor_alert_payload)
        assert "DAU Monitor - 2025-05-12" in result
        assert "DAU Monitor crossed threshold at 2025-05-12T11:00:00Z" not in result

    def test_condense_le_240(self, monitor_alert_payload: dict) -> None:
        adapter = AmplitudeAdapter(make_config())
        assert len(adapter.condense(monitor_alert_payload)) <= 240

    def test_condense_deterministic(self, monitor_alert_payload: dict) -> None:
        adapter = AmplitudeAdapter(make_config())
        assert adapter.condense(monitor_alert_payload) == adapter.condense(monitor_alert_payload)
