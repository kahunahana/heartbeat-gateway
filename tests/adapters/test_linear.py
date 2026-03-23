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


class TestLinearAdapterProjectName:
    """PG-4: condense() and normalize() must use project name, not team name."""

    @pytest.fixture
    def project_payload(self) -> dict:
        return {
            "action": "update",
            "type": "Issue",
            "createdAt": "2024-01-15T10:00:00.000Z",
            "data": {
                "id": "i2",
                "title": "Fix dedup fingerprint",
                "url": "https://linear.app/eng/issue/HG-1",
                "team": {"id": "team-1", "name": "RaPDS"},
                "project": {"id": "proj-1", "name": "Heartbeat-Gateway"},
                "state": {"name": "In Progress"},
                "priority": 2,
            },
            "updatedFrom": {},
        }

    def test_condense_uses_project_name_not_team_name(self, project_payload: dict) -> None:
        adapter = LinearAdapter(make_config())
        result = adapter.condense(project_payload)
        assert "Heartbeat-Gateway" in result, f"Expected project name in condensed output, got: {result}"
        assert "RaPDS" not in result, f"Team name must not appear when project name is available, got: {result}"

    def test_normalize_project_name_metadata_uses_project_not_team(self, project_payload: dict) -> None:
        adapter = LinearAdapter(make_config())
        event = adapter.normalize(project_payload, {})
        assert event is not None
        assert event.metadata["project_name"] == "Heartbeat-Gateway", (
            f"Expected project_name='Heartbeat-Gateway', got: {event.metadata['project_name']!r}"
        )

    def test_condense_falls_back_to_team_when_project_is_null(self) -> None:
        """project key present but null — must not raise AttributeError."""
        adapter = LinearAdapter(make_config())
        payload = {
            "action": "update",
            "type": "Issue",
            "createdAt": "2024-01-15T10:00:00.000Z",
            "data": {
                "id": "i3",
                "title": "Some issue",
                "team": {"id": "team-1", "name": "Engineering"},
                "project": None,
                "state": {"name": "Todo"},
                "priority": 0,
            },
            "updatedFrom": {},
        }
        result = adapter.condense(payload)
        assert "Engineering" in result

    def test_normalize_falls_back_to_team_when_project_is_null(self) -> None:
        """project key present but null — metadata project_name falls back to team name."""
        adapter = LinearAdapter(make_config())
        payload = {
            "action": "create",
            "type": "Issue",
            "createdAt": "2024-01-15T10:00:00.000Z",
            "data": {
                "id": "i4",
                "title": "Some issue",
                "team": {"id": "team-1", "name": "Engineering"},
                "project": None,
                "state": {"name": "Backlog"},
                "priority": 0,
            },
            "updatedFrom": {},
        }
        event = adapter.normalize(payload, {})
        assert event is not None
        assert event.metadata["project_name"] == "Engineering"


class TestLinearAdapterSignature:
    def test_valid_signature_passes(self, blocked_payload: dict) -> None:
        adapter = LinearAdapter(make_config(secret=SECRET))
        raw = json.dumps(blocked_payload).encode()
        sig = sign(raw, SECRET)
        assert adapter.verify_signature(raw, {"linear-signature": sig}) is True

    def test_invalid_signature_returns_false(self, blocked_payload: dict) -> None:
        adapter = LinearAdapter(make_config(secret=SECRET))
        raw = json.dumps(blocked_payload).encode()
        assert adapter.verify_signature(raw, {"linear-signature": "badsig"}) is False

    def test_no_secret_always_passes(self, blocked_payload: dict) -> None:
        adapter = LinearAdapter(make_config())
        raw = json.dumps(blocked_payload).encode()
        assert adapter.verify_signature(raw, {}) is True
