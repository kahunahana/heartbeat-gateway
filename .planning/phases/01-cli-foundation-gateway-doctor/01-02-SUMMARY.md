---
phase: 01-cli-foundation-gateway-doctor
plan: 02
subsystem: cli
tags: [click, rich, pydantic-settings, doctor, preflight, validation]

# Dependency graph
requires:
  - phase: 01-cli-foundation-gateway-doctor
    plan: 01
    provides: "Click CLI group, four deps (click, rich, questionary, python-dotenv), doctor stub with CheckResult/CheckStatus/DoctorRunner, 12 xfail test stubs"
provides:
  - "DoctorRunner.run() with 9 checks: config loads, API key format, SOUL.md exists, workspace writable, Linear UUID validation, HMAC secrets (FAIL if require_signatures else WARN), body size constant guard, SOUL.md content linter (UUID + scoping prefix patterns), require_signatures advisory"
  - "DoctorRunner.print_results() with rich table output ([OK]/[WARN]/[FAIL]) and Fix: hints"
  - "doctor Click command with --verbose and --env-file flags, exit code discipline (1 on FAIL, 0 on WARN-only)"
  - "cli.add_command(doctor) — doctor registered on Click group"
  - "14 passing doctor tests (12 original stubs + 2 meta-tests)"
affects:
  - phase-02-gateway-init

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Config loaded once in DoctorRunner.run(), passed to individual check methods as parameter"
    - "Catch both pydantic.ValidationError and pydantic_settings.exceptions.SettingsError in _check_config_loads"
    - "Exit code via raise SystemExit(1 if failed else 0) — not sys.exit(), not click.get_current_context().exit()"
    - "fix_hint structural invariant enforced by meta-test test_every_fail_has_fix_hint"
    - "HMAC secret checks: level = FAIL if require_signatures else WARN — single variable controls severity"

key-files:
  created: []
  modified:
    - heartbeat_gateway/commands/doctor.py
    - heartbeat_gateway/cli.py
    - tests/cli/test_doctor.py

key-decisions:
  - "Catch pydantic_settings.SettingsError in addition to pydantic.ValidationError — raised when JSON env vars (e.g. PROJECT_IDS=not-valid-json) fail to parse before reaching Pydantic validation"
  - "HMAC secret severity: WARN when require_signatures=False, FAIL when require_signatures=True — same check, single level variable"
  - "SOUL.md linter runs only when file exists and is readable — no double-FAIL when SOUL.md is already flagged FAIL"
  - "Body size check always PASS (EXPECTED_MIN_BODY_BYTES == 512*1024 by definition) — check exists to catch future regressions via test assertion"
  - "test_env_file_flag uses a separate workspace/ subdirectory — tmp_path itself is not reliably writable as expected"

patterns-established:
  - "Config-first check pattern: Check 1 returns (result, config | None); remaining checks are skipped if config is None"
  - "Meta-test pattern: test_every_fail_has_fix_hint iterates all results and asserts fix_hint non-empty for FAIL status — catches regressions in fix_hint coverage"
  - "Pitfall guard test: test_api_key_present_but_wrong_prefix_still_fails ensures 'plausible but wrong' input is rejected, not just missing-value case"

requirements-completed: [DOC-01, DOC-02, DOC-03, DOC-04, DOC-05, DOC-06, DOC-07, DOC-08, DOC-09, DOC-10, DOC-11, DOC-12]

# Metrics
duration: 25min
completed: 2026-03-25
---

# Phase 1 Plan 02: Gateway Doctor Implementation Summary

**DoctorRunner with 9 checks and rich terminal output closes PG-2 and PG-3 — `gateway doctor` gives actionable Fix: hints for every silent failure mode**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-03-25T00:00:00Z
- **Completed:** 2026-03-25T00:25:00Z
- **Tasks:** 2 (+ checkpoint)
- **Files modified:** 3

## Accomplishments

- Implemented all 9 DoctorRunner checks (config loads, API key format, SOUL.md exists, workspace writable, Linear UUID validation, HMAC secrets, body size limit, SOUL.md content linter, require_signatures advisory)
- Registered doctor command on cli group via cli.add_command(doctor) with --verbose and --env-file flags
- Flipped all 12 xfail stubs to passing tests and added 2 structural meta-tests (14 total)
- Full suite: 150 passed, 1 xfailed (intentional race condition), ruff clean

## Task Commits

1. **Task 1: Implement DoctorRunner and register doctor command** — `64706fc` (feat)
2. **Task 2: Flip xfail stubs to passing tests** — `18dd1e6` (feat, includes Rule 1 auto-fix)

## Files Created/Modified

- `heartbeat_gateway/commands/doctor.py` — Full DoctorRunner implementation with 9 checks, print_results(), and doctor Click command
- `heartbeat_gateway/cli.py` — Added cli.add_command(doctor) at bottom
- `tests/cli/test_doctor.py` — 12 xfail stubs converted to real tests, 2 meta-tests added

## Decisions Made

- Catch `pydantic_settings.SettingsError` in addition to `pydantic.ValidationError` in `_check_config_loads` — pydantic-settings raises this distinct exception when JSON env vars (e.g. `GATEWAY_WATCH__LINEAR__PROJECT_IDS=not-valid-json`) fail to decode before reaching Pydantic's validator
- HMAC secret severity controlled by a single `level` variable: `FAIL` if `require_signatures=True`, `WARN` otherwise — same check, consistent logic
- Body size check always PASS by definition (EXPECTED_MIN_BODY_BYTES replicated as 512*1024) — check exists to catch future regressions via test assertion `EXPECTED_MIN_BODY_BYTES >= 512*1024`
- SOUL.md linter only runs when the file exists — avoids double-FAIL when SOUL.md is already flagged missing
- `test_env_file_flag` creates a separate `workspace/` subdirectory under `tmp_path` to ensure a writable directory is passed to `GATEWAY_WORKSPACE_PATH`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Catch pydantic_settings.SettingsError in _check_config_loads**
- **Found during:** Task 2 (test execution of test_doctor_catches_config_error and test_doctor_catches_malformed_project_ids)
- **Issue:** `GATEWAY_WATCH__LINEAR__PROJECT_IDS=not-valid-json` caused `pydantic_settings.exceptions.SettingsError` to propagate uncaught through `DoctorRunner.run()`, crashing doctor instead of returning a FAIL CheckResult. The plan only specified catching `pydantic.ValidationError`.
- **Fix:** Added `except SettingsError as e:` branch in `_check_config_loads` returning a FAIL result with a JSON-focused fix_hint
- **Files modified:** `heartbeat_gateway/commands/doctor.py`
- **Verification:** `test_doctor_catches_config_error` and `test_doctor_catches_malformed_project_ids` both pass
- **Committed in:** `18dd1e6` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug: uncaught exception variant)
**Impact on plan:** Necessary for correctness — malformed JSON env vars are a documented user error (DOC-11 tests exactly this case). No scope creep.

## Issues Encountered

- `ruff format` reformatted `doctor.py` (line-length adjustments to multi-line strings) and `test_doctor.py` (import ordering). Both fixed inline and included in their respective task commits.

## User Setup Required

None — no external service configuration required for this plan.

## Next Phase Readiness

- `gateway doctor` is fully functional. PG-2 (no doctor command) and PG-3 (SOUL.md has no schema) are closed.
- Phase 2 (`gateway init`) can proceed independently — doctor is the verification step for init's output.
- No blockers introduced.

---
*Phase: 01-cli-foundation-gateway-doctor*
*Completed: 2026-03-25*
