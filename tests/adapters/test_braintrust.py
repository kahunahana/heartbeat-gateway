import json
from pathlib import Path

import pytest

from heartbeat_gateway.adapters.braintrust import BraintrustAdapter
from heartbeat_gateway.config.schema import BraintrustWatchConfig, GatewayConfig, WatchConfig

FIXTURES = Path(__file__).parent.parent / "fixtures"


def make_config(**braintrust_kwargs) -> GatewayConfig:
    return GatewayConfig(
        workspace_path=Path("/tmp"),
        soul_md_path=Path("/tmp/SOUL.md"),
        llm_api_key="test",
        watch=WatchConfig(braintrust=BraintrustWatchConfig(**braintrust_kwargs)),
    )


@pytest.fixture
def logs_payload() -> dict:
    return json.loads((FIXTURES / "braintrust_logs.json").read_text())


@pytest.fixture
def is_test_payload() -> dict:
    return json.loads((FIXTURES / "braintrust_is_test.json").read_text())


@pytest.fixture
def env_update_payload() -> dict:
    return json.loads((FIXTURES / "braintrust_environment_update.json").read_text())


class TestBraintrustAdapterNormalize:
    def test_is_test_returns_none(self, is_test_payload: dict) -> None:
        adapter = BraintrustAdapter(make_config())
        assert adapter.normalize(is_test_payload, {}) is None

    def test_normalizes_logs_event(self, logs_payload: dict) -> None:
        adapter = BraintrustAdapter(make_config())
        event = adapter.normalize(logs_payload, {})
        assert event is not None
        assert event.source == "braintrust"
        assert event.event_type == "logs"
        assert "production-eval" in event.payload_condensed
        assert "High-Priority Factuality" in event.payload_condensed

    def test_normalizes_environment_update(self, env_update_payload: dict) -> None:
        adapter = BraintrustAdapter(make_config())
        event = adapter.normalize(env_update_payload, {})
        assert event is not None
        assert event.source == "braintrust"
        assert event.event_type == "environment_update"
        assert "production" in event.payload_condensed
        assert "update" in event.payload_condensed

    def test_unrecognized_event_returns_none(self) -> None:
        adapter = BraintrustAdapter(make_config())
        payload = {"automation": {"event_type": "unknown"}}
        assert adapter.normalize(payload, {}) is None

    def test_logs_metadata_fields(self, logs_payload: dict) -> None:
        adapter = BraintrustAdapter(make_config())
        event = adapter.normalize(logs_payload, {})
        assert event is not None
        assert event.metadata["project_name"] == "production-eval"
        assert event.metadata["automation_name"] == "High-Priority Factuality"
        assert event.metadata["count"] == 5

    def test_env_update_metadata_fields(self, env_update_payload: dict) -> None:
        adapter = BraintrustAdapter(make_config())
        event = adapter.normalize(env_update_payload, {})
        assert event is not None
        assert event.metadata["env_slug"] == "production"
        assert event.metadata["action"] == "update"


class TestBraintrustAdapterSignature:
    def test_verify_always_true_no_secret(self, logs_payload: dict) -> None:
        # option-b: Braintrust has no webhook signing — permanent passthrough
        adapter = BraintrustAdapter(make_config())
        raw = json.dumps(logs_payload).encode()
        assert adapter.verify_signature(raw, {}) is True

    def test_verify_always_true_with_any_headers(self, logs_payload: dict) -> None:
        # Passthrough regardless of headers present
        adapter = BraintrustAdapter(make_config())
        raw = json.dumps(logs_payload).encode()
        assert adapter.verify_signature(raw, {"x-some-header": "anyvalue"}) is True


class TestBraintrustAdapterCondense:
    def test_condense_logs_le_240(self, logs_payload: dict) -> None:
        adapter = BraintrustAdapter(make_config())
        assert len(adapter.condense(logs_payload)) <= 240

    def test_condense_deterministic(self, logs_payload: dict) -> None:
        adapter = BraintrustAdapter(make_config())
        assert adapter.condense(logs_payload) == adapter.condense(logs_payload)

    def test_condense_env_update_le_240(self, env_update_payload: dict) -> None:
        adapter = BraintrustAdapter(make_config())
        assert len(adapter.condense(env_update_payload)) <= 240
