---
gsd_state_version: 1.0
milestone: v0.4
milestone_name: milestone
status: executing
stopped_at: Completed 06-02-PLAN.md — Amplitude route wired, doctor WARN added, 5 integration tests, 220 total passing
last_updated: "2026-04-04T00:15:00Z"
progress:
  total_phases: 6
  completed_phases: 5
  total_plans: 15
  completed_plans: 14
---

# STATE.md — heartbeat-gateway

## Project Reference

**What:** heartbeat-gateway v0.4.0 — Amplitude, Braintrust, and LangSmith webhook adapters + PostHog init wizard section
**Core Value:** Operators running AI agent stacks can classify signals from LLM eval, observability, and analytics platforms alongside Linear and GitHub — within the existing five-stage pipeline, zero structural changes.
**Current Focus:** Phase 6 in progress — 06-01 (AmplitudeAdapter + tests) complete; route wiring (06-02) and wizard (06-03) pending

## Current Position

- **Milestone:** v0.4.0 — Adapter Expansion
- **Phase:** Phase 6 — Amplitude Adapter (in progress)
- **Plan:** 06-02 complete (route wired, doctor WARN, 5 integration tests; 220 tests total)
- **Status:** In progress

## Progress

```
[█████████░] 93% — Phase 6 in progress (14/15 plans done)
Phase 3: Schema Foundation + PostHog Wizard  ✓ Complete (Plans 01-02 done)
Phase 4: Braintrust Adapter                  ✓ Complete (Plans 01-03 done, 2026-04-03)
Phase 5: LangSmith Adapter                   ✓ Complete (Plans 01-03 done, smoke test approved 2026-04-05)
Phase 6: Amplitude Adapter                   ░ In progress (Plans 01-02 done, 03 pending)
```

## Recent Decisions

- Amplitude route wired alphabetically after LangSmith; excluded from require_signatures enforcement; doctor WARN fires when require_signatures=true + amplitude secret set (06-02)
- make_gateway_config test helper extended with amplitude_secret kwarg — follows braintrust_secret / langsmith_token pattern (06-02)
- Amplitude verify_signature is permanent passthrough — Amplitude confirmed no webhook signing; docstring advises IP allowlisting (06-01)
- condense() uses charts[0].header not what_happened — what_happened embeds timestamp, breaking dedup determinism across redeliveries (06-01)
- Empty charts guard (if not charts: return None) prevents IndexError on monitor_alert with empty array (06-01)
- NormalizedEvent.source Literal updated in same task as adapter — no type: ignore comments needed (06-01)
- LangSmith init wizard token prompt uses questionary.password and env var GATEWAY_WATCH__LANGSMITH__TOKEN (05-03)
- LangSmith placed between Braintrust and Linear in checkbox — consistent with adapter build order (05-03)
- Inline wizard instructions explicitly state X-Langsmith-Secret header requirement (05-03)
- LangSmith uses X-Langsmith-Secret token header comparison (not HMAC) — hmac.compare_digest for timing safety even with static token (05-01)
- Clean run suppression (LSMT-05) is first check after Shape B detection — before any metadata extraction (05-01)
- feedback_stats aggregates only available from LangSmith automation webhooks — no individual comment field; documented as limitation (05-01)
- NormalizedEvent.source Literal updated in __init__.py to include 'langsmith' — type: ignore no longer needed (05-02)
- LangSmith adapter import sorted alphabetically (braintrust → github → langsmith → linear → posthog) per ruff isort (05-02)
- make_gateway_config test helper extended with langsmith_token kwarg mapping to LangSmithWatchConfig(token=...) (05-02)
- NormalizedEvent source='langsmith' uses type: ignore comment until Plan 02 updates the Literal in __init__.py (05-01)
- Adapter checkbox switched to unchecked-by-default with empty-selection guard — pre-checked caused UX inversion where Space toggled OFF instead of ON; overrides Phase 3 decision based on smoke test (04-03)
- braintrust excluded from require_signatures guard — permanent-passthrough adapters skip secret enforcement with inline comment (04-02)
- Braintrust verify_signature is permanent passthrough (option-b) — no webhook signing confirmed, docstring advises IP allowlisting (04-01)
- condense() uses automation name not time/count fields — preserves writer.py dedup determinism (04-01)
- is_test guard is first executable line in normalize() — BTST-02 constraint enforced (04-01)
- Build order: Schema → Braintrust → LangSmith → Amplitude (research consensus)
- All *WatchConfig classes must inherit BaseModel (not BaseSettings) — v0.2.0 regression prevention
- Amplitude verify_signature is permanent passthrough — Amplitude confirmed no webhook signing
- LangSmithWatchConfig uses token field (not secret) — matches LangSmith API token naming convention (FOUND-03)

## Blockers / Concerns

- litellm pinned to <1.82.7 pending BerriAI supply chain audit (carry-forward from v0.2.0)

## Pending Todos

- Execute Phase 6 Plan 03 (init wizard for Amplitude)

## Session Continuity

Last session: 2026-04-04T00:15:00Z
Stopped at: Completed 06-02-PLAN.md — Amplitude route wired, doctor WARN added, 5 integration tests, 220 total passing
