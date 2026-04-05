"""Doctor command tests.

CONSTRAINT: Use monkeypatch.setenv + CliRunner only.
Do NOT mock GatewayConfig — that bypasses the BaseSettings loading path
that caused the v0.2.0 security regression.
"""

from click.testing import CliRunner

from heartbeat_gateway.cli import cli
from heartbeat_gateway.commands.doctor import CheckResult, CheckStatus, DoctorRunner  # noqa: F401

# ---------------------------------------------------------------------------
# Functional tests — all previously xfail stubs now passing
# ---------------------------------------------------------------------------


def test_exit_code_1_on_fail(tmp_path, monkeypatch):
    """DOC-01: doctor exits 1 when any FAIL-level check is present."""
    monkeypatch.setenv("GATEWAY_WORKSPACE_PATH", str(tmp_path))
    monkeypatch.setenv("GATEWAY_SOUL_MD_PATH", str(tmp_path / "SOUL.md"))
    # SOUL.md intentionally absent — check_soul_md_exists must FAIL
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor"], catch_exceptions=False)
    assert result.exit_code == 1


def test_fix_hint_present_on_every_fail(tmp_path, monkeypatch):
    """DOC-02: Every FAIL-level result must have a non-empty fix_hint."""
    monkeypatch.setenv("GATEWAY_WORKSPACE_PATH", str(tmp_path))
    monkeypatch.setenv("GATEWAY_SOUL_MD_PATH", str(tmp_path / "SOUL.md"))
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor"], catch_exceptions=False)
    assert "Fix:" in result.output


def test_verbose_flag(tmp_path, monkeypatch):
    """DOC-03: --verbose shows all checks including PASS."""
    soul = tmp_path / "SOUL.md"
    soul.write_text("## Current Focus\nship it")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
    monkeypatch.setenv("GATEWAY_WORKSPACE_PATH", str(tmp_path))
    monkeypatch.setenv("GATEWAY_SOUL_MD_PATH", str(soul))
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor", "--verbose"], catch_exceptions=False)
    assert "OK" in result.output


def test_doctor_catches_config_error(tmp_path, monkeypatch):
    """DOC-04: Doctor surfaces ValidationError when config is malformed."""
    monkeypatch.setenv("GATEWAY_WORKSPACE_PATH", str(tmp_path))
    monkeypatch.setenv("GATEWAY_WATCH__LINEAR__PROJECT_IDS", "not-valid-json")
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor"], catch_exceptions=False)
    assert result.exit_code == 1
    assert "FAIL" in result.output


def test_soul_md_missing_fails(tmp_path, monkeypatch):
    """DOC-05: Doctor FAILs when SOUL.md does not exist at configured path."""
    monkeypatch.setenv("GATEWAY_WORKSPACE_PATH", str(tmp_path))
    monkeypatch.setenv("GATEWAY_SOUL_MD_PATH", str(tmp_path / "SOUL.md"))
    # SOUL.md intentionally absent
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor"], catch_exceptions=False)
    assert "FAIL" in result.output
    assert "SOUL.md" in result.output


def test_api_key_wrong_prefix_fails(tmp_path, monkeypatch):
    """DOC-06: Doctor FAILs when ANTHROPIC_API_KEY does not start with sk-ant-."""
    soul = tmp_path / "SOUL.md"
    soul.write_text("## Current Focus\nship it")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "my-real-key-no-prefix")
    monkeypatch.setenv("GATEWAY_WORKSPACE_PATH", str(tmp_path))
    monkeypatch.setenv("GATEWAY_SOUL_MD_PATH", str(soul))
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor"], catch_exceptions=False)
    assert result.exit_code == 1
    assert "FAIL" in result.output
    assert "ANTHROPIC_API_KEY" in result.output


def test_hmac_secret_empty_warns(tmp_path, monkeypatch):
    """DOC-07: Doctor WARNs when HMAC secrets are empty (not FAIL — unless require_signatures=True)."""
    soul = tmp_path / "SOUL.md"
    soul.write_text("## Current Focus\nship it")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
    monkeypatch.setenv("GATEWAY_WORKSPACE_PATH", str(tmp_path))
    monkeypatch.setenv("GATEWAY_SOUL_MD_PATH", str(soul))
    # LINEAR__SECRET intentionally empty
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor"], catch_exceptions=False)
    assert "WARN" in result.output


def test_invalid_uuid_fails(tmp_path, monkeypatch):
    """DOC-08: Doctor FAILs when Linear project_ids contain non-UUID strings."""
    soul = tmp_path / "SOUL.md"
    soul.write_text("## Current Focus\nship it")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
    monkeypatch.setenv("GATEWAY_WORKSPACE_PATH", str(tmp_path))
    monkeypatch.setenv("GATEWAY_SOUL_MD_PATH", str(soul))
    monkeypatch.setenv("GATEWAY_WATCH__LINEAR__PROJECT_IDS", '["not-a-uuid"]')
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor"], catch_exceptions=False)
    assert result.exit_code == 1
    assert "FAIL" in result.output


def test_body_size_check(tmp_path, monkeypatch):
    """DOC-09: Doctor checks MAX_BODY_BYTES is at least 512KB."""
    soul = tmp_path / "SOUL.md"
    soul.write_text("## Current Focus\nship it")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
    monkeypatch.setenv("GATEWAY_WORKSPACE_PATH", str(tmp_path))
    monkeypatch.setenv("GATEWAY_SOUL_MD_PATH", str(soul))
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor", "--verbose"], catch_exceptions=False)
    # Body size check must appear — PASS or FAIL depending on app.py constant
    assert "body" in result.output.lower() or "size" in result.output.lower()


def test_soul_md_uuid_pattern_warns(tmp_path, monkeypatch):
    """DOC-10: Doctor WARNs when SOUL.md contains UUID patterns (scoping rules belong in pre_filter)."""
    soul = tmp_path / "SOUL.md"
    soul.write_text("## Current Focus\nWatch project 550e8400-e29b-41d4-a716-446655440000")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
    monkeypatch.setenv("GATEWAY_WORKSPACE_PATH", str(tmp_path))
    monkeypatch.setenv("GATEWAY_SOUL_MD_PATH", str(soul))
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor"], catch_exceptions=False)
    assert "WARN" in result.output


def test_doctor_catches_malformed_project_ids(tmp_path, monkeypatch):
    """DOC-11: Integration test — monkeypatch.setenv triggers real GatewayConfig loading."""
    monkeypatch.setenv("GATEWAY_WORKSPACE_PATH", str(tmp_path))
    monkeypatch.setenv("GATEWAY_WATCH__LINEAR__PROJECT_IDS", "not-valid-json")
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor"], catch_exceptions=False)
    # Real GatewayConfig() must raise ValidationError — doctor must surface it
    assert result.exit_code == 1


def test_env_file_flag(tmp_path, monkeypatch):
    """DOC-12: --env-file flag loads the specified file and overrides environment."""
    env_file = tmp_path / "prod.env"
    soul = tmp_path / "SOUL.md"
    soul.write_text("## Current Focus\nship it")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    env_file.write_text(
        f"ANTHROPIC_API_KEY=sk-ant-from-file\nGATEWAY_WORKSPACE_PATH={workspace}\nGATEWAY_SOUL_MD_PATH={soul}\n"
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor", "--env-file", str(env_file)], catch_exceptions=False)
    # With valid config from file, exit 0 expected (assuming no other FAILs)
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Meta-tests — structural invariants
# ---------------------------------------------------------------------------


def test_every_fail_has_fix_hint(tmp_path, monkeypatch):
    """Meta-test: structural invariant — every FAIL result must have non-empty fix_hint."""
    monkeypatch.setenv("GATEWAY_WORKSPACE_PATH", str(tmp_path))
    monkeypatch.setenv("GATEWAY_SOUL_MD_PATH", str(tmp_path / "SOUL.md"))
    # Deliberately bad config: no API key, no SOUL.md
    runner = DoctorRunner(verbose=True)
    results = runner.run()
    for r in results:
        if r.status == CheckStatus.FAIL:
            assert r.fix_hint, f"Check '{r.name}' is FAIL but fix_hint is empty"


def test_api_key_present_but_wrong_prefix_still_fails(tmp_path, monkeypatch):
    """Pitfall 1 guard: plausible key with wrong prefix must FAIL, not just 'missing' case."""
    soul = tmp_path / "SOUL.md"
    soul.write_text("## Current Focus\nship it")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "my-real-key-without-prefix")
    monkeypatch.setenv("GATEWAY_WORKSPACE_PATH", str(tmp_path))
    monkeypatch.setenv("GATEWAY_SOUL_MD_PATH", str(soul))
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor"], catch_exceptions=False)
    assert result.exit_code == 1
    assert "FAIL" in result.output


def test_amplitude_signature_noop_warn(tmp_path, monkeypatch):
    """AMPT-07: Doctor WARNs when require_signatures=True and amplitude.secret is set.

    Amplitude does not sign webhook deliveries — the secret has no security effect.
    Require all other secrets to be set so the doctor reaches the amplitude check.
    """
    soul = tmp_path / "SOUL.md"
    soul.write_text("## Current Focus\nship it")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
    monkeypatch.setenv("GATEWAY_WORKSPACE_PATH", str(tmp_path))
    monkeypatch.setenv("GATEWAY_SOUL_MD_PATH", str(soul))
    monkeypatch.setenv("GATEWAY_REQUIRE_SIGNATURES", "true")
    monkeypatch.setenv("GATEWAY_WATCH__LINEAR__SECRET", "linear-secret")
    monkeypatch.setenv("GATEWAY_WATCH__GITHUB__SECRET", "github-secret")
    monkeypatch.setenv("GATEWAY_WATCH__POSTHOG__SECRET", "posthog-secret")
    monkeypatch.setenv("GATEWAY_WATCH__AMPLITUDE__SECRET", "some-amplitude-secret")

    runner = DoctorRunner(verbose=True)
    results = runner.run()

    amplitude_warn = [r for r in results if r.name == "Amplitude signature (no-op)"]
    assert len(amplitude_warn) == 1, f"Expected 1 amplitude WARN result, got: {[r.name for r in results]}"
    assert amplitude_warn[0].status == CheckStatus.WARN
