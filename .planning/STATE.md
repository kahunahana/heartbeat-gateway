---
gsd_state_version: 1.0
milestone: v0.4
milestone_name: milestone
status: planning
stopped_at: Completed 04-02-PLAN.md — BraintrustAdapter route registration
last_updated: "2026-04-02T15:00:00.000Z"
progress:
  total_phases: 6
  completed_phases: 3
  total_plans: 8
  completed_plans: 8
---

# STATE.md — heartbeat-gateway

## Project Reference

**What:** heartbeat-gateway v0.4.0 — Amplitude, Braintrust, and LangSmith webhook adapters + PostHog init wizard section
**Core Value:** Operators running AI agent stacks can classify signals from LLM eval, observability, and analytics platforms alongside Linear and GitHub — within the existing five-stage pipeline, zero structural changes.
**Current Focus:** Phase 4 Plan 02 complete — BraintrustAdapter route registered; Phase 4 Plan 03 (wizard section) is next

## Current Position

- **Milestone:** v0.4.0 — Adapter Expansion
- **Phase:** Phase 4 — Braintrust Adapter (in progress)
- **Plan:** Plan 04-02 complete; Plan 04-03 (wizard section) remains
- **Status:** In progress

## Progress

```
[████████░░] 83% — Phase 4 Plan 02 complete (8/? plans done)
Phase 3: Schema Foundation + PostHog Wizard  ✓ Complete (Plans 01-02 done)
Phase 4: Braintrust Adapter                  ▓ In progress (Plans 01-02 done; Plan 03 remains)
Phase 5: LangSmith Adapter                   ░ Not started
Phase 6: Amplitude Adapter                   ░ Not started
```

## Recent Decisions

- braintrust excluded from require_signatures guard — permanent-passthrough adapters skip secret enforcement with inline comment (04-02)
- Braintrust verify_signature is permanent passthrough (option-b) — no webhook signing confirmed, docstring advises IP allowlisting (04-01)
- condense() uses automation name not time/count fields — preserves writer.py dedup determinism (04-01)
- is_test guard is first executable line in normalize() — BTST-02 constraint enforced (04-01)
- v0.4.0 roadmap created 2026-04-01 — 4 phases (3–6), 26 requirements mapped
- Arize Phoenix deferred to v2 — OSS product confirmed no outbound webhook support
- LangSmith dataset change webhooks deferred to v2 — not available in LangSmith API as of 2026-04-01
- Build order: Schema → Braintrust → LangSmith → Amplitude (research consensus)
- Braintrust before LangSmith: uniform `organization/project/automation/details` envelope is cleaner first-adapter template
- LangSmith before Amplitude: payload is better documented; auth model simpler than Amplitude's no-auth-at-all + dual payload shapes
- All `*WatchConfig` classes must inherit BaseModel (not BaseSettings) — v0.2.0 regression prevention
- Amplitude `verify_signature` is permanent passthrough — Amplitude confirmed no webhook signing, no plans to add it
- LangSmithWatchConfig uses `token` field (not `secret`) — matches LangSmith API token naming convention (FOUND-03)
- Pre-check all adapters in checkbox by default — avoids silent empty-list bug when user presses Enter without Space (03-02)
- questionary.Choice(name, checked=True) pattern established for wizard checkbox adapter defaults (03-02)

## Blockers / Concerns

- **Phase 4 pre-build gate:** RESOLVED — Braintrust has no webhook signing (option-b chosen); verify_signature is permanent passthrough per AmplitudeAdapter pattern
- **Phase 5 pre-build gate:** LangSmith alert and fleet webhook payload shapes need one verification check before writing fixtures
- litellm pinned to `<1.82.7` pending BerriAI supply chain audit (carry-forward from v0.2.0)

## Pending Todos

- Execute Phase 4 Plan 03 (Braintrust wizard section)
- Execute Phase 5 (LangSmith Adapter)
- Execute Phase 6 (Amplitude Adapter)

## Session Continuity

Last session: 2026-04-02T15:00:00.000Z
Stopped at: Completed 04-02-PLAN.md — BraintrustAdapter route registration
