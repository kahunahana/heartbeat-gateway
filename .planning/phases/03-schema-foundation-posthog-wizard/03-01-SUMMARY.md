---
phase: 03-schema-foundation-posthog-wizard
plan: 01
subsystem: config
tags: [pydantic, pydantic-settings, config, schema, amplitude, braintrust, langsmith]

# Dependency graph
requires: []
provides:
  - AmplitudeWatchConfig BaseModel class with secret field
  - BraintrustWatchConfig BaseModel class with secret field
  - LangSmithWatchConfig BaseModel class with token field
  - WatchConfig extended with amplitude, braintrust, langsmith fields
  - tests/test_schema.py regression tests for env var loading
affects:
  - 03-02 (PostHog wizard — same schema file)
  - 04-braintrust-adapter (BraintrustWatchConfig)
  - 05-langsmith-adapter (LangSmithWatchConfig)
  - 06-amplitude-adapter (AmplitudeWatchConfig)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "New WatchConfig classes inherit BaseModel (not BaseSettings) — prevents v0.2.0-style silent secret bypass"
    - "WatchConfig fields use Field(default_factory=...) for backward compatibility"

key-files:
  created:
    - tests/test_schema.py
  modified:
    - heartbeat_gateway/config/schema.py

key-decisions:
  - "AmplitudeWatchConfig and BraintrustWatchConfig use 'secret' field; LangSmithWatchConfig uses 'token' (per FOUND-03 — LangSmith API token naming)"
  - "All three new classes inherit BaseModel not BaseSettings — architectural constraint to prevent env bypass regression"

patterns-established:
  - "TDD red-green: write xfail stubs, commit, add implementation, remove xfail decorators, confirm PASSED"
  - "New WatchConfig subclasses pattern: BaseModel + model_config extra=ignore + single field with default"

requirements-completed: [FOUND-01, FOUND-02, FOUND-03]

# Metrics
duration: 12min
completed: 2026-04-01
---

# Phase 3 Plan 01: Schema Foundation Summary

**AmplitudeWatchConfig, BraintrustWatchConfig, and LangSmithWatchConfig added to schema.py as BaseModel subclasses, with env var loading verified end-to-end via three regression tests**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-04-01T00:00:00Z
- **Completed:** 2026-04-01T00:12:00Z
- **Tasks:** 2 (+ 1 TDD RED commit)
- **Files modified:** 2

## Accomplishments

- Three new WatchConfig classes created in heartbeat_gateway/config/schema.py, each correctly inheriting BaseModel (not BaseSettings)
- WatchConfig extended with amplitude, braintrust, langsmith fields using Field(default_factory=...)
- GATEWAY_WATCH__AMPLITUDE__SECRET, GATEWAY_WATCH__BRAINTRUST__SECRET, GATEWAY_WATCH__LANGSMITH__TOKEN env vars now load end-to-end
- tests/test_schema.py created with three green regression tests confirming env var loading via real GatewayConfig() instantiation
- Full test suite: 162 passed, 1 xfailed (was 159 + 3 new)
- ruff check and ruff format --check both pass

## Task Commits

Each task was committed atomically:

1. **RED — xfail stubs** - `cef6ff7` (test)
2. **Task 1: Add three WatchConfig classes + remove xfail** - `d62e841` (feat)
3. **Task 2: Lint and format** - `e292b28` (chore)

## Files Created/Modified

- `heartbeat_gateway/config/schema.py` - Added AmplitudeWatchConfig, BraintrustWatchConfig, LangSmithWatchConfig; extended WatchConfig with three new fields
- `tests/test_schema.py` - Three regression tests: monkeypatch.setenv + real GatewayConfig() instantiation for all three adapters

## Decisions Made

- LangSmithWatchConfig uses `token` field (not `secret`) — LangSmith uses "API token" terminology per FOUND-03; env var is GATEWAY_WATCH__LANGSMITH__TOKEN
- All three classes inherit BaseModel not BaseSettings — architectural constraint documented in CLAUDE.md; BaseSettings would cause silent secret bypass via independent instantiation through default_factory

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Schema foundation complete: all three adapter phases (04 Braintrust, 05 LangSmith, 06 Amplitude) now have config models ready
- Plan 03-02 (PostHog wizard) can proceed immediately — schema.py is in clean state
- Phases 04/05/06 can reference config.watch.amplitude.secret, config.watch.braintrust.secret, config.watch.langsmith.token directly

---
*Phase: 03-schema-foundation-posthog-wizard*
*Completed: 2026-04-01*
