# Roadmap: heartbeat-gateway v0.4.0

**Milestone:** Adapter Expansion
**Goal:** Operators running AI agent stacks can classify signals from LLM eval, observability, and analytics platforms (Braintrust, LangSmith, Amplitude) alongside Linear and GitHub — within the existing five-stage pipeline, with no structural changes to classifier or writer.

---

## Phases

- [x] **Phase 3: Schema Foundation + PostHog Wizard** - Add three new WatchConfig models and PostHog init wizard section; prerequisite for all adapter phases (completed 2026-04-02)
- [x] **Phase 4: Braintrust Adapter** - HMAC-SHA256 verification, is_test suppression, logs + environment_update events (completed 2026-04-03)
- [ ] **Phase 5: LangSmith Adapter** - Custom header token auth, run errors + feedback + alert threshold events
- [ ] **Phase 6: Amplitude Adapter** - Permanent passthrough verify_signature, monitor_alert + chart.annotation events

---

## Phase Details

### Phase 3: Schema Foundation + PostHog Wizard
**Goal**: All new adapter config models exist in schema.py and PostHog init prompts are wired — no adapter code yet, but the config foundation every subsequent phase builds on is verified and tested.
**Depends on**: Phase 2 (gateway init must exist to add a section to it)
**Requirements**: FOUND-01, FOUND-02, FOUND-03, FOUND-04
**Success Criteria** (what must be TRUE):
  1. `GatewayConfig` loads `GATEWAY_WATCH__AMPLITUDE__SECRET`, `GATEWAY_WATCH__BRAINTRUST__SECRET`, and `GATEWAY_WATCH__LANGSMITH__TOKEN` from environment variables correctly — regression test confirms each value reaches the config object
  2. `gateway init` prompts for PostHog `project_id` and `secret` before the Linear section — a user running the wizard sees PostHog prompts in sequence
  3. All three new `*WatchConfig` classes inherit `BaseModel` (not `BaseSettings`) — the v0.2.0 security regression cannot recur
  4. `tests/cli/test_init.py` `_HAPPY_PATH_ANSWERS` updated to include PostHog answers — wizard tests pass without modification to answer count
**Plans**: 2 plans
Plans:
- [ ] 03-01-PLAN.md — Add AmplitudeWatchConfig, BraintrustWatchConfig, LangSmithWatchConfig to schema.py + regression tests
- [ ] 03-02-PLAN.md — Refactor gateway init with adapter checkbox + PostHog wizard section

### Phase 4: Braintrust Adapter
**Goal**: A Braintrust automation webhook arrives at `/webhooks/braintrust`, passes HMAC verification, and produces a classified HEARTBEAT.md or DELTA.md entry — or is correctly suppressed for test deliveries and unrecognized events.
**Depends on**: Phase 3 (BraintrustWatchConfig must exist in schema.py)
**Requirements**: BTST-01, BTST-02, BTST-03, BTST-04, BTST-05, BTST-06, BTST-07
**Success Criteria** (what must be TRUE):
  1. Saving a Braintrust automation (which sends `is_test: true`) produces no HEARTBEAT.md entry — normalize() returns None as its first action on test deliveries
  2. A Braintrust `logs` event with failing scores produces an ACTIONABLE entry in HEARTBEAT.md with score name, value, and project name visible
  3. A Braintrust `environment_update` event produces a DELTA entry with env name and change type visible
  4. A request with an invalid HMAC signature returns 401 — the route is protected
  5. `gateway init` prompts for Braintrust secret with BTQL automation setup instructions displayed inline
**Plans**: 3 plans
Plans:
- [x] 04-01-PLAN.md — Pre-build gate (HMAC header confirm), test stubs + fixtures, BraintrustAdapter implementation
- [x] 04-02-PLAN.md — Route registration in app.py, NormalizedEvent Literal update, integration tests
- [x] 04-03-PLAN.md — gateway init Braintrust section + wizard tests + docs/adapters.md

### Phase 5: LangSmith Adapter
**Goal**: A LangSmith webhook arrives at `/webhooks/langsmith`, passes custom-header token validation, and produces classified entries for run errors, negative feedback, and alert threshold crossings — while silently dropping clean run completions.
**Depends on**: Phase 3 (LangSmithWatchConfig must exist in schema.py)
**Requirements**: LSMT-01, LSMT-02, LSMT-03, LSMT-04, LSMT-05, LSMT-06, LSMT-07, LSMT-08
**Success Criteria** (what must be TRUE):
  1. A `run.completed` event with no errors produces no HEARTBEAT.md entry — the high-volume clean completion signal is always dropped
  2. A `run.completed` event with an error field produces an ACTIONABLE entry with run name, error message, and project name visible
  3. A feedback submission with a negative score produces an ACTIONABLE entry with feedback key, score, and comment visible
  4. An alert threshold event produces an ACTIONABLE entry with metric name and current/threshold values visible
  5. A request with a wrong or missing `X-Langsmith-Secret` header returns 401 when a token is configured; an unconfigured token allows all requests through (same pattern as other adapters)
  6. `gateway init` prompts for LangSmith token with webhook URL and `X-Langsmith-Secret` header configuration instructions displayed inline
**Plans**: 3 plans
Plans:
- [ ] 05-01-PLAN.md — Test fixtures + stubs, LangSmithAdapter implementation (token auth, multi-shape normalize, clean-run suppression)
- [ ] 05-02-PLAN.md — Route registration in app.py, NormalizedEvent Literal update, integration tests
- [ ] 05-03-PLAN.md — gateway init LangSmith section + wizard tests + docs/adapters.md + smoke test

### Phase 6: Amplitude Adapter
**Goal**: An Amplitude monitor alert webhook arrives at `/webhooks/amplitude`, is accepted without signature verification (Amplitude sends none), and produces a classified ACTIONABLE entry — while chart annotation events produce DELTA entries and unrecognized events are dropped cleanly.
**Depends on**: Phase 3 (AmplitudeWatchConfig must exist in schema.py)
**Requirements**: AMP-01, AMP-02, AMP-03, AMP-04, AMP-05, AMP-06, AMP-07
**Success Criteria** (what must be TRUE):
  1. An Amplitude `monitor_alert` webhook produces an ACTIONABLE entry with metric name, current value, and threshold value visible
  2. An Amplitude `chart.annotation` webhook produces a DELTA entry with annotation text and chart name visible
  3. `verify_signature` always returns True regardless of config — no Amplitude event ever returns 401 due to signature failure
  4. Two redeliveries of the same monitor alert produce exactly one HEARTBEAT.md entry — `condense()` output is deterministic (no timestamps or run IDs)
  5. `gateway init` prompts for Amplitude secret with an explicit inline warning that Amplitude does not sign webhooks and the field is for future compatibility only
**Plans**: TBD

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 3. Schema Foundation + PostHog Wizard | 2/2 | Complete   | 2026-04-02 |
| 4. Braintrust Adapter | 3/3 | Complete | 2026-04-03 |
| 5. LangSmith Adapter | 1/3 | In Progress|  |
| 6. Amplitude Adapter | 0/? | Not started | - |

---

## Coverage

| Requirement | Phase | Status |
|-------------|-------|--------|
| FOUND-01 | Phase 3 | Pending |
| FOUND-02 | Phase 3 | Pending |
| FOUND-03 | Phase 3 | Pending |
| FOUND-04 | Phase 3 | Pending |
| BTST-01 | Phase 4 | Complete (04-01) |
| BTST-02 | Phase 4 | Complete (04-01) |
| BTST-03 | Phase 4 | Complete (04-01) |
| BTST-04 | Phase 4 | Complete (04-01) |
| BTST-05 | Phase 4 | Complete (04-02) |
| BTST-06 | Phase 4 | Complete (04-03) |
| BTST-07 | Phase 4 | Complete (04-01) |
| LSMT-01 | Phase 5 | Pending |
| LSMT-02 | Phase 5 | Pending |
| LSMT-03 | Phase 5 | Pending |
| LSMT-04 | Phase 5 | Pending |
| LSMT-05 | Phase 5 | Pending |
| LSMT-06 | Phase 5 | Pending |
| LSMT-07 | Phase 5 | Pending |
| LSMT-08 | Phase 5 | Pending |
| AMP-01 | Phase 6 | Pending |
| AMP-02 | Phase 6 | Pending |
| AMP-03 | Phase 6 | Pending |
| AMP-04 | Phase 6 | Pending |
| AMP-05 | Phase 6 | Pending |
| AMP-06 | Phase 6 | Pending |
| AMP-07 | Phase 6 | Pending |

**v0.4.0 Coverage: 26/26 requirements mapped** (FOUND-01–04 counted as 4; AMP-01–07 as 7; BTST-01–07 as 7; LSMT-01–08 as 8)

---

## Key Constraints (from research)

**Phase 3 (Schema):**
- All `*WatchConfig` classes must inherit `BaseModel`, not `BaseSettings` — BaseSettings causes silent secret bypass (v0.2.0 regression)
- Add regression test per adapter: set env var via monkeypatch, instantiate GatewayConfig(), assert secret loaded correctly

**Phase 4 (Braintrust):**
- HMAC header name must be confirmed from `braintrust.dev/docs/guides/automations` before writing `verify_signature` — do not guess; a wrong header silently accepts all requests without verification
- `is_test` check is the **first** line of `normalize()`, before any other logic
- `condense()` must use `automation["name"]`, not `details["count"]` or `details["time_start"]` (dedup constraint)

**Phase 5 (LangSmith):**
- Token validated via `X-Langsmith-Secret` custom header — not HMAC, not query param
- `run.completed` with no errors → always return `None` (high-volume noise suppression, LSMT-05)
- Payload structure: run object nested under `kwargs` key — `payload.get("kwargs", {}).get("run_type", "")` not `payload.get("run_type", "")`
- `condense()` must use `kwargs["name"]` + `kwargs["session_name"]`, not `webhook_sent_at`
- Verify fleet and alert webhook payload shapes against `docs.langchain.com/langsmith/alerts-webhook` before writing fixtures

**Phase 6 (Amplitude):**
- `verify_signature` is a **permanent passthrough** — always returns True; docstring must state this explicitly and advise IP allowlisting
- Amplitude config `secret` field exists for symmetry only — setting it has no security effect
- Monitor payload wraps alerts in `charts` array: access `payload.get("charts", [])`, handle empty array
- `condense()` must use `charts[0]["header"]`, not `what_happened` (embeds a timestamp)
- Amplitude must be excluded from `require_signatures` enforcement; add `gateway doctor` warning when `GATEWAY_REQUIRE_SIGNATURES=true` and Amplitude secret is configured

---

## Archived: v0.3.0 Phases

### Phase 1: CLI Foundation + gateway doctor (COMPLETE)
**Goal:** Wire the Click CLI group and deliver a fully functional `gateway doctor` command that validates all known silent failure modes.
**Requirements:** CLI-01, CLI-02, CLI-03, DOC-01–DOC-12
**Status:** Complete — 2/2 plans executed

### Phase 2: gateway init (COMPLETE)
**Goal:** Deliver a fully functional `gateway init` wizard that guides users through `.env` configuration with TTY detection, inline UUID validation, merge-by-default handling, and atomic write.
**Requirements:** INIT-01–INIT-09
**Status:** Complete — 2/2 plans executed

---

*v0.3.0 roadmap created: 2026-03-25*
*v0.4.0 roadmap created: 2026-04-01*
*Source: REQUIREMENTS.md + .planning/research/SUMMARY.md*
