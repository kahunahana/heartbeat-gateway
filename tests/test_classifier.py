from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from heartbeat_gateway import NormalizedEvent
from heartbeat_gateway.classifier import Classifier
from heartbeat_gateway.config.schema import GatewayConfig

# ── helpers ──────────────────────────────────────────────────────────────────


def make_config(tmp_path: Path) -> GatewayConfig:
    return GatewayConfig(
        workspace_path=tmp_path,
        soul_md_path=tmp_path / "SOUL.md",
        llm_api_key="test-key",
    )


def make_event(
    event_type: str = "issue.assigned",
    payload_condensed: str = "Linear: issue assigned to you",
    metadata: dict | None = None,
) -> NormalizedEvent:
    return NormalizedEvent(
        source="linear",
        event_type=event_type,
        payload_condensed=payload_condensed,
        raw_payload={},
        timestamp=datetime(2026, 3, 19, 12, 0, 0, tzinfo=timezone.utc),
        metadata=metadata or {},
    )


def llm_mock(classification: str, rationale: str) -> AsyncMock:
    response = MagicMock()
    response.choices[0].message.content = json.dumps({"classification": classification, "rationale": rationale})
    return AsyncMock(return_value=response)


# ── tests ─────────────────────────────────────────────────────────────────────


async def test_actionable_populates_entry(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    event = make_event(
        event_type="ci.failure",
        metadata={"pr_url": "https://github.com/owner/repo/pull/1"},
    )

    with patch("litellm.acompletion", llm_mock("ACTIONABLE", "CI failed on main branch")):
        verdict = await Classifier(config).classify(event)

    assert verdict.verdict == "ACTIONABLE"
    assert verdict.entry is not None
    assert verdict.entry.source == "linear"
    assert verdict.entry.event_type == "ci.failure"
    assert verdict.entry.title == "CI failed on main branch"
    assert verdict.entry.url == "https://github.com/owner/repo/pull/1"
    assert verdict.entry.priority == "high"
    assert verdict.entry.timestamp == event.timestamp


async def test_delta_returns_no_entry(tmp_path: Path) -> None:
    config = make_config(tmp_path)

    with patch("litellm.acompletion", llm_mock("DELTA", "Worth noting")):
        verdict = await Classifier(config).classify(make_event())

    assert verdict.verdict == "DELTA"
    assert verdict.entry is None


async def test_ignore_returns_no_entry(tmp_path: Path) -> None:
    config = make_config(tmp_path)

    with patch("litellm.acompletion", llm_mock("IGNORE", "Not relevant")):
        verdict = await Classifier(config).classify(make_event())

    assert verdict.verdict == "IGNORE"
    assert verdict.entry is None


async def test_malformed_json_defaults_to_ignore(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    response = MagicMock()
    response.choices[0].message.content = "not valid json {"

    with patch("litellm.acompletion", AsyncMock(return_value=response)):
        verdict = await Classifier(config).classify(make_event())

    assert verdict.verdict == "IGNORE"
    assert verdict.rationale == "classifier error"


async def test_llm_exception_defaults_to_ignore(tmp_path: Path) -> None:
    config = make_config(tmp_path)

    with patch("litellm.acompletion", AsyncMock(side_effect=RuntimeError("network error"))):
        verdict = await Classifier(config).classify(make_event())

    assert verdict.verdict == "IGNORE"
    assert verdict.rationale == "classifier error"


async def test_missing_soul_md_completes(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    # soul_md_path points to a file that does not exist — should not raise

    with patch("litellm.acompletion", llm_mock("IGNORE", "no soul")):
        verdict = await Classifier(config).classify(make_event())

    assert verdict.verdict == "IGNORE"


async def test_missing_heartbeat_md_completes(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    # HEARTBEAT.md does not exist in tmp_path — should not raise

    with patch("litellm.acompletion", llm_mock("IGNORE", "no heartbeat")):
        verdict = await Classifier(config).classify(make_event())

    assert verdict.verdict == "IGNORE"


async def test_prompt_contains_payload_condensed(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    event = make_event(payload_condensed="unique-payload-marker-xyz")
    captured: list[dict] = []

    async def capturing_mock(**kwargs: object) -> MagicMock:
        captured.append(kwargs)  # type: ignore[arg-type]
        response = MagicMock()
        response.choices[0].message.content = json.dumps({"classification": "IGNORE", "rationale": "test"})
        return response

    with patch("litellm.acompletion", capturing_mock):
        await Classifier(config).classify(event)

    assert captured, "acompletion was not called"
    messages = captured[0]["messages"]
    assert any("unique-payload-marker-xyz" in m["content"] for m in messages)
