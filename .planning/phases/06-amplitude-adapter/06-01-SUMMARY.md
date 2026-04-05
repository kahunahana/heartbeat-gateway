---
phase: 06-amplitude-adapter
plan: 01
subsystem: api
tags: [amplitude, webhook, adapter, normalization, pytest]

# Dependency graph
requires:
  - phase: 05-langsmith-adapter
    provides: LangSmithAdapter pattern (verify_signature passthrough, normalize, condense)
  - phase: 03-schema-foundation
    provides: AmplitudeWatchConfig in schema.py, NormalizedEvent dataclass

provides:
  - AmplitudeAdapter with permanent-passthrough verify_signature
  - normalize() for monitor_alert and chart.annotation event types
  - condense() using charts[0].header (dedup-deterministic, never what_happened)
  - NormalizedEvent.source Literal updated to include "amplitude"
  - Test fixtures: amplitude_monitor_alert.json, amplitude_annotation.json
  - 9 unit tests across 3 test classes

affects:
  - 06-02 (route wiring will import AmplitudeAdapter)
  - 06-03 (init wizard will reference amplitude config)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Permanent-passthrough verify_signature with IP allowlist docstring advisory
    - Empty-guard before charts[0] access to prevent IndexError
    - condense() dispatches on event_type, uses stable header field (not timestamp-embedded fields)

key-files:
  created:
    - heartbeat_gateway/adapters/amplitude.py
    - tests/adapters/test_amplitude.py
    - tests/fixtures/amplitude_monitor_alert.json
    - tests/fixtures/amplitude_annotation.json
  modified:
    - heartbeat_gateway/__init__.py

key-decisions:
  - "Amplitude verify_signature is permanent passthrough — Amplitude confirmed no webhook signing; docstring advises IP allowlisting"
  - "condense() uses charts[0].header not what_happened — what_happened embeds timestamp, breaking dedup determinism"
  - "Empty charts guard (if not charts: return None) prevents IndexError on monitor_alert with empty array"
  - "NormalizedEvent.source Literal updated in same task as adapter implementation — no type: ignore comments needed"

patterns-established:
  - "AmplitudeAdapter mirrors BraintrustAdapter structure exactly (passthrough verify, dispatch normalize, dispatch condense)"
  - "make_config() test helper uses AmplitudeWatchConfig for config isolation"

requirements-completed: [AMP-01, AMP-02, AMP-03, AMP-04, AMP-07]

# Metrics
duration: 5min
completed: 2026-04-05
---

# Phase 6 Plan 01: Amplitude Adapter Summary

**AmplitudeAdapter with passthrough signature, two-branch normalization (monitor_alert/chart.annotation), and header-based deterministic condense(); NormalizedEvent Literal updated; 9 tests all passing**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-05T10:41:18Z
- **Completed:** 2026-04-05T10:46:03Z
- **Tasks:** 2 (TDD RED + GREEN)
- **Files modified:** 5

## Accomplishments

- AmplitudeAdapter implemented with permanent-passthrough verify_signature (Amplitude has no webhook signing)
- normalize() handles monitor_alert (with empty-charts guard returning None) and chart.annotation; unknown event_type returns None
- condense() uses charts[0].header (not what_happened) ensuring dedup determinism across redeliveries; all outputs <= 240 chars
- NormalizedEvent.source Literal extended to include "amplitude" — no type: ignore needed
- Full test suite: 215 passed, 1 xfailed (no regressions from prior phases)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create test fixtures and test stubs for AmplitudeAdapter** - `02546dd` (test)
2. **Task 2: Implement AmplitudeAdapter and update NormalizedEvent Literal** - `be6e26b` (feat)

_Note: TDD tasks follow RED (test) → GREEN (feat) commit pattern_

## Files Created/Modified

- `heartbeat_gateway/adapters/amplitude.py` - AmplitudeAdapter class (verify_signature, normalize, condense)
- `heartbeat_gateway/__init__.py` - NormalizedEvent.source Literal updated to include "amplitude"
- `tests/adapters/test_amplitude.py` - 9 unit tests: 2 signature, 4 normalize, 3 condense
- `tests/fixtures/amplitude_monitor_alert.json` - Monitor alert fixture with charts array
- `tests/fixtures/amplitude_annotation.json` - Chart annotation fixture

## Decisions Made

- Permanent-passthrough verify_signature: Amplitude confirmed no webhook signing; docstring explicitly advises IP allowlisting as mitigation
- condense() uses charts[0].header not what_happened: what_happened embeds a timestamp, causing dedup misses on redeliveries (same pattern as Braintrust using automation.name not time fields)
- Empty-charts guard returns None before charts[0] access: prevents IndexError; consistent with plan constraint "empty charts array on monitor_alert returns None"
- NormalizedEvent Literal updated in the same task: avoids needing type: ignore, keeps type checking clean throughout

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- AmplitudeAdapter is fully importable from heartbeat_gateway.adapters.amplitude
- Route wiring (06-02) can import AmplitudeAdapter and register /webhooks/amplitude endpoint
- Init wizard (06-03) can reference AmplitudeWatchConfig for amplitude secret prompt
- All success criteria met: 9 tests pass, ruff clean, Literal updated

## Self-Check: PASSED

All files present:
- heartbeat_gateway/adapters/amplitude.py: FOUND
- heartbeat_gateway/__init__.py: FOUND
- tests/adapters/test_amplitude.py: FOUND
- tests/fixtures/amplitude_monitor_alert.json: FOUND
- tests/fixtures/amplitude_annotation.json: FOUND
- .planning/phases/06-amplitude-adapter/06-01-SUMMARY.md: FOUND

All commits present:
- 02546dd: FOUND (test: TDD RED phase)
- be6e26b: FOUND (feat: TDD GREEN phase)

---
*Phase: 06-amplitude-adapter*
*Completed: 2026-04-05*
