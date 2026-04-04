---
phase: 5
slug: langsmith-adapter
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-03
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing, no new setup) |
| **Config file** | `pyproject.toml` (existing) |
| **Quick run command** | `uv run pytest tests/adapters/test_langsmith.py -x -q` |
| **Full suite command** | `uv run pytest -x -q` |
| **Estimated runtime** | ~20 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/adapters/test_langsmith.py -x -q`
- **After every plan wave:** Run `uv run pytest -x -q && uv run ruff check .`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | LSMT-01 | unit | `uv run pytest tests/adapters/test_langsmith.py::TestLangSmithAdapterSignature -x` | ❌ W0 | ⬜ pending |
| 05-01-02 | 01 | 1 | LSMT-02 | unit | `uv run pytest tests/adapters/test_langsmith.py::TestLangSmithAdapterNormalize::test_normalizes_run_error -x` | ❌ W0 | ⬜ pending |
| 05-01-03 | 01 | 1 | LSMT-03 | unit | `uv run pytest tests/adapters/test_langsmith.py::TestLangSmithAdapterNormalize::test_normalizes_feedback -x` | ❌ W0 | ⬜ pending |
| 05-01-04 | 01 | 1 | LSMT-04 | unit | `uv run pytest tests/adapters/test_langsmith.py::TestLangSmithAdapterNormalize::test_normalizes_alert -x` | ❌ W0 | ⬜ pending |
| 05-01-05 | 01 | 1 | LSMT-05 | unit | `uv run pytest tests/adapters/test_langsmith.py::TestLangSmithAdapterNormalize::test_clean_run_returns_none -x` | ❌ W0 | ⬜ pending |
| 05-01-06 | 01 | 1 | LSMT-08 | unit | `uv run pytest tests/adapters/test_langsmith.py::TestLangSmithAdapterCondense -x` | ❌ W0 | ⬜ pending |
| 05-02-01 | 02 | 2 | LSMT-06 | integration | `uv run pytest tests/test_app.py -k langsmith -x` | ❌ W0 | ⬜ pending |
| 05-03-01 | 03 | 2 | LSMT-07 | unit | `uv run pytest tests/cli/test_init.py -k langsmith -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/adapters/test_langsmith.py` — stubs for LSMT-01 through LSMT-05 and LSMT-08
- [ ] `tests/fixtures/langsmith_run_error.json` — run with error field populated (Shape B)
- [ ] `tests/fixtures/langsmith_run_clean.json` — run with error=null (always dropped)
- [ ] `tests/fixtures/langsmith_feedback.json` — negative feedback score via automation webhook
- [ ] `tests/fixtures/langsmith_alert.json` — alert threshold crossing

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| gateway init LangSmith section displays instructions and writes token | LSMT-07 | Interactive terminal prompts | Run `uv run heartbeat-gateway init`, select LangSmith, verify instructions display and token written to .env |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
