# Phase 3: Schema Foundation + PostHog Wizard — Context

**Gathered:** 2026-04-01
**Status:** Ready for planning
**Source:** Direct conversation — design decisions locked before planning

<domain>
## Phase Boundary

Phase 3 delivers two things:
1. Three new `*WatchConfig` classes in `schema.py` (AmplitudeWatchConfig, BraintrustWatchConfig, LangSmithWatchConfig) — config foundation for Phases 4/5/6
2. A refactored `gateway init` wizard that adds adapter selection via checkbox, adds PostHog prompts, and shows a help link for missing adapters

No adapter route handlers, normalizers, or classifiers ship in Phase 3. Schema and wizard only.

</domain>

<decisions>
## Implementation Decisions

### Adapter Checkbox — LOCKED
- `gateway init` must present a `questionary.checkbox()` for adapter selection BEFORE running any adapter prompt sections
- Only show adapters whose prompt branches are fully implemented — no placeholders for future adapters
- After Phase 3: checkbox shows Linear, GitHub, PostHog
- After Phase 4: adds Braintrust. After Phase 5: adds LangSmith. After Phase 6: adds Amplitude.
- Unselected adapters are silently skipped — no prompts, no .env entries written for them
- User selects subset; wizard only runs those sections in order

### Help Link — LOCKED
- After the checkbox (or at the end of the wizard), show:
  > "Don't see your adapter? https://github.com/kahunahana/heartbeat-gateway/blob/main/docs/adapters.md#adding-a-new-adapter"
- Source confirmed in CONTRIBUTING.md: adapter instructions live at `docs/adapters.md#adding-a-new-adapter`

### Wizard Refactor Scope — LOCKED
- Existing Linear and GitHub prompt sections are NOT removed — they are gated behind the checkbox selection
- If user selects Linear → run existing Linear prompts. If not selected → skip.
- Same for GitHub and PostHog.
- merge-by-default behavior (load existing .env values as prompt defaults) continues to apply per-adapter section

### PostHog Prompt Order — LOCKED (from existing roadmap success criterion)
- PostHog prompts run BEFORE the Linear section in the wizard sequence
- Checkbox order: PostHog, Linear, GitHub (or whatever makes UX sense — but PostHog before Linear)

### WatchConfig Inheritance — LOCKED
- All three new classes (AmplitudeWatchConfig, BraintrustWatchConfig, LangSmithWatchConfig) inherit `BaseModel`, NOT `BaseSettings`
- This is a hard constraint — BaseSettings caused silent secret bypass in v0.2.0 regression

### Regression Tests — LOCKED
- One regression test per new adapter: set env var via `monkeypatch.setenv`, instantiate `GatewayConfig()`, assert secret loaded correctly
- Test pattern: `monkeypatch.setenv` only, never mocked `GatewayConfig`

### Test Impact — LOCKED
- `tests/cli/test_init.py` `_HAPPY_PATH_ANSWERS` must be updated to include PostHog answers
- All existing wizard tests must pass — the checkbox refactor cannot break existing Linear/GitHub test paths

### Claude's Discretion
- Exact questionary widget type for checkbox (questionary.checkbox vs questionary.select)
- Whether to show the adapter help link before or after the checkbox
- Internal function structure for the refactored init command
- Whether adapter sections are dispatched via a dict/registry or sequential if-branches

</decisions>

<specifics>
## Specific References

- Adapter docs link: `https://github.com/kahunahana/heartbeat-gateway/blob/main/docs/adapters.md#adding-a-new-adapter`
- Source: `CONTRIBUTING.md` line 37: `See [docs/adapters.md](docs/adapters.md#adding-a-new-adapter) for the full adapter interface and registration steps.`
- Existing wizard implementation: `src/heartbeat_gateway/commands/init.py`
- Existing wizard tests: `tests/cli/test_init.py`
- Schema file: `src/heartbeat_gateway/schema.py`
- GatewayConfig: nested config loaded via pydantic-settings env var parsing

</specifics>

<deferred>
## Deferred Ideas

- Braintrust, LangSmith, Amplitude prompt sections — Phase 4/5/6 respectively
- Adapter ordering configurability — users cannot reorder the checkbox list in Phase 3
- "Skip all" / "Configure none" as explicit checkbox option — not required

</deferred>

---

*Phase: 03-schema-foundation-posthog-wizard*
*Context gathered: 2026-04-01 via direct conversation*
