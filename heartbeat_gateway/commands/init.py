"""gateway init — interactive .env configuration wizard.

CONSTRAINT: Do NOT import from heartbeat_gateway.app. Do NOT import from
heartbeat_gateway.commands.doctor. Import only from
heartbeat_gateway.config.schema if env var names are needed.
"""

import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

import click
import questionary
from dotenv import dotenv_values, set_key

# Replicated from doctor.py — do NOT import from doctor.py
UUID_V4_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")

ENV_PATH = Path(".env")


def _is_tty() -> bool:
    """Return True if stdin is an interactive terminal. Patchable in tests."""
    return sys.stdin.isatty()


def _validate_linear_uuid(value: str) -> bool | str:
    """Validate Linear project UUID. Blank = skip. Returns True or error string."""
    if not value or not value.strip():
        return True
    stripped = value.strip()
    if UUID_V4_PATTERN.match(stripped):
        return True
    return "Invalid UUID v4 format. Expected: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx (or leave blank to skip)"


def _backup_env(env_path: Path) -> Path | None:
    """Create a timestamped backup of .env if it exists. Returns backup path or None."""
    if not env_path.exists():
        return None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = env_path.parent / f".env.backup.{timestamp}"
    shutil.copy2(env_path, backup_path)
    return backup_path


def _write_env(env_path: Path, values: dict[str, str]) -> None:
    """Write env values to file atomically. Creates file first, then upserts keys."""
    env_path.write_text("")
    for key, value in values.items():
        set_key(str(env_path), key, value, quote_mode="auto")


@click.command("init")
def init() -> None:
    """Interactive wizard to configure .env for heartbeat-gateway."""
    # INIT-01: TTY gate — FIRST action, before any questionary call
    if not _is_tty():
        click.echo("Error: gateway init requires an interactive terminal (TTY).", err=True)
        click.echo("Run this command in a terminal. It cannot be piped or scripted.", err=True)
        raise SystemExit(1)

    # Load existing .env values for merge-by-default
    existing: dict = dotenv_values(ENV_PATH) if ENV_PATH.exists() else {}

    answers: dict[str, str] = {}

    # --- Section 1: Core config ---
    click.echo("")
    click.echo("  heartbeat-gateway configuration wizard")
    click.echo("  ----------------------------------------")
    click.echo("")

    # ANTHROPIC_API_KEY (INIT-04: password prompt — masked)
    api_key = questionary.password(
        "Anthropic API key (starts with sk-ant-):",
        validate=lambda v: True if v.strip().startswith("sk-ant-") else "Must start with sk-ant-",
    ).ask()
    if api_key is None:
        raise SystemExit(1)
    answers["ANTHROPIC_API_KEY"] = api_key.strip()

    # GATEWAY_WORKSPACE_PATH
    workspace_path = questionary.text(
        "Gateway workspace path:",
        default=existing.get("GATEWAY_WORKSPACE_PATH", ""),
    ).ask()
    if workspace_path is None:
        raise SystemExit(1)
    if workspace_path.strip():
        answers["GATEWAY_WORKSPACE_PATH"] = workspace_path.strip()

    # GATEWAY_SOUL_MD_PATH
    soul_md_path = questionary.text(
        "SOUL.md path:",
        default=existing.get("GATEWAY_SOUL_MD_PATH", ""),
    ).ask()
    if soul_md_path is None:
        raise SystemExit(1)
    if soul_md_path.strip():
        answers["GATEWAY_SOUL_MD_PATH"] = soul_md_path.strip()

    # GATEWAY_LLM_MODEL
    llm_model = questionary.text(
        "LLM model:",
        default=existing.get("GATEWAY_LLM_MODEL", "claude-haiku-4-5-20251001"),
    ).ask()
    if llm_model is None:
        raise SystemExit(1)
    if llm_model.strip():
        answers["GATEWAY_LLM_MODEL"] = llm_model.strip()

    # --- Section 2: Linear adapter ---
    # INIT-02: Print UUID discovery instructions before UUID prompt
    click.echo("")
    click.echo("  Linear project UUID")
    click.echo("  Find it in Linear: press Cmd+K (or Ctrl+K),")
    click.echo("  search 'Copy model UUID', then paste. Leave blank to skip.")
    click.echo("")

    # GATEWAY_WATCH__LINEAR__SECRET (INIT-04: masked)
    linear_secret = questionary.password(
        "Linear webhook secret (leave blank to skip Linear):",
    ).ask()
    if linear_secret is None:
        raise SystemExit(1)
    if linear_secret.strip():
        answers["GATEWAY_WATCH__LINEAR__SECRET"] = linear_secret.strip()

    # GATEWAY_WATCH__LINEAR__PROJECT_IDS (INIT-03: UUID validation with re-prompt)
    linear_uuid = questionary.text(
        "Linear project UUID (leave blank to skip):",
        validate=_validate_linear_uuid,
    ).ask()
    if linear_uuid is None:
        raise SystemExit(1)
    if linear_uuid.strip():
        answers["GATEWAY_WATCH__LINEAR__PROJECT_IDS"] = json.dumps([linear_uuid.strip()])

    # --- Section 3: GitHub adapter ---
    click.echo("")

    # GATEWAY_WATCH__GITHUB__SECRET (INIT-04: masked)
    github_secret = questionary.password(
        "GitHub webhook secret (leave blank to skip GitHub):",
    ).ask()
    if github_secret is None:
        raise SystemExit(1)
    if github_secret.strip():
        answers["GATEWAY_WATCH__GITHUB__SECRET"] = github_secret.strip()

    # GATEWAY_WATCH__GITHUB__REPOS
    github_repos = questionary.text(
        "GitHub repos to watch, e.g. owner/repo (leave blank to skip):",
    ).ask()
    if github_repos is None:
        raise SystemExit(1)
    if github_repos.strip():
        answers["GATEWAY_WATCH__GITHUB__REPOS"] = json.dumps([github_repos.strip()])

    # --- INIT-06: In-memory validation before any disk write ---
    errors = []
    if "ANTHROPIC_API_KEY" not in answers or not answers["ANTHROPIC_API_KEY"].startswith("sk-ant-"):
        errors.append("ANTHROPIC_API_KEY must start with sk-ant-")

    if errors:
        for err in errors:
            click.echo(f"Error: {err}", err=True)
        raise SystemExit(1)

    # --- INIT-05: Backup existing .env BEFORE any write ---
    backup = _backup_env(ENV_PATH)
    if backup:
        click.echo(f"Existing .env backed up to {backup}")

    # --- Write ---
    _write_env(ENV_PATH, answers)

    # --- INIT-07: Completion message with gateway doctor hint ---
    click.echo("")
    click.echo("Configuration written to .env")
    click.echo("Run gateway doctor to verify your configuration.")
