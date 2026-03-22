from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient

from heartbeat_gateway.app import create_app
from heartbeat_gateway.config.schema import GatewayConfig

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def _llm_mock(classification: str, rationale: str = "test rationale") -> AsyncMock:
    response = MagicMock()
    response.choices[0].message.content = json.dumps({"classification": classification, "rationale": rationale})
    return AsyncMock(return_value=response)


@pytest.fixture
def config(tmp_path):
    soul = tmp_path / "SOUL.md"
    soul.write_text("# SOUL\nFocus: shipping fast.\n")
    return GatewayConfig(workspace_path=tmp_path, soul_md_path=soul)


@pytest.fixture
def client(config):
    return TestClient(create_app(config))


# ── 1. Linear issue.blocked → ACTIONABLE → HEARTBEAT.md ─────────────────────


def test_linear_blocked_issue_writes_heartbeat(client, config):
    payload = _load("linear_issue_blocked.json")
    with patch("litellm.acompletion", _llm_mock("ACTIONABLE", "Blocked issue needs attention")):
        resp = client.post("/webhooks/linear", json=payload)
    assert resp.status_code == 200
    assert resp.json() == {"status": "actionable"}
    heartbeat = (config.workspace_path / "HEARTBEAT.md").read_text()
    assert "LINEAR:ISSUE.STATUS_CHANGED" in heartbeat
    assert "Blocked issue needs attention" in heartbeat


# ── 2. Linear comment.created (unrelated) → IGNORE → HEARTBEAT.md empty ────
# The comment fixture carries no projectId/teamId directly in data, so the
# pre-filter project-scoping check short-circuits (event_project is None).
# The classifier returns IGNORE, leaving HEARTBEAT.md unwritten.


def test_linear_comment_unrelated_not_written(client, config):
    payload = _load("linear_comment_unrelated.json")
    with patch("litellm.acompletion", _llm_mock("IGNORE", "unrelated to watched work")):
        resp = client.post("/webhooks/linear", json=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"
    assert not (config.workspace_path / "HEARTBEAT.md").exists()


# ── 3. GitHub ci.failure → ACTIONABLE → HEARTBEAT.md ───────────────────────


def test_github_ci_failure_writes_heartbeat(client, config):
    payload = _load("github_ci_failure.json")
    with patch("litellm.acompletion", _llm_mock("ACTIONABLE", "CI failed on main — investigate")):
        resp = client.post(
            "/webhooks/github",
            json=payload,
            headers={"X-GitHub-Event": "check_run"},
        )
    assert resp.status_code == 200
    assert resp.json() == {"status": "actionable"}
    heartbeat = (config.workspace_path / "HEARTBEAT.md").read_text()
    assert "GITHUB:CI.FAILURE" in heartbeat
    assert "CI failed on main" in heartbeat


# ── 4. GitHub star → adapter returns None → ignored, no LLM call ────────────
# GitHubAdapter._extract_event has no handler for "star" → normalize() returns
# None → pipeline short-circuits before pre-filter or classifier.


def test_github_star_ignored_no_llm(client, config):
    payload = _load("github_star.json")
    with patch("litellm.acompletion", AsyncMock(side_effect=AssertionError("LLM must not be called"))):
        resp = client.post(
            "/webhooks/github",
            json=payload,
            headers={"X-GitHub-Event": "star"},
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"
    assert not (config.workspace_path / "HEARTBEAT.md").exists()


# ── 5. PostHog $pageview → adapter returns None → ignored, no LLM call ──────
# PostHogAdapter._classify has no handler for bare $pageview events →
# normalize() returns None → pipeline short-circuits.


def test_posthog_pageview_ignored_no_llm(client, config):
    payload = _load("posthog_pageview.json")
    with patch("litellm.acompletion", AsyncMock(side_effect=AssertionError("LLM must not be called"))):
        resp = client.post("/webhooks/posthog", json=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"
    assert not (config.workspace_path / "HEARTBEAT.md").exists()


# ── 6. Classifier returns DELTA → DELTA.md written, HEARTBEAT.md empty ──────


def test_delta_verdict_writes_delta_md(client, config):
    payload = _load("linear_issue_blocked.json")
    with patch("litellm.acompletion", _llm_mock("DELTA", "status tracking info")):
        resp = client.post("/webhooks/linear", json=payload)
    assert resp.status_code == 200
    assert resp.json() == {"status": "delta"}
    assert not (config.workspace_path / "HEARTBEAT.md").exists()
    delta = (config.workspace_path / "DELTA.md").read_text()
    assert "LINEAR:ISSUE.STATUS_CHANGED" in delta


# ── 7. Dedup — two identical Linear events → one entry in HEARTBEAT.md ──────
# Linear issue blocked carries data.url in metadata → HeartbeatEntry.url is
# set → _is_duplicate fires on the second write via `→ {url}` presence check.


def test_duplicate_linear_events_deduped(client, config):
    payload = _load("linear_issue_blocked.json")
    with patch("litellm.acompletion", _llm_mock("ACTIONABLE", "Blocked issue needs attention")):
        resp1 = client.post("/webhooks/linear", json=payload)
        resp2 = client.post("/webhooks/linear", json=payload)
    assert resp1.json() == {"status": "actionable"}
    assert resp2.json() == {"status": "actionable"}
    heartbeat = (config.workspace_path / "HEARTBEAT.md").read_text()
    assert heartbeat.count("LINEAR:ISSUE.STATUS_CHANGED") == 1


# ── 8. Invalid JSON body → 500 ───────────────────────────────────────────────
# The route handler calls json.loads(body) manually — invalid JSON raises an
# exception caught by the `except Exception` block, which returns 500.


def test_invalid_json_returns_500(client, config):
    with patch("litellm.acompletion", AsyncMock(side_effect=AssertionError("LLM must not be called"))):
        resp = client.post(
            "/webhooks/linear",
            content=b"not valid json {{{{",
            headers={"content-type": "application/json"},
        )
    assert resp.status_code == 500
    assert resp.json() == {"status": "error"}


# ── 9. PostHog insight threshold alert → ACTIONABLE ─────────────────────────
# PostHog adapter dispatches on payload["type"] — no event header needed.


def test_posthog_threshold_alert_writes_heartbeat(client, config):
    msg = "Error rate exceeded threshold — investigate immediately"
    with patch("litellm.acompletion", _llm_mock("ACTIONABLE", msg)):
        payload = json.dumps(_load("posthog_threshold_alert.json")).encode()
        resp = client.post(
            "/webhooks/posthog",
            content=payload,
            headers={"Content-Type": "application/json"},
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "actionable"
    content = (config.workspace_path / "HEARTBEAT.md").read_text()
    assert "[POSTHOG:INSIGHT.THRESHOLD]" in content
    assert "Error rate exceeded threshold" in content


# ── 10. CI failure duplicate events → deduped ────────────────────────────────
# github_ci_failure.json produces entry.url=None (check_run adapter ignores html_url).
# Dedup must fall back to title fingerprint: "[GITHUB:CI.FAILURE] {title}".


def test_duplicate_ci_failure_not_written_twice(client, config):
    """CI failure has no URL — title-fingerprint dedup must prevent duplicate writes."""
    rationale = "CI failure on main requires immediate investigation"
    fingerprint = f"[GITHUB:CI.FAILURE] {rationale[:120]}"
    payload = json.dumps(_load("github_ci_failure.json")).encode()
    headers = {"Content-Type": "application/json", "X-GitHub-Event": "check_run"}

    with patch("litellm.acompletion", _llm_mock("ACTIONABLE", rationale)):
        client.post("/webhooks/github", content=payload, headers=headers)

    with patch("litellm.acompletion", _llm_mock("ACTIONABLE", rationale)):
        client.post("/webhooks/github", content=payload, headers=headers)

    content = (config.workspace_path / "HEARTBEAT.md").read_text()
    # Full fingerprint must appear exactly once
    assert content.count(fingerprint) == 1


# ── 11. Audit log written for ACTIONABLE event ───────────────────────────────


def test_audit_log_written_for_actionable(client, config):
    import json as _json

    rationale = "Blocked issue requires agent attention"
    with patch("litellm.acompletion", _llm_mock("ACTIONABLE", rationale)):
        payload = json.dumps(_load("linear_issue_blocked.json")).encode()
        client.post(
            "/webhooks/linear",
            content=payload,
            headers={"Content-Type": "application/json"},
        )
    audit_path = config.workspace_path / "audit.log"
    assert audit_path.exists(), "audit.log was not created"
    record = _json.loads(audit_path.read_text().strip().splitlines()[0])
    assert record["classification"] == "ACTIONABLE"
    assert record["source"] == "linear"
    assert record["rationale"] == rationale
