---
phase: 03-schema-foundation-posthog-wizard
verified: 2026-04-01T00:00:00Z
status: passed
score: 12/13 must-haves verified
re_verification: false
human_verification:
  - test: "Run `uv run heartbeat-gateway init` in a real terminal (not CliRunner). Walk through the full wizard interactively."
    expected: "1) Checkbox appears with 'Which adapters do you want to configure?' showing PostHog, Linear, GitHub — all pre-checked. 2) Help link 'Don't see your adapter? https://github.com/kahunahana/heartbeat-gateway/blob/main/docs/adapters.md#adding-a-new-adapter' is displayed after the checkbox. 3) If PostHog is checked, PostHog project_id and secret prompts appear before the Linear section. 4) Deselecting an adapter in the checkbox causes its prompts to be skipped entirely. 5) Wizard completes with 'gateway doctor' in output."
    why_human: "questionary.checkbox() renders a TTY-interactive widget that CliRunner bypasses entirely via monkeypatching. Automated tests verify the logic but cannot confirm the terminal renders the checkbox, the pre-checked defaults display, or the Space/Enter UX behaves as intended. The empty-checkbox bug (commit de8cc49) was only discovered through real terminal testing."
---

# Phase 3: Schema Foundation + PostHog Wizard Verification Report

**Phase Goal:** Add schema foundation for 3 new adapters (Amplitude, Braintrust, LangSmith) and extend the gateway init wizard with PostHog support and checkbox adapter selection.
**Verified:** 2026-04-01
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | GatewayConfig loads GATEWAY_WATCH__AMPLITUDE__SECRET at config.watch.amplitude.secret | VERIFIED | `test_amplitude_config_loads_from_env` PASSED — real GatewayConfig() instantiation with monkeypatch.setenv confirms env var flows through pydantic-settings nested delimiter |
| 2 | GatewayConfig loads GATEWAY_WATCH__BRAINTRUST__SECRET at config.watch.braintrust.secret | VERIFIED | `test_braintrust_config_loads_from_env` PASSED |
| 3 | GatewayConfig loads GATEWAY_WATCH__LANGSMITH__TOKEN at config.watch.langsmith.token | VERIFIED | `test_langsmith_config_loads_from_env` PASSED — note field is `token`, not `secret`, as required by FOUND-03 |
| 4 | All three new WatchConfig classes inherit BaseModel (not BaseSettings) | VERIFIED | schema.py lines 32–48: `class AmplitudeWatchConfig(BaseModel)`, `class BraintrustWatchConfig(BaseModel)`, `class LangSmithWatchConfig(BaseModel)` — no BaseSettings in class hierarchy |
| 5 | WatchConfig extension is backward-compatible (extra='ignore' + default_factory) | VERIFIED | schema.py lines 56–58: all three fields use `Field(default_factory=...)`. Full suite: 164 passed, 1 xfailed — no regression. |
| 6 | Checkbox appears in wizard before adapter sections | VERIFIED | init.py lines 118–126: `questionary.checkbox(...)` inserted after core config prompts (Section 1), before all adapter sections |
| 7 | Checkbox offers PostHog, Linear, GitHub in that order | VERIFIED | init.py lines 120–124: `Choice("PostHog", checked=True)`, `Choice("Linear", checked=True)`, `Choice("GitHub", checked=True)` |
| 8 | Help link appears after checkbox | VERIFIED | init.py lines 130–133: `click.echo("  Don't see your adapter? https://github.com/kahunahana/heartbeat-gateway/blob/main/docs/adapters.md#adding-a-new-adapter")` immediately follows checkbox block |
| 9 | PostHog prompts run before Linear section | VERIFIED | init.py lines 135–154 (Section 2: PostHog) precede lines 156–180 (Section 3: Linear). `test_posthog_prompts_before_linear` PASSED |
| 10 | Unselected adapters produce no prompts and no .env entries | VERIFIED | `test_checkbox_gates_adapters` PASSED — GitHub-only selection writes no LINEAR or POSTHOG keys to .env |
| 11 | Happy-path test with 10 text/password answers + all-adapters checkbox passes | VERIFIED | `test_wizard_happy_path` PASSED with updated `_HAPPY_PATH_ANSWERS` (10 items); checkbox handled separately via default |
| 12 | Existing tests continue to pass after wizard refactor | VERIFIED | All 11 init tests pass; full suite 164 passed, 1 xfailed (same xfail as before Phase 3) |
| 13 | Real terminal renders checkbox correctly with pre-checked defaults and correct UX | HUMAN NEEDED | CliRunner bypasses questionary TTY rendering. SUMMARY documents that a real terminal bug (empty list on Enter without Space) was caught and fixed via commit de8cc49, but formal terminal approval is not recorded in phase artifacts. |

**Score:** 12/13 truths verified (1 requires human confirmation)

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `heartbeat_gateway/config/schema.py` | AmplitudeWatchConfig, BraintrustWatchConfig, LangSmithWatchConfig classes + WatchConfig fields | VERIFIED | File exists (82 lines). Contains all three classes at lines 32–58. Each inherits BaseModel. WatchConfig has `amplitude`, `braintrust`, `langsmith` fields with `Field(default_factory=...)`. File is ruff-clean. |
| `tests/test_schema.py` | Regression tests for env var loading for all three adapters | VERIFIED | File exists (25 lines). Three tests present with no xfail decorators. All three PASSED in test run. |
| `heartbeat_gateway/commands/init.py` | Refactored wizard with questionary.checkbox() + PostHog section | VERIFIED | File exists (225 lines). Contains `questionary.checkbox` at line 118. PostHog section at lines 135–154. Help link at lines 130–133. Gating logic for all three adapters confirmed. |
| `tests/cli/test_init.py` | Updated _HAPPY_PATH_ANSWERS (10 items), _make_questionary_mocks with checkbox_answer, two new test functions | VERIFIED | File exists (287 lines). `_QUESTIONARY_CHECKBOX` constant at line 30. `_make_questionary_mocks` accepts `checkbox_answer` parameter at line 40. `_HAPPY_PATH_ANSWERS` is 10 items. `test_posthog_prompts_before_linear` and `test_checkbox_gates_adapters` both present and PASSED. |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| WatchConfig | AmplitudeWatchConfig | `amplitude: AmplitudeWatchConfig = Field(default_factory=AmplitudeWatchConfig)` | WIRED | schema.py line 56 — exact pattern matches plan requirement |
| WatchConfig | BraintrustWatchConfig | `braintrust: BraintrustWatchConfig = Field(default_factory=BraintrustWatchConfig)` | WIRED | schema.py line 57 |
| WatchConfig | LangSmithWatchConfig | `langsmith: LangSmithWatchConfig = Field(default_factory=LangSmithWatchConfig)` | WIRED | schema.py line 58 |
| GatewayConfig | WatchConfig | `env_nested_delimiter='__'` in model_config + `watch: WatchConfig = Field(default_factory=WatchConfig)` | WIRED | schema.py lines 62–81 — confirmed end-to-end by all three schema regression tests passing |
| tests/cli/test_init.py | questionary.checkbox in init.py | `monkeypatch.setattr(_QUESTIONARY_CHECKBOX, mock_checkbox)` | WIRED | test_init.py line 69 patches `heartbeat_gateway.commands.init.questionary.checkbox` |
| gateway init wizard | PostHog section | `if "PostHog" in selected_adapters:` | WIRED | init.py line 136 — section gated correctly; `test_posthog_prompts_before_linear` confirms key written to .env |
| GATEWAY_WATCH__POSTHOG__PROJECT_ID | PostHogWatchConfig.project_id | `answers["GATEWAY_WATCH__POSTHOG__PROJECT_ID"] = posthog_project_id.strip()` | WIRED | init.py line 146 — key written when project_id is non-empty |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| FOUND-01 | 03-01 | WatchConfig adds AmplitudeWatchConfig model with secret field | SATISFIED | schema.py lines 32–35; test_amplitude_config_loads_from_env PASSED |
| FOUND-02 | 03-01 | WatchConfig adds BraintrustWatchConfig model with secret field | SATISFIED | schema.py lines 38–41; test_braintrust_config_loads_from_env PASSED |
| FOUND-03 | 03-01 | WatchConfig adds LangSmithWatchConfig model with token field | SATISFIED | schema.py lines 44–47 — field is `token` (not secret); test_langsmith_config_loads_from_env PASSED |
| FOUND-04 | 03-02 | gateway init wizard adds PostHog section — project_id + secret prompts before Linear | SATISFIED (automated) / HUMAN NEEDED (TTY visual) | init.py PostHog section precedes Linear; test_posthog_prompts_before_linear and test_checkbox_gates_adapters PASSED; checkbox TTY render needs human confirm |

No orphaned requirements found. All four Phase 3 requirements are claimed and covered.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | — | — | — |

No TODO/FIXME/placeholder comments, no empty implementations, no stub handlers in any phase files. xfail decorators were correctly removed from both test files after implementation. ruff check exits 0 on all four phase files.

---

## Human Verification Required

### 1. Real Terminal Checkbox Rendering

**Test:** In an interactive terminal, run `uv run heartbeat-gateway init`. Walk through the full wizard.

**Expected:**
1. After the core config prompts (API key, workspace path, SOUL.md path, LLM model), a checkbox prompt appears: "Which adapters do you want to configure?" with PostHog, Linear, and GitHub listed — all pre-checked with `[x]` indicators.
2. The instruction "(Space to toggle, Enter to confirm)" is visible below or near the checkbox.
3. After confirming the checkbox selection, the help link appears: "  Don't see your adapter? https://github.com/kahunahana/heartbeat-gateway/blob/main/docs/adapters.md#adding-a-new-adapter"
4. If PostHog is selected, PostHog project_id and PostHog secret prompts appear before any Linear prompts.
5. Deselecting an adapter (pressing Space on it before Enter) causes that adapter's prompts to be skipped entirely.
6. Wizard completes with "gateway doctor" in output.
7. Test the "no adapters" edge case: deselect all three. Wizard should complete with core config only — no adapter .env entries.

**Why human:** questionary.checkbox() renders an interactive TTY widget that CliRunner replaces with a monkeypatched mock. Automated tests verify gate logic and .env output but cannot confirm the visual rendering, the `[x]` pre-checked default display, or the Space/Enter interaction model. The SUMMARY documents that this exact TTY test caught a real bug (empty-list behavior on Enter without Space, fixed in commit de8cc49) — confirming the importance of this checkpoint.

**Note:** The SUMMARY (03-02-SUMMARY.md) documents that the human checkpoint was completed and the bug found was fixed before the phase was marked complete. This verification is seeking formal recorded approval to close the gate.

---

## Gaps Summary

No blocking gaps found. All automated checks pass:
- 14/14 targeted tests pass (3 schema + 11 init)
- Full suite: 164 passed, 1 xfailed (no regressions; xfailed test is the pre-existing intentional race condition demo)
- ruff check and ruff format --check both exit 0 on all four phase files
- All four FOUND requirements have implementation evidence
- No anti-patterns, stubs, or orphaned artifacts detected

The single human_needed item is the TTY visual verification of the checkbox widget rendering. The SUMMARY indicates a human ran the wizard and caught a bug (fixed it), but no formal "approved" record exists in the phase artifacts — this needs a final terminal confirmation to close the checkpoint gate.

---

_Verified: 2026-04-01_
_Verifier: Claude (gsd-verifier)_
