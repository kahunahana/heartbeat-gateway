---
phase: 03-schema-foundation-posthog-wizard
plan: 02
subsystem: cli
tags: [questionary, checkbox, init-wizard, posthog, dotenv]

# Dependency graph
requires:
  - phase: 03-01
    provides: PostHogWatchConfig schema fields (project_id, secret) already in GatewayConfig
provides:
  - questionary.checkbox() adapter selection gate in gateway init wizard
  - PostHog project_id and secret prompts in wizard
  - Checkbox pre-checks all adapters by default (Space to deselect)
  - Adapter-gated sections: PostHog before Linear before GitHub
affects:
  - Phase 4 (Braintrust adapter) — wizard pattern established for adding new adapter sections

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "questionary.Choice(name, checked=True) for pre-checked checkbox defaults"
    - "checkbox instruction=(Space to toggle, Enter to confirm) UX guidance"
    - "Adapter sections gated behind 'AdapterName' in selected_adapters list membership check"

key-files:
  created: []
  modified:
    - heartbeat_gateway/commands/init.py
    - tests/cli/test_init.py

key-decisions:
  - "Pre-check all adapters by default — user presses Enter to keep all, Space to deselect unwanted; avoids silent empty-list bug"
  - "Add instruction text to checkbox prompt so users know Space toggles, Enter confirms"
  - "PostHog section runs before Linear section (FOUND-04 requirement)"

patterns-established:
  - "Checkbox adapter gate: use Choice(name, checked=True) for sensible defaults"
  - "New adapter wizard section: add Choice to checkbox list + gated if-block after checkbox"

requirements-completed: [FOUND-04]

# Metrics
duration: 25min
completed: 2026-04-01
---

# Phase 3 Plan 02: PostHog Init Wizard Summary

**questionary.checkbox() adapter selection gate in gateway init with all adapters pre-checked by default, PostHog project_id + secret prompts before Linear, and UX fix for empty-list bug when user presses Enter without Space**

## Performance

- **Duration:** ~25 min (including bug diagnosis and fix)
- **Started:** 2026-04-01T00:00:00Z
- **Completed:** 2026-04-01T00:25:00Z
- **Tasks:** 3 (Tasks 1+2 from prior session; Task 3 = bug fix in this session)
- **Files modified:** 2

## Accomplishments

- Added questionary.checkbox() to gateway init wizard with PostHog, Linear, GitHub options
- PostHog section (project_id + secret) runs before Linear — satisfies FOUND-04
- Fixed critical UX bug: checkbox now pre-checks all adapters so pressing Enter without Space still configures all three (prior behavior returned empty list, skipping all adapter prompts)
- Added "(Space to toggle, Enter to confirm)" instruction hint to checkbox prompt
- Full mock infrastructure for checkbox in tests: `_make_questionary_mocks` accepts `checkbox_answer` parameter; `_QUESTIONARY_CHECKBOX` patch target added
- Two new tests: `test_posthog_prompts_before_linear`, `test_checkbox_gates_adapters`
- Full suite: 164 passed, 1 xfailed

## Task Commits

1. **Task 1: Checkbox refactor + PostHog wizard section** - `1503422` (feat)
2. **Task 2: Lint and full suite verification** - `2b53b58` (chore)
3. **Task 3: Fix empty checkbox bug** - `de8cc49` (fix)

## Files Created/Modified

- `heartbeat_gateway/commands/init.py` - questionary.checkbox() with pre-checked Choice objects + PostHog adapter section
- `tests/cli/test_init.py` - Updated mock infrastructure, _HAPPY_PATH_ANSWERS (10 items), two new tests

## Decisions Made

- Pre-check all adapters by default: `Choice("PostHog", checked=True)` etc. The default should be "configure everything" — advanced users can deselect. This avoids the silent empty-list failure when users press Enter without Space.
- Added `instruction="(Space to toggle, Enter to confirm)"` — questionary's built-in instruction rendering; no extra click.echo() needed.
- PostHog before Linear: matches FOUND-04 requirement and logical order (analytics → project management → SCM).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Pre-check all adapters to fix empty-list checkbox behavior**
- **Found during:** Task 3 (human verification)
- **Issue:** `questionary.checkbox()` with plain string choices returns `[]` when user presses Enter without pressing Space to toggle items. User highlighted PostHog and pressed Enter, which submitted an empty list. `"PostHog" in []` is False, so the PostHog prompts were silently skipped.
- **Fix:** Replaced plain string choices with `questionary.Choice("PostHog", checked=True)` (and same for Linear, GitHub). Added `instruction="(Space to toggle, Enter to confirm)"` for UX clarity.
- **Files modified:** `heartbeat_gateway/commands/init.py`
- **Verification:** All 11 init tests pass; `uv run pytest` 164 passed, 1 xfailed; ruff clean
- **Committed in:** `de8cc49`

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug)
**Impact on plan:** Fix required for correct operation; no scope creep.

## Issues Encountered

The checkbox UX bug was only discoverable through real terminal testing — CliRunner mocks bypass questionary entirely, so the empty-list behavior was invisible to automated tests. The human checkpoint gate caught it correctly.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 3 Plan 02 complete — PostHog wizard section delivered and verified
- Phase 4 (Braintrust Adapter) can begin — wizard pattern established for adding new adapter: add `Choice(name, checked=True)` to checkbox list, add gated if-block with adapter prompts
- Pattern note: any new adapter wizard section should use `Choice(name, checked=True)` not plain strings

---
*Phase: 03-schema-foundation-posthog-wizard*
*Completed: 2026-04-01*
