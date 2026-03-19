import hashlib
import hmac
import json
from pathlib import Path

import pytest

from heartbeat_gateway.adapters.github import GitHubAdapter
from heartbeat_gateway.config.schema import GatewayConfig, GitHubWatchConfig, WatchConfig

FIXTURES = Path(__file__).parent.parent / "fixtures"
SECRET = "test-github-secret"


def make_config(**github_kwargs) -> GatewayConfig:
    return GatewayConfig(
        workspace_path=Path("/tmp"),
        soul_md_path=Path("/tmp/SOUL.md"),
        llm_api_key="test",
        watch=WatchConfig(github=GitHubWatchConfig(**github_kwargs)),
    )


def sign(payload: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


@pytest.fixture
def ci_failure_payload() -> dict:
    return json.loads((FIXTURES / "github_ci_failure.json").read_text())


@pytest.fixture
def pr_merged_payload() -> dict:
    return json.loads((FIXTURES / "github_pr_merged.json").read_text())


@pytest.fixture
def star_payload() -> dict:
    return json.loads((FIXTURES / "github_star.json").read_text())


class TestGitHubAdapterNormalize:
    def test_normalizes_ci_failure(self, ci_failure_payload: dict) -> None:
        adapter = GitHubAdapter(make_config())
        event = adapter.normalize(ci_failure_payload, {"x-github-event": "check_run"})
        assert event is not None
        assert event.source == "github"
        assert event.event_type == "ci.failure"
        assert event.metadata["ci_conclusion"] == "failure"
        assert event.metadata["repo"] == "kahunahana/heartbeat-gateway"
        assert event.metadata["branch"] == "main"

    def test_normalizes_pr_merged(self, pr_merged_payload: dict) -> None:
        adapter = GitHubAdapter(make_config())
        event = adapter.normalize(pr_merged_payload, {"x-github-event": "pull_request"})
        assert event is not None
        assert event.event_type == "pr.merged"
        assert event.metadata["pr_number"] == 15
        assert event.metadata["repo"] == "kahunahana/heartbeat-gateway"

    def test_star_event_returns_none(self, star_payload: dict) -> None:
        adapter = GitHubAdapter(make_config())
        assert adapter.normalize(star_payload, {"x-github-event": "star"}) is None

    def test_unrecognized_event_returns_none(self) -> None:
        adapter = GitHubAdapter(make_config())
        assert adapter.normalize({}, {"x-github-event": "marketplace_purchase"}) is None

    def test_check_run_not_completed_returns_none(self, ci_failure_payload: dict) -> None:
        payload = {**ci_failure_payload, "action": "created"}
        adapter = GitHubAdapter(make_config())
        assert adapter.normalize(payload, {"x-github-event": "check_run"}) is None

    def test_pr_opened(self) -> None:
        adapter = GitHubAdapter(make_config())
        payload = {
            "action": "opened",
            "pull_request": {
                "number": 5,
                "title": "Add feature",
                "merged": False,
                "html_url": "https://github.com/org/repo/pull/5",
                "head": {"ref": "feature/x", "sha": "abc"},
                "base": {"ref": "main"},
            },
            "repository": {"full_name": "org/repo"},
        }
        event = adapter.normalize(payload, {"x-github-event": "pull_request"})
        assert event is not None
        assert event.event_type == "pr.opened"

    def test_condense_ci_le_240_chars(self, ci_failure_payload: dict) -> None:
        adapter = GitHubAdapter(make_config())
        assert len(adapter.condense(ci_failure_payload)) <= 240

    def test_condense_pr_le_240_chars(self, pr_merged_payload: dict) -> None:
        adapter = GitHubAdapter(make_config())
        assert len(adapter.condense(pr_merged_payload)) <= 240

    def test_condense_ci_content(self, ci_failure_payload: dict) -> None:
        adapter = GitHubAdapter(make_config())
        result = adapter.condense(ci_failure_payload)
        assert "CI" in result
        assert "failure" in result
        assert "main" in result


class TestGitHubAdapterSignature:
    def test_valid_signature_passes(self, ci_failure_payload: dict) -> None:
        adapter = GitHubAdapter(make_config(secret=SECRET))
        raw = json.dumps(ci_failure_payload).encode()
        sig = sign(raw, SECRET)
        assert adapter.verify_signature(raw, {"x-hub-signature-256": sig}) is True

    def test_invalid_signature_returns_false(self, ci_failure_payload: dict) -> None:
        adapter = GitHubAdapter(make_config(secret=SECRET))
        raw = json.dumps(ci_failure_payload).encode()
        assert adapter.verify_signature(raw, {"x-hub-signature-256": "sha256=badsig"}) is False

    def test_no_secret_always_passes(self, ci_failure_payload: dict) -> None:
        adapter = GitHubAdapter(make_config())
        raw = json.dumps(ci_failure_payload).encode()
        assert adapter.verify_signature(raw, {}) is True
