import json
from pathlib import Path

import pytest

from heartbeat_gateway.adapters.langsmith import LangSmithAdapter
from heartbeat_gateway.config.schema import GatewayConfig, LangSmithWatchConfig, WatchConfig

FIXTURES = Path(__file__).parent.parent / "fixtures"


def make_config(**langsmith_kwargs) -> GatewayConfig:
    return GatewayConfig(
        workspace_path=Path("/tmp"),
        soul_md_path=Path("/tmp/SOUL.md"),
        llm_api_key="test",
        watch=WatchConfig(langsmith=LangSmithWatchConfig(**langsmith_kwargs)),
    )


@pytest.fixture
def error_fixture() -> dict:
    return json.loads((FIXTURES / "langsmith_run_error.json").read_text())


@pytest.fixture
def clean_fixture() -> dict:
    return json.loads((FIXTURES / "langsmith_run_clean.json").read_text())


@pytest.fixture
def feedback_fixture() -> dict:
    return json.loads((FIXTURES / "langsmith_feedback.json").read_text())


@pytest.fixture
def alert_fixture() -> dict:
    return json.loads((FIXTURES / "langsmith_alert.json").read_text())


class TestLangSmithAdapterSignature:
    def test_token_match_returns_true(self, error_fixture: dict) -> None:
        adapter = LangSmithAdapter(make_config(token="test-token"))
        raw = json.dumps(error_fixture).encode()
        assert adapter.verify_signature(raw, {"x-langsmith-secret": "test-token"}) is True

    def test_token_mismatch_returns_false(self, error_fixture: dict) -> None:
        adapter = LangSmithAdapter(make_config(token="test-token"))
        raw = json.dumps(error_fixture).encode()
        assert adapter.verify_signature(raw, {"x-langsmith-secret": "wrong"}) is False

    def test_no_token_always_passes(self, error_fixture: dict) -> None:
        # LSMT-01: when token="" (unconfigured), all requests pass through
        adapter = LangSmithAdapter(make_config(token=""))
        raw = json.dumps(error_fixture).encode()
        assert adapter.verify_signature(raw, {}) is True


class TestLangSmithAdapterNormalize:
    def test_clean_run_returns_none(self, clean_fixture: dict) -> None:
        # LSMT-05: run.completed with error=null is always dropped
        adapter = LangSmithAdapter(make_config())
        assert adapter.normalize(clean_fixture, {}) is None

    def test_normalizes_run_error(self, error_fixture: dict) -> None:
        # LSMT-02: run.completed with error returns NormalizedEvent
        adapter = LangSmithAdapter(make_config())
        event = adapter.normalize(error_fixture, {})
        assert event is not None
        assert event.source == "langsmith"
        assert event.event_type == "run.error"
        assert event.metadata["run_name"] == "my-evaluation-chain"
        assert "Rate limit exceeded" in event.metadata["error_message"]

    def test_normalizes_run_error_metadata(self, error_fixture: dict) -> None:
        # LSMT-02: metadata includes session_name
        adapter = LangSmithAdapter(make_config())
        event = adapter.normalize(error_fixture, {})
        assert event is not None
        assert event.metadata["session_name"] == "production-eval"

    def test_normalizes_feedback(self, feedback_fixture: dict) -> None:
        # LSMT-03: feedback payload with negative score returns NormalizedEvent
        adapter = LangSmithAdapter(make_config())
        event = adapter.normalize(feedback_fixture, {})
        assert event is not None
        assert event.source == "langsmith"
        assert event.event_type == "feedback"
        assert event.metadata["feedback_key"] in ("user_score", "thumbs_down")
        assert event.metadata["feedback_score"] < 0

    def test_normalizes_alert(self, alert_fixture: dict) -> None:
        # LSMT-04: alert threshold payload returns NormalizedEvent
        adapter = LangSmithAdapter(make_config())
        event = adapter.normalize(alert_fixture, {})
        assert event is not None
        assert event.source == "langsmith"
        assert event.event_type == "alert.threshold"
        assert event.metadata["alert_rule_name"] == "High Error Rate"
        assert event.metadata["triggered_metric_value"] == 15
        assert event.metadata["triggered_threshold"] == 10

    def test_unrecognized_returns_none(self) -> None:
        adapter = LangSmithAdapter(make_config())
        assert adapter.normalize({"unknown_key": "val"}, {}) is None


class TestLangSmithAdapterCondense:
    def test_condense_run_error_le_240(self, error_fixture: dict) -> None:
        adapter = LangSmithAdapter(make_config())
        assert len(adapter.condense(error_fixture)) <= 240

    def test_condense_deterministic(self, error_fixture: dict) -> None:
        adapter = LangSmithAdapter(make_config())
        assert adapter.condense(error_fixture) == adapter.condense(error_fixture)

    def test_condense_alert_le_240(self, alert_fixture: dict) -> None:
        adapter = LangSmithAdapter(make_config())
        assert len(adapter.condense(alert_fixture)) <= 240

    def test_condense_no_timestamps(self, error_fixture: dict) -> None:
        # LSMT-08: condense must not include webhook_sent_at value
        adapter = LangSmithAdapter(make_config())
        result = adapter.condense(error_fixture)
        assert "2024-08-30T23:07:40.150000+00:00" not in result
