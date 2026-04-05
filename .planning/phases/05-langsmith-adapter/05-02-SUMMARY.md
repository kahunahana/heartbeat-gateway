---
phase: 05-langsmith-adapter
plan: "02"
subsystem: api
tags: [langsmith, fastapi, webhook, adapter, integration-test]

# Dependency graph
requires:
  - phase: 05-01
    provides: LangSmithAdapter class with verify_signature and normalize methods
provides:
  - /webhooks/langsmith route registered in FastAPI app
  - /webhook/langsmith 308 redirect registered
  - LangSmithAdapter on app.state.langsmith_adapter
  - NormalizedEvent.source Literal updated to include 'langsmith'
  - langsmith exclusion comment in require_signatures guard
  - Integration tests for /webhooks/langsmith route
affects: [05-03, 06-amplitude-adapter]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Adapter wiring: import → app.state registration → route → redirect (same pattern as braintrust)"
    - "require_signatures exclusion comment for non-HMAC adapters"
    - "TDD: RED commit with failing tests, GREEN commit with implementation"

key-files:
  created: []
  modified:
    - heartbeat_gateway/__init__.py
    - heartbeat_gateway/app.py
    - tests/test_app.py

key-decisions:
  - "Import order follows ruff isort: braintrust → github → langsmith (alphabetical within adapter group)"
  - "make_gateway_config extended with langsmith_token kwarg, mapping to LangSmithWatchConfig(token=...)"

patterns-established:
  - "New adapter wiring: add import, add app.state.{source}_adapter, add route, add redirect"
  - "Non-HMAC adapters get explicit exclusion comment in require_signatures guard"

requirements-completed: [LSMT-06]

# Metrics
duration: 15min
completed: 2026-04-04
---

# Phase 5 Plan 02: LangSmith Adapter Route Wiring Summary

**LangSmithAdapter wired into FastAPI via /webhooks/langsmith route, NormalizedEvent Literal updated, and 4 integration tests passing — TDD red-green cycle complete**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-04T17:10:00Z
- **Completed:** 2026-04-04T17:25:00Z
- **Tasks:** 2 (TDD RED + GREEN)
- **Files modified:** 3

## Accomplishments

- Updated `NormalizedEvent.source` Literal in `__init__.py` to include `"langsmith"` — removes the `# type: ignore` workaround from 05-01
- Registered `LangSmithAdapter` on `app.state`, added `/webhooks/langsmith` POST route and `/webhook/langsmith` 308 redirect in `app.py`
- Added `# langsmith excluded from require_signatures` comment to the guard block (token header, not HMAC)
- All 4 integration tests for `/webhooks/langsmith` pass; full suite 206 passed, 1 xfailed (intentional)

## Task Commits

Each task was committed atomically:

1. **Task 1: Update NormalizedEvent Literal and add integration test stubs** - `e2ab780` (test)
2. **Task 2: Register LangSmithAdapter in app.py (GREEN)** - `e2e54f0` (feat)

_Note: TDD tasks have two commits (test RED → feat GREEN)_

## Files Created/Modified

- `heartbeat_gateway/__init__.py` - NormalizedEvent.source Literal now includes "langsmith"
- `heartbeat_gateway/app.py` - LangSmithAdapter import, app.state registration, route, redirect, exclusion comment
- `tests/test_app.py` - LangSmithWatchConfig import, make_gateway_config extended, TestLangSmithWebhookRoute class (4 tests)

## Decisions Made

- Import order: placed `langsmith` import alphabetically between `github` and `linear` in adapter imports (ruff isort)
- `make_gateway_config` helper extended with `langsmith_token` kwarg (not breaking — defaults to empty string), maps to `LangSmithWatchConfig(token=langsmith_token)`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed ruff import sort order**
- **Found during:** Task 2 (after initial edit)
- **Issue:** LangSmith import was placed after BraintrustAdapter instead of alphabetically — ruff I001 violation
- **Fix:** Reordered adapter imports to: braintrust → github → langsmith → linear → posthog
- **Files modified:** heartbeat_gateway/app.py
- **Verification:** `ruff check heartbeat_gateway/app.py` passes cleanly
- **Committed in:** e2e54f0 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - import sort order)
**Impact on plan:** Minor cosmetic fix required by ruff. No behavior change.

## Issues Encountered

None — plan executed as specified. ruff format also applied to `tests/test_app.py` to satisfy `ruff format --check .`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 05-02 complete: LangSmith adapter fully integrated into the gateway pipeline
- 05-03 (LangSmith init wizard section) is the remaining plan in Phase 5
- Full suite green with no regressions; ready to proceed

---
*Phase: 05-langsmith-adapter*
*Completed: 2026-04-04*
