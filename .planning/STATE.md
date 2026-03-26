# STATE.md — heartbeat-gateway

## Project Reference

**What:** heartbeat-gateway v0.3.0 — `gateway doctor` + `gateway init` CLI commands
**Core Value:** Close PG-1 and PG-2; a new user can run `gateway init` then `gateway doctor` and reach a verified configuration without silent failures.
**Current Focus:** Phase 1 execution — Wire Click CLI group, add deps, implement DoctorRunner with 9 checks.

## Current Position

- **Milestone:** v0.3.0
- **Phase:** 1 of 2 — CLI Foundation + gateway doctor
- **Plan:** 2 of 2 — Plan 01 complete, Plan 02 ready to execute
- **Status:** Executing — Plan 01 complete

## Progress

```
[█████░░░░░] 50% — Phase 1 Plan 01 complete (CLI foundation + test scaffold)
```

## Recent Decisions

- `gateway doctor` before `gateway init` — doctor must be trusted before init's output can be verified
- SOUL.md linter folds into doctor (PG-3) — two product gaps close for the price of one
- Phase 1: CLI Foundation + doctor | Phase 2: gateway init
- All four new deps (click, rich, questionary, python-dotenv) declared as explicit in pyproject.toml
- doctor command NOT registered in cli.py at Plan 01 — added in Plan 02 Task 3 after DoctorRunner is complete
- xfail(strict=False) used for doctor stubs — Plan 02 flips them passing without changing test file
- CheckResult.fix_hint must be non-empty when status == FAIL (enforced by convention, tested in DOC-02)

## Blockers / Concerns

- litellm pinned to `<1.82.7` pending BerriAI supply chain audit (carry-forward from v0.2.0)
- PG-4 (Linear adapter bug) carry-forward — not in v0.3.0 scope

## Pending Todos

_None captured_

## Session Continuity

Last session: 2026-03-26 (Phase 1 Plan 01 executed — Click CLI group, 4 new deps, Wave 0 test scaffold committed)
Stopped at: Completed 01-01-PLAN.md — ready to execute 01-02-PLAN.md (DoctorRunner implementation)
Resume file: .planning/phases/01-cli-foundation-gateway-doctor/01-02-PLAN.md
