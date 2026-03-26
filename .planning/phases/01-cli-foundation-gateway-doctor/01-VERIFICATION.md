---
phase: 01-cli-foundation-gateway-doctor
verified: 2026-03-25T00:00:00Z
status: passed
score: 8/8 must-haves verified
re_verification: false
---

# Phase 1: CLI Foundation + gateway doctor — Verification Report

**Phase Goal:** Wire the Click CLI group and deliver a fully functional `gateway doctor` command that validates all known silent failure modes with structured output, fix hints, and correct exit code discipline. Existing `heartbeat-gateway` entry point must remain unbroken.
**Verified:** 2026-03-25
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `gateway doctor` exits 1 when any FAIL-level check is present | VERIFIED | `test_exit_code_1_on_fail` passes; `doctor()` calls `raise SystemExit(1 if failed else 0)` |
| 2 | `gateway doctor` exits 0 when all checks pass or only WARN-level issues found | VERIFIED | `test_env_file_flag` asserts `exit_code == 0` on valid config; WARN not counted in `failed` list |
| 3 | Every FAIL-level result has a non-empty fix_hint printed inline as "Fix: ..." | VERIFIED | `test_every_fail_has_fix_hint` (meta-test) iterates all results; `print_results()` renders `Fix:` line; `test_fix_hint_present_on_every_fail` passes |
| 4 | Default output (no --verbose) shows only WARN and FAIL checks | VERIFIED | `print_results()` only adds PASS rows when `self.verbose` is True |
| 5 | `gateway doctor --verbose` shows all checks including PASS | VERIFIED | `test_verbose_flag` asserts "OK" in output; `elif self.verbose: table.add_row("[green][ OK ]...")` present |
| 6 | `gateway doctor --env-file <path>` loads the specified file before config construction | VERIFIED | `test_env_file_flag` passes; `load_dotenv(env_file, override=True)` present in `doctor()` |
| 7 | Bare `heartbeat-gateway` invocation still starts the server (no breaking change) | VERIFIED | `cli.py` uses `invoke_without_command=True`; bare call invokes `serve`; `test_cli_group_importable` passes |
| 8 | All 12 test stubs in test_doctor.py pass (no xfail remaining) | VERIFIED | Full suite: 150 passed, 1 xfailed (pre-existing race condition); `tests/cli/` shows 17 passed, 0 xfailed |

**Score:** 8/8 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `heartbeat_gateway/cli.py` | Click group with `invoke_without_command=True`, `serve` command, `cli.add_command(doctor)` | VERIFIED | File exists, 23 lines, exports `cli`, `cli.add_command(doctor)` at bottom |
| `heartbeat_gateway/commands/__init__.py` | Empty package marker | VERIFIED | File exists |
| `heartbeat_gateway/commands/doctor.py` | DoctorRunner with 9 checks, CheckResult, CheckStatus, EXPECTED_MIN_BODY_BYTES | VERIFIED | File exists, 376 lines, all 9 check methods present, full implementation (no stubs/NotImplementedError) |
| `pyproject.toml` | Entry point `heartbeat_gateway.cli:cli`; deps: click>=8.1.0, rich>=13.0.0, questionary>=2.0.0, python-dotenv>=1.0.0 | VERIFIED | All four deps present in `dependencies`; scripts section shows `heartbeat-gateway = "heartbeat_gateway.cli:cli"` |
| `tests/cli/__init__.py` | Empty package marker | VERIFIED | File exists |
| `tests/cli/test_cli.py` | 3 passing tests for CLI-01, CLI-02, CLI-03 | VERIFIED | 3 tests, all pass |
| `tests/cli/test_doctor.py` | 12 passing tests (was xfail stubs) plus 2 meta-tests = 14 total | VERIFIED | 14 tests, all pass, no xfail markers present |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `pyproject.toml` | `heartbeat_gateway/cli.py` | `[project.scripts]` entry point | VERIFIED | `heartbeat-gateway = "heartbeat_gateway.cli:cli"` present at line 44 |
| `heartbeat_gateway/cli.py` | `heartbeat_gateway/commands/doctor.py` | `cli.add_command(doctor)` | VERIFIED | Import at line 20, `cli.add_command(doctor)` at line 22 |
| `heartbeat_gateway/commands/doctor.py` | `heartbeat_gateway/config/schema.py` | `GatewayConfig()` construction in `_check_config_loads` | VERIFIED | `from heartbeat_gateway.config.schema import GatewayConfig` at line 19; `GatewayConfig()` called in `_check_config_loads` |
| `tests/cli/test_doctor.py` | `heartbeat_gateway/cli.py` | `CliRunner().invoke(cli, ['doctor', ...])` | VERIFIED | `runner.invoke(cli, ["doctor", ...])` pattern present across all 12 functional tests |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| CLI-01 | 01-01 | Bare invocation starts server — no breaking change | SATISFIED | `invoke_without_command=True` + `ctx.invoke(serve)`; test passes |
| CLI-02 | 01-01 | click as explicit dependency in pyproject.toml | SATISFIED | `"click>=8.1.0"` at line 31 of pyproject.toml; `test_click_explicit_dependency` passes |
| CLI-03 | 01-01 | New `cli.py` entry point wires Click group | SATISFIED | `heartbeat-gateway = "heartbeat_gateway.cli:cli"` in scripts; `test_entry_point_is_cli` passes |
| DOC-01 | 01-02 | `gateway doctor` exits 0 only if no FAIL-level issues | SATISFIED | `raise SystemExit(1 if failed else 0)`; `test_exit_code_1_on_fail` passes |
| DOC-02 | 01-02 | Each check carries fix_hint shown inline on failure | SATISFIED | `test_fix_hint_present_on_every_fail` and `test_every_fail_has_fix_hint` both pass |
| DOC-03 | 01-02 | Default shows only WARN/FAIL; --verbose shows PASS | SATISFIED | `print_results()` guards PASS rows behind `self.verbose`; `test_verbose_flag` passes |
| DOC-04 | 01-02 | Check — config loads without ValidationError | SATISFIED | `_check_config_loads()` catches both `ValidationError` and `SettingsError`; `test_doctor_catches_config_error` passes |
| DOC-05 | 01-02 | Check — SOUL.md exists at configured path and is readable | SATISFIED | `_check_soul_md_exists()` implemented; `test_soul_md_missing_fails` passes |
| DOC-06 | 01-02 | Check — Anthropic API key present and matches `sk-ant-` prefix | SATISFIED | `_check_api_key()` validates prefix; `test_api_key_wrong_prefix_fails` passes |
| DOC-07 | 01-02 | Check — HMAC secrets non-empty for each configured source | SATISFIED | `_check_hmac_secrets()` warns or fails depending on `require_signatures`; `test_hmac_secret_empty_warns` passes |
| DOC-08 | 01-02 | Check — Linear project_ids parseable as valid UUID v4 | SATISFIED | `_check_linear_project_ids()` with `UUID_V4_PATTERN`; `test_invalid_uuid_fails` passes |
| DOC-09 | 01-02 | Check — body size limit >= 512KB | SATISFIED | `_check_body_size_limit()` guards `EXPECTED_MIN_BODY_BYTES`; `test_body_size_check` passes |
| DOC-10 | 01-02 | Check — SOUL.md content linter warns on scoping patterns | SATISFIED | `_check_soul_md_content()` checks UUID patterns + scoping prefixes; `test_soul_md_uuid_pattern_warns` passes |
| DOC-11 | 01-02 | Doctor tests use `monkeypatch.setenv` + CliRunner — no mocked GatewayConfig | SATISFIED | CONSTRAINT comment in test file; all tests use `monkeypatch.setenv`; confirmed no `unittest.mock.patch` on GatewayConfig |
| DOC-12 | 01-02 | `gateway doctor` accepts `--env-file <path>` flag | SATISFIED | `--env-file` click option present; `load_dotenv(env_file, override=True)` used; `test_env_file_flag` passes |

**All 15 declared requirement IDs satisfied. No orphaned requirements.**

The REQUIREMENTS.md traceability table marks all CLI-01 through DOC-12 as "Complete" for Phase 1.

---

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `heartbeat_gateway/cli.py` line 20 | `from heartbeat_gateway.commands.doctor import doctor  # noqa: E402` — import at module bottom after function definitions | Info | Not a stub; module-level import position is unconventional but functional. The `noqa: E402` suppression is intentional — documented in the SUMMARY as a deliberate pattern to keep cli.py independently testable at Plan 01 boundary. No impact on correctness. |

No blocker or warning-level anti-patterns found. No TODO/FIXME/placeholder comments in phase files. No `NotImplementedError` remaining in `DoctorRunner` (both `run()` and `print_results()` fully implemented).

---

### Human Verification Required

#### 1. Rich terminal output visual check

**Test:** Run `uv run heartbeat-gateway doctor` in a terminal without a `.env` file present.
**Expected:** Rich table with `[FAIL]` rows in red, `WARN` rows in yellow, each followed by a `Fix:` hint line. Summary line shows counts.
**Why human:** Rich markup rendering (color codes, table formatting) cannot be verified programmatically via CliRunner — CliRunner strips ANSI codes.

#### 2. Bare invocation starts uvicorn

**Test:** Run `uv run heartbeat-gateway` (no subcommand) in a terminal.
**Expected:** uvicorn starts and binds to 0.0.0.0:8080.
**Why human:** The test suite only verifies the `cli` group is importable and invocable; it does not spin up uvicorn. The lazy import path (`import uvicorn` inside `serve()`) is untested in isolation.

---

## Summary

Phase 1 goal is fully achieved. The `gateway doctor` command exists, is wired into the Click group, implements all 9 checks covering every documented silent failure mode, produces fix hints on every FAIL, and has correct exit code discipline. The existing bare `heartbeat-gateway` invocation is unbroken.

All 15 requirement IDs declared in the two plans (CLI-01, CLI-02, CLI-03, DOC-01 through DOC-12) have verified implementation backed by passing tests. The full test suite shows 150 passed, 1 xfailed (a pre-existing race condition test unrelated to this phase). Ruff is clean.

The one notable deviation from the plan skeleton was the addition of `pydantic_settings.SettingsError` handling in `_check_config_loads` — this was a necessary correctness fix discovered during test execution (DOC-11 and DOC-04 test exactly the malformed JSON env var case that triggers it).

---

_Verified: 2026-03-25_
_Verifier: Claude (gsd-verifier)_
