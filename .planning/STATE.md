---
gsd_state_version: 1.0
milestone: v0.4
milestone_name: milestone
status: planning
stopped_at: Phase 4 complete — Braintrust Adapter done; Phase 5 (LangSmith) is next
last_updated: "2026-04-03T03:00:00.000Z"
progress:
  total_phases: 6
  completed_phases: 4
  total_plans: 9
  completed_plans: 9
---

# STATE.md — heartbeat-gateway

## Project Reference

**What:** heartbeat-gateway v0.4.0 — Amplitude, Braintrust, and LangSmith webhook adapters + PostHog init wizard section
**Core Value:** Operators running AI agent stacks can classify signals from LLM eval, observability, and analytics platforms alongside Linear and GitHub — within the existing five-stage pipeline, zero structural changes.
**Current Focus:** Phase 4 complete — BraintrustAdapter fully wired, tested, documented, and smoke-tested; Phase 5 (LangSmith) is next

## Current Position

- **Milestone:** v0.4.0 — Adapter Expansion
- **Phase:** Phase 4 — Braintrust Adapter (complete)
- **Plan:** All 3 plans complete (04-01, 04-02, 04-03)
- **Status:** Ready for Phase 5

## Progress

```
[████████░░] 67% — Phase 4 complete (9 plans done, 2 phases remain)
Phase 3: Schema Foundation + PostHog Wizard  ✓ Complete (Plans 01-02 done)
Phase 4: Braintrust Adapter                  ✓ Complete (Plans 01-03 done, 2026-04-03)
Phase 5: LangSmith Adapter                   ░ Not started
Phase 6: Amplitude Adapter                   ░ Not started
```

## Recent Decisions

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

- **Phase 5 pre-build gate:** LangSmith alert and fleet webhook payload shapes need one verification check before writing fixtures
- litellm pinned to `<1.82.7` pending BerriAI supply chain audit (carry-forward from v0.2.0)

## Pending Todos

- Plan and execute Phase 5 (LangSmith Adapter)
- Plan and execute Phase 6 (Amplitude Adapter)

## Session Continuity

Last session: 2026-04-03
Stopped at: Phase 4 complete — all 3 plans done, smoke test passed, SUMMARY written. Phase 5 (LangSmith) is next — needs planning.
