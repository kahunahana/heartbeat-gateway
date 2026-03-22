"""Tests for MCP server tools — verify correct file reads and response shapes."""

import pytest

from heartbeat_gateway.mcp_server import get_gateway_status, read_delta, read_heartbeat, read_soul


@pytest.fixture
def workspace(tmp_path):
    heartbeat = tmp_path / "HEARTBEAT.md"
    heartbeat.write_text(
        "# Heartbeat Tasks\n\n## Active Tasks\n\n"
        "<!-- heartbeat-gateway writes below this line -->\n"
        "- [ ] [GITHUB:CI.FAILURE] CI failed on main\n"
        "      \u2192 None | 2026-03-21T10:00:00+00:00\n\n## Completed\n",
        encoding="utf-8",
    )
    delta = tmp_path / "DELTA.md"
    delta.write_text("- [2026-03-21] [GITHUB:PR.OPENED] PR opened\n", encoding="utf-8")
    soul = tmp_path / "SOUL.md"
    soul.write_text("# SOUL\n\n## Current Focus\nShipping v0.1.1\n", encoding="utf-8")
    return tmp_path


def test_read_heartbeat_returns_active_tasks(workspace):
    result = read_heartbeat(workspace)
    assert "[GITHUB:CI.FAILURE]" in result
    assert "CI failed on main" in result


def test_read_delta_returns_recent_lines(workspace):
    result = read_delta(workspace, max_lines=5)
    assert "PR opened" in result


def test_read_soul_returns_contents(workspace):
    soul_path = workspace / "SOUL.md"
    result = read_soul(soul_path)
    assert "Shipping v0.1.1" in result


def test_get_gateway_status_returns_config(workspace):
    result = get_gateway_status(workspace, workspace / "SOUL.md")
    assert "workspace" in result
    assert "soul_md" in result
