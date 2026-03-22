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


# ---------------------------------------------------------------------------
# Concurrency tests
# ---------------------------------------------------------------------------


def _make_entry(title: str, workspace: Path) -> HeartbeatEntry:
    return HeartbeatEntry(
        source="github",
        event_type="ci_failure",
        title=title,
        timestamp=datetime.now(tz=timezone.utc),
        url=f"https://github.com/org/repo/actions/runs/{title}",
        priority="high",
    )


def test_concurrent_writes_preserve_all_entries(tmp_path: Path) -> None:
    """Both entries must survive sequential write_actionable calls."""
    config = GatewayConfig(workspace_path=tmp_path)
    writer = HeartbeatWriter(config)
    entry_a = _make_entry("run-111", tmp_path)
    entry_b = _make_entry("run-222", tmp_path)
    writer.write_actionable(entry_a)
    writer.write_actionable(entry_b)
    content = (tmp_path / "HEARTBEAT.md").read_text()
    assert "run-111" in content
    assert "run-222" in content


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Demonstrates the pre-lock race condition. SlowWriter intentionally bypasses "
        "FileLock to show that without a lock, last-write-wins silently drops an entry. "
        "This test is expected to fail and must continue to do so."
    ),
)
def test_race_condition_without_lock_drops_entry(tmp_path: Path) -> None:
    """Forces concurrent interleaving via barrier — without FileLock, one entry is lost.

    Uses a SlowWriter subclass that holds a barrier between read and write so
    both threads read the same baseline content before either thread writes,
    guaranteeing last-write-wins drops one entry when no lock is present.
    Marked xfail(strict=True): it must always fail — if it ever passes the suite
    breaks, which would mean the race was somehow eliminated in SlowWriter itself.
    """
    import threading

    barrier = threading.Barrier(2)

    class SlowWriter(HeartbeatWriter):
        """Pauses between read and write to force the race window."""

        def write_actionable(self, entry: HeartbeatEntry) -> None:  # type: ignore[override]
            self._ensure_heartbeat_exists()
            content = self._heartbeat_path.read_text(encoding="utf-8")
            # Both threads reach the barrier before either writes — classic race.
            barrier.wait(timeout=5)
            if self._is_duplicate(entry, content):
                return
            marker_pos = content.find(ACTIVE_TASKS_MARKER)
            if marker_pos == -1:
                content += f"\n{entry.to_markdown()}\n"
            else:
                insert_pos = marker_pos + len(ACTIVE_TASKS_MARKER)
                content = content[:insert_pos] + f"\n{entry.to_markdown()}" + content[insert_pos:]
            self._heartbeat_path.write_text(content, encoding="utf-8")

    config = GatewayConfig(workspace_path=tmp_path)
    writer = SlowWriter(config)

    errors = []

    def write(entry):
        try:
            writer.write_actionable(entry)
        except Exception as e:
            errors.append(f"err: {e}")

    entry_a = _make_entry("race-aaa", tmp_path)
    entry_b = _make_entry("race-bbb", tmp_path)
    t1 = threading.Thread(target=write, args=(entry_a,))
    t2 = threading.Thread(target=write, args=(entry_b,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert not errors, f"Thread errors: {errors}"
    content = writer._heartbeat_path.read_text()
    assert "race-aaa" in content
    assert "race-bbb" in content


def test_concurrent_writes_via_threads(tmp_path: Path) -> None:
    """10 threads writing simultaneously — all entries must appear."""
    import threading

    config = GatewayConfig(workspace_path=tmp_path)
    writer = HeartbeatWriter(config)
    errors = []

    def write(i):
        try:
            writer.write_actionable(_make_entry(f"run-{i:03d}", tmp_path))
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=write, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Write errors: {errors}"
    content = (tmp_path / "HEARTBEAT.md").read_text()
    for i in range(10):
        assert f"run-{i:03d}" in content, f"Entry run-{i:03d} missing"
