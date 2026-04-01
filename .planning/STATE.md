---
gsd_state_version: 1.0
milestone: v0.4
milestone_name: adapter-expansion
status: researching
stopped_at: null
last_updated: "2026-04-01T00:00:00.000Z"
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# STATE.md — heartbeat-gateway

## Project Reference

**What:** heartbeat-gateway v0.3.0 — `gateway doctor` + `gateway init` CLI commands
**Core Value:** Close PG-1 and PG-2; a new user can run `gateway init` then `gateway doctor` and reach a verified configuration without silent failures.
**Current Focus:** Phase 1 complete — CLI foundation + gateway doctor implemented and verified.

## Current Position

- **Milestone:** v0.4.0 — Adapter Expansion
- **Phase:** Not started (defining requirements)
- **Plan:** —
- **Status:** Researching — parallel domain research in progress

## Progress

```
[░░░░░░░░░░] 0% — v0.4.0 not started
```

## Recent Decisions

- v0.3.0 decisions archived in .planning/phases/01-*/SUMMARY.md and .planning/phases/02-*/SUMMARY.md
- v0.4.0 started 2026-04-01 — 4 new adapters + PostHog init wizard section
- All adapters must follow WebhookAdapter interface: verify_signature + normalize + condense
- ACTIONABLE signals: eval run failures, trace anomalies, human feedback, dataset changes
- Batch/streaming ingestion out of scope — webhook-first constraint maintained

## Blockers / Concerns

- litellm pinned to `<1.82.7` pending BerriAI supply chain audit (carry-forward from v0.2.0)
- PG-4 (Linear adapter bug) carry-forward — not in v0.3.0 scope
- Integration test fixtures should explicitly zero secrets to prevent uv .env auto-loading from affecting test results (carry-forward)

## Pending Todos

_None captured_

## Session Continuity

Last session: 2026-04-01
Stopped at: v0.4.0 milestone start — parallel research running for Amplitude, Braintrust, Arize Phoenix, LangSmith
