# Requirements: heartbeat-gateway

**Core Value:** A developer can deploy heartbeat-gateway and have AI agents receiving real-time classified webhook events within 20 minutes.

## v0.3.0 Requirements — All Complete ✓

### CLI Foundation
- [x] **CLI-01**: `heartbeat-gateway` bare invocation continues to start the server — zero breaking change
- [x] **CLI-02**: Click added as explicit dependency in `pyproject.toml`
- [x] **CLI-03**: New `heartbeat_gateway/cli.py` entry point wires Click group; `app.py` untouched

### gateway doctor
- [x] **DOC-01** through **DOC-12**: All doctor checks, fix hints, verbose flag, env-file flag — Complete

### gateway init
- [x] **INIT-01** through **INIT-09**: TTY detection, masked secrets, UUID validation, backup, atomic write — Complete

---

## v0.4.0 Requirements — Adapter Expansion

**Defined:** 2026-04-01
**Milestone goal:** Add Amplitude, Braintrust, and LangSmith webhook adapters; add PostHog section to gateway init wizard.

### Schema & Foundation (FOUND)

- [x] **FOUND-01**: `WatchConfig` adds `AmplitudeWatchConfig` model — `secret` field (no-op for verification; exists for config symmetry; Amplitude does not sign webhooks)
- [x] **FOUND-02**: `WatchConfig` adds `BraintrustWatchConfig` model — `secret` field for HMAC-SHA256 verification
- [x] **FOUND-03**: `WatchConfig` adds `LangSmithWatchConfig` model — `token` field for custom header auth (not HMAC)
- [ ] **FOUND-04**: `gateway init` wizard adds PostHog section — `project_id` + `secret` prompts before Linear section

### Amplitude Adapter (AMP)

- [ ] **AMP-01**: `AmplitudeAdapter.verify_signature()` always returns `True`; docstring explicitly documents the no-signing limitation and advises IP allowlisting as mitigation
- [ ] **AMP-02**: Normalizes `monitor_alert` events — metric name, current value, threshold value → ACTIONABLE candidate
- [ ] **AMP-03**: Normalizes `chart.annotation` events — annotation text, chart name → DELTA candidate
- [ ] **AMP-04**: Returns `None` for unrecognized event types
- [ ] **AMP-05**: `/webhooks/amplitude` route wired in `app.py`; `AmplitudeAdapter` registered in app state; pre-filter integration
- [ ] **AMP-06**: `gateway init` includes Amplitude section — secret prompt with no-signing warning displayed inline
- [ ] **AMP-07**: Unit tests (verify passthrough, normalize monitor_alert, normalize annotation, normalize unknown→None) + fixture JSON in `tests/fixtures/` + `docs/adapters.md` updated

### Braintrust Adapter (BTST)

- [ ] **BTST-01**: `BraintrustAdapter.verify_signature()` uses HMAC-SHA256; exact header name confirmed at build time from `braintrust.dev/docs/guides/automations`
- [ ] **BTST-02**: `normalize()` returns `None` as its **first action** when `payload.get("details", {}).get("is_test") == True` — prevents phantom HEARTBEAT entries on every automation save
- [ ] **BTST-03**: Normalizes `logs` events with failing scores (BTQL-filtered automations) — score name, value, project name → ACTIONABLE
- [ ] **BTST-04**: Normalizes `environment_update` events — env name, change type → DELTA
- [ ] **BTST-05**: `/webhooks/braintrust` route wired in `app.py`; `BraintrustAdapter` registered; pre-filter integration
- [ ] **BTST-06**: `gateway init` includes Braintrust section — secret prompt + BTQL automation setup instructions
- [ ] **BTST-07**: Unit tests (verify HMAC, is_test→None, logs normalize, env_update normalize, unknown→None) + fixture JSON + `docs/adapters.md` updated

### LangSmith Adapter (LSMT)

- [ ] **LSMT-01**: `LangSmithAdapter.verify_signature()` validates `X-Langsmith-Secret` custom header token (not HMAC); returns `True` if no token configured (same pattern as other adapters)
- [ ] **LSMT-02**: Normalizes run completion events with errors — run name, error message, project name → ACTIONABLE
- [ ] **LSMT-03**: Normalizes feedback submission events with negative scores — feedback key, score, comment → ACTIONABLE
- [ ] **LSMT-04**: Normalizes alert threshold events — metric name, current/threshold values → ACTIONABLE
- [ ] **LSMT-05**: Returns `None` for `run.completed` events with no errors (high-volume noise; always drop)
- [ ] **LSMT-06**: `/webhooks/langsmith` route wired in `app.py`; `LangSmithAdapter` registered; pre-filter integration
- [ ] **LSMT-07**: `gateway init` includes LangSmith section — token prompt + webhook URL instructions
- [ ] **LSMT-08**: Unit tests (verify token, run error→normalize, feedback→normalize, alert→normalize, clean run→None) + fixture JSON + `docs/adapters.md` updated (notes dataset webhooks as unavailable)

## v2 Requirements (Deferred)

- **ARIZE-01**: Arize AX adapter — deferred; OSS Phoenix has no outbound webhooks; requires Arize AX (hosted/paid)
- **LSMT-DATASET**: LangSmith dataset change webhooks — not available in LangSmith API as of 2026-04-01
- **PG-05**: MCP server HTTP/SSE transport (replaces stdio — fixes SSH reliability)
- **ADAPTER-SLACK**: Slack adapter
- **ADAPTER-SENTRY**: Sentry adapter
- **ADAPTER-PD**: PagerDuty adapter

## Out of Scope

| Feature | Reason |
|---------|--------|
| Arize Phoenix OSS adapter | OSS product emits no webhooks; Arize AX deferred to future milestone |
| LangSmith dataset change webhooks | Not available in LangSmith API as of 2026-04-01 |
| Batch/streaming ingestion | Webhook-first constraint maintained (Amplitude Data Export, LangSmith bulk export) |
| Web UI / dashboard | Contradicts markdown-as-API design philosophy |
| Multi-tenant / SaaS | Single-operator tool by design |

## Traceability

### v0.3.0 (All Complete)
| Requirement | Phase | Status |
|-------------|-------|--------|
| CLI-01–03 | Phase 1 | Complete |
| DOC-01–12 | Phase 1 | Complete |
| INIT-01–09 | Phase 2 | Complete |

### v0.4.0
| Requirement | Phase | Status |
|-------------|-------|--------|
| FOUND-01 | Phase 3 | Complete |
| FOUND-02 | Phase 3 | Complete |
| FOUND-03 | Phase 3 | Complete |
| FOUND-04 | Phase 3 | Pending |
| BTST-01 | Phase 4 | Pending |
| BTST-02 | Phase 4 | Pending |
| BTST-03 | Phase 4 | Pending |
| BTST-04 | Phase 4 | Pending |
| BTST-05 | Phase 4 | Pending |
| BTST-06 | Phase 4 | Pending |
| BTST-07 | Phase 4 | Pending |
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

**v0.4.0 Coverage: 26/26 requirements mapped** ✓

---
*v0.3.0 requirements defined: 2026-03-25*
*v0.4.0 requirements defined: 2026-04-01*
*Last updated: 2026-04-01 after roadmap creation*
