---
phase: 6
slug: amplitude-adapter
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-05
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing, no new setup) |
| **Config file** | `pyproject.toml` (existing) |
| **Quick run command** | `uv run pytest tests/adapters/test_amplitude.py -x -q` |
| **Full suite command** | `uv run pytest -x -q` |
| **Estimated runtime** | ~20 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/adapters/test_amplitude.py -x -q`
- **After every plan wave:** Run `uv run pytest -x -q && uv run ruff check .`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | AMP-01 | unit | `uv run pytest tests/adapters/test_amplitude.py::TestAmplitudeAdapterSignature -x` | ❌ W0 | ⬜ pending |
| 06-01-02 | 01 | 1 | AMP-02 | unit | `uv run pytest tests/adapters/test_amplitude.py::TestAmplitudeAdapterNormalize::test_normalizes_monitor_alert -x` | ❌ W0 | ⬜ pending |
| 06-01-03 | 01 | 1 | AMP-03 | unit | `uv run pytest tests/adapters/test_amplitude.py::TestAmplitudeAdapterNormalize::test_normalizes_chart_annotation -x` | ❌ W0 | ⬜ pending |
| 06-01-04 | 01 | 1 | AMP-04 | unit | `uv run pytest tests/adapters/test_amplitude.py::TestAmplitudeAdapterNormalize::test_unrecognized_event_returns_none -x` | ❌ W0 | ⬜ pending |
| 06-01-05 | 01 | 1 | AMP-05 | unit | `uv run pytest tests/adapters/test_amplitude.py::TestAmplitudeAdapterCondense -x` | ❌ W0 | ⬜ pending |
| 06-02-01 | 02 | 2 | AMP-06 | integration | `uv run pytest tests/test_app.py -k amplitude -x` | ❌ W0 | ⬜ pending |
| 06-03-01 | 03 | 2 | AMP-07 | unit | `uv run pytest tests/cli/test_init.py -k amplitude -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/adapters/test_amplitude.py` — stubs for AMP-01 through AMP-05
- [ ] `tests/fixtures/amplitude_monitor_alert.json` — monitor alert with charts array
- [ ] `tests/fixtures/amplitude_chart_annotation.json` — chart annotation event
- [ ] `tests/fixtures/amplitude_unknown.json` — unrecognized event type (always dropped)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| gateway init Amplitude section displays warning and writes secret | AMP-07 | Interactive terminal prompts | Run `uv run heartbeat-gateway init`, select Amplitude, verify warning about no webhook signing displays and secret written to .env |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
