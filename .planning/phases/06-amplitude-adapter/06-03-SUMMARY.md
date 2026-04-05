---
phase: 06-amplitude-adapter
plan: 03
subsystem: cli
tags: [questionary, amplitude, init-wizard, docs]

# Dependency graph
requires:
  - phase: 06-amplitude-adapter
    provides: AmplitudeAdapter implementation and route wiring (plans 01-02)
  - phase: 05-langsmith-adapter
    provides: LangSmith wizard pattern used as template for Amplitude section
provides:
  - Amplitude checkbox entry in gateway init wizard (after LangSmith, before Linear)
  - No-signing warning inline before secret prompt
  - GATEWAY_WATCH__AMPLITUDE__SECRET written to .env when secret provided
  - docs/adapters.md Amplitude section with events, auth, setup, and limitations
affects: [06-amplitude-adapter, smoke-test, v0.4.0-release]

# Tech tracking
tech-stack:
  added: []
  patterns: [questionary.password for adapter secret prompts, no-signing inline warning pattern for passthrough adapters]

key-files:
  created: []
  modified:
    - heartbeat_gateway/commands/init.py
    - tests/cli/test_init.py
    - docs/adapters.md

key-decisions:
  - "Amplitude checkbox placed after LangSmith, before Linear — consistent with adapter build order convention"
  - "No-signing warning displayed inline before secret prompt — matches Braintrust pattern for passthrough adapters"
  - "questionary.password used for Amplitude secret — consistent with all other adapter secret prompts"

patterns-established:
  - "Passthrough adapter wizard pattern: inline no-signing warning + password prompt for future-compat secret"

requirements-completed: [AMP-06]

# Metrics
duration: 15min
completed: 2026-04-04
---

# Phase 6 Plan 03: Amplitude Init Wizard and Docs Summary

**Amplitude init wizard section with no-signing warning, GATEWAY_WATCH__AMPLITUDE__SECRET env var support, and docs/adapters.md Amplitude section completing the v0.4.0 adapter expansion**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-04T00:20:00Z
- **Completed:** 2026-04-04T00:35:00Z
- **Tasks:** 2 of 3 complete (Task 3 is human-verify checkpoint)
- **Files modified:** 3

## Accomplishments

- Amplitude added to gateway init checkbox list (after LangSmith, before Linear — build order convention)
- No-signing warning displayed inline before secret prompt, matching Braintrust passthrough pattern
- GATEWAY_WATCH__AMPLITUDE__SECRET written to .env when secret provided
- Three new tests: secret written, warning displayed, not-selected produces no env var
- docs/adapters.md Amplitude section added in alphabetical position (before Braintrust) with events table, auth explanation, setup instructions, and limitations
- Full test suite: 223 passed, 1 xfailed, ruff clean

## Task Commits

1. **Task 1: Add Amplitude section to gateway init wizard and update tests** - `3007e40` (feat)
2. **Task 2: Update docs/adapters.md with Amplitude section** - `f381662` (docs)
3. **Task 3: Smoke test** - awaiting human verification (checkpoint)

## Files Created/Modified

- `heartbeat_gateway/commands/init.py` - Added Amplitude checkbox entry and Section 4b with no-signing warning and secret prompt
- `tests/cli/test_init.py` - Added 3 Amplitude-specific tests; updated prompt order comment
- `docs/adapters.md` - Added ## Amplitude section (alphabetical, before Braintrust) with events, auth, setup, config, condensed examples, and limitations

## Decisions Made

- Amplitude placed after LangSmith in checkbox — consistent with adapter build order (PostHog → Braintrust → LangSmith → Amplitude → Linear → GitHub)
- No-signing warning uses same inline pattern as would be expected for any passthrough adapter (Braintrust precedent)
- questionary.password for secret prompt — consistent with all other adapter sections

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required for this plan.

## Next Phase Readiness

- Task 3 (smoke test) requires human verification: run `uv run heartbeat-gateway init`, select Amplitude, verify no-signing warning and .env output
- After smoke test approval: v0.4.0 Amplitude adapter is fully complete (plans 01-03 done)
- Full test suite green (223 passed, 1 xfailed) and ruff clean

---
*Phase: 06-amplitude-adapter*
*Completed: 2026-04-04*
