---
phase: 05-langsmith-adapter
verified: 2026-04-04T02:30:00Z
status: passed
score: 8/8 must-haves verified
re_verification: false
gaps: []
human_verification:
  - test: "Manual wizard smoke test"
    expected: "Running `uv run gateway init`, selecting LangSmith, confirms inline instructions show 'LangSmith webhook setup', 'Settings → Webhooks → Add Webhook', 'X-Langsmith-Secret: <your-token>', and the token is written to .env as GATEWAY_WATCH__LANGSMITH__TOKEN"
    why_human: "03-SUMMARY documents Task 3 as approved by user (smoke test approved signal given). This is noted for completeness — the automated init tests cover the functional path."
---

# Phase 5: LangSmith Adapter Verification Report

**Phase Goal:** A LangSmith webhook arrives at `/webhooks/langsmith`, passes custom-header token validation, and produces classified entries for run errors, negative feedback, and alert threshold crossings — while silently dropping clean run completions.
**Verified:** 2026-04-04T02:30:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `verify_signature` returns True when token matches X-Langsmith-Secret header | VERIFIED | `test_token_match_returns_true` passes; `hmac.compare_digest(token, incoming)` at langsmith.py:25 |
| 2 | `verify_signature` returns False when token does not match X-Langsmith-Secret header | VERIFIED | `test_token_mismatch_returns_false` passes; compare_digest returns False on mismatch |
| 3 | `verify_signature` returns True when no token configured (passthrough) | VERIFIED | `test_no_token_always_passes` passes; early return `True` when `not token` at langsmith.py:22-23 |
| 4 | `normalize()` returns None for Shape B payloads with `error=null` (LSMT-05 clean run suppression) | VERIFIED | `test_clean_run_returns_none` passes; `if not error: return None` at langsmith.py:47-48 |
| 5 | `normalize()` returns NormalizedEvent(source='langsmith', event_type='run.error') for Shape B with error | VERIFIED | `test_normalizes_run_error` and `test_normalizes_run_error_metadata` pass; source, event_type, run_name, session_name, error_message all in metadata |
| 6 | `normalize()` returns NormalizedEvent(source='langsmith', event_type='feedback') for Shape A with negative score | VERIFIED | `test_normalizes_feedback` passes; feedback_key, feedback_score < 0 confirmed |
| 7 | `normalize()` returns NormalizedEvent(source='langsmith', event_type='alert.threshold') for alert payload | VERIFIED | `test_normalizes_alert` passes; alert_rule_name, triggered_metric_value=15, triggered_threshold=10 confirmed |
| 8 | `condense()` is deterministic and <= 240 chars, uses name+session not webhook_sent_at | VERIFIED | `test_condense_deterministic`, `test_condense_run_error_le_240`, `test_condense_alert_le_240`, `test_condense_no_timestamps` all pass |

**Score:** 8/8 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `heartbeat_gateway/adapters/langsmith.py` | LangSmithAdapter with verify_signature, normalize, condense | VERIFIED | 149 lines; all three methods substantive; exports LangSmithAdapter |
| `tests/adapters/test_langsmith.py` | 13 tests across 3 classes | VERIFIED | 13 tests; TestLangSmithAdapterSignature (3), TestLangSmithAdapterNormalize (6), TestLangSmithAdapterCondense (4); all pass |
| `tests/fixtures/langsmith_run_error.json` | Shape B with error field | VERIFIED | Exists; run_id, kwargs, error with message field |
| `tests/fixtures/langsmith_run_clean.json` | Shape B with error=null | VERIFIED | Exists; kwargs present, `"error": null` |
| `tests/fixtures/langsmith_feedback.json` | Shape A with negative feedback_stats | VERIFIED | Exists; rule_id, runs, feedback_stats with user_score avg=-1.0 |
| `tests/fixtures/langsmith_alert.json` | Alert threshold shape | VERIFIED | Exists; alert_rule_id, triggered_metric_value=15, triggered_threshold=10 |
| `heartbeat_gateway/__init__.py` | NormalizedEvent.source Literal includes 'langsmith' | VERIFIED | Line 8: `Literal["linear", "github", "posthog", "braintrust", "langsmith"]` |
| `heartbeat_gateway/app.py` | LangSmithAdapter registered, route + redirect wired | VERIFIED | LangSmithAdapter imported (line 11); `app.state.langsmith_adapter = LangSmithAdapter(config)` (line 110); `/webhooks/langsmith` route (line 128-130); `/webhook/langsmith` 308 redirect (line 149-151) |
| `tests/test_app.py` | 4 integration tests for /webhooks/langsmith | VERIFIED | TestLangSmithWebhookRoute: test_clean_run_returns_ignored, test_wrong_token_returns_401, test_no_token_always_passes, test_singular_redirect; all 4 pass |
| `heartbeat_gateway/commands/init.py` | LangSmith checkbox + token prompt section | VERIFIED | Choice("LangSmith") at line 124; Section 4 block at lines 188-204; X-Langsmith-Secret instruction at line 194; GATEWAY_WATCH__LANGSMITH__TOKEN written at line 204 |
| `tests/cli/test_init.py` | 2 new LangSmith tests; existing tests unaffected | VERIFIED | test_langsmith_section_writes_token and test_langsmith_not_selected_no_env_var; both pass; full init test suite 21 pass |
| `docs/adapters.md` | LangSmith section with 3 event types + limitations | VERIFIED | Section at line 224; three event types (run.error, feedback, alert.threshold); dataset limitation noted at line 261 |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `heartbeat_gateway/adapters/langsmith.py` | `heartbeat_gateway/__init__.py` | `NormalizedEvent(source='langsmith', ...)` | VERIFIED | `source="langsmith"` at lines 62, 80, 104 of langsmith.py; Literal includes "langsmith" in __init__.py:8 |
| `heartbeat_gateway/adapters/langsmith.py` | `heartbeat_gateway/config/schema.py` | `self.config.watch.langsmith.token` | VERIFIED | `self.config.watch.langsmith.token` at langsmith.py:21; `LangSmithWatchConfig` with `token` field at schema.py:44 |
| `heartbeat_gateway/app.py` | `heartbeat_gateway/adapters/langsmith.py` | `app.state.langsmith_adapter = LangSmithAdapter(config)` | VERIFIED | LangSmithAdapter imported at app.py:11; `app.state.langsmith_adapter = LangSmithAdapter(config)` at app.py:110 |
| `heartbeat_gateway/app.py` | `_process_webhook` | `_process_webhook(request, 'langsmith')` | VERIFIED | Route handler at app.py:128-130 calls `_process_webhook(request, "langsmith")`; `_process_webhook` resolves adapter via `getattr(state, f"{source}_adapter")` |
| `heartbeat_gateway/commands/init.py` | `.env` | `answers["GATEWAY_WATCH__LANGSMITH__TOKEN"]` | VERIFIED | Pattern `GATEWAY_WATCH__LANGSMITH__TOKEN` at init.py:204; test_langsmith_section_writes_token confirms value lands in .env |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| LSMT-01 | 05-01 | `verify_signature` validates X-Langsmith-Secret header; passthrough if unconfigured | SATISFIED | `hmac.compare_digest` at langsmith.py:25; passthrough at line 22-23; 3 signature tests pass |
| LSMT-02 | 05-01 | Normalizes run completion with error — run name, error message | SATISFIED | `event_type="run.error"` at langsmith.py:63; metadata includes run_name, error_message; `test_normalizes_run_error` passes |
| LSMT-03 | 05-01 | Normalizes feedback with negative scores — feedback key, score | SATISFIED | Shape A dispatch at langsmith.py:89-111; `event_type="feedback"`; feedback_key, feedback_score in metadata; `test_normalizes_feedback` passes |
| LSMT-04 | 05-01 | Normalizes alert threshold — metric name, current/threshold values | SATISFIED | Alert dispatch at langsmith.py:71-86; `event_type="alert.threshold"`; all metric fields in metadata; `test_normalizes_alert` passes |
| LSMT-05 | 05-01 | Returns None for run.completed with no error | SATISFIED | Clean-run suppression as first check at langsmith.py:47-48; `test_clean_run_returns_none` passes |
| LSMT-06 | 05-02 | `/webhooks/langsmith` route wired; LangSmithAdapter registered; pre-filter integration | SATISFIED | Route at app.py:128-130; `app.state.langsmith_adapter` at line 110; pre_filter at line 103 runs on all events via `_process_webhook` |
| LSMT-07 | 05-03 | `gateway init` includes LangSmith section — token prompt + webhook URL + header instructions | SATISFIED | Section 4 in init.py lines 188-204; X-Langsmith-Secret instruction explicit; GATEWAY_WATCH__LANGSMITH__TOKEN written; 2 tests pass; smoke test user-approved per 05-03-SUMMARY |
| LSMT-08 | 05-01 | Unit tests for verify, normalize (all shapes), clean drop, fixtures in tests/fixtures/ | SATISFIED | 13 tests across 3 classes; 4 fixture files; all pass |

**Requirements coverage: 8/8 — all LSMT-01 through LSMT-08 satisfied**

No orphaned requirements. All 8 IDs declared in plan frontmatter match REQUIREMENTS.md and have verified implementation evidence.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `heartbeat_gateway/adapters/langsmith.py` | 62, 80, 104 | `# type: ignore[arg-type]  # Literal updated in Plan 02` | Info | Stale comment — Literal WAS updated in Plan 02. The type: ignore is no longer needed but causes no runtime impact. Ruff does not flag it. |

No blockers or warnings. The stale `type: ignore` comments are inert cosmetic residue from the TDD phasing; they do not affect behavior or type safety.

---

## Human Verification Required

### 1. Manual wizard smoke test

**Test:** Run `uv run gateway init`, select LangSmith only in the checkbox, enter a token value, verify .env output.
**Expected:** Terminal shows "LangSmith webhook setup", "Settings → Webhooks → Add Webhook", "X-Langsmith-Secret: <your-token>"; .env contains `GATEWAY_WATCH__LANGSMITH__TOKEN=<entered-value>`.
**Why human:** Interactive TTY wizard; questionary prompts cannot be fully simulated in CI.
**Note:** 05-03-SUMMARY documents this as user-approved (Task 3 resume signal received). Flagged here for completeness only — not a blocker.

---

## Full Suite Regression Check

**Run:** `uv run pytest -x -q --tb=no`
**Result:** 206 passed, 1 xfailed (intentional race condition test)
**Ruff:** All checks passed on all phase files

No regressions introduced. Test count grew from pre-phase baseline consistent with 13 adapter tests + 4 integration tests + 2 init tests added by this phase.

---

## Gaps Summary

No gaps. All phase goals are achieved:

- `/webhooks/langsmith` route exists and is wired to LangSmithAdapter via `_process_webhook`
- Token header validation uses `hmac.compare_digest`; passthrough when unconfigured
- Three payload shapes dispatched correctly: Shape B (run.error), alert (alert.threshold), Shape A (feedback)
- Clean run suppression (LSMT-05) fires as the first check after Shape B detection
- NormalizedEvent.source Literal includes "langsmith" — no runtime type errors
- 308 redirect from `/webhook/langsmith` confirmed
- `require_signatures` guard explicitly excludes langsmith with comment
- `gateway init` wizard includes LangSmith section with correct env var key
- `docs/adapters.md` documents all three event types and the dataset webhook limitation

---

_Verified: 2026-04-04T02:30:00Z_
_Verifier: Claude (gsd-verifier)_
