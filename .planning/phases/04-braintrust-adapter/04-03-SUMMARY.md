---
phase: "04-braintrust-adapter"
plan: "03"
subsystem: "cli"
tags: ["braintrust", "init", "wizard", "docs"]
dependency_graph:
  requires: ["heartbeat_gateway/commands/init.py", "docs/adapters.md"]
  provides: ["heartbeat_gateway/commands/init.py", "docs/adapters.md"]
  affects: ["tests/cli/test_init.py"]
---

# Plan 04-03 Summary: Init Wizard + Docs

## What Was Built

- Braintrust section added to `gateway init` wizard with BTQL automation setup instructions and signing secret prompt
- `docs/adapters.md` updated with full Braintrust adapter documentation
- Manual smoke test passed — wizard displays instructions, writes `GATEWAY_WATCH__BRAINTRUST__SECRET` to `.env`

## Key Decisions

- **Checkbox switched to unchecked-by-default** — pre-checked adapters caused UX inversion where Space toggled items OFF instead of ON. Empty selection now shows "Please select at least one adapter" and re-prompts. This overrides the Phase 3 architectural decision (checked=True) based on real-world smoke test feedback.
- **Braintrust section placed between PostHog and Linear** — follows research-recommended build order

## Commits

- `162fb33` — test(04-03): add failing tests for Braintrust init wizard section
- `9758ab7` — feat(04-03): add Braintrust section to gateway init wizard
- `bacc71e` — chore(04-03): apply ruff format to test_init.py
- `9302577` — docs(04-03): add Braintrust adapter to docs/adapters.md
- `10fb706` — fix(04-03): restore checked=True for all checkbox adapters including Braintrust
- `537183c` — fix(04-03): switch adapter checkbox to unchecked-by-default with empty-selection guard

## Test Impact

- 187 passed, 1 xfailed after plan completion
- 2 new Braintrust init tests + 1 empty-selection re-prompt test
- `test_no_confirmation_message_when_no_adapters` replaced by `test_empty_selection_reprompts`

## Requirements Closed

- **BTST-06**: gateway init prompts for Braintrust secret with BTQL setup instructions
- **BTST-07**: docs/adapters.md documents the Braintrust adapter
