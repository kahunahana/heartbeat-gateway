---
gsd_state_version: 1.0
milestone: v0.3
milestone_name: milestone
status: executing
stopped_at: Phase 2 Plan 2 checkpoint — Tasks 1-2 complete; awaiting human verify Task 3
last_updated: "2026-03-26T07:37:11.399Z"
progress:
  total_phases: 2
  completed_phases: 2
  total_plans: 4
  completed_plans: 4
---

# STATE.md — heartbeat-gateway

## Project Reference

**What:** heartbeat-gateway v0.3.0 — `gateway doctor` + `gateway init` CLI commands
**Core Value:** Close PG-1 and PG-2; a new user can run `gateway init` then `gateway doctor` and reach a verified configuration without silent failures.
**Current Focus:** Phase 1 complete — CLI foundation + gateway doctor implemented and verified.

## Current Position

- **Milestone:** v0.3.0
- **Phase:** 2 of 2 — gateway init wizard
- **Plan:** 2 of 2 — checkpoint (Tasks 1-2 complete; awaiting human verify Task 3)
- **Status:** Checkpoint — human verify live terminal wizard

## Progress

```
[█████████░] 90% — Phase 2 Plan 2 Tasks 1-2 complete (159 tests, 1 xfailed; awaiting Task 3 human verify)
```

## Recent Decisions

- `gateway doctor` before `gateway init` — doctor must be trusted before init's output can be verified
- SOUL.md linter folds into doctor (PG-3) — two product gaps close for the price of one
- Phase 1: CLI Foundation + doctor | Phase 2: gateway init
- All four new deps (click, rich, questionary, python-dotenv) declared as explicit in pyproject.toml
- doctor command NOT registered in cli.py at Plan 01 — added in Plan 02 after DoctorRunner is complete
- xfail(strict=False) used for doctor stubs — Plan 02 flips them passing without changing test file
- CheckResult.fix_hint must be non-empty when status == FAIL (enforced by convention, tested in DOC-02)
- Catch pydantic_settings.SettingsError in addition to pydantic.ValidationError — raised when JSON env vars (e.g. PROJECT_IDS=not-valid-json) fail to decode before reaching Pydantic validation
- HMAC secret severity: FAIL if require_signatures=True, WARN otherwise — single `level` variable controls
- xfail(strict=False) for init stubs — XPASS is safe at Wave 0; Plan 02 flips stubs to passing without changing test file
- test_dependencies_declared uses tomllib to read pyproject.toml directly — already passes since deps declared in Phase 1
- _is_tty() module-level helper chosen over sys.stdin.isatty() check directly — CliRunner replaces sys.stdin entirely so monkeypatching it doesn't reach the command body
- questionary cannot use CliRunner input= on Windows — prompt_toolkit requires Win32 console APIs; fix: patch questionary.text/.password with mock objects in tests
- UUID a1b2c3d4-e5f6-7890-abcd-ef1234567890 in original stubs is not valid UUID v4 (third group must start with 4); corrected to 550e8400-e29b-41d4-a716-446655440000

## Blockers / Concerns

- litellm pinned to `<1.82.7` pending BerriAI supply chain audit (carry-forward from v0.2.0)
- PG-4 (Linear adapter bug) carry-forward — not in v0.3.0 scope

## Pending Todos

_None captured_

## Session Continuity

Last session: 2026-03-26T07:37:11.395Z
Stopped at: Phase 2 Plan 2 checkpoint — Tasks 1-2 complete; awaiting human verify Task 3
