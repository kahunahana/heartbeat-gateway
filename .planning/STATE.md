# STATE.md — heartbeat-gateway

## Project Reference

**What:** heartbeat-gateway v0.3.0 — `gateway doctor` + `gateway init` CLI commands
**Core Value:** Close PG-1 and PG-2; a new user can run `gateway init` then `gateway doctor` and reach a verified configuration without silent failures.
**Current Focus:** Phase 1 complete — CLI foundation + gateway doctor implemented and verified.

## Current Position

- **Milestone:** v0.3.0
- **Phase:** 1 of 2 — CLI Foundation + gateway doctor
- **Plan:** 2 of 2 — COMPLETE (human verified 2026-03-25)
- **Status:** Phase 1 complete — ready for Phase 2 (gateway init)

## Progress

```
[██████████] 100% — Phase 1 complete (gateway doctor with 9 checks, 150 tests passing)
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

## Blockers / Concerns

- litellm pinned to `<1.82.7` pending BerriAI supply chain audit (carry-forward from v0.2.0)
- PG-4 (Linear adapter bug) carry-forward — not in v0.3.0 scope

## Pending Todos

_None captured_

## Session Continuity

Last session: 2026-03-25 (Phase 1 Plan 02 executed — DoctorRunner 9 checks, 14 tests, cli.add_command registered)
Stopped at: Phase 1 complete — human verified `gateway doctor` terminal output 2026-03-25
Resume file: Phase 2 (gateway init) — 02-XX-PLAN.md not yet created
