---
phase: 3
slug: schema-foundation-posthog-wizard
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-01
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `pyproject.toml` — `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/cli/test_init.py tests/test_schema.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/cli/test_init.py tests/test_schema.py -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 3-01-01 | 01 | 1 | FOUND-01 | unit | `uv run pytest tests/test_schema.py::test_amplitude_config_loads_from_env -x` | ❌ Wave 0 | ⬜ pending |
| 3-01-02 | 01 | 1 | FOUND-02 | unit | `uv run pytest tests/test_schema.py::test_braintrust_config_loads_from_env -x` | ❌ Wave 0 | ⬜ pending |
| 3-01-03 | 01 | 1 | FOUND-03 | unit | `uv run pytest tests/test_schema.py::test_langsmith_config_loads_from_env -x` | ❌ Wave 0 | ⬜ pending |
| 3-02-01 | 02 | 2 | FOUND-04 | unit | `uv run pytest tests/cli/test_init.py::test_posthog_prompts_before_linear -x` | ❌ Wave 0 | ⬜ pending |
| 3-02-02 | 02 | 2 | FOUND-04 | unit | `uv run pytest tests/cli/test_init.py::test_wizard_happy_path -x` | ✅ (update) | ⬜ pending |
| 3-02-03 | 02 | 2 | FOUND-04 | unit | `uv run pytest tests/cli/test_init.py::test_checkbox_gates_adapters -x` | ❌ Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_schema.py` — xfail stubs for FOUND-01, FOUND-02, FOUND-03 (regression tests for new WatchConfig env var loading)
- [ ] New xfail test functions in `tests/cli/test_init.py` — stubs for FOUND-04 (checkbox gating, PostHog before Linear ordering)

*No new framework installation needed — pytest already configured in pyproject.toml.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `gateway init` terminal output shows checkbox before adapter prompts | FOUND-04 | Visual TTY rendering cannot be fully captured by CliRunner | Run `gateway init` in real terminal; confirm checkbox appears before PostHog/Linear/GitHub prompts |
| Adapter help link displays correctly | FOUND-04 | String output in real terminal | Run `gateway init`; confirm link to docs/adapters.md appears at wizard end |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
