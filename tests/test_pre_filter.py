from datetime import datetime, timezone
from pathlib import Path

import pytest

from heartbeat_gateway import NormalizedEvent
from heartbeat_gateway.config.schema import (
    GatewayConfig,
    GitHubWatchConfig,
    LinearWatchConfig,
    PostHogWatchConfig,
    WatchConfig,
)
from heartbeat_gateway.pre_filter import ALWAYS_DROP, PreFilter


def make_event(source: str, event_type: str, metadata: dict | None = None) -> NormalizedEvent:
    return NormalizedEvent(
        source=source,  # type: ignore[arg-type]
        event_type=event_type,
        payload_condensed="test event",
        raw_payload={},
        timestamp=datetime(2026, 3, 19, 12, 0, 0, tzinfo=timezone.utc),
        metadata=metadata or {},
    )


def make_config(tmp_path: Path, **watch_kwargs) -> GatewayConfig:
    return GatewayConfig(
        workspace_path=tmp_path,
        soul_md_path=tmp_path / "SOUL.md",
        llm_api_key="test",
        watch=WatchConfig(**watch_kwargs),
    )


@pytest.fixture
def pre_filter() -> PreFilter:
    return PreFilter()


@pytest.fixture
def open_config(tmp_path: Path) -> GatewayConfig:
    """Config with no scoping restrictions."""
    return make_config(tmp_path)


# --- Always-drop rules ---


@pytest.mark.parametrize("event_type", ALWAYS_DROP["linear"])
def test_linear_always_drop(pre_filter: PreFilter, open_config: GatewayConfig, event_type: str) -> None:
    event = make_event("linear", event_type)
    dropped, reason = pre_filter.should_drop(event, open_config)
    assert dropped
    assert "always_drop" in reason


@pytest.mark.parametrize("event_type", ALWAYS_DROP["github"])
def test_github_always_drop(pre_filter: PreFilter, open_config: GatewayConfig, event_type: str) -> None:
    event = make_event("github", event_type)
    dropped, reason = pre_filter.should_drop(event, open_config)
    assert dropped
    assert "always_drop" in reason


@pytest.mark.parametrize("event_type", ALWAYS_DROP["posthog"])
def test_posthog_always_drop(pre_filter: PreFilter, open_config: GatewayConfig, event_type: str) -> None:
    event = make_event("posthog", event_type)
    dropped, reason = pre_filter.should_drop(event, open_config)
    assert dropped
    assert "always_drop" in reason


# --- GitHub scoping ---


def test_github_repo_not_in_watchlist_drops(pre_filter: PreFilter, tmp_path: Path) -> None:
    config = make_config(tmp_path, github=GitHubWatchConfig(repos=["owner/watched-repo"]))
    event = make_event("github", "pr.opened", metadata={"repo": "owner/other-repo"})
    dropped, reason = pre_filter.should_drop(event, config)
    assert dropped
    assert "repo_not_watched" in reason


def test_github_repo_in_watchlist_passes(pre_filter: PreFilter, tmp_path: Path) -> None:
    config = make_config(tmp_path, github=GitHubWatchConfig(repos=["owner/watched-repo"]))
    event = make_event("github", "pr.opened", metadata={"repo": "owner/watched-repo"})
    dropped, _ = pre_filter.should_drop(event, config)
    assert not dropped


def test_github_empty_watchlist_passes_all_repos(pre_filter: PreFilter, open_config: GatewayConfig) -> None:
    event = make_event("github", "pr.opened", metadata={"repo": "any/repo"})
    dropped, _ = pre_filter.should_drop(event, open_config)
    assert not dropped


def test_github_branch_not_watched_drops(pre_filter: PreFilter, tmp_path: Path) -> None:
    config = make_config(tmp_path, github=GitHubWatchConfig(branches=["main"]))
    event = make_event("github", "ci.failure", metadata={"branch": "feature/experiment"})
    dropped, reason = pre_filter.should_drop(event, config)
    assert dropped
    assert "branch_not_watched" in reason


def test_github_watched_branch_passes(pre_filter: PreFilter, tmp_path: Path) -> None:
    config = make_config(tmp_path, github=GitHubWatchConfig(branches=["main"]))
    event = make_event("github", "ci.failure", metadata={"branch": "main"})
    dropped, _ = pre_filter.should_drop(event, config)
    assert not dropped


def test_github_pr_from_feature_branch_not_dropped(pre_filter: PreFilter, tmp_path: Path) -> None:
    """PR events must not be branch-filtered — PR branches are ephemeral and never 'main'."""
    config = make_config(tmp_path, github=GitHubWatchConfig(branches=["main"]))
    event = make_event("github", "pull_request", metadata={"repo": "owner/repo", "branch": "feature/my-feature"})
    dropped, reason = pre_filter.should_drop(event, config)
    assert not dropped, f"PR event was incorrectly dropped: {reason}"


# --- Linear scoping ---


def test_linear_project_not_watched_drops(pre_filter: PreFilter, tmp_path: Path) -> None:
    config = make_config(tmp_path, linear=LinearWatchConfig(project_ids=["proj-abc"]))
    event = make_event("linear", "issue.updated", metadata={"project_id": "proj-xyz"})
    dropped, reason = pre_filter.should_drop(event, config)
    assert dropped
    assert "project_not_watched" in reason


def test_linear_empty_project_list_passes_all(pre_filter: PreFilter, open_config: GatewayConfig) -> None:
    event = make_event("linear", "issue.updated", metadata={"project_id": "any-project"})
    dropped, _ = pre_filter.should_drop(event, open_config)
    assert not dropped


# --- PostHog scoping ---


def test_posthog_wrong_project_drops(pre_filter: PreFilter, tmp_path: Path) -> None:
    config = make_config(tmp_path, posthog=PostHogWatchConfig(project_id="proj-123"))
    event = make_event("posthog", "insight.threshold", metadata={"project_id": "proj-999"})
    dropped, reason = pre_filter.should_drop(event, config)
    assert dropped
    assert "posthog_project_mismatch" in reason


def test_posthog_no_project_configured_passes_all(pre_filter: PreFilter, open_config: GatewayConfig) -> None:
    event = make_event("posthog", "insight.threshold", metadata={"project_id": "any"})
    dropped, _ = pre_filter.should_drop(event, open_config)
    assert not dropped


# --- Statelessness ---


def test_pre_filter_is_stateless(pre_filter: PreFilter, open_config: GatewayConfig) -> None:
    event = make_event("github", "pr.opened", metadata={"repo": "any/repo"})
    result1 = pre_filter.should_drop(event, open_config)
    result2 = pre_filter.should_drop(event, open_config)
    assert result1 == result2
