---
phase: 1
slug: cli-foundation-gateway-doctor
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-25
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3.x |
| **Config file** | `pyproject.toml` — `[tool.pytest.ini_options]` with `testpaths = ["tests"]` |
| **Quick run command** | `uv run pytest tests/cli/ -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~15 seconds (full suite) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/cli/ -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green (`uv run pytest` + `uv run ruff check .` + `uv run ruff format --check .`)
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | CLI-01 | unit | `uv run pytest tests/cli/test_cli.py::test_bare_invocation_starts_server -x` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 1 | CLI-02 | static | `uv run pytest tests/cli/test_cli.py::test_click_explicit_dependency -x` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 1 | CLI-03 | unit | `uv run pytest tests/cli/test_cli.py::test_entry_point_is_cli -x` | ❌ W0 | ⬜ pending |
| 1-02-01 | 02 | 2 | DOC-01 | unit | `uv run pytest tests/cli/test_doctor.py::test_exit_code_1_on_fail -x` | ❌ W0 | ⬜ pending |
| 1-02-02 | 02 | 2 | DOC-02 | unit | `uv run pytest tests/cli/test_doctor.py::test_fix_hint_present_on_every_fail -x` | ❌ W0 | ⬜ pending |
| 1-02-03 | 02 | 2 | DOC-03 | unit | `uv run pytest tests/cli/test_doctor.py::test_verbose_flag -x` | ❌ W0 | ⬜ pending |
| 1-02-04 | 02 | 2 | DOC-04 | integration | `uv run pytest tests/cli/test_doctor.py::test_doctor_catches_config_error -x` | ❌ W0 | ⬜ pending |
| 1-02-05 | 02 | 2 | DOC-05 | unit | `uv run pytest tests/cli/test_doctor.py::test_soul_md_missing_fails -x` | ❌ W0 | ⬜ pending |
| 1-02-06 | 02 | 2 | DOC-06 | unit | `uv run pytest tests/cli/test_doctor.py::test_api_key_wrong_prefix_fails -x` | ❌ W0 | ⬜ pending |
| 1-02-07 | 02 | 2 | DOC-07 | unit | `uv run pytest tests/cli/test_doctor.py::test_hmac_secret_empty_warns -x` | ❌ W0 | ⬜ pending |
| 1-02-08 | 02 | 2 | DOC-08 | unit | `uv run pytest tests/cli/test_doctor.py::test_invalid_uuid_fails -x` | ❌ W0 | ⬜ pending |
| 1-02-09 | 02 | 2 | DOC-09 | unit | `uv run pytest tests/cli/test_doctor.py::test_body_size_check -x` | ❌ W0 | ⬜ pending |
| 1-02-10 | 02 | 2 | DOC-10 | unit | `uv run pytest tests/cli/test_doctor.py::test_soul_md_uuid_pattern_warns -x` | ❌ W0 | ⬜ pending |
| 1-02-11 | 02 | 2 | DOC-11 | integration | `uv run pytest tests/cli/test_doctor.py::test_doctor_catches_malformed_project_ids -x` | ❌ W0 | ⬜ pending |
| 1-02-12 | 02 | 2 | DOC-12 | unit | `uv run pytest tests/cli/test_doctor.py::test_env_file_flag -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

All test files and implementation stubs are new — none exist yet:

- [ ] `tests/cli/__init__.py` — empty package marker
- [ ] `tests/cli/test_cli.py` — stub tests for CLI-01, CLI-02, CLI-03 (failing stubs only)
- [ ] `tests/cli/test_doctor.py` — stub tests for DOC-01 through DOC-12 (failing stubs only)
- [ ] `heartbeat_gateway/commands/__init__.py` — empty package marker
- [ ] `heartbeat_gateway/cli.py` — stub (import only, no logic)
- [ ] `heartbeat_gateway/commands/doctor.py` — stub (CheckResult dataclass only)

No framework install needed — pytest 8.3.x already in dev dependencies.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Terminal output renders [OK]/[WARN]/[FAIL] with rich colors | DOC-01, DOC-02, DOC-03 | CliRunner strips ANSI; visual check needed | Run `gateway doctor` in real terminal with all-pass config; confirm colors render |
| `gateway doctor --verbose` shows all checks including PASS | DOC-03 | Output volume varies by env; visual validation | Run with a known-good .env; confirm PASS checks appear |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
