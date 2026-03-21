from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient

from heartbeat_gateway import HeartbeatEntry, NormalizedEvent
from heartbeat_gateway.app import create_app
from heartbeat_gateway.classifier import ClassifierVerdict
from heartbeat_gateway.config.schema import GatewayConfig

# ── autouse safety net ────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _no_real_llm_calls():
    """Block accidental litellm calls in every server test."""
    with patch("litellm.acompletion", AsyncMock(side_effect=AssertionError("LLM called in test"))):
        yield


# ── shared fixtures ───────────────────────────────────────────────────────────


@pytest.fixture
def app():
    """App with all I/O components replaced by mocks."""
    application = create_app(GatewayConfig())
    application.state.linear_adapter = MagicMock()
    application.state.github_adapter = MagicMock()
    application.state.posthog_adapter = MagicMock()
    application.state.pre_filter = MagicMock()
    application.state.pre_filter.should_drop.return_value = (False, "")
    application.state.classifier = MagicMock()
    application.state.writer = MagicMock()
    return application


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def ts():
    return datetime(2024, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
def linear_event(ts):
    return NormalizedEvent(
        source="linear",
        event_type="issue.created",
        payload_condensed="Linear: [] Test issue",
        raw_payload={},
        timestamp=ts,
    )


@pytest.fixture
def github_event(ts):
    return NormalizedEvent(
        source="github",
        event_type="ci.failure",
        payload_condensed="GitHub: CI 'CI / test' failure on main — kahunahana/heartbeat-gateway",
        raw_payload={},
        timestamp=ts,
    )


@pytest.fixture
def posthog_event(ts):
    return NormalizedEvent(
        source="posthog",
        event_type="insight.threshold",
        payload_condensed="PostHog: insight 'Error rate' threshold crossed — 0.05 vs 0.01",
        raw_payload={},
        timestamp=ts,
    )


@pytest.fixture
def actionable_verdict(ts):
    entry = HeartbeatEntry(
        source="linear",
        event_type="issue.created",
        title="Review this issue",
        timestamp=ts,
    )
    return ClassifierVerdict(verdict="ACTIONABLE", rationale="needs review", entry=entry)


@pytest.fixture
def delta_verdict():
    return ClassifierVerdict(verdict="DELTA", rationale="informational", entry=None)


@pytest.fixture
def ignore_verdict():
    return ClassifierVerdict(verdict="IGNORE", rationale="not relevant", entry=None)


# ── sample payloads ───────────────────────────────────────────────────────────

LINEAR_PAYLOAD = {"action": "create", "type": "Issue", "data": {"title": "Test issue"}}

GITHUB_CI_PAYLOAD = {
    "action": "completed",
    "check_run": {
        "name": "CI / test",
        "conclusion": "failure",
        "head_sha": "abc123",
        "check_suite": {"head_branch": "main"},
    },
    "repository": {"full_name": "kahunahana/heartbeat-gateway"},
}

POSTHOG_THRESHOLD_PAYLOAD = {
    "type": "insight_threshold_alert",
    "insight": {"name": "Error rate"},
    "current_value": 0.05,
    "threshold": {"value": 0.01},
    "timestamp": "2024-01-01T00:00:00Z",
}


# ── Linear webhook tests ──────────────────────────────────────────────────────


def test_linear_webhook_actionable(app, client, linear_event, actionable_verdict):
    app.state.linear_adapter.verify_signature.return_value = True
    app.state.linear_adapter.normalize.return_value = linear_event
    app.state.classifier.classify = AsyncMock(return_value=actionable_verdict)

    resp = client.post("/webhooks/linear", json=LINEAR_PAYLOAD)

    assert resp.status_code == 200
    assert resp.json() == {"status": "actionable"}
    app.state.writer.write_actionable.assert_called_once_with(actionable_verdict.entry)


def test_linear_webhook_invalid_signature(app, client):
    app.state.linear_adapter.verify_signature.return_value = False

    resp = client.post("/webhooks/linear", json=LINEAR_PAYLOAD)

    assert resp.status_code == 401
    assert resp.json() == {"status": "unauthorized"}


# ── GitHub webhook tests ──────────────────────────────────────────────────────


def test_github_webhook_ci_failure(app, client, github_event, delta_verdict):
    app.state.github_adapter.verify_signature.return_value = True
    app.state.github_adapter.normalize.return_value = github_event
    app.state.classifier.classify = AsyncMock(return_value=delta_verdict)

    resp = client.post(
        "/webhooks/github",
        json=GITHUB_CI_PAYLOAD,
        headers={"X-GitHub-Event": "check_run"},
    )

    assert resp.status_code == 200
    assert resp.json()["status"] in {"actionable", "delta", "ignored"}


def test_github_webhook_invalid_signature(app, client):
    app.state.github_adapter.verify_signature.return_value = False

    resp = client.post("/webhooks/github", json=GITHUB_CI_PAYLOAD)

    assert resp.status_code == 401
    assert resp.json() == {"status": "unauthorized"}


# ── PostHog webhook tests ─────────────────────────────────────────────────────


def test_posthog_webhook_threshold_breach(app, client, posthog_event, actionable_verdict):
    app.state.posthog_adapter.verify_signature.return_value = True
    app.state.posthog_adapter.normalize.return_value = posthog_event
    app.state.classifier.classify = AsyncMock(return_value=actionable_verdict)

    resp = client.post("/webhooks/posthog", json=POSTHOG_THRESHOLD_PAYLOAD)

    assert resp.status_code == 200
    assert resp.json()["status"] in {"actionable", "delta", "ignored"}


def test_posthog_webhook_invalid_signature(app, client):
    app.state.posthog_adapter.verify_signature.return_value = False

    resp = client.post("/webhooks/posthog", json=POSTHOG_THRESHOLD_PAYLOAD)

    assert resp.status_code == 401
    assert resp.json() == {"status": "unauthorized"}


# ── Pipeline edge-case tests ──────────────────────────────────────────────────


def test_prefilter_drop_returns_ignored_with_reason(app, client, linear_event):
    app.state.linear_adapter.verify_signature.return_value = True
    app.state.linear_adapter.normalize.return_value = linear_event
    app.state.pre_filter.should_drop.return_value = (True, "always_drop:Issue.viewed")

    resp = client.post("/webhooks/linear", json=LINEAR_PAYLOAD)

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ignored"
    assert body["reason"] == "always_drop:Issue.viewed"
    app.state.classifier.classify.assert_not_called()


def test_adapter_normalize_none_returns_ignored_with_reason(app, client):
    app.state.linear_adapter.verify_signature.return_value = True
    app.state.linear_adapter.normalize.return_value = None

    resp = client.post("/webhooks/linear", json={"type": "unknown_event"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ignored"
    assert body["reason"] == "unrecognized_event_type"
    app.state.classifier.classify.assert_not_called()


def test_classifier_ignore_verdict_returns_ignored_with_reason(app, client, linear_event, ignore_verdict):
    app.state.linear_adapter.verify_signature.return_value = True
    app.state.linear_adapter.normalize.return_value = linear_event
    app.state.classifier.classify = AsyncMock(return_value=ignore_verdict)

    resp = client.post("/webhooks/linear", json=LINEAR_PAYLOAD)

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ignored"
    assert body["reason"] == "not relevant"
    app.state.writer.write_actionable.assert_not_called()
    app.state.writer.write_delta.assert_not_called()


# ── Health endpoint ───────────────────────────────────────────────────────────


def test_health_endpoint(client):
    resp = client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "version": "0.1.0"}


# ── Singular path redirect tests ──────────────────────────────────────────────


@pytest.mark.parametrize("source", ["linear", "github", "posthog"])
def test_singular_webhook_path_redirects(client, source):
    """POST /webhook/{source} (singular) must 308-redirect to /webhooks/{source} (plural)."""
    resp = client.post(f"/webhook/{source}", json={}, follow_redirects=False)

    assert resp.status_code == 308
    assert resp.headers["location"] == f"/webhooks/{source}"
