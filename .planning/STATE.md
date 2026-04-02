---
gsd_state_version: 1.0
milestone: v0.4
milestone_name: milestone
status: completed
stopped_at: Completed 03-01-PLAN.md — schema foundation for Amplitude, Braintrust, LangSmith
last_updated: "2026-04-02T02:35:07.237Z"
progress:
  total_phases: 6
  completed_phases: 2
  total_plans: 6
  completed_plans: 5
---

# STATE.md — heartbeat-gateway

## Project Reference

**What:** heartbeat-gateway v0.4.0 — Amplitude, Braintrust, and LangSmith webhook adapters + PostHog init wizard section
**Core Value:** Operators running AI agent stacks can classify signals from LLM eval, observability, and analytics platforms alongside Linear and GitHub — within the existing five-stage pipeline, zero structural changes.
**Current Focus:** Phase 3 Plan 01 complete — schema foundation laid for all three new adapters

## Current Position

- **Milestone:** v0.4.0 — Adapter Expansion
- **Phase:** Phase 3 — Schema Foundation + PostHog Wizard
- **Plan:** Plan 02 (PostHog wizard)
- **Status:** Plan 03-01 complete; ready for Plan 03-02

## Progress

```
[█░░░░░░░░░] ~17% — Phase 3 Plan 01 complete (1/6 plans done)
Phase 3: Schema Foundation + PostHog Wizard  ░ In progress (Plan 01 done)
Phase 4: Braintrust Adapter                  ░ Not started
Phase 5: LangSmith Adapter                   ░ Not started
Phase 6: Amplitude Adapter                   ░ Not started
```

## Recent Decisions

- v0.4.0 roadmap created 2026-04-01 — 4 phases (3–6), 26 requirements mapped
- Arize Phoenix deferred to v2 — OSS product confirmed no outbound webhook support
- LangSmith dataset change webhooks deferred to v2 — not available in LangSmith API as of 2026-04-01
- Build order: Schema → Braintrust → LangSmith → Amplitude (research consensus)
- Braintrust before LangSmith: uniform `organization/project/automation/details` envelope is cleaner first-adapter template
- LangSmith before Amplitude: payload is better documented; auth model simpler than Amplitude's no-auth-at-all + dual payload shapes
- All `*WatchConfig` classes must inherit BaseModel (not BaseSettings) — v0.2.0 regression prevention
- Amplitude `verify_signature` is permanent passthrough — Amplitude confirmed no webhook signing, no plans to add it
- LangSmithWatchConfig uses `token` field (not `secret`) — matches LangSmith API token naming convention (FOUND-03)

## Blockers / Concerns

- **Phase 4 pre-build gate:** Braintrust HMAC header name unconfirmed — must look up `braintrust.dev/docs/guides/automations` before writing `verify_signature`; do not guess
- **Phase 5 pre-build gate:** LangSmith alert and fleet webhook payload shapes need one verification check before writing fixtures
- litellm pinned to `<1.82.7` pending BerriAI supply chain audit (carry-forward from v0.2.0)

## Pending Todos

- Execute Plan 03-02 (PostHog init wizard section)
- Execute Plan 03-03 if exists (or move to Phase 4)

## Session Continuity

Last session: 2026-04-02T02:35:07.232Z
Stopped at: Completed 03-01-PLAN.md — schema foundation for Amplitude, Braintrust, LangSmith
