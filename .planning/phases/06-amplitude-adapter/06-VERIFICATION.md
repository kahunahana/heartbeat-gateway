---
phase: 06-amplitude-adapter
verified: 2026-04-04T00:00:00Z
status: passed
score: 7/7 must-haves verified
---

# Phase 6: Amplitude Adapter Verification Report

**Phase Goal:** An Amplitude monitor alert webhook arrives at `/webhooks/amplitude`, is accepted without signature verification (Amplitude sends none), and produces a classified ACTIONABLE entry — while chart annotation events produce DELTA entries and unrecognized events are dropped cleanly.
**Verified:** 2026-04-04
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | `verify_signature()` always returns True regardless of payload or headers | VERIFIED | `amplitude.py` line 15: `return True`; 2 passing tests confirm both empty-header and any-header paths |
| 2 | `monitor_alert` with charts array produces NormalizedEvent with source='amplitude' and event_type='monitor_alert' | VERIFIED | `amplitude.py` lines 20-40; `test_normalizes_monitor_alert` passes with metadata assertions |
| 3 | `chart.annotation` produces NormalizedEvent with source='amplitude' and event_type='chart.annotation' | VERIFIED | `amplitude.py` lines 42-58; `test_normalizes_annotation` passes with annotation_label and chart_name assertions |
| 4 | Unrecognized event_type returns None | VERIFIED | `amplitude.py` line 60: `return None`; `test_unrecognized_event_returns_none` passes |
| 5 | Empty charts array on monitor_alert returns None (no IndexError) | VERIFIED | `amplitude.py` lines 22-23: `if not charts: return None`; `test_empty_charts_returns_none` passes |
| 6 | `condense()` uses charts[0]['header'], never what_happened — deterministic across redeliveries | VERIFIED | `amplitude.py` line 68: `f"Amplitude: monitor alert — {header}"[:240]`; `test_condense_uses_header_not_what_happened` explicitly asserts what_happened string is absent |
| 7 | POST `/webhooks/amplitude` is wired, accepts requests without signature verification, and routes through the pipeline | VERIFIED | `app.py` lines 135-137 and 160-162; 4 integration tests in `TestAmplitudeWebhookRoute` pass including 308 redirect test |

**Score:** 7/7 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `heartbeat_gateway/adapters/amplitude.py` | AmplitudeAdapter with verify_signature, normalize, condense | VERIFIED | 76 lines (min 40); all three methods implemented and substantive |
| `heartbeat_gateway/__init__.py` | NormalizedEvent.source Literal includes 'amplitude' | VERIFIED | Line 8: `Literal["linear", "github", "posthog", "braintrust", "langsmith", "amplitude"]` |
| `tests/adapters/test_amplitude.py` | Unit tests for signature, normalize, condense | VERIFIED | 89 lines (min 80); 9 tests across 3 classes, all passing |
| `tests/fixtures/amplitude_monitor_alert.json` | Monitor alert fixture with charts array | VERIFIED | Present; contains charts array with header, body, url, and what_happened fields |
| `tests/fixtures/amplitude_annotation.json` | Chart annotation fixture | VERIFIED | Present; contains annotation.label, annotation.description, chart.name |
| `heartbeat_gateway/app.py` | Amplitude route registration, adapter state, require_signatures exclusion | VERIFIED | Lines 9, 111, 135-137, 160-162, 88-90; amplitude_adapter in state; exclusion comment present |
| `heartbeat_gateway/commands/doctor.py` | Amplitude no-op signature WARN check | VERIFIED | Lines 243-257; WARN fires when require_signatures=true and amplitude.secret is set |
| `heartbeat_gateway/commands/init.py` | Amplitude checkbox entry and wizard section | VERIFIED | Lines 125, 208-223; "Amplitude" in checkbox after LangSmith before Linear; no-signing warning displayed; GATEWAY_WATCH__AMPLITUDE__SECRET written |
| `docs/adapters.md` | Amplitude adapter documentation | VERIFIED | Section at line 180; includes events table, authentication advisory, setup instructions, limitations |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `heartbeat_gateway/adapters/amplitude.py` | `heartbeat_gateway/__init__.py` | `NormalizedEvent` import | WIRED | Line 3: `from heartbeat_gateway import NormalizedEvent` |
| `heartbeat_gateway/adapters/amplitude.py` | `heartbeat_gateway/adapters/base.py` | `WebhookAdapter` base class | WIRED | Line 4: `from heartbeat_gateway.adapters.base import WebhookAdapter`; line 8: `class AmplitudeAdapter(WebhookAdapter)` |
| `tests/adapters/test_amplitude.py` | `heartbeat_gateway/adapters/amplitude.py` | `AmplitudeAdapter` import | WIRED | Line 6: `from heartbeat_gateway.adapters.amplitude import AmplitudeAdapter` |
| `heartbeat_gateway/app.py` | `heartbeat_gateway/adapters/amplitude.py` | import and state registration | WIRED | Line 9: `from heartbeat_gateway.adapters.amplitude import AmplitudeAdapter`; line 111: `app.state.amplitude_adapter = AmplitudeAdapter(config)` |
| `heartbeat_gateway/app.py` | `app.state.amplitude_adapter` | FastAPI state binding | WIRED | `_process_webhook(request, "amplitude")` calls `getattr(state, "amplitude_adapter")` via the generic dispatch at line 36 |
| `heartbeat_gateway/commands/init.py` | `GATEWAY_WATCH__AMPLITUDE__SECRET` | answers dict key assignment | WIRED | Line 223: `answers["GATEWAY_WATCH__AMPLITUDE__SECRET"] = amplitude_secret.strip()` |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| AMP-01 | 06-01 | `AmplitudeAdapter.verify_signature()` always returns `True`; docstring documents no-signing limitation and IP allowlist advisory | SATISFIED | `amplitude.py` line 12-15; docstring present; 2 tests passing |
| AMP-02 | 06-01 | Normalizes `monitor_alert` events — metric name, current value, threshold → ACTIONABLE candidate | SATISFIED | `amplitude.py` lines 20-40; metadata includes metric_header, metric_body, chart_url |
| AMP-03 | 06-01 | Normalizes `chart.annotation` events — annotation text, chart name → DELTA candidate | SATISFIED | `amplitude.py` lines 42-58; metadata includes annotation_label, annotation_description, chart_name |
| AMP-04 | 06-01 | Returns `None` for unrecognized event types | SATISFIED | `amplitude.py` line 60; `test_unrecognized_event_returns_none` passes |
| AMP-05 | 06-02 | `/webhooks/amplitude` route wired in `app.py`; `AmplitudeAdapter` registered in app state; pre-filter integration | SATISFIED | `app.py` lines 111, 135-137, 160-162; routes through `_process_webhook` which calls pre_filter |
| AMP-06 | 06-03 | `gateway init` includes Amplitude section — secret prompt with no-signing warning displayed inline | SATISFIED | `init.py` lines 208-223; 3 passing init tests: `test_amplitude_section_writes_secret`, `test_amplitude_no_signing_warning_displayed`, `test_amplitude_not_selected_no_env_var` |
| AMP-07 | 06-01 | Unit tests (verify passthrough, normalize monitor_alert, normalize annotation, normalize unknown→None) + fixture JSON + `docs/adapters.md` updated | SATISFIED | 9 unit tests passing; fixtures present; `docs/adapters.md` has Amplitude section with events, auth, setup, limitations |

**All 7 AMP requirements verified. No orphaned requirements.**

---

### Anti-Patterns Found

None. Scanned all phase-modified files:
- No TODO/FIXME/XXX/HACK/PLACEHOLDER comments
- No stub return values (`return null`, `return {}`, `return []`)
- No console.log-only implementations
- No `type: ignore` workarounds
- `condense()` correctly guards charts index access before use (empty-array guard at line 67)

---

### Human Verification Required

**Task 3 of Plan 06-03 was marked `gate: blocking` (human smoke test).** The plan's automated checks (`uv run pytest -x -q && uv run ruff check .`) both pass. The human-facing items are:

#### 1. Init wizard — Amplitude flow

**Test:** Run `uv run heartbeat-gateway init` in a temp directory, select only "Amplitude" from the checkbox.
**Expected:** No-signing warning displays before the secret prompt; entering a test secret writes `GATEWAY_WATCH__AMPLITUDE__SECRET` to `.env`.
**Why human:** Questionary interactive prompts cannot be verified by automated test for visual rendering — only that the answers write correctly (covered by `test_amplitude_section_writes_secret`). The visual ordering and warning placement require human confirmation.

#### 2. End-to-end smoke POST

**Test:** With the gateway running, POST `{"event_type":"monitor_alert","charts":[{"header":"Test","body":"Test"}]}` to `/webhooks/amplitude`.
**Expected:** Returns 200 with `{"status": "actionable"}` or `{"status": "ignored"}` depending on classifier verdict.
**Why human:** Classifier behavior depends on live SOUL.md and LLM API key — cannot be verified statically.

#### 3. Doctor WARN with running config

**Test:** Set `GATEWAY_REQUIRE_SIGNATURES=true` and `GATEWAY_WATCH__AMPLITUDE__SECRET=any` in `.env`, then run `uv run heartbeat-gateway doctor --env-file .env`.
**Expected:** Output shows `[WARN] Amplitude signature (no-op)` message.
**Why human:** Automated test (`test_amplitude_signature_noop_warn`) covers this at unit level; human verification confirms the rendered output in terminal context.

---

### Summary

Phase 6 delivers a complete, production-quality Amplitude adapter. All 7 requirements (AMP-01 through AMP-07) are satisfied with verified implementations. The adapter correctly:

- Accepts all webhooks without signature verification (Amplitude sends none)
- Routes `monitor_alert` events toward ACTIONABLE classification via deterministic condense using `charts[0].header`
- Routes `chart.annotation` events toward DELTA classification
- Returns None cleanly for unrecognized event types
- Guards against IndexError on empty charts arrays

The full test suite passes: 223 tests passed, 1 xfailed (intentional race condition demonstration). Ruff is clean. All key links are wired. The only outstanding item is the human smoke test from Plan 03 Task 3, which is a blocking gate per the plan but has all automated preconditions satisfied.

---

_Verified: 2026-04-04_
_Verifier: Claude (gsd-verifier)_
