import hashlib
import hmac
import json
from pathlib import Path

import pytest

from heartbeat_gateway.adapters.linear import LinearAdapter
from heartbeat_gateway.config.schema import GatewayConfig, LinearWatchConfig, WatchConfig

FIXTURES = Path(__file__).parent.parent / "fixtures"
SECRET = "test-linear-secret"


def make_config(**linear_kwargs) -> GatewayConfig:
    return GatewayConfig(
        workspace_path=Path("/tmp"),
        soul_md_path=Path("/tmp/SOUL.md"),
        llm_api_key="test",
        watch=WatchConfig(linear=LinearWatchConfig(**linear_kwargs)),
    )


def sign(payload: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


@pytest.fixture
def blocked_payload() -> dict:
    return json.loads((FIXTURES / "linear_issue_blocked.json").read_text())


@pytest.fixture
def comment_payload() -> dict:
    return json.loads((FIXTURES / "linear_comment_unrelated.json").read_text())


class TestLinearAdapterNormalize:
    def test_normalizes_status_change(self, blocked_payload: dict) -> None:
        adapter = LinearAdapter(make_config())
        event = adapter.normalize(blocked_payload, {})
        assert event is not None
        assert event.source == "linear"
        assert event.event_type == "issue.status_changed"
        assert event.metadata["status_to"] == "Blocked"
        assert event.metadata["status_from"] == "In Progress"

    def test_normalizes_comment(self, comment_payload: dict) -> None:
        adapter = LinearAdapter(make_config())
        event = adapter.normalize(comment_payload, {})
        assert event is not None
        assert event.event_type == "comment.created"

    def test_unrecognized_type_returns_none(self) -> None:
        adapter = LinearAdapter(make_config())
        payload = {"action": "update", "type": "Cycle", "data": {}, "updatedFrom": {}}
        assert adapter.normalize(payload, {}) is None

    def test_issue_created(self) -> None:
        adapter = LinearAdapter(make_config())
        payload = {
            "action": "create",
            "type": "Issue",
            "createdAt": "2024-01-15T10:00:00.000Z",
            "data": {"id": "i1", "title": "New issue", "team": {"name": "Eng"}, "state": {"name": "Backlog"}},
            "updatedFrom": {},
        }
        event = adapter.normalize(payload, {})
        assert event is not None
        assert event.event_type == "issue.created"

    def test_condense_le_240_chars(self, blocked_payload: dict) -> None:
        adapter = LinearAdapter(make_config())
        assert len(adapter.condense(blocked_payload)) <= 240

    def test_condense_status_change_format(self, blocked_payload: dict) -> None:
        adapter = LinearAdapter(make_config())
        result = adapter.condense(blocked_payload)
        assert "Engineering" in result
        assert "Blocked" in result


class TestLinearAdapterSignature:
    def test_valid_signature_passes(self, blocked_payload: dict) -> None:
        adapter = LinearAdapter(make_config(secret=SECRET))
        raw = json.dumps(blocked_payload).encode()
        sig = sign(raw, SECRET)
        assert adapter.verify_signature(raw, {"x-linear-signature": sig}) is True

    def test_invalid_signature_returns_false(self, blocked_payload: dict) -> None:
        adapter = LinearAdapter(make_config(secret=SECRET))
        raw = json.dumps(blocked_payload).encode()
        assert adapter.verify_signature(raw, {"x-linear-signature": "badsig"}) is False

    def test_no_secret_always_passes(self, blocked_payload: dict) -> None:
        adapter = LinearAdapter(make_config())
        raw = json.dumps(blocked_payload).encode()
        assert adapter.verify_signature(raw, {}) is True
