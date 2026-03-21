from datetime import datetime, timezone
from pathlib import Path

import pytest

from heartbeat_gateway import HeartbeatEntry, NormalizedEvent
from heartbeat_gateway.config.schema import GatewayConfig
from heartbeat_gateway.writer import ACTIVE_TASKS_MARKER, HeartbeatWriter


@pytest.fixture
def config(tmp_path: Path) -> GatewayConfig:
    return GatewayConfig(
        workspace_path=tmp_path,
        soul_md_path=tmp_path / "SOUL.md",
        llm_api_key="test-key",
    )


@pytest.fixture
def writer(config: GatewayConfig) -> HeartbeatWriter:
    return HeartbeatWriter(config)


@pytest.fixture
def sample_entry() -> HeartbeatEntry:
    return HeartbeatEntry(
        source="github",
        event_type="ci.failure",
        title="CI failed on main - test-auth workflow",
        url="https://github.com/owner/repo/actions/runs/123",
        timestamp=datetime(2026, 3, 19, 12, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def sample_event() -> NormalizedEvent:
    return NormalizedEvent(
        source="linear",
        event_type="issue.status_changed",
        payload_condensed="Linear: [ENG] Auth blocked → Blocked",
        raw_payload={},
        timestamp=datetime(2026, 3, 19, 12, 0, 0, tzinfo=timezone.utc),
    )


def test_creates_heartbeat_when_absent(
    writer: HeartbeatWriter, sample_entry: HeartbeatEntry, config: GatewayConfig
) -> None:
    assert not writer.heartbeat_file_exists()
    writer.write_actionable(sample_entry)
    assert writer.heartbeat_file_exists()
    content = (config.workspace_path / "HEARTBEAT.md").read_text()
    assert "# Heartbeat Tasks" in content
    assert ACTIVE_TASKS_MARKER in content


def test_writes_correctly_formatted_entry(
    writer: HeartbeatWriter, sample_entry: HeartbeatEntry, config: GatewayConfig
) -> None:
    writer.write_actionable(sample_entry)
    content = (config.workspace_path / "HEARTBEAT.md").read_text()
    assert "- [ ] [GITHUB:CI.FAILURE]" in content
    assert "test-auth workflow" in content
    assert "https://github.com/owner/repo/actions/runs/123" in content


def test_deduplicates_same_url(writer: HeartbeatWriter, sample_entry: HeartbeatEntry, config: GatewayConfig) -> None:
    writer.write_actionable(sample_entry)
    writer.write_actionable(sample_entry)
    content = (config.workspace_path / "HEARTBEAT.md").read_text()
    assert content.count("CI failed on main") == 1


def test_writes_delta(writer: HeartbeatWriter, sample_event: NormalizedEvent, config: GatewayConfig) -> None:
    writer.write_delta(sample_event)
    delta_path = config.workspace_path / "DELTA.md"
    assert delta_path.exists()
    content = delta_path.read_text()
    assert "LINEAR:ISSUE.STATUS_CHANGED" in content
    assert "Auth blocked" in content


def test_heartbeat_entry_to_markdown(sample_entry: HeartbeatEntry) -> None:
    md = sample_entry.to_markdown()
    assert md.startswith("- [ ] [GITHUB:CI.FAILURE]")
    assert "test-auth workflow" in md
    assert "https://github.com/owner/repo/actions/runs/123" in md
    assert "2026-03-19T12:00:00+00:00" in md


def test_read_active_tasks_empty_when_no_file(writer: HeartbeatWriter) -> None:
    assert writer.read_active_tasks() == ""


def test_read_active_tasks_returns_section(writer: HeartbeatWriter, sample_entry: HeartbeatEntry) -> None:
    writer.write_actionable(sample_entry)
    tasks = writer.read_active_tasks()
    assert "CI failed on main" in tasks


def test_injects_marker_into_existing_file_without_marker(
    writer: HeartbeatWriter, sample_entry: HeartbeatEntry, config: GatewayConfig
) -> None:
    heartbeat_path = config.workspace_path / "HEARTBEAT.md"
    heartbeat_path.write_text("# Heartbeat Tasks\n\n## Active Tasks\n\n## Completed\n", encoding="utf-8")
    writer.write_actionable(sample_entry)
    content = heartbeat_path.read_text()
    assert ACTIVE_TASKS_MARKER in content
    marker_pos = content.find(ACTIVE_TASKS_MARKER)
    heading_pos = content.find("## Active Tasks")
    assert heading_pos < marker_pos


def test_inject_marker_is_idempotent(
    writer: HeartbeatWriter, sample_entry: HeartbeatEntry, config: GatewayConfig
) -> None:
    heartbeat_path = config.workspace_path / "HEARTBEAT.md"
    heartbeat_path.write_text("# Heartbeat Tasks\n\n## Active Tasks\n\n## Completed\n", encoding="utf-8")
    writer.write_actionable(sample_entry)
    writer.write_actionable(sample_entry)
    content = heartbeat_path.read_text()
    assert content.count(ACTIVE_TASKS_MARKER) == 1


def test_warns_when_no_active_tasks_heading(
    writer: HeartbeatWriter, sample_entry: HeartbeatEntry, config: GatewayConfig, caplog: pytest.LogCaptureFixture
) -> None:
    heartbeat_path = config.workspace_path / "HEARTBEAT.md"
    heartbeat_path.write_text("# Heartbeat Tasks\n\nSome content without the expected heading.\n", encoding="utf-8")
    import logging
    with caplog.at_level(logging.WARNING):
        writer.write_actionable(sample_entry)
    assert ACTIVE_TASKS_MARKER not in heartbeat_path.read_text()


def test_config_loads_from_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-api-key-from-env")
    config = GatewayConfig(workspace_path=tmp_path, soul_md_path=tmp_path / "SOUL.md")
    assert config.llm_api_key == "test-api-key-from-env"
