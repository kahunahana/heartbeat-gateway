import tomllib
from pathlib import Path


def test_click_explicit_dependency():
    """CLI-02: click must be an explicit dependency, not just transitive."""
    pyproject = Path("pyproject.toml")
    data = tomllib.loads(pyproject.read_text())
    deps = data["project"]["dependencies"]
    click_deps = [d for d in deps if d.startswith("click")]
    assert click_deps, "click must be an explicit dependency in pyproject.toml"


def test_entry_point_is_cli():
    """CLI-03: Entry point must be heartbeat_gateway.cli:cli."""
    pyproject = Path("pyproject.toml")
    data = tomllib.loads(pyproject.read_text())
    scripts = data["project"]["scripts"]
    assert scripts["heartbeat-gateway"] == "heartbeat_gateway.cli:cli"


def test_cli_group_importable():
    """CLI-01: cli group must be importable (entry point exists)."""
    from heartbeat_gateway.cli import cli

    assert cli is not None
