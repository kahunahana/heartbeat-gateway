---
phase: 01-cli-foundation-gateway-doctor
plan: 01
subsystem: cli
tags: [click, rich, questionary, python-dotenv, pytest, tdd]

# Dependency graph
requires: []
provides:
  - heartbeat_gateway/cli.py — Click group with invoke_without_command=True and serve subcommand
  - heartbeat_gateway/commands/__init__.py — package marker enabling doctor import
  - heartbeat_gateway/commands/doctor.py — CheckResult, CheckStatus, DoctorRunner stubs
  - tests/cli/test_cli.py — 3 passing tests (CLI-01, CLI-02, CLI-03)
  - tests/cli/test_doctor.py — 12 xfail stubs (DOC-01 through DOC-12)
  - pyproject.toml — updated entry point + 4 new explicit deps
affects: [01-02, plan-02-gateway-doctor-implementation]

# Tech tracking
tech-stack:
  added: [click>=8.1.0, rich>=13.0.0, questionary>=2.0.0, python-dotenv>=1.0.0]
  patterns:
    - Click group with invoke_without_command=True for default server behavior
    - Lazy import of uvicorn inside serve() to avoid top-level side effects
    - TDD xfail stubs — Wave 0 scaffold so Plan 02 flips them green
    - CONSTRAINT pattern in module docstring to prevent prohibited imports

key-files:
  created:
    - heartbeat_gateway/cli.py
    - heartbeat_gateway/commands/__init__.py
    - heartbeat_gateway/commands/doctor.py
    - tests/cli/__init__.py
    - tests/cli/test_cli.py
    - tests/cli/test_doctor.py
  modified:
    - pyproject.toml

key-decisions:
  - "doctor command NOT registered in cli.py at Plan 01 — added in Plan 02 Task 3 after DoctorRunner is complete"
  - "All four new deps declared explicitly in pyproject.toml even though click was already transitive"
  - "xfail(strict=False) used for doctor stubs so full suite stays green; Plan 02 flips them passing"
  - "CheckResult.fix_hint must be non-empty when status == FAIL — enforced by docstring convention, tested in DOC-02"

patterns-established:
  - "Module docstring CONSTRAINT: pattern documents prohibited imports (no app.py in doctor/cli)"
  - "Wave 0 TDD scaffold: create xfail stubs before implementing, Plan N+1 turns them green"
  - "noqa: F401 on imported-but-unused stubs that serve as forward declarations for Plan 02"

requirements-completed: [CLI-01, CLI-02, CLI-03]

# Metrics
duration: 6min
completed: 2026-03-26
---

# Phase 01 Plan 01: CLI Foundation + Wave 0 Test Scaffold Summary

**Click CLI group wired with invoke_without_command=True, entry point switched to cli:cli, four new deps declared explicitly, and Wave 0 xfail test scaffold (3 passing + 12 xfail) ready for Plan 02 to implement against.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-26T05:35:21Z
- **Completed:** 2026-03-26T05:41:18Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Click CLI group with `invoke_without_command=True` — bare `heartbeat-gateway` still starts uvicorn (no breaking change)
- Entry point switched from `heartbeat_gateway.app:main` to `heartbeat_gateway.cli:cli` in pyproject.toml
- Four new deps made explicit: click>=8.1.0, rich>=13.0.0, questionary>=2.0.0, python-dotenv>=1.0.0
- Wave 0 TDD scaffold: 3 passing tests (CLI-01/02/03) + 12 xfail stubs (DOC-01 through DOC-12)
- Full test suite passes: 136 passed, 13 xfailed, ruff clean

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire Click group, update pyproject.toml entry point, declare all four new deps** - `a728b5a` (feat)
2. **Task 2: Wave 0 — Create failing test stubs for CLI-01/02/03 and DOC-01 through DOC-12, plus doctor.py stub** - `26080d4` (test)

## Files Created/Modified

- `heartbeat_gateway/cli.py` — Click group, invoke_without_command=True, serve subcommand with lazy uvicorn import
- `heartbeat_gateway/commands/__init__.py` — Empty package marker enabling `from heartbeat_gateway.commands.doctor import ...`
- `heartbeat_gateway/commands/doctor.py` — CheckStatus enum, CheckResult dataclass, DoctorRunner stub (NotImplementedError), EXPECTED_MIN_BODY_BYTES constant
- `tests/cli/__init__.py` — Empty package marker for pytest discovery
- `tests/cli/test_cli.py` — 3 passing tests: test_click_explicit_dependency, test_entry_point_is_cli, test_cli_group_importable
- `tests/cli/test_doctor.py` — 12 xfail stubs for DOC-01 through DOC-12 using monkeypatch.setenv + CliRunner pattern
- `pyproject.toml` — Entry point updated, 4 deps added, uv.lock regenerated

## Decisions Made

- doctor command is NOT registered in cli.py at Plan 01 — it will be added in Plan 02 Task 3 after DoctorRunner.run() is complete. This keeps cli.py independently testable at this plan boundary.
- xfail stubs use `strict=False` so they show as xfailed (not failing) in the full suite. Plan 02 implementations will flip them to passing without needing to change the test file.
- `EXPECTED_MIN_BODY_BYTES = 512 * 1024` is replicated in doctor.py (not imported from app.py) per the CONSTRAINT documented in the module docstring — prevents a dependency on app.py that the plan explicitly prohibited.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed ruff lint errors in generated files**
- **Found during:** Task 2 (Wave 0 test stubs)
- **Issue:** `field` imported but unused in doctor.py (F401); import blocks unsorted in doctor.py and test_doctor.py (I001); unused CheckResult/CheckStatus/DoctorRunner imports in test_doctor.py (F401)
- **Fix:** Removed `field` from doctor.py imports; added `# noqa: F401` to forward-declaration imports in test_doctor.py; applied `ruff check --fix` for I001; applied `ruff format`
- **Files modified:** heartbeat_gateway/commands/doctor.py, tests/cli/test_doctor.py
- **Verification:** `ruff check .` and `ruff format --check .` both exit 0
- **Committed in:** `26080d4` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - lint correctness)
**Impact on plan:** Fix necessary for CI compliance. No scope creep — the plan specified ruff clean in the verification section.

## Issues Encountered

- `uv sync` without `--dev` removed pytest/ruff from the venv. Resolved by using `uv run --extra dev` for all test/lint commands. Not a code issue — uv correctly distinguishes production vs dev environments.

## Next Phase Readiness

- Plan 02 (01-02) can begin immediately: DoctorRunner.run() has NotImplementedError stubs, 12 xfail tests exist for all checks, doctor command needs to be registered in cli.py
- No blockers for Plan 02 execution
- Pre-existing blocker carries forward: litellm pinned to <1.82.7 pending BerriAI audit (out of scope for this plan)

---
*Phase: 01-cli-foundation-gateway-doctor*
*Completed: 2026-03-26*
