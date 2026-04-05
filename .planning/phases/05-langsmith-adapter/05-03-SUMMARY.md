---
phase: 05-langsmith-adapter
plan: "03"
subsystem: cli
tags: [questionary, wizard, init, langsmith, dotenv]

# Dependency graph
requires:
  - phase: 05-01
    provides: LangSmithAdapter implemented with GATEWAY_WATCH__LANGSMITH__TOKEN config key
provides:
  - LangSmith checkbox entry in gateway init wizard (between Braintrust and Linear)
  - GATEWAY_WATCH__LANGSMITH__TOKEN written to .env when token provided
  - docs/adapters.md LangSmith section with events, auth, setup, and limitations
affects: [05-02, phase-06-amplitude]

# Tech tracking
tech-stack:
  added: []
  patterns: [questionary.password for token prompts (parallel to Braintrust secret pattern)]

key-files:
  created: []
  modified:
    - heartbeat_gateway/commands/init.py
    - tests/cli/test_init.py
    - docs/adapters.md

key-decisions:
  - "LangSmith uses token (not secret) in prompt text and env var name — GATEWAY_WATCH__LANGSMITH__TOKEN"
  - "LangSmith placed between Braintrust and Linear in checkbox — consistent with adapter implementation order"
  - "Wizard instructions explicitly call out X-Langsmith-Secret header requirement inline"

patterns-established:
  - "New adapter wizard section: checkbox choice + click.echo instructions block + questionary.password prompt"

requirements-completed: [LSMT-07]

# Metrics
duration: 15min
completed: 2026-04-05
---

# Phase 5 Plan 03: LangSmith Init Wizard Summary

**LangSmith adapter checkbox and token prompt added to gateway init wizard with webhook URL and X-Langsmith-Secret header setup instructions, plus full LangSmith section in docs/adapters.md**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-04T22:00:00Z
- **Completed:** 2026-04-04T22:15:00Z
- **Tasks:** 3 of 3 complete (Task 3 smoke test approved by user)
- **Files modified:** 3

## Accomplishments

- LangSmith added to adapter checkbox (between Braintrust and Linear, unchecked by default)
- Selecting LangSmith displays inline setup instructions including X-Langsmith-Secret header guidance before the token prompt
- GATEWAY_WATCH__LANGSMITH__TOKEN written to .env when a non-blank token is provided; absent when not selected
- All 21 init tests pass including 2 new LSMT-07 tests; existing _HAPPY_PATH_ANSWERS unaffected
- docs/adapters.md documents LangSmith with three event types, token auth, setup steps, and dataset webhook limitation

## Task Commits

Each task was committed atomically:

1. **Test RED: LangSmith failing tests** - `5eceb3f` (test)
2. **Task 1: Add LangSmith section to init wizard** - `384ea57` (feat)
3. **Chore: ruff format test_init.py** - `116df99` (chore)
4. **Task 2: Update docs/adapters.md** - `03de28d` (docs)

_Note: TDD — RED commit precedes GREEN (feat) commit per TDD protocol_

## Files Created/Modified

- `heartbeat_gateway/commands/init.py` - LangSmith Choice added to checkbox; Section 4 LangSmith block with instructions and token prompt
- `tests/cli/test_init.py` - Two new LSMT-07 tests: token written when selected, absent when not selected
- `docs/adapters.md` - LangSmith section: webhook URL, token auth, setup instructions, three event types, suppressed events, config env var, limitations note

## Decisions Made

- LangSmith section numbered as Section 4 (Linear bumped to 5, GitHub to 6) — maintains sequential numbering in init.py
- Password prompt text matches plan spec exactly: "LangSmith API token (leave blank to skip):"
- Inline echo instructions explicitly state "X-Langsmith-Secret: <your-token>" to guide users — critical because it's a custom header, not a standard signing mechanism

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required beyond what the wizard handles.

## Next Phase Readiness

- Task 3 smoke test approved: user ran `uv run heartbeat-gateway init`, selected LangSmith only, confirmed wizard displayed "LangSmith webhook setup", "Settings → Webhooks → Add Webhook", "X-Langsmith-Secret: <your-token>", and token prompt with "leave blank to skip". Gateway doctor showed 8 passed, 2 warned (Linear/GitHub secrets not set — expected).
- Phase 5 is fully complete (05-01 adapter, 05-02 route wiring, 05-03 wizard)
- Phase 6 (Amplitude Adapter) ready to begin

---
*Phase: 05-langsmith-adapter*
*Completed: 2026-04-05*

## Self-Check: PASSED

- init.py: FOUND
- test_init.py: FOUND
- adapters.md: FOUND
- 05-03-SUMMARY.md: FOUND
- Commit 5eceb3f (test RED): FOUND
- Commit 384ea57 (feat Task 1): FOUND
- Commit 03de28d (docs Task 2): FOUND
