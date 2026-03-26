---
phase: 2
slug: gateway-init
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-26
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3.0+ |
| **Config file** | `pyproject.toml` — `[tool.pytest.ini_options]` testpaths = ["tests"] |
| **Quick run command** | `uv run pytest tests/cli/test_init.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/cli/test_init.py -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 2-01-01 | 01 | 1 | INIT-01..09 | unit | `uv run pytest tests/cli/test_init.py -x` | ❌ W0 | ⬜ pending |
| 2-01-02 | 01 | 1 | INIT-01..09 | unit | `uv run pytest tests/cli/test_init.py -x` | ❌ W0 | ⬜ pending |
| 2-02-01 | 02 | 2 | INIT-01 | unit | `uv run pytest tests/cli/test_init.py::test_tty_detection_exits -x` | ❌ W0 | ⬜ pending |
| 2-02-02 | 02 | 2 | INIT-02,03,04 | unit | `uv run pytest tests/cli/test_init.py -x -k "uuid or instruction or secret"` | ❌ W0 | ⬜ pending |
| 2-02-03 | 02 | 2 | INIT-05,06 | unit | `uv run pytest tests/cli/test_init.py -x -k "backup or atomic"` | ❌ W0 | ⬜ pending |
| 2-02-04 | 02 | 2 | INIT-07,08 | unit | `uv run pytest tests/cli/test_init.py -x -k "completion or dependencies"` | ❌ W0 | ⬜ pending |
| 2-02-05 | 02 | 2 | INIT-09 | integration | `uv run pytest tests/cli/test_init.py::test_wizard_happy_path -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/cli/test_init.py` — xfail stubs for all 9 INIT requirements (INIT-01 through INIT-09)
- [ ] `heartbeat_gateway/commands/init.py` — stub command with `NotImplementedError` (so import in cli.py doesn't crash)

*Existing infrastructure (pytest, CliRunner, monkeypatch) fully covers phase requirements — no new config needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Rich terminal output and prompt display | INIT-02, INIT-04 | CliRunner captures stdout but can't verify TTY rendering or password masking visually | Run `uv run heartbeat-gateway init` in a real terminal; confirm instruction block renders before UUID prompt; confirm secret input is masked |
| Merge-by-default pre-fills existing values | INIT-05 | Requires an actual `.env` file on disk and visual confirmation | Create a `.env`, re-run `gateway init`, confirm existing values appear as defaults in prompts |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
