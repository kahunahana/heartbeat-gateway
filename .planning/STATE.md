---
gsd_state_version: 1.0
milestone: v0.4
milestone_name: adapter-expansion
status: planning
stopped_at: null
last_updated: "2026-04-01T00:00:00.000Z"
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# STATE.md — heartbeat-gateway

## Project Reference

**What:** heartbeat-gateway v0.4.0 — Amplitude, Braintrust, and LangSmith webhook adapters + PostHog init wizard section
**Core Value:** Operators running AI agent stacks can classify signals from LLM eval, observability, and analytics platforms alongside Linear and GitHub — within the existing five-stage pipeline, zero structural changes.
**Current Focus:** Roadmap defined — ready to plan Phase 3 (Schema Foundation + PostHog Wizard)

## Current Position

- **Milestone:** v0.4.0 — Adapter Expansion
- **Phase:** Phase 3 (not started)
- **Plan:** —
- **Status:** Roadmap complete — ready for `/gsd:plan-phase 3`

## Progress

```
[░░░░░░░░░░] 0% — v0.4.0 not started (4 phases remaining)
Phase 3: Schema Foundation + PostHog Wizard  ░ Not started
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

## Blockers / Concerns

- **Phase 4 pre-build gate:** Braintrust HMAC header name unconfirmed — must look up `braintrust.dev/docs/guides/automations` before writing `verify_signature`; do not guess
- **Phase 5 pre-build gate:** LangSmith alert and fleet webhook payload shapes need one verification check before writing fixtures
- litellm pinned to `<1.82.7` pending BerriAI supply chain audit (carry-forward from v0.2.0)

## Pending Todos

- Run `/gsd:plan-phase 3` to create the Phase 3 execution plan

## Session Continuity

Last session: 2026-04-01
Stopped at: v0.4.0 roadmap complete — Phase 3 ready to plan
