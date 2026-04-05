---
phase: 05-langsmith-adapter
plan: 01
subsystem: adapter
tags: [langsmith, webhook, hmac, tdd, python]

# Dependency graph
requires:
  - phase: 03-schema-foundation
    provides: LangSmithWatchConfig with token field in schema.py
  - phase: 04-braintrust-adapter
    provides: BraintrustAdapter pattern for adapter structure and test conventions
provides:
  - LangSmithAdapter class with verify_signature, normalize, condense
  - Four fixture JSON files covering all three payload shapes
  - 13 tests across three classes covering LSMT-01 through LSMT-05 and LSMT-08
affects:
  - 05-02 (route wiring — LangSmithAdapter must be imported and registered)
  - 05-03 (wizard — adapter is the destination for config written by wizard)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "hmac.compare_digest for timing-safe token header comparison (not HMAC computation)"
    - "Three-shape dispatch via discriminator key presence (kwargs, alert_rule_id, rule_id)"
    - "Clean-run suppression as first check after shape detection (LSMT-05)"
    - "condense() uses name+session not timestamps for writer.py dedup determinism"

key-files:
  created:
    - heartbeat_gateway/adapters/langsmith.py
    - tests/adapters/test_langsmith.py
    - tests/fixtures/langsmith_run_error.json
    - tests/fixtures/langsmith_run_clean.json
    - tests/fixtures/langsmith_feedback.json
    - tests/fixtures/langsmith_alert.json
  modified: []

key-decisions:
  - "LangSmith uses token header comparison (X-Langsmith-Secret), not HMAC computation — confirmed by FOUND-03"
  - "Clean run suppression (LSMT-05) is the first check after Shape B detection, before any metadata extraction"
  - "feedback_stats aggregates used for feedback normalization — no individual comment field available from LangSmith automation webhooks"
  - "NormalizedEvent source='langsmith' uses type: ignore comment — Literal updated in Plan 02"

patterns-established:
  - "Discriminator key dispatch: check 'kwargs' first (Shape B), then 'alert_rule_id', then 'rule_id' (Shape A)"
  - "Passthrough when token empty — consistent with other adapters' no-secret behavior"

requirements-completed: [LSMT-01, LSMT-02, LSMT-03, LSMT-04, LSMT-05, LSMT-08]

# Metrics
duration: 15min
completed: 2026-04-04
---

# Phase 5 Plan 01: LangSmith Adapter Summary

**LangSmithAdapter with timing-safe token auth, three-shape normalize dispatch, and clean-run suppression — 13 tests across all LSMT requirements**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-04T01:49:50Z
- **Completed:** 2026-04-04T02:05:00Z
- **Tasks:** 2 (TDD: RED then GREEN)
- **Files modified:** 6

## Accomplishments

- Implemented `LangSmithAdapter` with `verify_signature` using `hmac.compare_digest` for timing-safe token header comparison (not HMAC computation — LangSmith uses static tokens)
- `normalize()` dispatches across three payload shapes via discriminator keys: Shape B (kwargs), alert (alert_rule_id), Shape A (rule_id); clean runs dropped first (LSMT-05)
- `condense()` deterministic using name+session, never webhook_sent_at, ensuring writer.py dedup correctness
- Four fixture JSON files covering all real LangSmith webhook shapes
- 13 tests pass, full adapter suite (60 tests) unaffected

## Task Commits

Each task was committed atomically:

1. **Task 1: Write test fixtures and test stubs (RED)** - `690a268` (test)
2. **Task 2: Implement LangSmithAdapter (GREEN)** - `64a4c1e` (feat)

## Files Created/Modified

- `heartbeat_gateway/adapters/langsmith.py` - LangSmithAdapter class with verify_signature, normalize, condense
- `tests/adapters/test_langsmith.py` - 13 tests across TestLangSmithAdapterSignature, TestLangSmithAdapterNormalize, TestLangSmithAdapterCondense
- `tests/fixtures/langsmith_run_error.json` - Shape B fixture with error field populated
- `tests/fixtures/langsmith_run_clean.json` - Shape B fixture with error=null (always dropped)
- `tests/fixtures/langsmith_feedback.json` - Shape A fixture with negative feedback_stats
- `tests/fixtures/langsmith_alert.json` - Alert threshold fixture with alert_rule_id

## Decisions Made

- LangSmith uses token header comparison (`X-Langsmith-Secret`) not HMAC computation — plan confirmed by FOUND-03. `hmac.compare_digest` used for timing safety even though token is static.
- Clean run suppression (LSMT-05) is the very first check after Shape B detection — before metadata extraction or any other processing.
- `feedback_stats` aggregates are the only feedback data available from LangSmith automation webhooks; individual comment field does not exist. Documented in code.
- `NormalizedEvent(source="langsmith")` requires `type: ignore[arg-type]` comment since the `Literal` type annotation in `__init__.py` does not yet include "langsmith" — this is resolved in Plan 02.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- LangSmithAdapter is complete and tested; Plan 02 (route wiring) can proceed
- Plan 02 must update `NormalizedEvent` source Literal to include "langsmith" and wire the route in `app.py`
- Fixture files are in place for any integration tests Plan 02 may need

---
*Phase: 05-langsmith-adapter*
*Completed: 2026-04-04*

## Self-Check: PASSED

- FOUND: heartbeat_gateway/adapters/langsmith.py
- FOUND: tests/adapters/test_langsmith.py
- FOUND: tests/fixtures/langsmith_run_error.json
- FOUND: tests/fixtures/langsmith_run_clean.json
- FOUND: tests/fixtures/langsmith_feedback.json
- FOUND: tests/fixtures/langsmith_alert.json
- FOUND: commit 690a268 (test stubs + fixtures)
- FOUND: commit 64a4c1e (LangSmithAdapter implementation)
