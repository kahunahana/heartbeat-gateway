from __future__ import annotations

from pathlib import Path

import pytest

from heartbeat_gateway.app import create_app
from heartbeat_gateway.config.schema import (
    GatewayConfig,
    GitHubWatchConfig,
    LinearWatchConfig,
    PostHogWatchConfig,
    WatchConfig,
)


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
