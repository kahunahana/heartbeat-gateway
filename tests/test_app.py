from __future__ import annotations

import json as _json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from heartbeat_gateway.app import MAX_BODY_BYTES, create_app
from heartbeat_gateway.config.schema import (
    AmplitudeWatchConfig,
    BraintrustWatchConfig,
    GatewayConfig,
    GitHubWatchConfig,
    LangSmithWatchConfig,
    LinearWatchConfig,
    PostHogWatchConfig,
    WatchConfig,
)


def make_gateway_config(
    tmp_path: Path,
    braintrust_secret: str = "",
    langsmith_token: str = "",
    amplitude_secret: str = "",
) -> GatewayConfig:
    """Factory helper for tests that need a GatewayConfig with optional adapter credentials."""
    return GatewayConfig(
        workspace_path=tmp_path,
        watch=WatchConfig(
            amplitude=AmplitudeWatchConfig(secret=amplitude_secret),
            braintrust=BraintrustWatchConfig(secret=braintrust_secret),
            langsmith=LangSmithWatchConfig(token=langsmith_token),
        ),
    )


def test_secrets_loaded_from_environment_variables(tmp_path: Path, monkeypatch):
    """GATEWAY_WATCH__GITHUB__SECRET (and linear/posthog) must be read from env vars.

    This test guards against the BaseSettings nesting bug where nested models
    instantiated via default_factory bypass env var loading entirely.
    """
    monkeypatch.setenv("GATEWAY_WATCH__GITHUB__SECRET", "gh-env-secret")
    monkeypatch.setenv("GATEWAY_WATCH__LINEAR__SECRET", "linear-env-secret")
    monkeypatch.setenv("GATEWAY_WATCH__POSTHOG__SECRET", "posthog-env-secret")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")

    config = GatewayConfig(workspace_path=tmp_path)

    assert config.watch.github.secret == "gh-env-secret", (
        "GitHub secret not loaded from GATEWAY_WATCH__GITHUB__SECRET — "
        "nested model likely instantiated via default_factory, bypassing env var loading"
    )
    assert config.watch.linear.secret == "linear-env-secret"
    assert config.watch.posthog.secret == "posthog-env-secret"


def test_require_signatures_raises_on_missing_secret(tmp_path: Path):
    """create_app must raise ValueError when require_signatures=True and a secret is absent."""
    config = GatewayConfig(
        workspace_path=tmp_path,
        require_signatures=True,
        watch=WatchConfig(github=GitHubWatchConfig(secret="")),
    )
    with pytest.raises(ValueError, match="github"):
        create_app(config)


def test_require_signatures_passes_when_all_secrets_set(tmp_path: Path):
    """create_app must succeed when require_signatures=True and all secrets present."""
    config = GatewayConfig(
        workspace_path=tmp_path,
        require_signatures=True,
        watch=WatchConfig(
            github=GitHubWatchConfig(secret="gh-secret"),
            linear=LinearWatchConfig(secret="linear-secret"),
            posthog=PostHogWatchConfig(secret="ph-secret"),
        ),
    )
    app = create_app(config)
    assert app is not None


def test_require_signatures_false_allows_missing_secret(tmp_path: Path):
    """Default require_signatures=False must not raise even with empty secrets."""
    config = GatewayConfig(workspace_path=tmp_path)
    app = create_app(config)
    assert app is not None


def test_body_too_large_returns_413(tmp_path: Path):
    """POST body above MAX_BODY_BYTES must be rejected with 413."""
    config = GatewayConfig(workspace_path=tmp_path)
    app = create_app(config)
    client = TestClient(app)
    large_body = b"x" * (MAX_BODY_BYTES + 1)
    response = client.post(
        "/webhooks/github",
        content=large_body,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413


def test_body_at_limit_is_not_rejected_by_size(tmp_path: Path):
    """POST body exactly at MAX_BODY_BYTES must not be rejected by size check (reaches sig check instead)."""
    config = GatewayConfig(workspace_path=tmp_path)
    app = create_app(config)
    client = TestClient(app)
    body = b'{"event": "' + b"x" * (MAX_BODY_BYTES - 20) + b'"}'
    response = client.post(
        "/webhooks/github",
        content=body,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code != 413


def test_classifier_failure_writes_failed_audit_record(tmp_path):
    """When classifier raises, a failed record must appear in audit.log."""
    config = GatewayConfig(workspace_path=tmp_path)
    app = create_app(config)

    app.state.classifier.classify = AsyncMock(side_effect=RuntimeError("LLM down"))
    app.state.github_adapter.verify_signature = lambda body, headers: True

    client = TestClient(app, raise_server_exceptions=False)
    payload = _json.dumps(
        {
            "action": "opened",
            "pull_request": {
                "title": "test PR",
                "html_url": "https://github.com/x/y/pull/1",
                "number": 1,
            },
        }
    )
    response = client.post(
        "/webhooks/github",
        content=payload,
        headers={"X-GitHub-Event": "pull_request", "Content-Type": "application/json"},
    )

    assert response.status_code == 500
    audit_path = tmp_path / "audit.log"
    assert audit_path.exists(), "audit.log must exist after failed processing"
    records = [_json.loads(line) for line in audit_path.read_text().splitlines() if line.strip()]
    failed = [r for r in records if r.get("status") == "failed"]
    assert len(failed) >= 1, f"Expected failed record, got: {records}"


class TestBraintrustWebhookRoute:
    """BTST-05: /webhooks/braintrust route integration tests."""

    LOGS_PAYLOAD = {
        "organization": {"id": "org-1", "name": "my-org"},
        "project": {"id": "proj-1", "name": "test-project"},
        "automation": {"id": "auto-1", "name": "Test Alert", "event_type": "logs"},
        "details": {"is_test": True, "message": "test", "count": 0, "related_logs_url": ""},
    }

    def test_is_test_payload_returns_ignored(self, tmp_path: Path):
        client = TestClient(create_app(make_gateway_config(tmp_path)))
        resp = client.post("/webhooks/braintrust", json=self.LOGS_PAYLOAD)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"

    def test_invalid_signature_always_passes_no_signing(self, tmp_path: Path):
        # Braintrust has no webhook signing — verify_signature is permanent passthrough (option-b).
        # Any request, including one with a bad header, must not return 401.
        config = make_gateway_config(tmp_path, braintrust_secret="real-secret")
        client = TestClient(create_app(config))
        resp = client.post(
            "/webhooks/braintrust",
            content=_json.dumps(self.LOGS_PAYLOAD).encode(),
            headers={"content-type": "application/json", "x-braintrust-signature": "badsig"},
        )
        assert resp.status_code != 401

    def test_no_secret_always_passes(self, tmp_path: Path):
        client = TestClient(create_app(make_gateway_config(tmp_path)))
        resp = client.post("/webhooks/braintrust", json=self.LOGS_PAYLOAD)
        assert resp.status_code == 200

    def test_singular_redirect(self, tmp_path: Path):
        client = TestClient(create_app(make_gateway_config(tmp_path)), follow_redirects=False)
        resp = client.post("/webhook/braintrust")
        assert resp.status_code == 308
        assert resp.headers["location"] == "/webhooks/braintrust"


class TestLangSmithWebhookRoute:
    """LSMT-06: /webhooks/langsmith route integration tests."""

    CLEAN_RUN_PAYLOAD = {
        "run_id": "uuid-001",
        "thread_id": "session-001",
        "assistant_id": "agent",
        "status": "success",
        "kwargs": {"run_type": "chain", "name": "test-chain", "session_name": "test"},
        "error": None,
    }

    RUN_ERROR_PAYLOAD = {
        "run_id": "uuid-002",
        "thread_id": "session-001",
        "assistant_id": "agent",
        "status": "error",
        "kwargs": {"run_type": "chain", "name": "test-chain", "session_name": "test"},
        "error": {"error": "TestError", "message": "Something failed"},
    }

    def test_clean_run_returns_ignored(self, tmp_path: Path):
        client = TestClient(create_app(make_gateway_config(tmp_path)))
        resp = client.post("/webhooks/langsmith", json=self.CLEAN_RUN_PAYLOAD)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"

    def test_wrong_token_returns_401(self, tmp_path: Path):
        config = make_gateway_config(tmp_path, langsmith_token="real-token")
        client = TestClient(create_app(config))
        resp = client.post(
            "/webhooks/langsmith",
            content=_json.dumps(self.RUN_ERROR_PAYLOAD).encode(),
            headers={"content-type": "application/json", "x-langsmith-secret": "wrong"},
        )
        assert resp.status_code == 401

    def test_no_token_always_passes(self, tmp_path: Path):
        client = TestClient(create_app(make_gateway_config(tmp_path)))
        resp = client.post("/webhooks/langsmith", json=self.CLEAN_RUN_PAYLOAD)
        assert resp.status_code == 200

    def test_singular_redirect(self, tmp_path: Path):
        client = TestClient(create_app(make_gateway_config(tmp_path)), follow_redirects=False)
        resp = client.post("/webhook/langsmith")
        assert resp.status_code == 308
        assert resp.headers["location"] == "/webhooks/langsmith"


class TestAmplitudeWebhookRoute:
    """AMPT-06: /webhooks/amplitude route integration tests."""

    MONITOR_ALERT_PAYLOAD = {
        "event_type": "monitor_alert",
        "charts": [
            {
                "header": "DAU Monitor - 2025-05-12",
                "body": "Current value: 850. Threshold: 1000.",
                "url": "https://analytics.amplitude.com/org/chart/abc123",
            }
        ],
        "what_happened": "DAU Monitor crossed threshold at 2025-05-12T11:00:00Z",
    }

    def test_amplitude_monitor_alert_returns_200(self, tmp_path: Path):
        """AMPT-06a: POST with monitor_alert payload returns 200."""
        client = TestClient(create_app(make_gateway_config(tmp_path)))
        resp = client.post("/webhooks/amplitude", json=self.MONITOR_ALERT_PAYLOAD)
        assert resp.status_code == 200
        assert resp.json()["status"] in ("actionable", "ignored", "delta")

    def test_amplitude_unknown_event_ignored(self, tmp_path: Path):
        """AMPT-06b: POST with unrecognized event_type returns ignored."""
        client = TestClient(create_app(make_gateway_config(tmp_path)))
        resp = client.post("/webhooks/amplitude", json={"event_type": "something_else"})
        assert resp.status_code == 200
        assert "ignored" in resp.text

    def test_amplitude_no_signature_always_passes(self, tmp_path: Path):
        """AMPT-06c: Amplitude never returns 401 — verify_signature is a permanent passthrough."""
        config = make_gateway_config(tmp_path, amplitude_secret="some-secret")
        client = TestClient(create_app(config))
        resp = client.post(
            "/webhooks/amplitude",
            content=_json.dumps({"event_type": "something_else"}).encode(),
            headers={"content-type": "application/json", "x-amplitude-signature": "badsig"},
        )
        assert resp.status_code != 401

    def test_amplitude_redirect_308(self, tmp_path: Path):
        """AMPT-06d: POST /webhook/amplitude returns 308 redirect preserving POST method."""
        client = TestClient(create_app(make_gateway_config(tmp_path)), follow_redirects=False)
        resp = client.post("/webhook/amplitude")
        assert resp.status_code == 308
        assert resp.headers["location"] == "/webhooks/amplitude"
