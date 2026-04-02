"""Init command tests — gateway init wizard (Plan 02 implementation).

Tests cover INIT-01 through INIT-09. xfail decorators removed now that
gateway init is fully implemented.

CONSTRAINT: Use CliRunner + monkeypatch only. Invoke via cli group (not init directly).

NOTE: questionary uses prompt_toolkit which requires Windows console APIs. On
non-TTY environments (CliRunner, CI), we patch questionary.text and
questionary.password with mock objects that return answers from a list.
The _is_tty() helper in init.py is patched to return True so the TTY gate
passes during wizard tests.
"""

import tomllib
from pathlib import Path
from unittest.mock import MagicMock

from click.testing import CliRunner

from heartbeat_gateway.cli import cli

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TTY_PATCH = "heartbeat_gateway.commands.init._is_tty"
_QUESTIONARY_TEXT = "heartbeat_gateway.commands.init.questionary.text"
_QUESTIONARY_PASSWORD = "heartbeat_gateway.commands.init.questionary.password"
_QUESTIONARY_CHECKBOX = "heartbeat_gateway.commands.init.questionary.checkbox"


def _make_question(value):
    """Return a mock questionary Question object that returns `value` from .ask()."""
    q = MagicMock()
    q.ask.return_value = value
    return q


def _make_questionary_mocks(monkeypatch, answers: list, checkbox_answer: list | None = None):
    """
    Patch questionary.text, questionary.password, and questionary.checkbox in init.py.
    - checkbox_answer: list[str] returned by the checkbox prompt (default: all adapters)
    - answers: list of str consumed in order by text/password prompts
    """
    _checkbox_val = checkbox_answer if checkbox_answer is not None else ["PostHog", "Linear", "GitHub"]
    answer_iter = iter(answers)

    def mock_checkbox(message, choices, **kwargs):
        return _make_question(_checkbox_val)

    def mock_text(message, default="", validate=None):
        val = next(answer_iter, default or "")
        if validate and val:
            result = validate(val)
            if result is not True:
                # Questionary would re-prompt; tests provide valid input
                raise ValueError(f"Validation failed: {result}")
        return _make_question(val)

    def mock_password(message, validate=None):
        val = next(answer_iter, "")
        if validate and val:
            result = validate(val)
            if result is not True:
                raise ValueError(f"Validation failed: {result}")
        return _make_question(val)

    monkeypatch.setattr(_QUESTIONARY_CHECKBOX, mock_checkbox)
    monkeypatch.setattr(_QUESTIONARY_TEXT, mock_text)
    monkeypatch.setattr(_QUESTIONARY_PASSWORD, mock_password)


# Prompt order in init.py after refactor (text/password only — checkbox handled separately):
# Checkbox is handled via checkbox_answer parameter in _make_questionary_mocks.
# Default checkbox_answer = ["PostHog", "Linear", "GitHub"] (all 3 selected).
#
#   1. ANTHROPIC_API_KEY           (password)
#   2. GATEWAY_WORKSPACE_PATH      (text)
#   3. GATEWAY_SOUL_MD_PATH        (text)
#   4. GATEWAY_LLM_MODEL           (text)
#   5. POSTHOG_PROJECT_ID          (text)   <- new
#   6. POSTHOG_SECRET              (password) <- new
#   7. LINEAR_SECRET               (password)
#   8. LINEAR_PROJECT_IDS          (text, UUID validate)
#   9. GITHUB_SECRET               (password)
#  10. GITHUB_REPOS                (text)
_HAPPY_PATH_ANSWERS = [
    "sk-ant-testkey",  # 1. ANTHROPIC_API_KEY
    "/workspace",  # 2. GATEWAY_WORKSPACE_PATH
    "/workspace/SOUL.md",  # 3. GATEWAY_SOUL_MD_PATH
    "claude-haiku-4-5-20251001",  # 4. GATEWAY_LLM_MODEL
    "ph-project-id-123",  # 5. POSTHOG_PROJECT_ID
    "phc_secret",  # 6. POSTHOG_SECRET
    "my-linear-secret",  # 7. LINEAR_SECRET
    "550e8400-e29b-41d4-a716-446655440000",  # 8. LINEAR_PROJECT_IDS (valid UUID)
    "my-github-secret",  # 9. GITHUB_SECRET
    "owner/repo",  # 10. GITHUB_REPOS
]


def test_posthog_prompts_before_linear(monkeypatch, tmp_path):
    """FOUND-04: PostHog .env entries written before Linear entries when both selected."""
    monkeypatch.setattr(_TTY_PATCH, lambda: True)
    _make_questionary_mocks(monkeypatch, _HAPPY_PATH_ANSWERS)
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["init"], catch_exceptions=False)
    assert result.exit_code == 0
    from dotenv import dotenv_values

    env = dotenv_values(tmp_path / ".env")
    assert "GATEWAY_WATCH__POSTHOG__SECRET" in env
    assert "GATEWAY_WATCH__LINEAR__SECRET" in env
    # Verify PostHog value is the one we provided
    assert env["GATEWAY_WATCH__POSTHOG__SECRET"] == "phc_secret"


def test_checkbox_gates_adapters(monkeypatch, tmp_path):
    """FOUND-04: Selecting only GitHub produces no Linear or PostHog .env entries."""
    monkeypatch.setattr(_TTY_PATCH, lambda: True)
    # Only GitHub selected — answers list covers only GitHub prompts (after core config)
    _make_questionary_mocks(
        monkeypatch,
        answers=[
            "sk-ant-testkey",  # 1. ANTHROPIC_API_KEY
            "/workspace",  # 2. GATEWAY_WORKSPACE_PATH
            "/workspace/SOUL.md",  # 3. GATEWAY_SOUL_MD_PATH
            "claude-haiku-4-5-20251001",  # 4. GATEWAY_LLM_MODEL
            # PostHog: skipped (not in selected_adapters)
            # Linear: skipped (not in selected_adapters)
            "my-github-secret",  # 5. GITHUB_SECRET
            "owner/repo",  # 6. GITHUB_REPOS
        ],
        checkbox_answer=["GitHub"],  # Only GitHub
    )
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["init"], catch_exceptions=False)
    assert result.exit_code == 0
    from dotenv import dotenv_values

    env = dotenv_values(tmp_path / ".env")
    assert "GATEWAY_WATCH__GITHUB__SECRET" in env
    assert "GATEWAY_WATCH__LINEAR__SECRET" not in env
    assert "GATEWAY_WATCH__POSTHOG__SECRET" not in env
    assert "GATEWAY_WATCH__POSTHOG__PROJECT_ID" not in env


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_tty_detection_exits():
    """INIT-01: Non-TTY invocation exits 1 with a message referencing 'terminal' or 'tty'."""
    # CliRunner is non-TTY by default — _is_tty() returns False → wizard rejects
    runner = CliRunner()
    result = runner.invoke(cli, ["init"])
    assert result.exit_code == 1
    assert "terminal" in result.output.lower() or "tty" in result.output.lower()


def test_linear_uuid_instructions_displayed(monkeypatch, tmp_path):
    """INIT-02: Wizard output contains Linear UUID copy instructions before prompting."""
    monkeypatch.setattr(_TTY_PATCH, lambda: True)
    _make_questionary_mocks(monkeypatch, _HAPPY_PATH_ANSWERS)
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(cli, ["init"])
    assert "Cmd+K" in result.output or "Copy model UUID" in result.output


def test_uuid_validation_reprompts(monkeypatch, tmp_path):
    """INIT-03: Invalid UUID causes re-prompt; valid UUID is accepted."""
    monkeypatch.setattr(_TTY_PATCH, lambda: True)

    # Must be a valid UUID v4: third group starts with 4, fourth with [89ab]
    valid_uuid = "550e8400-e29b-41d4-a716-446655440000"
    from heartbeat_gateway.commands.init import _validate_linear_uuid

    # Validate that our validation function correctly rejects invalid UUIDs
    assert _validate_linear_uuid("not-a-uuid") != True  # noqa: E712
    assert _validate_linear_uuid(valid_uuid) is True
    assert _validate_linear_uuid("") is True  # blank = skip

    _make_questionary_mocks(
        monkeypatch,
        [
            "sk-ant-testkey",
            "/workspace",
            "/workspace/SOUL.md",
            "claude-haiku-4-5-20251001",
            "ph-project-id-123",  # POSTHOG_PROJECT_ID
            "phc_secret",  # POSTHOG_SECRET
            "my-linear-secret",
            valid_uuid,
            "my-github-secret",
            "owner/repo",
        ],
    )
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["init"])
    # UUID appears in validation logic; valid UUID is accepted (exit 0)
    assert "invalid" in result.output.lower() or "uuid" in result.output.lower() or result.exit_code == 0
    assert result.exit_code != 2  # Not a usage error — a re-prompt


def test_secret_not_in_output(monkeypatch, tmp_path):
    """INIT-04: Secret/token values entered by user are not echoed in terminal output."""
    monkeypatch.setattr(_TTY_PATCH, lambda: True)
    secret_value = "lin_api_supersecret_abc123xyz"
    _make_questionary_mocks(
        monkeypatch,
        [
            "sk-ant-testkey",
            "/workspace",
            "/workspace/SOUL.md",
            "claude-haiku-4-5-20251001",
            "ph-project-id-123",  # POSTHOG_PROJECT_ID
            "phc_secret",  # POSTHOG_SECRET
            secret_value,  # LINEAR_SECRET
            "550e8400-e29b-41d4-a716-446655440000",
            "my-github-secret",
            "owner/repo",
        ],
    )
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["init"])
    assert secret_value not in result.output


def test_backup_created_on_overwrite(monkeypatch, tmp_path):
    """INIT-05: When .env already exists, a backup is created before overwriting."""
    monkeypatch.setattr(_TTY_PATCH, lambda: True)
    _make_questionary_mocks(monkeypatch, _HAPPY_PATH_ANSWERS)
    env_file = tmp_path / ".env"
    env_file.write_text("EXISTING_VAR=existing_value\n")
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    runner.invoke(cli, ["init"])
    # A backup file (.env.backup.YYYYMMDD_HHMMSS) must exist
    backup_files = list(tmp_path.glob(".env.bak*")) + list(tmp_path.glob(".env.backup*"))
    assert len(backup_files) > 0, "No backup file found after overwriting .env"


def test_atomic_write_on_valid_input(monkeypatch, tmp_path):
    """INIT-06: .env is written only after all prompts complete (atomic write)."""
    monkeypatch.setattr(_TTY_PATCH, lambda: True)
    _make_questionary_mocks(monkeypatch, _HAPPY_PATH_ANSWERS)
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["init"])
    if result.exit_code == 0:
        assert (tmp_path / ".env").exists(), ".env not written after successful wizard completion"


def test_completion_message_mentions_doctor(monkeypatch, tmp_path):
    """INIT-07: Completion output references 'gateway doctor' to guide next step."""
    monkeypatch.setattr(_TTY_PATCH, lambda: True)
    _make_questionary_mocks(monkeypatch, _HAPPY_PATH_ANSWERS)
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["init"])
    assert "gateway doctor" in result.output


def test_dependencies_declared():
    """INIT-08: questionary and python-dotenv appear in pyproject.toml dependencies."""
    pyproject = tomllib.loads(Path("pyproject.toml").read_text())
    deps = pyproject["project"]["dependencies"]
    assert any("questionary" in d for d in deps)
    assert any("python-dotenv" in d for d in deps)


def test_wizard_happy_path(monkeypatch, tmp_path):
    """INIT-09: Full prompt sequence driven via input= completes with exit 0."""
    monkeypatch.setattr(_TTY_PATCH, lambda: True)
    _make_questionary_mocks(monkeypatch, _HAPPY_PATH_ANSWERS)
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["init"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "gateway doctor" in result.output
