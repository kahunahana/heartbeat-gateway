---
gsd_state_version: 1.0
milestone: v0.4
milestone_name: milestone
status: executing
stopped_at: Completed 05-01-PLAN.md — LangSmithAdapter implemented, 13 tests pass
last_updated: "2026-04-05T03:15:06.517Z"
progress:
  total_phases: 6
  completed_phases: 4
  total_plans: 12
  completed_plans: 10
---

# STATE.md — heartbeat-gateway

## Project Reference

**What:** heartbeat-gateway v0.4.0 — Amplitude, Braintrust, and LangSmith webhook adapters + PostHog init wizard section
**Core Value:** Operators running AI agent stacks can classify signals from LLM eval, observability, and analytics platforms alongside Linear and GitHub — within the existing five-stage pipeline, zero structural changes.
**Current Focus:** Phase 5 (LangSmith Adapter) in progress — 05-01 complete, LangSmithAdapter built and tested; 05-02 (route wiring) and 05-03 (wizard) remain

## Current Position

- **Milestone:** v0.4.0 — Adapter Expansion
- **Phase:** Phase 5 — LangSmith Adapter (in progress)
- **Plan:** 05-01 complete (adapter); 05-02 and 05-03 pending
- **Status:** In progress — Phase 5

## Progress

```
[████████░░] 83% — Phase 5 in progress (10 plans done, 2 plans remain in Phase 5, Phase 6 remains)
Phase 3: Schema Foundation + PostHog Wizard  ✓ Complete (Plans 01-02 done)
Phase 4: Braintrust Adapter                  ✓ Complete (Plans 01-03 done, 2026-04-03)
Phase 5: LangSmith Adapter                   ▓ In progress (Plan 01 done, 2026-04-04)
Phase 6: Amplitude Adapter                   ░ Not started
```

## Recent Decisions

- LangSmith uses X-Langsmith-Secret token header comparison (not HMAC) — hmac.compare_digest for timing safety even with static token (05-01)
- Clean run suppression (LSMT-05) is first check after Shape B detection — before any metadata extraction (05-01)
- feedback_stats aggregates only available from LangSmith automation webhooks — no individual comment field; documented as limitation (05-01)
- NormalizedEvent source='langsmith' uses type: ignore comment until Plan 02 updates the Literal in __init__.py (05-01)
- Adapter checkbox switched to unchecked-by-default with empty-selection guard — pre-checked caused UX inversion where Space toggled OFF instead of ON; overrides Phase 3 decision based on smoke test (04-03)
- braintrust excluded from require_signatures guard — permanent-passthrough adapters skip secret enforcement with inline comment (04-02)
- Braintrust verify_signature is permanent passthrough (option-b) — no webhook signing confirmed, docstring advises IP allowlisting (04-01)
- condense() uses automation name not time/count fields — preserves writer.py dedup determinism (04-01)
- is_test guard is first executable line in normalize() — BTST-02 constraint enforced (04-01)
- Build order: Schema → Braintrust → LangSmith → Amplitude (research consensus)
- All `*WatchConfig` classes must inherit BaseModel (not BaseSettings) — v0.2.0 regression prevention
- Amplitude `verify_signature` is permanent passthrough — Amplitude confirmed no webhook signing
- LangSmithWatchConfig uses `token` field (not `secret`) — matches LangSmith API token naming convention (FOUND-03)

## Blockers / Concerns

- litellm pinned to `<1.82.7` pending BerriAI supply chain audit (carry-forward from v0.2.0)

## Pending Todos

- Execute Phase 5 Plan 02 (route wiring — wire LangSmithAdapter in app.py, update NormalizedEvent Literal)
- Execute Phase 5 Plan 03 (wizard — gateway init LangSmith section)
- Plan and execute Phase 6 (Amplitude Adapter)

## Session Continuity

Last session: 2026-04-05T03:15:06.514Z
Stopped at: Completed 05-01-PLAN.md — LangSmithAdapter implemented, 13 tests pass
