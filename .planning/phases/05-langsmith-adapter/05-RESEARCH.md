# Phase 5: LangSmith Adapter - Research

**Researched:** 2026-04-02
**Domain:** LangSmith webhook integration, Python adapter pattern
**Confidence:** MEDIUM — LangSmith payload structures partially verified from official docs; `kwargs` structure from roadmap requires a pre-build verification gate

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| LSMT-01 | `LangSmithAdapter.verify_signature()` validates `X-Langsmith-Secret` custom header token; returns `True` if no token configured | Auth pattern confirmed from official docs — custom headers are user-configured; `X-Langsmith-Secret` is the header name convention for this project |
| LSMT-02 | Normalizes run completion events with errors — run name, error message, project name → ACTIONABLE | Run payload `error` field documented; `name` and session info in run object |
| LSMT-03 | Normalizes feedback submission events with negative scores — feedback key, score, comment → ACTIONABLE | Feedback in `feedback_stats` per run in `runs[]` array; individual feedback fields documented in SDK schema |
| LSMT-04 | Normalizes alert threshold events — metric name, current/threshold values → ACTIONABLE | Alert webhook fields fully documented: `alert_rule_attribute`, `triggered_metric_value`, `triggered_threshold` |
| LSMT-05 | Returns `None` for `run.completed` events with no errors (high-volume noise; always drop) | Implemented via `error` field check in run objects |
| LSMT-06 | `/webhooks/langsmith` route wired in `app.py`; `LangSmithAdapter` registered; pre-filter integration | Route pattern established by Braintrust adapter; direct copy |
| LSMT-07 | `gateway init` includes LangSmith section — token prompt + webhook URL instructions | Init wizard pattern established; LangSmith uses `GATEWAY_WATCH__LANGSMITH__TOKEN` |
| LSMT-08 | Unit tests + fixture JSON + `docs/adapters.md` updated (notes dataset webhooks as unavailable) | Test pattern from Braintrust; fixtures need real payload shapes |
</phase_requirements>

---

## Summary

LangSmith exposes **two distinct webhook systems** that the adapter must handle differently. The first is the **automation/rules webhook** (from the Automations UI), which sends a payload with a top-level `runs[]` array, `rule_id`, `start_time`/`end_time`, and `feedback_stats`. The second is the **LangGraph agent webhook** (from agent deployment configuration), which sends a single-run payload with `kwargs`, `run_id`, `webhook_sent_at`, and an `error` field directly on the payload root.

The roadmap's CRITICAL RESEARCH FOCUS specifies `payload.get("kwargs", {}).get("run_type", "")` — this describes the LangGraph agent webhook format, not the automation/rules format. This is a critical distinction: the two webhook types arrive at the same endpoint but have different JSON shapes. The planner must decide whether the adapter handles one or both shapes, or whether the roadmap's `kwargs` reference is the authoritative decision regardless of the official docs' terminology.

Authentication is handled via a **custom header** that the operator configures in LangSmith's webhook header UI. The LangSmith platform does not compute an HMAC signature — instead, operators add a static secret as a custom HTTP header (which this project names `X-Langsmith-Secret`). This is exactly the same mechanism as adding any custom header in LangSmith's webhook configuration UI. The header name `X-Langsmith-Secret` is a project-defined convention, not a LangSmith platform standard.

**Primary recommendation:** Treat the roadmap's payload structure description (using `kwargs`) as authoritative for the LangGraph agent webhook variant. Build a pre-build gate checkpoint to verify whether the LangSmith UI allows setting `X-Langsmith-Secret` as a custom header. Model the adapter after the Braintrust template exactly.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `heartbeat_gateway.adapters.base.WebhookAdapter` | project-local | ABC with `verify_signature`, `normalize`, `condense` | All adapters inherit this |
| `heartbeat_gateway.NormalizedEvent` | project-local | Dataclass emitted by `normalize()` | Pipeline contract between adapter and pre-filter |
| `heartbeat_gateway.config.schema.LangSmithWatchConfig` | project-local (already exists) | Config model with `token: str = ""` | Created in Phase 3 (FOUND-03) |
| `datetime`, `timezone` (stdlib) | 3.12 | Timestamp construction in normalize | Same as Braintrust adapter |

### No Additional Dependencies Required

The LangSmith adapter needs zero new dependencies. Token comparison uses `hmac.compare_digest()` (stdlib) for timing-safe string comparison. No HMAC computation needed — just a string equality check.

**Installation:** None — all required libraries already installed.

---

## Architecture Patterns

### Recommended File Locations

```
heartbeat_gateway/
└── adapters/
    └── langsmith.py          # New file — LangSmithAdapter class

tests/
├── adapters/
│   └── test_langsmith.py     # New file — mirrors test_braintrust.py structure
└── fixtures/
    ├── langsmith_run_error.json        # run.completed with error field populated
    ├── langsmith_run_clean.json        # run.completed with error=null (always dropped)
    ├── langsmith_feedback.json         # feedback event with negative score
    └── langsmith_alert.json           # alert threshold crossing event
```

### Pattern 1: Token Header Auth (not HMAC)

LangSmith uses a **static token in a custom header** — not HMAC-SHA256. The operator configures `X-Langsmith-Secret: <token>` in LangSmith's webhook header config UI. The adapter reads that header and compares it to the configured token.

```python
# Source: derived from LangSmith docs + PostHog adapter pattern (posthog.py)
def verify_signature(self, payload: bytes, headers: dict) -> bool:
    token = self.config.watch.langsmith.token
    if not token:
        return True  # unconfigured = allow all (same as other adapters)
    incoming = headers.get("x-langsmith-secret", "")
    return hmac.compare_digest(token, incoming)
```

Note: `hmac.compare_digest` is used for timing-safe comparison even though this is not HMAC. This prevents timing attacks on token comparison.

### Pattern 2: Two-Payload-Shape Strategy

The LangSmith adapter must handle two distinct payload shapes arriving at the same endpoint. The shape is distinguishable by the presence of `rule_id` (automation/rules webhook) vs. `run_id` / `kwargs` (LangGraph agent webhook):

**Shape A — Automation/Rules webhook** (from LangSmith Automations UI):
```json
{
  "rule_id": "uuid",
  "start_time": "2024-...",
  "end_time": "2024-...",
  "runs": [
    {
      "id": "run-uuid",
      "name": "my_chain",
      "run_type": "chain",
      "status": "error",
      "error": "RateLimitError: ...",
      "session_id": "session-uuid",
      "start_time": "...",
      "end_time": "..."
    }
  ],
  "feedback_stats": {
    "user_score": {"n": 2, "avg": -0.5}
  }
}
```

**Shape B — LangGraph Agent webhook** (roadmap's specified format):
```json
{
  "run_id": "uuid",
  "thread_id": "uuid",
  "assistant_id": "agent",
  "status": "success",
  "webhook_sent_at": "2024-...",
  "kwargs": {
    "run_type": "chain",
    "name": "my_agent"
  },
  "error": null
}
```

**Resolution for implementation:** The roadmap explicitly states to use `payload.get("kwargs", {}).get("run_type", "")`. Treat Shape B (LangGraph agent webhook) as the primary target. The fixture files should use Shape B. Distinguish by checking `"kwargs" in payload` vs. `"rule_id" in payload` if multi-shape support is needed. **Alert threshold events** always use Shape A's structure (from the alerts-webhook docs).

### Pattern 3: Event Type Detection

Unlike Braintrust (which has an `event_type` field), LangSmith webhooks have no single discriminator. Dispatch logic:

```python
# Run events (Shape B / LangGraph agent webhooks)
if "kwargs" in payload:
    error = payload.get("error")
    if not error:
        return None  # LSMT-05: clean completions always dropped
    # normalize as run error

# Alert threshold events (alerts-webhook shape)
if "alert_rule_id" in payload:
    # normalize as alert threshold

# Automation/Rules webhooks (Shape A — runs array)
if "rule_id" in payload:
    runs = payload.get("runs", [])
    # check each run for errors or negative feedback_stats
```

### Pattern 4: Suppression-First for Run Completions

LSMT-05 is a high-volume noise suppression requirement. The clean-run check must be **the first branch** after shape detection — before any normalization logic:

```python
def normalize(self, payload: dict, headers: dict) -> NormalizedEvent | None:
    # Shape B: LangGraph agent webhook
    if "kwargs" in payload:
        error = payload.get("error")
        if not error:
            return None  # LSMT-05: always drop clean completions
        # ... proceed to error normalization
```

### Pattern 5: condense() uses stable identifiers

Per roadmap constraint: `condense()` must use `kwargs["name"]` + `kwargs["session_name"]` — NOT `webhook_sent_at` (timestamp makes dedup non-deterministic):

```python
def condense(self, payload: dict) -> str:
    kwargs = payload.get("kwargs", {})
    name = kwargs.get("name", "")
    session = kwargs.get("session_name", "")  # may be absent; use session_id fallback
    error = payload.get("error", "")
    return f"LangSmith: [{session}] '{name}' — {error}"[:240]
```

**Warning:** `session_name` is NOT confirmed in official docs (only `session_id` is documented). This field name comes from the roadmap's constraints. Build a pre-build gate to verify.

### Anti-Patterns to Avoid

- **Using `webhook_sent_at` in condense():** Timestamps change on redelivery, breaking the 5-minute dedup window in `writer.py`. Use `name` + session identifier.
- **Checking `payload.get("run_type")` at top level:** The run type is nested under `kwargs` in the LangGraph agent webhook format. Top-level access silently returns `""`.
- **Assuming a single payload shape:** LangSmith sends structurally different payloads for run webhooks vs. alert webhooks vs. automation/rules webhooks.
- **Implementing HMAC verification:** LangSmith does not sign webhooks. The `X-Langsmith-Secret` is a static token in a user-configured custom header, compared with string equality.
- **Allowing `require_signatures` to block LangSmith:** LangSmith cannot provide HMAC signing, so the adapter should be excluded from `require_signatures` enforcement (like Braintrust).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Timing-safe token comparison | `token == incoming` | `hmac.compare_digest(token, incoming)` | Prevents timing oracle attacks even on non-HMAC tokens |
| Dedup fingerprint | Timestamp-based ID | `name` + `session_name`/`session_id` | `writer.py` dedup is fingerprint-based; timestamps cause duplicate entries on redelivery |
| Config field naming | Using `secret` for LangSmith | `config.watch.langsmith.token` | FOUND-03 explicitly uses `token`; using `secret` breaks env var loading |

**Key insight:** The hard part of this adapter is not the code — it is knowing which payload shape to write fixtures for. The `kwargs` nesting is the critical structural invariant. Get it wrong in fixtures and every test verifies the wrong thing.

---

## Common Pitfalls

### Pitfall 1: Wrong payload shape for run events

**What goes wrong:** Developer reads the LangSmith automation/rules webhook docs (Shape A with `runs[]` array) and builds fixtures around that shape. But the roadmap specifies `payload.get("kwargs", {})`, which is the LangGraph agent webhook shape (Shape B).

**Why it happens:** LangSmith has two webhook systems with different JSON structures. The docs for each are on different pages.

**How to avoid:** Use Shape B (LangGraph agent webhook) for run-related fixtures. Confirm with a pre-build gate: send a test webhook from LangSmith and capture the raw payload.

**Warning signs:** If your normalize code looks like `payload["runs"][0]["error"]`, you're using Shape A. The roadmap explicitly uses `payload.get("kwargs", {})`.

### Pitfall 2: `session_name` field may not exist

**What goes wrong:** `condense()` uses `kwargs.get("session_name", "")` but the field doesn't exist in the actual LangSmith payload — it's `session_id` (a UUID) in official docs.

**Why it happens:** The roadmap constraint uses `kwargs["session_name"]` but official docs only document `session_id` (UUID) as the session identifier.

**How to avoid:** In the pre-build gate, verify whether `session_name` exists in the actual webhook payload. If absent, fall back to `session_id`. Use `.get()` with empty string default in all cases.

**Warning signs:** `session_name` is empty in all condensed strings even when sessions are active.

### Pitfall 3: NormalizedEvent Literal missing "langsmith"

**What goes wrong:** `NormalizedEvent.source` has a `Literal["linear", "github", "posthog", "braintrust"]` type annotation. Adding `source="langsmith"` causes a mypy/type error.

**Why it happens:** The Literal was updated for Braintrust in Phase 4 (Plan 02) but must be updated again for LangSmith.

**How to avoid:** Update `heartbeat_gateway/__init__.py` to add `"langsmith"` to the source Literal when wiring the route.

**Warning signs:** mypy error or test importing NormalizedEvent with source="langsmith" fails type check.

### Pitfall 4: LangSmith excluded from require_signatures guard

**What goes wrong:** If `GATEWAY_REQUIRE_SIGNATURES=true` is set and `langsmith` is not excluded, `create_app()` raises `ValueError` blocking startup even when token is configured (because token != HMAC secret enforcement).

**Why it happens:** `require_signatures` guard in `app.py` checks that sources have secrets. LangSmith has a `token` not a `secret`, and has no HMAC signing anyway.

**How to avoid:** Add `# langsmith excluded from require_signatures — verify_signature uses token header, not HMAC` comment in `app.py`'s require_signatures block (same pattern as the Braintrust exclusion comment already present).

**Warning signs:** Server fails to start when `GATEWAY_REQUIRE_SIGNATURES=true`.

### Pitfall 5: Alert payload shape confusion

**What goes wrong:** Alert threshold events (`LSMT-04`) use a completely different payload shape than run events. Trying to access `payload.get("kwargs", {})` on an alert payload returns `{}`.

**Why it happens:** Alert webhooks are documented at `docs.langchain.com/langsmith/alerts-webhook` and have `alert_rule_id`, `alert_rule_attribute`, `triggered_metric_value`, `triggered_threshold` at the top level — no `kwargs`, no `runs[]`.

**How to avoid:** Detect alert payloads by checking `"alert_rule_id" in payload` before the `"kwargs" in payload` check. Write a separate `langsmith_alert.json` fixture that matches the documented alert shape exactly.

---

## Code Examples

### verify_signature (token header, not HMAC)

```python
# Pattern: static token in custom header — timing-safe comparison
import hmac

def verify_signature(self, payload: bytes, headers: dict) -> bool:
    """Validates X-Langsmith-Secret custom header token.
    Returns True if no token configured (same passthrough pattern as other adapters).
    LangSmith does not sign webhooks with HMAC — X-Langsmith-Secret is a static
    token the operator configures in LangSmith's webhook header UI.
    """
    token = self.config.watch.langsmith.token
    if not token:
        return True
    incoming = headers.get("x-langsmith-secret", "")
    return hmac.compare_digest(token, incoming)
```

### normalize run error (Shape B — LangGraph agent webhook)

```python
# payload.get("kwargs", {}) is the canonical nesting per roadmap constraint
def _normalize_run_error(self, payload: dict) -> NormalizedEvent:
    kwargs = payload.get("kwargs", {})
    error = payload.get("error", {})
    error_msg = error.get("message", str(error)) if isinstance(error, dict) else str(error)
    name = kwargs.get("name", "")
    session = kwargs.get("session_name", "") or payload.get("thread_id", "")

    metadata = {
        "run_name": name,
        "session_name": session,
        "error_message": error_msg,
        "run_type": kwargs.get("run_type", ""),
    }
    return NormalizedEvent(
        source="langsmith",
        event_type="run.error",
        payload_condensed=self.condense(payload),
        raw_payload=payload,
        timestamp=datetime.now(tz=timezone.utc),
        metadata=metadata,
    )
```

### normalize alert threshold event

```python
# Source: docs.langchain.com/langsmith/alerts-webhook — field names confirmed
def _normalize_alert(self, payload: dict) -> NormalizedEvent:
    metadata = {
        "project_name": payload.get("project_name", ""),
        "alert_rule_name": payload.get("alert_rule_name", ""),
        "alert_rule_attribute": payload.get("alert_rule_attribute", ""),  # error_count | feedback_score | latency | cost
        "triggered_metric_value": payload.get("triggered_metric_value"),
        "triggered_threshold": payload.get("triggered_threshold"),
    }
    return NormalizedEvent(
        source="langsmith",
        event_type="alert.threshold",
        payload_condensed=self.condense(payload),
        raw_payload=payload,
        timestamp=datetime.now(tz=timezone.utc),
        metadata=metadata,
    )
```

### condense (deterministic, no timestamps)

```python
# Uses name + session — NOT webhook_sent_at — for dedup stability
def condense(self, payload: dict) -> str:
    # Alert threshold shape
    if "alert_rule_id" in payload:
        project = payload.get("project_name", "")
        rule = payload.get("alert_rule_name", "")
        attr = payload.get("alert_rule_attribute", "")
        val = payload.get("triggered_metric_value", "")
        threshold = payload.get("triggered_threshold", "")
        return f"LangSmith: [{project}] alert '{rule}' — {attr} {val} > {threshold}"[:240]

    # Run error shape (kwargs nesting)
    kwargs = payload.get("kwargs", {})
    name = kwargs.get("name", "")
    session = kwargs.get("session_name", "") or payload.get("thread_id", "")
    error = payload.get("error")
    if error:
        err_msg = error.get("message", str(error)) if isinstance(error, dict) else str(error)
        return f"LangSmith: [{session}] '{name}' — error: {err_msg}"[:240]

    return f"LangSmith: [{session}] '{name}'"[:240]
```

### Fixture JSON — langsmith_run_error.json (Shape B)

```json
{
  "run_id": "1ef6a5b8-4457-6db0-8b15-cffd3797fa04",
  "thread_id": "my-project-session",
  "assistant_id": "agent",
  "status": "error",
  "created_at": "2024-08-30T23:07:38.242730+00:00",
  "updated_at": "2024-08-30T23:07:40.120000+00:00",
  "run_started_at": "2024-08-30T23:07:38.300000+00:00",
  "run_ended_at": "2024-08-30T23:07:40.100000+00:00",
  "webhook_sent_at": "2024-08-30T23:07:40.150000+00:00",
  "metadata": {},
  "kwargs": {
    "run_type": "chain",
    "name": "my-evaluation-chain",
    "session_name": "production-eval"
  },
  "error": {
    "error": "RateLimitError",
    "message": "Rate limit exceeded for model gpt-4"
  }
}
```

### Fixture JSON — langsmith_run_clean.json (Shape B, no error → always dropped)

```json
{
  "run_id": "2ab7c6d9-5568-7ec1-9c26-d00e4898gb15",
  "thread_id": "my-project-session",
  "assistant_id": "agent",
  "status": "success",
  "created_at": "2024-08-30T23:07:38.242730+00:00",
  "updated_at": "2024-08-30T23:07:40.120000+00:00",
  "run_started_at": "2024-08-30T23:07:38.300000+00:00",
  "run_ended_at": "2024-08-30T23:07:40.100000+00:00",
  "webhook_sent_at": "2024-08-30T23:07:40.150000+00:00",
  "metadata": {},
  "kwargs": {
    "run_type": "chain",
    "name": "my-evaluation-chain",
    "session_name": "production-eval"
  },
  "error": null
}
```

### Fixture JSON — langsmith_alert.json (alert threshold shape)

```json
{
  "project_name": "production-evals",
  "alert_rule_id": "a3b2c1d0-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
  "alert_rule_name": "High Error Rate",
  "alert_rule_type": "threshold",
  "alert_rule_attribute": "error_count",
  "triggered_metric_value": 15,
  "triggered_threshold": 10,
  "timestamp": "2024-08-30T23:07:40.150000+00:00"
}
```

### Fixture JSON — langsmith_feedback.json (negative feedback, Shape A automation/rules)

The feedback requirement (LSMT-03) is the most ambiguous. Official docs show `feedback_stats` as part of the automation/rules webhook (`runs[]` array shape). The feedback event likely arrives as Shape A with runs containing negative `feedback_stats`:

```json
{
  "rule_id": "rule-uuid-here",
  "start_time": "2024-08-30T22:00:00.000000+00:00",
  "end_time": "2024-08-30T23:00:00.000000+00:00",
  "runs": [
    {
      "id": "run-uuid",
      "name": "my_chain",
      "run_type": "chain",
      "status": "success",
      "session_id": "session-uuid",
      "start_time": "2024-08-30T22:05:00.000000+00:00",
      "end_time": "2024-08-30T22:05:02.000000+00:00"
    }
  ],
  "feedback_stats": {
    "user_score": {"n": 1, "avg": -1.0, "values": {}},
    "thumbs_down": {"n": 1, "avg": -1.0, "values": {}}
  }
}
```

**CRITICAL WARNING (LOW confidence):** The feedback fixture shape above is inferred from docs — not directly confirmed from a real payload capture. The LSMT-03 requirement specifies "feedback key, score, and comment visible" but the automation/rules webhook only exposes `feedback_stats` (aggregate statistics), not individual feedback records with comments. This creates an open question (see below).

---

## Two Webhook Systems — Disambiguation Table

| Property | Automation/Rules webhook | LangGraph Agent webhook |
|----------|--------------------------|------------------------|
| Trigger | Automation rule matches runs | Agent run completes |
| Top-level discriminator | `"rule_id"` key | `"run_id"` + `"kwargs"` key |
| Run data location | `payload["runs"][0]` | `payload` root + `payload["kwargs"]` |
| Error field location | `payload["runs"][0]["status"] == "error"` + possible `error` field | `payload["error"]` (null when clean) |
| Feedback location | `payload["feedback_stats"]` (aggregated) | Not applicable |
| Alert type | Separate alert-webhook format | Not applicable |
| Auth | Query param secret (LangSmith recommendation) | Custom headers (configured in langgraph.json) |
| `session_name` field | `payload["runs"][0]["session_id"]` (UUID) | `payload["kwargs"]["session_name"]` (roadmap spec) |

**Roadmap decision:** The roadmap's `kwargs` nesting references LangGraph agent webhooks. This is the primary target. The alert fixture uses the documented alert-webhook shape.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Query param secret (`?secret=...`) | Custom header (`X-Langsmith-Secret: <token>`) | This adapter's design decision | Headers not logged by default; query params appear in access logs |
| HMAC signing (like PostHog/GitHub) | Static token header comparison | LangSmith platform design | No request signing available from LangSmith |

**Not available (deferred):**
- LangSmith dataset change webhooks: Not available as of 2026-04-01 (documented in REQUIREMENTS.md v2 deferred list as LSMT-DATASET)

---

## Open Questions

1. **`session_name` field existence in actual LangGraph agent webhook payload**
   - What we know: Official LangSmith docs document `session_id` (a UUID) not `session_name` (human-readable). The roadmap's constraint explicitly says `kwargs["session_name"]`.
   - What's unclear: Whether `session_name` is a real field in the `kwargs` object or if it should be `session_id` from the root level.
   - Recommendation: Pre-build gate checkpoint — test a real LangSmith webhook delivery OR fall back gracefully: `kwargs.get("session_name", "") or payload.get("thread_id", "")`. The `thread_id` field is documented in the LangGraph agent webhook example.

2. **Feedback event payload shape for individual feedback records**
   - What we know: LSMT-03 requires "feedback key, score, and comment visible" in the ACTIONABLE entry. The automation/rules webhook delivers `feedback_stats` as aggregated statistics (avg, count) — not individual feedback records with comment text.
   - What's unclear: Whether a feedback-triggered automation rule delivers individual feedback items or only aggregated stats. If only aggregated, there is no `comment` field available.
   - Recommendation: Model fixture using `feedback_stats` with `key` as the feedback dimension name (e.g., `"user_score"`), `avg` as the score, and omit `comment` (or use empty string). Document in `docs/adapters.md` that comment is unavailable in this webhook type.

3. **X-Langsmith-Secret header name — is this project-defined or LangSmith standard?**
   - What we know: Official LangSmith docs do not mention `X-Langsmith-Secret` as a standard header. LangSmith allows operators to configure arbitrary custom headers per webhook URL. The header name `X-Langsmith-Secret` is this project's naming convention.
   - What's unclear: No evidence that LangSmith automatically sends any authentication header. The operator must configure `X-Langsmith-Secret: <token>` in LangSmith's webhook config UI, and the adapter validates it.
   - Recommendation: Treat as fully project-defined. Document in `gateway init` wizard: "In LangSmith, open your webhook configuration, click Headers, and add: `X-Langsmith-Secret: <your-token>`". No pre-build gate needed — the behavior is correct by design.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing, no new setup) |
| Config file | `pyproject.toml` (existing) |
| Quick run command | `uv run pytest tests/adapters/test_langsmith.py -x -q` |
| Full suite command | `uv run pytest -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LSMT-01 | Token present + correct header → True; wrong header → False; no token → True | unit | `uv run pytest tests/adapters/test_langsmith.py::TestLangSmithAdapterSignature -x` | ❌ Wave 0 |
| LSMT-02 | run.completed with error → NormalizedEvent with error msg + run name + session | unit | `uv run pytest tests/adapters/test_langsmith.py::TestLangSmithAdapterNormalize::test_normalizes_run_error -x` | ❌ Wave 0 |
| LSMT-03 | feedback payload with negative score → NormalizedEvent with key + score | unit | `uv run pytest tests/adapters/test_langsmith.py::TestLangSmithAdapterNormalize::test_normalizes_feedback -x` | ❌ Wave 0 |
| LSMT-04 | alert threshold payload → NormalizedEvent with metric + values | unit | `uv run pytest tests/adapters/test_langsmith.py::TestLangSmithAdapterNormalize::test_normalizes_alert -x` | ❌ Wave 0 |
| LSMT-05 | run.completed with error=null → normalize() returns None | unit | `uv run pytest tests/adapters/test_langsmith.py::TestLangSmithAdapterNormalize::test_clean_run_returns_none -x` | ❌ Wave 0 |
| LSMT-06 | POST /webhooks/langsmith → 200 with run_error fixture | integration | `uv run pytest tests/test_app.py -k langsmith -x` | ❌ Wave 0 |
| LSMT-07 | gateway init LangSmith section writes GATEWAY_WATCH__LANGSMITH__TOKEN | unit | `uv run pytest tests/cli/test_init.py -k langsmith -x` | ❌ Wave 0 |
| LSMT-08 | condense() ≤ 240 chars and deterministic | unit | `uv run pytest tests/adapters/test_langsmith.py::TestLangSmithAdapterCondense -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/adapters/test_langsmith.py -x -q`
- **Per wave merge:** `uv run pytest -x -q && uv run ruff check .`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/adapters/test_langsmith.py` — covers LSMT-01 through LSMT-05 and LSMT-08
- [ ] `tests/fixtures/langsmith_run_error.json` — run with error field populated (Shape B)
- [ ] `tests/fixtures/langsmith_run_clean.json` — run with error=null (always dropped)
- [ ] `tests/fixtures/langsmith_feedback.json` — negative feedback score via automation webhook
- [ ] `tests/fixtures/langsmith_alert.json` — alert threshold crossing

---

## Sources

### Primary (HIGH confidence)

- `docs.langchain.com/langsmith/alerts-webhook` — Alert webhook field names: `project_name`, `alert_rule_id`, `alert_rule_name`, `alert_rule_type`, `alert_rule_attribute`, `triggered_metric_value`, `triggered_threshold`, `timestamp`
- `docs.langchain.com/langsmith/webhooks` — Automation/rules webhook structure: `rule_id`, `runs[]` array, `feedback_stats`; query param authentication pattern
- `docs.langchain.com/langsmith/use-webhooks` — LangGraph agent webhook structure: `run_id`, `kwargs`, `error` field, `webhook_sent_at`; Shape B confirmed with JSON example
- `docs.langchain.com/langsmith/run-data-format` — Run object fields: `id`, `name`, `run_type`, `status`, `error`, `session_id`, `start_time`, `end_time`
- `heartbeat_gateway/adapters/braintrust.py` — Implementation template (project-local)
- `heartbeat_gateway/config/schema.py` — `LangSmithWatchConfig.token` field confirmed (FOUND-03)

### Secondary (MEDIUM confidence)

- `changelog.langchain.com/announcements/set-up-webhook-notifications-for-run-rules` — Custom headers per webhook URL confirmed (LangSmith allows arbitrary headers, stored encrypted)
- `reference.langchain.com/python/langsmith/schemas/Feedback` — Feedback schema: `key`, `score`, `value`, `comment` fields in individual feedback records

### Tertiary (LOW confidence)

- Roadmap constraint: `kwargs["session_name"]` — field name not confirmed in official docs; only `session_id` documented. Treat as requiring pre-build gate verification.
- Feedback fixture shape — inferred from `feedback_stats` documentation; individual feedback records with `comment` may not be available in automation webhook payloads.

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — no new dependencies; config already in schema.py (FOUND-03 complete)
- Architecture patterns: MEDIUM — two webhook shapes create dispatch complexity; feedback payload shape is LOW confidence
- Alert webhook fields: HIGH — fully documented at `docs.langchain.com/langsmith/alerts-webhook`
- Run webhook fields: MEDIUM — Shape B confirmed from docs; `session_name` field in `kwargs` is LOW (roadmap-specified, not officially documented)
- Authentication: HIGH — custom header pattern confirmed; `X-Langsmith-Secret` is project convention, not LangSmith standard
- Pitfalls: HIGH — derived from verified doc discrepancies and existing adapter patterns

**Research date:** 2026-04-02
**Valid until:** 2026-05-02 (LangSmith docs stable; API changes are versioned)
