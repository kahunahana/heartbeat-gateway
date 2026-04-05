---
phase: 06-amplitude-adapter
plan: 02
subsystem: api
tags: [fastapi, amplitude, webhook, doctor, integration-tests]

# Dependency graph
requires:
  - phase: 06-amplitude-adapter/06-01
    provides: AmplitudeAdapter with verify_signature passthrough and normalize()
provides:
  - POST /webhooks/amplitude route registered in FastAPI app
  - POST /webhook/amplitude 308 redirect
  - app.state.amplitude_adapter state binding
  - Amplitude excluded from require_signatures enforcement
  - Doctor WARN when require_signatures=true + amplitude.secret set
  - 4 integration tests for /webhooks/amplitude route
  - 1 doctor test for amplitude signature no-op WARN
affects: [06-03-amplitude-wizard, smoke-tests]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Permanent-passthrough adapters excluded from require_signatures enforcement with inline comment"
    - "Doctor WARN pattern for no-op secrets — surface misconfiguration without blocking"

key-files:
  created: []
  modified:
    - heartbeat_gateway/app.py
    - heartbeat_gateway/commands/doctor.py
    - tests/test_app.py
    - tests/cli/test_doctor.py

key-decisions:
  - "Amplitude route placed after langsmith route — consistent with build order (alpha after LangSmith in route list)"
  - "amplitude_adapter registered before braintrust_adapter in app.state — alphabetical ordering"
  - "Doctor WARN fires only when both require_signatures=True AND amplitude.secret is set — avoids noise in default config"
  - "make_gateway_config extended with amplitude_secret kwarg — follows existing braintrust_secret / langsmith_token pattern"

patterns-established:
  - "Adapter state registration: app.state.{source}_adapter = {Adapter}(config) alphabetical in create_app()"
  - "Require-signatures exclusion: inline comment in the missing-secrets guard block, no validator changes"

requirements-completed: [AMP-05]

# Metrics
duration: 15min
completed: 2026-04-04
---

# Phase 6 Plan 02: Amplitude Route Wiring Summary

**AmplitudeAdapter wired into FastAPI with /webhooks/amplitude route, 308 redirect, require_signatures exclusion, doctor WARN for no-op secret, and 5 new tests (220 total passing)**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-04T00:00:00Z
- **Completed:** 2026-04-04T00:15:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- POST /webhooks/amplitude and POST /webhook/amplitude (308 redirect) fully operational
- Amplitude excluded from require_signatures enforcement — no ValueError ever raised for amplitude missing secret
- Doctor emits WARN when GATEWAY_REQUIRE_SIGNATURES=true and GATEWAY_WATCH__AMPLITUDE__SECRET is set (no-op secret advisory)
- 5 new tests added: 4 route integration tests + 1 doctor WARN test; full suite at 220 passed / 1 xfailed

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire Amplitude route in app.py and add doctor WARN check** - `05b6266` (feat)
2. **Task 2: Add integration tests for /webhooks/amplitude route and doctor WARN** - `abbd154` (test)

**Plan metadata:** (see final commit)

## Files Created/Modified

- `heartbeat_gateway/app.py` - Added AmplitudeAdapter import, state binding, /webhooks/amplitude route, /webhook/amplitude redirect, require_signatures exclusion comment
- `heartbeat_gateway/commands/doctor.py` - Added Amplitude signature no-op WARN in _check_hmac_secrets()
- `tests/test_app.py` - Extended make_gateway_config with amplitude_secret; added TestAmplitudeWebhookRoute class (4 tests)
- `tests/cli/test_doctor.py` - Added test_amplitude_signature_noop_warn

## Decisions Made

- Amplitude route placed after LangSmith in route list — consistent with adapter build order
- amplitude_adapter registered before braintrust_adapter in app.state — alphabetical ordering matches imports
- Doctor WARN fires only when both require_signatures=True AND amplitude.secret is non-empty — avoids noise in default (no-secret) config
- make_gateway_config extended with amplitude_secret kwarg, consistent with braintrust_secret and langsmith_token pattern

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Amplitude route fully operational; Phase 6 Plan 03 (init wizard Amplitude section) is unblocked
- 220 tests passing — test baseline stable for wizard work

## Self-Check: PASSED

- heartbeat_gateway/app.py — FOUND
- heartbeat_gateway/commands/doctor.py — FOUND
- tests/test_app.py — FOUND
- tests/cli/test_doctor.py — FOUND
- .planning/phases/06-amplitude-adapter/06-02-SUMMARY.md — FOUND
- Commit 05b6266 — FOUND
- Commit abbd154 — FOUND

---
*Phase: 06-amplitude-adapter*
*Completed: 2026-04-04*
