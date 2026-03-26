---
phase: 02-gateway-init
plan: 01
subsystem: testing
tags: [click, pytest, xfail, tdd, cli]

# Dependency graph
requires:
  - phase: 01-cli-foundation-gateway-doctor
    provides: cli.py with doctor registered; CliRunner test pattern established
provides:
  - xfail test contract for gateway init (9 stubs, INIT-01 through INIT-09)
  - heartbeat_gateway/commands/init.py stub importable via cli group
  - cli.py with init registered alongside doctor
affects: [02-02-PLAN.md — implements the stubs created here]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "xfail(strict=False) stubs document expected behavior before implementation"
    - "Tests invoke cli group (not command directly) — same as test_doctor.py"
    - "Each stub includes assertions describing required behavior even while failing"

key-files:
  created:
    - heartbeat_gateway/commands/init.py
    - tests/cli/test_init.py
  modified:
    - heartbeat_gateway/cli.py

key-decisions:
  - "xfail(strict=False) chosen over xfail(strict=True) — XPASS is safe at stub stage; Plan 02 flips them"
  - "test_dependencies_declared reads pyproject.toml with tomllib — already passes since deps were declared in Phase 1"
  - "monkeypatch.setattr('sys.stdin.isatty', lambda: True) included in TTY-dependent stubs to test correct path once implemented"

patterns-established:
  - "init.py carries same CONSTRAINT comment as doctor.py — no imports from heartbeat_gateway.app"
  - "cli.py import registration pattern: import on its own line + cli.add_command() on next line"

requirements-completed: [INIT-01, INIT-02, INIT-03, INIT-04, INIT-05, INIT-06, INIT-07, INIT-08, INIT-09]

# Metrics
duration: 5min
completed: 2026-03-26
---

# Phase 2 Plan 01: gateway init Wave 0 — xfail stubs + stub command Summary

**9 Nyquist-compliant xfail test stubs covering INIT-01 through INIT-09, plus importable init stub registered in cli.py**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-26T07:16:29Z
- **Completed:** 2026-03-26T07:22:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Created `heartbeat_gateway/commands/init.py` as a `@click.command("init")` stub that raises `NotImplementedError`
- Created `tests/cli/test_init.py` with 9 `xfail(strict=False)` stubs — one per INIT requirement — each with real assertions documenting required behavior
- Registered `init` in `heartbeat_gateway/cli.py` immediately after doctor, using the identical import pattern
- Full suite: 150 passed + 7 xfailed + 3 xpassed — zero failures, zero errors

## Task Commits

Each task was committed atomically:

1. **Task 1: Create init.py stub and xfail test stubs** - `b1aaafd` (test)
2. **Task 2: Register init command in cli.py** - `f114b5e` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `heartbeat_gateway/commands/init.py` - Stub @click.command("init") with NotImplementedError and CONSTRAINT comment
- `tests/cli/test_init.py` - 9 xfail(strict=False) stubs for INIT-01 through INIT-09
- `heartbeat_gateway/cli.py` - Added init import and cli.add_command(init) after doctor block

## Decisions Made

- `xfail(strict=False)` chosen so XPASS is not an error at stub stage — Plan 02 will flip tests passing without touching the test file
- `test_dependencies_declared` (INIT-08) reads pyproject.toml directly with `tomllib` — no xfail flip needed since questionary and python-dotenv were already declared in Phase 1
- `monkeypatch.setattr("sys.stdin.isatty", lambda: True)` included in TTY-dependent stubs so they test the correct code path once implementation exists

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed ruff lint error (unused variable) in test_backup_created_on_overwrite**
- **Found during:** Task 2 verification (ruff check)
- **Issue:** `result` assigned but not used in the isolated_filesystem block — F841 lint error
- **Fix:** Removed assignment, kept `runner.invoke()` call as expression
- **Files modified:** tests/cli/test_init.py
- **Verification:** `ruff check .` passes; `ruff format --check .` passes
- **Committed in:** f114b5e (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - lint/bug)
**Impact on plan:** Minor fix required to satisfy ruff check. No scope change.

## Issues Encountered

None beyond the ruff lint fix above.

## Next Phase Readiness

- Wave 0 contract is in place — Plan 02 can implement each INIT requirement and flip the xfail stubs to passing tests
- `gateway init` is importable and appears in `gateway --help` output
- All 9 test stubs have concrete assertions; no stub bodies are empty

---
*Phase: 02-gateway-init*
*Completed: 2026-03-26*
