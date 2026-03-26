# STATE.md — heartbeat-gateway

## Project Reference

**What:** heartbeat-gateway v0.3.0 — `gateway doctor` + `gateway init` CLI commands
**Core Value:** Close PG-1 and PG-2; a new user can run `gateway init` then `gateway doctor` and reach a verified configuration without silent failures.
**Current Focus:** Planning phase — requirements defined, research complete, roadmap not yet created.

## Current Position

- **Milestone:** v0.3.0
- **Phase:** Pre-roadmap (research complete, phases not yet planned)
- **Plan:** None yet
- **Status:** Ready to plan

## Progress

```
[░░░░░░░░░░] 0% — Requirements + research done, no phases planned yet
```

## Recent Decisions

- `gateway doctor` before `gateway init` — doctor must be trusted before init's output can be verified
- SOUL.md linter folds into doctor (PG-3) — two product gaps close for the price of one
- Phase 1: CLI Foundation + doctor | Phase 2: gateway init
- All four new deps (click, rich, questionary, python-dotenv) declared as explicit in pyproject.toml

## Blockers / Concerns

- litellm pinned to `<1.82.7` pending BerriAI supply chain audit (carry-forward from v0.2.0)
- PG-4 (Linear adapter bug) carry-forward — not in v0.3.0 scope

## Pending Todos

_None captured_

## Session Continuity

Last session: 2026-03-25 (project initialized, requirements defined, research completed)
Stopped at: Pre-planning — ready to create roadmap and plan Phase 1
Resume file: none
