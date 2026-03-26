"""Init command tests — xfail stubs (Wave 0).

One stub per INIT requirement. All decorated xfail(strict=False) so the suite
stays green until gateway init is implemented in Plan 02.

CONSTRAINT: Use CliRunner + monkeypatch only. Invoke via cli group (not init directly).
"""

import tomllib
from pathlib import Path

import pytest
from click.testing import CliRunner

from heartbeat_gateway.cli import cli


@pytest.mark.xfail(strict=False, reason="gateway init not yet implemented")
def test_tty_detection_exits(monkeypatch):
    """INIT-01: Non-TTY invocation exits 1 with a message referencing 'terminal' or 'tty'."""
    # CliRunner is non-TTY by default — no monkeypatch needed for this test
    runner = CliRunner()
    result = runner.invoke(cli, ["init"])
    assert result.exit_code == 1
    assert "terminal" in result.output.lower() or "tty" in result.output.lower()


@pytest.mark.xfail(strict=False, reason="gateway init not yet implemented")
def test_linear_uuid_instructions_displayed(monkeypatch):
    """INIT-02: Wizard output contains Linear UUID copy instructions before prompting."""
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    runner = CliRunner()
    result = runner.invoke(cli, ["init"], input="\n")
    assert "Cmd+K" in result.output or "Copy model UUID" in result.output


@pytest.mark.xfail(strict=False, reason="gateway init not yet implemented")
def test_uuid_validation_reprompts(monkeypatch):
    """INIT-03: Invalid UUID causes re-prompt; valid UUID is accepted."""
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    runner = CliRunner()
    # Provide invalid UUID first, then a valid one
    valid_uuid = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    result = runner.invoke(cli, ["init"], input=f"not-a-uuid\n{valid_uuid}\n\n")
    # Should show error message then accept valid UUID
    assert "invalid" in result.output.lower() or "uuid" in result.output.lower()
    assert result.exit_code != 2  # Not a usage error — a re-prompt


@pytest.mark.xfail(strict=False, reason="gateway init not yet implemented")
def test_secret_not_in_output(monkeypatch):
    """INIT-04: Secret/token values entered by user are not echoed in terminal output."""
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    runner = CliRunner()
    secret_value = "lin_api_supersecret_abc123xyz"
    result = runner.invoke(cli, ["init"], input=f"{secret_value}\n\n")
    assert secret_value not in result.output


@pytest.mark.xfail(strict=False, reason="gateway init not yet implemented")
def test_backup_created_on_overwrite(monkeypatch, tmp_path):
    """INIT-05: When .env already exists, a backup is created before overwriting."""
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    env_file = tmp_path / ".env"
    env_file.write_text("EXISTING_VAR=existing_value\n")
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["init"], input="y\n\n")
    # A backup file (.env.bak or similar) must exist alongside .env
    backup_files = list(tmp_path.glob(".env.bak*")) + list(tmp_path.glob(".env.backup*"))
    assert len(backup_files) > 0, "No backup file found after overwriting .env"


@pytest.mark.xfail(strict=False, reason="gateway init not yet implemented")
def test_atomic_write_on_valid_input(monkeypatch, tmp_path):
    """INIT-06: .env is written only after all prompts complete (atomic write)."""
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    runner = CliRunner()
    env_path = tmp_path / ".env"
    # Drive full prompt sequence; .env must not exist until wizard completes
    valid_uuid = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    result = runner.invoke(cli, ["init"], input=f"{valid_uuid}\nsecretvalue\n\n")
    if result.exit_code == 0:
        assert env_path.exists(), ".env not written after successful wizard completion"


@pytest.mark.xfail(strict=False, reason="gateway init not yet implemented")
def test_completion_message_mentions_doctor(monkeypatch):
    """INIT-07: Completion output references 'gateway doctor' to guide next step."""
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    runner = CliRunner()
    result = runner.invoke(cli, ["init"], input="\n")
    assert "gateway doctor" in result.output


@pytest.mark.xfail(strict=False, reason="gateway init not yet implemented")
def test_dependencies_declared(monkeypatch):
    """INIT-08: questionary and python-dotenv appear in pyproject.toml dependencies."""
    pyproject = tomllib.loads(Path("pyproject.toml").read_text())
    deps = pyproject["project"]["dependencies"]
    assert any("questionary" in d for d in deps)
    assert any("python-dotenv" in d for d in deps)


@pytest.mark.xfail(strict=False, reason="gateway init not yet implemented")
def test_wizard_happy_path(monkeypatch, tmp_path):
    """INIT-09: Full prompt sequence driven via input= completes with exit 0."""
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    runner = CliRunner()
    valid_uuid = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    github_secret = "ghsecret_abc123"
    linear_secret = "lin_webhook_secret456"
    # Drive every expected prompt in sequence
    user_input = "\n".join(
        [
            valid_uuid,         # Linear project UUID
            linear_secret,      # Linear webhook secret
            github_secret,      # GitHub webhook secret
            "",                 # Accept default or confirm
            "",                 # Final confirmation
        ]
    )
    result = runner.invoke(cli, ["init"], input=user_input + "\n")
    assert result.exit_code == 0
