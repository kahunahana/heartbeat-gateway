---
phase: 4
slug: braintrust-adapter
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-01
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/adapters/test_braintrust.py -x -q` |
| **Full suite command** | `uv run pytest -x -q && uv run ruff check .` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/adapters/test_braintrust.py -x -q`
- **After every plan wave:** Run `uv run pytest -x -q && uv run ruff check .`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 4-01-01 | 01 | 1 | BTST-01 | unit | `uv run pytest tests/adapters/test_braintrust.py::test_verify_signature -x -q` | ❌ W0 | ⬜ pending |
| 4-01-02 | 01 | 1 | BTST-02 | unit | `uv run pytest tests/adapters/test_braintrust.py::test_normalize_is_test_returns_none -x -q` | ❌ W0 | ⬜ pending |
| 4-01-03 | 01 | 1 | BTST-03 | unit | `uv run pytest tests/adapters/test_braintrust.py::test_normalize_logs_actionable -x -q` | ❌ W0 | ⬜ pending |
| 4-01-04 | 01 | 1 | BTST-04 | unit | `uv run pytest tests/adapters/test_braintrust.py::test_normalize_environment_update_delta -x -q` | ❌ W0 | ⬜ pending |
| 4-02-01 | 02 | 2 | BTST-05 | integration | `uv run pytest tests/test_routes.py -k braintrust -x -q` | ❌ W0 | ⬜ pending |
| 4-02-02 | 02 | 2 | BTST-05 | unit | `uv run pytest tests/test_routes.py::test_braintrust_invalid_sig_returns_401 -x -q` | ❌ W0 | ⬜ pending |
| 4-02-03 | 02 | 2 | BTST-06 | manual | see Manual-Only table | N/A | ⬜ pending |
| 4-02-04 | 02 | 2 | BTST-07 | unit | `uv run pytest -x -q` (full suite) | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/adapters/test_braintrust.py` — stubs for BTST-01, BTST-02, BTST-03, BTST-04
- [ ] `tests/fixtures/braintrust_logs.json` — fixture payload for `logs` event
- [ ] `tests/fixtures/braintrust_environment_update.json` — fixture payload for `environment_update` event
- [ ] `tests/fixtures/braintrust_is_test.json` — fixture payload with `details.is_test: true`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `gateway init` Braintrust section prompts for secret with BTQL instructions | BTST-06 | Wizard is interactive CLI — pytest cannot drive questionary prompts reliably | Run `uv run gateway init`, select Braintrust in checkbox, verify secret prompt appears and BTQL setup instructions are shown inline |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
