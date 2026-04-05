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
# Dedup falls back to payload_condensed fingerprint (deterministic, from adapter).
# This guards against the production bug where different LLM rationale on each call
# caused title-based fingerprints to miss duplicates.


def test_duplicate_ci_failure_not_written_twice(client, config):
    """CI failure has no URL — payload_condensed dedup must prevent duplicate writes
    even when the LLM generates different rationale text on each call."""
    payload = json.dumps(_load("github_ci_failure.json")).encode()
    headers = {"Content-Type": "application/json", "X-GitHub-Event": "check_run"}

    with patch("litellm.acompletion", _llm_mock("ACTIONABLE", "CI failure on main — first rationale")):
        client.post("/webhooks/github", content=payload, headers=headers)

    # Different rationale simulates non-deterministic LLM output for the same event
    with patch("litellm.acompletion", _llm_mock("ACTIONABLE", "CI failure — completely different rationale text")):
        client.post("/webhooks/github", content=payload, headers=headers)

    content = (config.workspace_path / "HEARTBEAT.md").read_text()
    assert content.count("- [ ] [GITHUB:CI.FAILURE]") == 1


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


# ── 12. Braintrust logs → ACTIONABLE → HEARTBEAT.md ────────────────────────
# BraintrustAdapter normalizes "logs" events with automation name and count.


def test_braintrust_logs_writes_heartbeat(client, config):
    payload = _load("braintrust_logs.json")
    msg = "Failing eval scores detected in production pipeline"
    with patch("litellm.acompletion", _llm_mock("ACTIONABLE", msg)):
        resp = client.post("/webhooks/braintrust", json=payload)
    assert resp.status_code == 200
    assert resp.json() == {"status": "actionable"}
    heartbeat = (config.workspace_path / "HEARTBEAT.md").read_text()
    assert "[BRAINTRUST:LOGS]" in heartbeat
    assert msg in heartbeat


# ── 13. Braintrust environment_update → DELTA → DELTA.md ──────────────────


def test_braintrust_env_update_writes_delta(client, config):
    payload = _load("braintrust_environment_update.json")
    with patch("litellm.acompletion", _llm_mock("DELTA", "Environment config changed")):
        resp = client.post("/webhooks/braintrust", json=payload)
    assert resp.status_code == 200
    assert resp.json() == {"status": "delta"}
    assert not (config.workspace_path / "HEARTBEAT.md").exists()
    delta = (config.workspace_path / "DELTA.md").read_text()
    assert "BRAINTRUST:ENVIRONMENT_UPDATE" in delta


# ── 14. Braintrust is_test → ignored, no LLM call ─────────────────────────
# Test deliveries are suppressed as the first line of normalize().


def test_braintrust_is_test_ignored_no_llm(client, config):
    payload = _load("braintrust_is_test.json")
    with patch("litellm.acompletion", AsyncMock(side_effect=AssertionError("LLM must not be called"))):
        resp = client.post("/webhooks/braintrust", json=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"
    assert not (config.workspace_path / "HEARTBEAT.md").exists()


# ── 15. Braintrust duplicate logs events → deduped ────────────────────────
# condense() uses automation name (deterministic), not count or timestamps.


def test_braintrust_duplicate_logs_deduped(client, config):
    payload = _load("braintrust_logs.json")
    with patch("litellm.acompletion", _llm_mock("ACTIONABLE", "Eval failure — first")):
        client.post("/webhooks/braintrust", json=payload)
    with patch("litellm.acompletion", _llm_mock("ACTIONABLE", "Eval failure — different rationale")):
        client.post("/webhooks/braintrust", json=payload)
    heartbeat = (config.workspace_path / "HEARTBEAT.md").read_text()
    assert heartbeat.count("[BRAINTRUST:LOGS]") == 1


# ── 16. LangSmith run error → ACTIONABLE → HEARTBEAT.md ───────────────────
# Shape B payload with error field populated.


def test_langsmith_run_error_writes_heartbeat(client, config):
    payload = _load("langsmith_run_error.json")
    msg = "Agent run failed — investigate error"
    with patch("litellm.acompletion", _llm_mock("ACTIONABLE", msg)):
        resp = client.post(
            "/webhooks/langsmith",
            json=payload,
            headers={"X-Langsmith-Secret": ""},
        )
    assert resp.status_code == 200
    assert resp.json() == {"status": "actionable"}
    heartbeat = (config.workspace_path / "HEARTBEAT.md").read_text()
    assert "[LANGSMITH:RUN.ERROR]" in heartbeat
    assert msg in heartbeat


# ── 17. LangSmith clean run → ignored, no LLM call ────────────────────────
# LSMT-05: clean completions (error=null) are always dropped.


def test_langsmith_clean_run_ignored_no_llm(client, config):
    payload = _load("langsmith_run_clean.json")
    with patch("litellm.acompletion", AsyncMock(side_effect=AssertionError("LLM must not be called"))):
        resp = client.post(
            "/webhooks/langsmith",
            json=payload,
            headers={"X-Langsmith-Secret": ""},
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"
    assert not (config.workspace_path / "HEARTBEAT.md").exists()


# ── 18. LangSmith feedback → ACTIONABLE → HEARTBEAT.md ────────────────────
# Shape A payload with negative feedback score.


def test_langsmith_feedback_writes_heartbeat(client, config):
    payload = _load("langsmith_feedback.json")
    msg = "Negative user feedback on agent output"
    with patch("litellm.acompletion", _llm_mock("ACTIONABLE", msg)):
        resp = client.post(
            "/webhooks/langsmith",
            json=payload,
            headers={"X-Langsmith-Secret": ""},
        )
    assert resp.status_code == 200
    assert resp.json() == {"status": "actionable"}
    heartbeat = (config.workspace_path / "HEARTBEAT.md").read_text()
    assert "[LANGSMITH:FEEDBACK]" in heartbeat
    assert msg in heartbeat


# ── 19. LangSmith alert → ACTIONABLE → HEARTBEAT.md ───────────────────────
# Alert threshold crossing event.


def test_langsmith_alert_writes_heartbeat(client, config):
    payload = _load("langsmith_alert.json")
    msg = "Alert threshold exceeded for latency metric"
    with patch("litellm.acompletion", _llm_mock("ACTIONABLE", msg)):
        resp = client.post(
            "/webhooks/langsmith",
            json=payload,
            headers={"X-Langsmith-Secret": ""},
        )
    assert resp.status_code == 200
    assert resp.json() == {"status": "actionable"}
    heartbeat = (config.workspace_path / "HEARTBEAT.md").read_text()
    assert "[LANGSMITH:ALERT.THRESHOLD]" in heartbeat
    assert msg in heartbeat


# ── 20. LangSmith auth rejection → 401 ────────────────────────────────────
# When a token is configured, mismatched X-Langsmith-Secret returns 401.


def test_langsmith_bad_token_returns_401(client, config):
    config.watch.langsmith.token = "correct-token"
    payload = _load("langsmith_run_error.json")
    with patch("litellm.acompletion", AsyncMock(side_effect=AssertionError("LLM must not be called"))):
        resp = client.post(
            "/webhooks/langsmith",
            json=payload,
            headers={"X-Langsmith-Secret": "wrong-token"},
        )
    assert resp.status_code == 401


# ── 21. Amplitude monitor_alert → ACTIONABLE → HEARTBEAT.md ───────────────
# Amplitude payloads have no signature — verify_signature always passes.


def test_amplitude_monitor_alert_writes_heartbeat(client, config):
    payload = _load("amplitude_monitor_alert.json")
    msg = "Error rate spike detected — requires attention"
    with patch("litellm.acompletion", _llm_mock("ACTIONABLE", msg)):
        resp = client.post("/webhooks/amplitude", json=payload)
    assert resp.status_code == 200
    assert resp.json() == {"status": "actionable"}
    heartbeat = (config.workspace_path / "HEARTBEAT.md").read_text()
    assert "[AMPLITUDE:MONITOR_ALERT]" in heartbeat
    assert msg in heartbeat


# ── 22. Amplitude chart.annotation → DELTA → DELTA.md ─────────────────────


def test_amplitude_annotation_writes_delta(client, config):
    payload = _load("amplitude_annotation.json")
    with patch("litellm.acompletion", _llm_mock("DELTA", "Chart annotation added")):
        resp = client.post("/webhooks/amplitude", json=payload)
    assert resp.status_code == 200
    assert resp.json() == {"status": "delta"}
    assert not (config.workspace_path / "HEARTBEAT.md").exists()
    delta = (config.workspace_path / "DELTA.md").read_text()
    assert "AMPLITUDE:CHART.ANNOTATION" in delta


# ── 23. Amplitude unknown event → ignored, no LLM call ────────────────────


def test_amplitude_unknown_ignored_no_llm(client, config):
    payload = {"event_type": "unknown_amplitude_event", "data": {}}
    with patch("litellm.acompletion", AsyncMock(side_effect=AssertionError("LLM must not be called"))):
        resp = client.post("/webhooks/amplitude", json=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"
    assert not (config.workspace_path / "HEARTBEAT.md").exists()


# ── 24. Amplitude duplicate monitor_alert → deduped ───────────────────────
# condense() uses charts[0]["header"] (deterministic), not what_happened (timestamp).


def test_amplitude_duplicate_monitor_alert_deduped(client, config):
    payload = _load("amplitude_monitor_alert.json")
    with patch("litellm.acompletion", _llm_mock("ACTIONABLE", "Alert — first rationale")):
        client.post("/webhooks/amplitude", json=payload)
    with patch("litellm.acompletion", _llm_mock("ACTIONABLE", "Alert — different rationale")):
        client.post("/webhooks/amplitude", json=payload)
    heartbeat = (config.workspace_path / "HEARTBEAT.md").read_text()
    assert heartbeat.count("[AMPLITUDE:MONITOR_ALERT]") == 1
