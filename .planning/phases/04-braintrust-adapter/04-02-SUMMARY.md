---
phase: "04-braintrust-adapter"
plan: "02"
subsystem: "api"
tags: ["braintrust", "fastapi", "route", "adapter", "integration-tests", "literal"]

dependency_graph:
  requires:
    - phase: "04-braintrust-adapter"
      plan: "01"
      provides: "BraintrustAdapter class with verify_signature/normalize/condense"
  provides:
    - "POST /webhooks/braintrust route registered in app.py"
    - "POST /webhook/braintrust 308 redirect route"
    - "app.state.braintrust_adapter = BraintrustAdapter(config)"
    - "NormalizedEvent.source Literal includes 'braintrust'"
  affects:
    - "05-langsmith-adapter"
    - "06-amplitude-adapter"

tech-stack:
  added: []
  patterns:
    - "braintrust excluded from require_signatures guard — permanent-passthrough adapters skip secret enforcement"
    - "make_gateway_config() helper in test_app.py for parameterized integration tests"

key-files:
  created: []
  modified:
    - heartbeat_gateway/__init__.py
    - heartbeat_gateway/app.py
    - tests/test_app.py

key-decisions:
  - "braintrust excluded from require_signatures guard — verify_signature is permanent passthrough (option-b from plan 01), comment documents the exclusion explicitly"
  - "test_invalid_signature_always_passes_no_signing asserts != 401 instead of skipping — tests the passthrough behavior positively"

patterns-established:
  - "Permanent-passthrough adapters: add adapter to app.state, add route, omit from require_signatures guard with inline comment"
  - "Integration test classes use tmp_path fixture for GatewayConfig — consistent with existing standalone test functions"

requirements-completed:
  - BTST-05

duration: "~8 minutes"
completed: "2026-04-02"
---

# Phase 4 Plan 02: Braintrust Route Registration Summary

**BraintrustAdapter wired into FastAPI app with /webhooks/braintrust route, 308 redirect, NormalizedEvent Literal update, and 4 passing integration tests.**

## Performance

- **Duration:** ~8 minutes
- **Started:** 2026-04-02T14:53:00Z
- **Completed:** 2026-04-02T14:55:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Updated `NormalizedEvent.source` Literal from `["linear", "github", "posthog"]` to include `"braintrust"` — eliminates runtime TypeError before the classifier
- Registered `BraintrustAdapter` on `app.state.braintrust_adapter` and wired `POST /webhooks/braintrust` route through `_process_webhook`
- Added `POST /webhook/braintrust` 308 redirect (preserves POST method), matching the pattern for linear/github/posthog
- Excluded braintrust from `require_signatures` guard with explicit comment documenting the option-b decision
- Full test suite: 185 passed, 1 xfailed (4 new integration tests, up from 181 in Plan 01)

## Task Commits

Each task was committed atomically:

1. **Task 1: Update NormalizedEvent Literal and add integration test stubs (RED)** — `31f7fc8` (test)
2. **Task 2: Register BraintrustAdapter in app.py (GREEN)** — `b13dd8a` (feat)

**Plan metadata:** (docs commit to follow)

## Files Created/Modified

- `heartbeat_gateway/__init__.py` — NormalizedEvent.source Literal updated to include "braintrust"
- `heartbeat_gateway/app.py` — BraintrustAdapter import, adapter registration, /webhooks/braintrust route, /webhook/braintrust redirect, require_signatures exclusion comment
- `tests/test_app.py` — make_gateway_config() helper, TestBraintrustWebhookRoute class with 4 integration tests

## Decisions Made

**1. Braintrust excluded from require_signatures guard with explicit comment**
Option-b was decided in Plan 01 (permanent-passthrough verify_signature). Rather than raising ValueError when `require_signatures=True` and no braintrust secret is set, the guard skips braintrust entirely with a comment: `# braintrust excluded from require_signatures — verify_signature is permanent passthrough`. This matches the same pattern that would apply to AmplitudeAdapter.

**2. Invalid-signature test asserts `!= 401` (not skip)**
Since option-b was chosen, the test for "bad signature" was reframed as a positive assertion of the passthrough behavior: any POST to /webhooks/braintrust with a bad signature header must not return 401. This provides more test coverage than a skipped test.

## Deviations from Plan

None — plan executed exactly as written.

The plan specified adapting `make_gateway_config` to the existing test pattern. The existing file had no such helper, so one was added (Rule 2 boundary case — not a deviation, this was explicitly called out in the plan's action text: "Adapt make_gateway_config to accept braintrust_secret. Read the existing test_app.py helper pattern to match it exactly — do not introduce a new factory if one already exists."). Since no factory existed, creating one is correct plan execution.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 4 Plan 03 (PostHog wizard section update to include Braintrust) is ready to execute
- Phase 5 (LangSmith Adapter) can proceed once Plan 03 is complete
- All braintrust integration tests pass; adapter is fully live in the pipeline

---
*Phase: 04-braintrust-adapter*
*Completed: 2026-04-02*

## Self-Check: PASSED

Files verified:
- heartbeat_gateway/__init__.py: FOUND
- heartbeat_gateway/app.py: FOUND
- tests/test_app.py: FOUND
- .planning/phases/04-braintrust-adapter/04-02-SUMMARY.md: FOUND

Commits verified:
- 31f7fc8 (test stubs RED): FOUND
- b13dd8a (feat GREEN): FOUND
