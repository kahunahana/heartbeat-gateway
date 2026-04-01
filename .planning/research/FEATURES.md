# Features Research: v0.4.0 Adapters

**Domain:** Webhook adapter implementation — Amplitude, Braintrust, Arize Phoenix, LangSmith
**Project:** heartbeat-gateway v0.4.0
**Researched:** 2026-03-31
**Overall confidence:** MEDIUM — LangSmith and Braintrust payload shapes confirmed from official docs; Amplitude monitor payload confirmed from community sources; Arize Phoenix has no outbound webhooks (confirmed from multiple sources)

---

## Amplitude

### Webhook Architecture Overview

Amplitude has **three distinct webhook systems** that serve different purposes. Implementers must understand which system is relevant — they have different payloads, different authentication models, and are aimed at different use cases.

| System | Purpose | Auth | Relevance |
|--------|---------|------|-----------|
| Custom Monitor Webhooks | Alert when KPIs change | None (URL-only) | HIGH — actionable signals |
| Cohort Webhooks | Sync behavioral cohorts to endpoints | None (URL-only) | LOW — user segmentation, not agent signals |
| Event Streaming Webhooks | Stream raw event data out | Custom headers | LOW — high-volume raw events, not alerts |

For heartbeat-gateway, **Custom Monitor Webhooks** are the signal type worth handling. Cohort and Event Streaming webhooks are not suitable for agent task queues.

### Event Types

Amplitude custom monitor webhooks do not use a structured `event_type` field. The payload structure implies a single logical event type: a threshold-based monitor has fired.

**Effective event type strings for the adapter:**

| Internal Event Type | When | Source |
|---------------------|------|--------|
| `monitor.alert` | A custom monitor threshold was crossed | Always present when payload has `charts[]` |

Amplitude also supports **Cohort Webhooks** (different payload shape):

| Internal Event Type | When |
|---------------------|------|
| `cohort.membership` | User enters or exits a behavioral cohort |

**Complexity note:** Amplitude has no server-sent `event_type` field. The adapter must infer type from payload structure (presence of `charts` array vs `users` array).

### Payload Shapes

**Custom Monitor Webhook payload** (confidence: MEDIUM — from official Amplitude community examples):

```json
{
  "charts": [
    {
      "header": "DAU Monitoring Alert",
      "user_segment_idx": "0",
      "segment_value_label": null,
      "what_happened": "2022-10-13 14:00:00: 44.4 is lower than the threshold 55.0.",
      "chart_url": "https://analytics.amplitude.com/mychart?source=custom_monitor_webhook",
      "rca_url": "https://analytics.amplitude.com/mychart?source=custom_monitor_email&RCA.time=...",
      "filename": "chart.png",
      "contentType": "image/png",
      "cid": "12345",
      "metric": "chart_monitor_metric",
      "change_str": 19,
      "direction": false,
      "image_url": "https://example.s3.amazonaws.com/image.png",
      "anomaly_label": {
        "segment": "0",
        "value": null
      },
      "anomaly_message": "2022-10-13 14:00:00: 44.4 is lower than the threshold 55.0."
    }
  ]
}
```

Key fields:
- `charts` (array) — one entry per alert segment; presence of this field identifies a monitor.alert event
- `charts[n].header` — the monitor/chart name (use as alert title)
- `charts[n].what_happened` — human-readable description of the threshold crossing
- `charts[n].anomaly_message` — same content as `what_happened`, use as fallback
- `charts[n].direction` — boolean; `false` = metric went down (below threshold), `true` = went up (above threshold)
- `charts[n].change_str` — numeric magnitude of the change (integer, not a string despite the name)
- `charts[n].chart_url` — deep link to the chart in Amplitude
- `charts[n].metric` — always `"chart_monitor_metric"` for custom monitors; no semantic information

**Cohort Webhook payload** (confidence: HIGH — from official Amplitude documentation):

```json
{
  "cohort_name": "Power Users",
  "cohort_id": "abc123",
  "in_cohort": true,
  "computed_time": "1692206763",
  "message_id": "9baaa88f-9d46-4ee5-a946-be0c6aea0046::enter::0",
  "users": [
    {
      "user_id": "user_789"
    }
  ]
}
```

Key fields:
- `cohort_name` — name of the behavioral cohort
- `cohort_id` — stable ID
- `in_cohort` — boolean; `true` = user(s) entered, `false` = user(s) exited
- `message_id` — dedup key; encodes `::enter::` or `::exit::` in the string
- `users` — array of users affected; each has `user_id`
- `computed_time` — Unix epoch seconds (string)

### Authentication

**Critical limitation:** Amplitude custom monitor webhooks have **no signature verification**. Amplitude confirmed they cannot send webhooks with credentials. The URL itself is the only auth mechanism.

Implication for `verify_signature()`: Must always return `True` (passthrough). Add a comment explaining this is by design, not a bug. Optionally support an operator-configured shared secret embedded in the URL as a query param, validated server-side.

### ACTIONABLE / DELTA / IGNORE Classification

| Event Type | Classification | Rationale |
|------------|---------------|-----------|
| `monitor.alert` | ACTIONABLE | A KPI crossed a threshold the operator configured. Requires investigation. |
| `cohort.membership` | DELTA | Informational — a user segment changed. No immediate action required for agents. |

**Recommended pre-filter behavior:** Cohort membership events should likely be dropped at the pre-filter layer, not forwarded to the LLM at all. They generate high volume and contain no agent-actionable signal unless the operator's SOUL.md explicitly cares about cohort changes.

### Condense Format

```python
# monitor.alert
def condense(payload):
    charts = payload.get("charts", [])
    if not charts:
        return "Amplitude: monitor alert (no chart data)"[:240]
    first = charts[0]
    name = first.get("header", "unknown monitor")
    message = first.get("what_happened") or first.get("anomaly_message", "")
    count = len(charts)
    suffix = f" (+{count-1} more)" if count > 1 else ""
    return f"Amplitude: monitor '{name}' — {message}{suffix}"[:240]

# cohort.membership
def condense_cohort(payload):
    cohort = payload.get("cohort_name", "unknown")
    direction = "entered" if payload.get("in_cohort") else "exited"
    count = len(payload.get("users", []))
    return f"Amplitude: {count} user(s) {direction} cohort '{cohort}'"[:240]
```

**Example output:**
- `Amplitude: monitor 'DAU Monitoring Alert' — 2022-10-13 14:00:00: 44.4 is lower than the threshold 55.0.`
- `Amplitude: 3 user(s) entered cohort 'Power Users'`

### Metadata Fields

```python
metadata = {
    "monitor_name": charts[0].get("header"),          # monitor name
    "chart_url": charts[0].get("chart_url"),           # deep link for agent
    "direction": charts[0].get("direction"),            # False=below threshold, True=above
    "change_magnitude": charts[0].get("change_str"),   # numeric magnitude
    "segment": charts[0].get("anomaly_label", {}).get("segment"),
    "alert_count": len(charts),                        # number of segments triggered
    # cohort fields (when event_type == "cohort.membership")
    "cohort_name": payload.get("cohort_name"),
    "cohort_id": payload.get("cohort_id"),
    "in_cohort": payload.get("in_cohort"),
    "affected_user_count": len(payload.get("users", [])),
}
```

---

## Braintrust

### Webhook Architecture Overview

Braintrust uses an **Automations** system (in alpha as of 2025) where operators configure automation rules with a BTQL (Braintrust Query Language) filter. When logs match the filter within a polling interval, a webhook payload is dispatched.

There are **two event types** in Braintrust automations:

1. **Log event** (`"event_type": "logs"`) — triggers when production logs match a BTQL filter (e.g., low eval scores, specific metadata flags)
2. **Environment update** (`"event_type": "environment_update"`) — triggers when a prompt is deployed or removed from an environment

These are the **only two event types** Braintrust webhooks currently support. Eval run completion, dataset changes, and human annotation feedback are **not** natively webhook-able in Braintrust — they require polling the REST API. This is a significant scope constraint.

**Confidence:** HIGH — confirmed from official Braintrust automations documentation.

### Event Types

| Internal Event Type | Braintrust `event_type` | Trigger |
|---------------------|------------------------|---------|
| `log.matched` | `"logs"` | Logs matching a BTQL filter accumulated in the polling window |
| `prompt.deployed` | `"environment_update"` | Prompt version assigned to or removed from an environment |

### Payload Shapes

**Log event payload** (confidence: HIGH — from official Braintrust docs):

```json
{
  "organization": {
    "id": "org_123",
    "name": "your-organization"
  },
  "project": {
    "id": "proj_456",
    "name": "your-project"
  },
  "automation": {
    "id": "c5b32408-8568-4bff-9299-8cdd56979b67",
    "name": "High-Priority Factuality",
    "description": "Alert on factuality scores for logs with priority 0 in metadata",
    "event_type": "logs",
    "btql_filter": "metadata.priority = 0 AND scores.Factuality < 0.9",
    "interval_seconds": 3600,
    "url": "https://braintrust.dev/app/your-org/p/your-project/configuration/automations?aid=..."
  },
  "details": {
    "is_test": false,
    "message": "High-Priority Factuality: 5 logs triggered automation in the last 1 hour",
    "time_start": "2025-05-12T10:00:00.000Z",
    "time_end": "2025-05-12T11:00:00.000Z",
    "count": 5,
    "related_logs_url": "https://braintrust.dev/app/your-org/p/your-project/logs?search=..."
  }
}
```

**Environment update payload** (confidence: MEDIUM — from Braintrust alerts documentation):

```json
{
  "organization": {
    "id": "org_123",
    "name": "your-organization"
  },
  "project": {
    "id": "proj_456",
    "name": "your-project"
  },
  "automation": {
    "id": "auto_789",
    "name": "Production Prompt Deploy Alert",
    "description": "Notify when prompts are deployed to production",
    "event_type": "environment_update",
    "url": "https://braintrust.dev/app/..."
  },
  "details": {
    "is_test": false,
    "environment": {
      "slug": "production"
    },
    "prompt": {
      "id": "prompt_abc",
      "slug": "my-classifier"
    },
    "new_version": "v3.2.1",
    "action": "update"
  }
}
```

Notes on `environment_update` details:
- `details.action` — `"update"` (prompt deployed) or `"delete"` (prompt removed from env)
- `details.new_version` — `null` when `action == "delete"`
- `details.environment.slug` — environment name (e.g. `"production"`, `"staging"`)
- `details.prompt.slug` — the prompt's identifier

### Authentication

Braintrust webhook authentication method is not documented in any searched source. **Confidence: LOW.** Implementation should:
1. Attempt to find a shared secret/signing key in Braintrust automation settings
2. Default to `verify_signature() -> True` (passthrough) until confirmed
3. Flag in code comments that signature verification needs manual confirmation against live Braintrust UI

### ACTIONABLE / DELTA / IGNORE Classification

| Event Type | Classification | Rationale |
|------------|---------------|-----------|
| `log.matched` | Depends on BTQL filter intent | If filter targets score failures → ACTIONABLE; if informational logging → DELTA. Recommend: ACTIONABLE by default since operators create automations to be notified. |
| `prompt.deployed` (action=update) | DELTA | A prompt version went to production. Informational for agent context. |
| `prompt.deployed` (action=delete) | DELTA | Prompt removed from environment. Low urgency. |

**Recommended classification strategy:** Use `details.count` as a signal. If `count >= 1` and the automation's `btql_filter` is present (indicating a quality threshold filter), classify as ACTIONABLE. Operators can tune SOUL.md to downgrade to DELTA if needed.

**Note on "eval run failures":** Braintrust does not send webhooks on eval run completion or failure. Operators wanting eval failure alerts must configure a Log automation with a BTQL filter targeting low eval scores (e.g., `scores.Correctness < 0.8`). Document this constraint in the adapter's docstring.

### Condense Format

```python
def condense(payload):
    event_type = payload.get("automation", {}).get("event_type", "")
    org = payload.get("organization", {}).get("name", "")
    project = payload.get("project", {}).get("name", "")
    details = payload.get("details", {})
    automation_name = payload.get("automation", {}).get("name", "")

    if event_type == "logs":
        count = details.get("count", 0)
        message = details.get("message", "")
        return f"Braintrust: [{project}] {automation_name} — {count} logs matched ({message})"[:240]

    if event_type == "environment_update":
        env = details.get("environment", {}).get("slug", "unknown")
        prompt = details.get("prompt", {}).get("slug", "unknown")
        version = details.get("new_version") or "removed"
        action = details.get("action", "update")
        return f"Braintrust: [{project}] prompt '{prompt}' {action} → {env} @ {version}"[:240]

    return f"Braintrust: [{project}] {automation_name}"[:240]
```

**Example outputs:**
- `Braintrust: [my-project] High-Priority Factuality — 5 logs matched (High-Priority Factuality: 5 logs triggered automation in the last 1 hour)`
- `Braintrust: [my-project] prompt 'my-classifier' update → production @ v3.2.1`

### Metadata Fields

```python
metadata = {
    "org_name": payload.get("organization", {}).get("name"),
    "project_name": payload.get("project", {}).get("name"),
    "project_id": payload.get("project", {}).get("id"),
    "automation_name": payload.get("automation", {}).get("name"),
    "automation_id": payload.get("automation", {}).get("id"),
    "event_type": payload.get("automation", {}).get("event_type"),
    "btql_filter": payload.get("automation", {}).get("btql_filter"),
    "interval_seconds": payload.get("automation", {}).get("interval_seconds"),
    "matched_count": payload.get("details", {}).get("count"),
    "related_logs_url": payload.get("details", {}).get("related_logs_url"),
    "is_test": payload.get("details", {}).get("is_test"),
    # environment_update only
    "environment_slug": payload.get("details", {}).get("environment", {}).get("slug"),
    "prompt_slug": payload.get("details", {}).get("prompt", {}).get("slug"),
    "prompt_version": payload.get("details", {}).get("new_version"),
    "deploy_action": payload.get("details", {}).get("action"),
}
```

---

## Arize Phoenix

### Critical Finding: No Native Outbound Webhooks

**Arize Phoenix does not have native outbound webhook support.** This was confirmed from multiple sources including the official documentation and third-party analyses (confidence: HIGH).

Phoenix is an open-source, self-hosted LLM observability platform. It provides:
- REST API for reading traces, spans, and annotations
- A UI for viewing evaluations and annotations
- Python/TypeScript client libraries for writing annotations programmatically

It does **not** have:
- Outbound webhooks triggered by trace anomalies
- Alert rules that POST to a URL
- Notification integrations with webhook endpoints

**Implication for v0.4.0:** A traditional "Phoenix sends webhooks to heartbeat-gateway" architecture is not possible. The milestone goal of "Arize Phoenix adapter — trace anomalies, eval failures, monitor alerts" requires a different integration approach.

### Alternative Integration Approaches

Three patterns exist for getting Phoenix signals into heartbeat-gateway:

**Option A: Pull adapter (polling)** — Add a `gateway poll phoenix` command that queries Phoenix's REST API on a schedule. This is out of scope per PROJECT.md ("Batch/streaming ingestion (non-webhook) — webhook-first is the design constraint") and adds complexity.

**Option B: Custom instrumentation webhook emit** — Instrument the application's eval runner to POST directly to heartbeat-gateway when scores fall below thresholds. Phoenix is just the storage layer; the application logic triggers the webhook. This works but bypasses Phoenix entirely — the adapter is effectively just a generic webhook receiver.

**Option C: Defer Phoenix adapter** — Remove Phoenix from v0.4.0 scope. Document the limitation. Revisit when Phoenix adds webhook support (no evidence this is on their roadmap as of 2026).

**Recommendation:** Option C. The other three platforms (Amplitude, Braintrust, LangSmith) all have real webhook capabilities. Shipping a Phoenix "adapter" that is actually a custom instrumentation shim would mislead users about what the adapter does.

If the maintainer wants to keep Phoenix in scope, Option B is viable and should be documented clearly as "requires custom instrumentation, not a Phoenix webhook."

### Arize (Cloud Platform) — Separate Product

Arize.com (the cloud/enterprise platform, distinct from the open-source Phoenix) **does** have monitors and alerting with notification providers including webhooks. However:
- It is a paid cloud product, not open source
- The documentation for outbound webhook payloads is not publicly accessible without an account
- Conflating "Arize Phoenix" (OSS) with "Arize AX" (cloud) would mislead operators

This research covers only Arize Phoenix (OSS). Arize AX webhook adapter is a separate, future scope item.

### Stub Adapter (if Phoenix stays in scope)

If the maintainer decides to include a Phoenix adapter stub for Option B (custom instrumentation), the following event types and payload shapes are recommended:

**Suggested inbound payload shape** (operator-defined, not Phoenix-native):

```json
{
  "source": "phoenix",
  "event_type": "eval.score_below_threshold",
  "project_name": "my-agent",
  "span_id": "abc123",
  "trace_id": "xyz789",
  "eval_name": "hallucination",
  "score": 0.12,
  "threshold": 0.3,
  "timestamp": "2026-03-31T10:00:00Z",
  "trace_url": "http://localhost:6006/projects/1/traces/xyz789"
}
```

| Internal Event Type | Trigger |
|---------------------|---------|
| `eval.score_below_threshold` | An eval score dropped below a configured threshold |
| `span.error` | A span recorded an error status |
| `annotation.negative` | A human annotator marked a trace as negative/incorrect |

These are **not Phoenix API types** — they are a suggested convention for operators who self-instrument.

---

## LangSmith

### Webhook Architecture Overview

LangSmith has **two distinct webhook systems**:

1. **Automation Rule Webhooks** — fire when traces match an automation filter rule; payload is a batch of Run objects
2. **Alert Webhooks** — fire when a metric threshold is crossed (error_count, latency, feedback_score); payload is a threshold notification

Both are real outbound webhooks with reliable documentation. LangSmith is the highest-fidelity platform for this milestone.

**Complexity note:** LangSmith has many possible event patterns but only a focused subset matters for agent use: error runs, negative feedback, and threshold alerts.

### Event Types

**Automation Rule Webhooks** — triggered when runs match a filter:

| Internal Event Type | LangSmith Trigger | Recommended Filter |
|---------------------|------------------|--------------------|
| `run.error` | Automation rule: `status == "error"` | Filter on error status, any run type |
| `run.failed_eval` | Automation rule: custom feedback score filter | Filter on feedback key below threshold |
| `run.matched` | Any automation rule match | Catch-all for operator-defined filters |

**Alert Webhooks** — triggered by metric thresholds:

| Internal Event Type | `alert_rule_attribute` value | Trigger |
|---------------------|------------------------------|---------|
| `alert.error_count` | `"error_count"` | Error count crossed threshold |
| `alert.latency` | `"latency"` | P50/P95 latency crossed threshold |
| `alert.feedback_score` | `"feedback_score"` | Average feedback score crossed threshold |

**Total meaningful event types: 6.** The adapter should handle all of them. The pre-filter can drop `run.matched` if the operator hasn't configured relevant rules.

### Payload Shapes

**Automation Rule Webhook payload** (confidence: HIGH — from official LangSmith documentation):

```json
{
  "rule_id": "550e8400-e29b-41d4-a716-446655440000",
  "start_time": "2024-01-15T10:00:00Z",
  "end_time": "2024-01-15T10:05:00Z",
  "runs": [
    {
      "id": "run_abc123",
      "name": "my-chain",
      "run_type": "chain",
      "status": "error",
      "error": "ValueError: context length exceeded",
      "start_time": "2024-01-15T10:01:00Z",
      "end_time": "2024-01-15T10:01:05Z",
      "trace_id": "trace_xyz",
      "session_id": "sess_456",
      "parent_run_ids": [],
      "child_run_ids": ["run_child1"],
      "inputs": {"question": "..."},
      "outputs": null,
      "feedback_stats": {
        "correctness": {"n": 1, "avg": 0.0}
      },
      "total_tokens": 1250,
      "prompt_tokens": 980,
      "completion_tokens": 270,
      "tenant_id": "tenant_789",
      "tags": ["production", "v2"]
    }
  ],
  "feedback_stats": {
    "correctness": {"n": 5, "avg": 0.6}
  }
}
```

Key fields in the Run object:
- `id` — run UUID
- `run_type` — `"chain"`, `"llm"`, `"tool"`, `"retriever"`, `"embedding"`, `"prompt"`, `"parser"`
- `status` — `"success"`, `"error"`, `"pending"`
- `error` — error message string when `status == "error"`, else null
- `name` — the chain/agent/tool name as defined in code
- `trace_id` — parent trace UUID (same as `id` for root runs)
- `session_id` — the LangSmith project session
- `feedback_stats` — per-key dict with `n` (count) and `avg` (average score)
- `tags` — operator-applied tags
- `total_tokens` — token count (useful for cost anomaly detection)

**Alert Webhook payload** (confidence: HIGH — from official LangSmith documentation):

```json
{
  "alert_rule_id": "550e8400-e29b-41d4-a716-446655440000",
  "alert_rule_attribute": "error_count",
  "triggered_metric_value": 47,
  "triggered_threshold": 10,
  "timestamp": "2024-01-15T10:05:00Z"
}
```

- `alert_rule_attribute` — one of `"error_count"`, `"latency"`, `"feedback_score"`
- `triggered_metric_value` — the actual measured value that triggered the alert
- `triggered_threshold` — the configured threshold value
- `alert_rule_id` — use as dedup key (this field is explicitly documented for deduplication)

**Distinguishing payload types:** The presence of `"runs"` array identifies an automation webhook; the presence of `"alert_rule_id"` without `"runs"` identifies an alert webhook.

### Authentication

LangSmith automation rule webhooks use **query parameter bearer token authentication** — the operator embeds a secret in the webhook URL as a query param (e.g., `?token=mysecret`). The receiving handler validates the token.

LangSmith alert webhooks: authentication method not confirmed from available sources. Likely the same query-param approach.

**Implication for `verify_signature()`:** The gateway must extract a token from the URL query string or a configured header, not from an `X-Signature` header. This differs from Linear and GitHub's HMAC approach. The adapter's `verify_signature()` implementation should compare a configured `secret` value against a query param or `Authorization: Bearer` header value passed from the FastAPI route layer.

**LOW confidence** — verify against live LangSmith UI before shipping.

### ACTIONABLE / DELTA / IGNORE Classification

| Event Type | Classification | Rationale |
|------------|---------------|-----------|
| `run.error` | ACTIONABLE | A production run failed with an error. Agent should investigate. |
| `run.failed_eval` | ACTIONABLE | Eval score below threshold — quality regression in production. |
| `alert.error_count` | ACTIONABLE | Error volume crossed operator-configured threshold. |
| `alert.latency` | DELTA | Latency degradation is informational unless severe. Let SOUL.md escalate. |
| `alert.feedback_score` | ACTIONABLE | Negative human feedback trend — quality issue. |
| `run.matched` | DELTA | Generic automation match without a failure signal. Informational. |

**Classification strategy for automation webhooks:** Check `runs[n].status`. If any run has `status == "error"`, classify as `run.error` (ACTIONABLE). Otherwise check `feedback_stats` for low scores → `run.failed_eval`. Otherwise → `run.matched` (DELTA).

### Condense Format

```python
def condense(payload):
    # Alert webhook
    if "alert_rule_id" in payload and "runs" not in payload:
        attr = payload.get("alert_rule_attribute", "unknown")
        value = payload.get("triggered_metric_value", "")
        threshold = payload.get("triggered_threshold", "")
        return f"LangSmith: alert — {attr} {value} exceeded threshold {threshold}"[:240]

    # Automation webhook
    runs = payload.get("runs", [])
    rule_id = payload.get("rule_id", "")[:8]  # short ID for fingerprint
    error_runs = [r for r in runs if r.get("status") == "error"]

    if error_runs:
        first = error_runs[0]
        name = first.get("name", "unknown")
        error = (first.get("error") or "")[:80]
        count = len(error_runs)
        suffix = f" (+{count-1} more)" if count > 1 else ""
        return f"LangSmith: run error in '{name}' — {error}{suffix}"[:240]

    # Feedback-based match
    fb = payload.get("feedback_stats", {})
    if fb:
        low_keys = [k for k, v in fb.items() if isinstance(v, dict) and v.get("avg", 1.0) < 0.7]
        if low_keys:
            keys_str = ", ".join(low_keys[:3])
            return f"LangSmith: low feedback scores — {keys_str} (rule {rule_id})"[:240]

    run_name = runs[0].get("name", "unknown") if runs else "unknown"
    return f"LangSmith: automation rule {rule_id} matched {len(runs)} run(s) in '{run_name}'"[:240]
```

**Example outputs:**
- `LangSmith: run error in 'my-chain' — ValueError: context length exceeded`
- `LangSmith: alert — error_count 47 exceeded threshold 10`
- `LangSmith: low feedback scores — correctness, relevance (rule 550e8400)`

### Metadata Fields

```python
# Automation webhook metadata
metadata = {
    "rule_id": payload.get("rule_id"),
    "run_count": len(payload.get("runs", [])),
    "error_count": sum(1 for r in runs if r.get("status") == "error"),
    "first_run_id": runs[0].get("id") if runs else None,
    "first_run_name": runs[0].get("name") if runs else None,
    "first_run_type": runs[0].get("run_type") if runs else None,
    "first_error": runs[0].get("error") if runs else None,
    "session_id": runs[0].get("session_id") if runs else None,
    "trace_id": runs[0].get("trace_id") if runs else None,
    "feedback_keys": list(payload.get("feedback_stats", {}).keys()),
    "tags": runs[0].get("tags", []) if runs else [],
}

# Alert webhook metadata
metadata = {
    "alert_rule_id": payload.get("alert_rule_id"),
    "alert_rule_attribute": payload.get("alert_rule_attribute"),
    "triggered_metric_value": payload.get("triggered_metric_value"),
    "triggered_threshold": payload.get("triggered_threshold"),
}
```

---

## Table Stakes vs Differentiators

### Summary Table Across All Platforms

| Feature | Amplitude | Braintrust | Arize Phoenix | LangSmith |
|---------|-----------|------------|---------------|-----------|
| Has outbound webhooks | Yes | Yes | **No** | Yes |
| HMAC signature verification | **No** | Unknown | N/A | No (query token) |
| Alert/threshold notifications | Yes (monitor.alert) | Indirect via BTQL | No | Yes (alerts webhook) |
| Eval failure notifications | No | Via BTQL filter | No | Yes (automation + feedback) |
| Trace/run error notifications | No | Via BTQL filter | No | Yes (automation, status=error) |
| Human feedback/annotation webhooks | No | No | No | Yes (alert on feedback_score) |
| Dataset change webhooks | No | No | No | **No** (feature not found) |
| Prompt deployment events | No | Yes (env update) | No | No |
| Payload contains deep link URL | Yes (chart_url) | Yes (related_logs_url) | N/A | Via app_path on Run object |
| Event types per adapter | 2 | 2 | N/A (stub only) | 6 |

### Table Stakes (must implement for adapter to be useful)

| Feature | Priority | Notes |
|---------|----------|-------|
| Amplitude `monitor.alert` ingestion | HIGH | Core value — KPI threshold fires |
| LangSmith `run.error` detection | HIGH | Most common agent error signal |
| LangSmith `alert.error_count` | HIGH | Batch error alerting |
| Braintrust `log.matched` for low scores | HIGH | Proxy for eval failures |
| LangSmith `alert.feedback_score` | HIGH | Negative human feedback trend |

### Differentiators (valuable but secondary)

| Feature | Priority | Notes |
|---------|----------|-------|
| Braintrust `prompt.deployed` | MEDIUM | Useful for tracking prompt version deployments |
| LangSmith `alert.latency` | MEDIUM | Performance regression signal |
| Amplitude `cohort.membership` | LOW | May be relevant to product-aware agents |
| LangSmith `run.failed_eval` | MEDIUM | Requires operator to configure BTQL-equivalent rules |

### Anti-Features (explicitly do not build for v0.4.0)

| Anti-Feature | Why Avoid |
|--------------|-----------|
| Arize Phoenix polling adapter | Breaks webhook-first design constraint; Phoenix has no webhooks |
| Amplitude Event Streaming adapter | High-volume raw event stream; not an alert signal |
| LangSmith dataset change webhooks | LangSmith does not expose dataset change webhooks; would require polling |
| Braintrust experiment/eval run webhooks | Braintrust does not expose these as webhook events; only logs-based |

### Scope Reduction Recommendation

**Drop Arize Phoenix from v0.4.0 scope.** The platform has no outbound webhook capability. Shipping a "Phoenix adapter" requires either (a) breaking the webhook-first design constraint with a polling adapter, or (b) shipping a stub that requires custom application instrumentation — neither of which is what the milestone description implies.

The remaining three platforms (Amplitude, Braintrust, LangSmith) all have real webhook capabilities and are implementable within the webhook-first architecture.

---

## Open Questions / LOW Confidence Items

1. **Braintrust signature verification** — No documentation found on whether Braintrust signs webhook payloads with a shared secret. Must verify in the live UI before implementing `verify_signature()`. Default to passthrough until confirmed.

2. **LangSmith query-param vs header auth** — Confirmed that operators embed secrets in URLs, but the exact mechanism (query param `?token=`, `Authorization: Bearer`, or custom header) needs live verification against LangSmith's webhook configuration UI.

3. **Amplitude webhook POST headers** — Amplitude confirms no signature; but it's worth checking if they set any identifying headers (e.g., `User-Agent: Amplitude-Webhook`) that can be used for basic validation.

4. **LangSmith dataset webhooks** — Research found no evidence of LangSmith webhook events for dataset changes (new examples, version published). This was a user-stated priority signal but may not be achievable via webhooks. The GitHub issue #1516 in langsmith-sdk requests "Prompt Management Webhooks" suggesting this feature set is still being expanded.

5. **Braintrust `is_test: true` handling** — The automation payload includes `details.is_test`. The adapter should return `None` from `normalize()` for test payloads, mirroring how other adapters handle test/ping events.

---

## Sources

- [Braintrust Automations documentation](https://www.braintrust.dev/docs/guides/automations) — HIGH confidence
- [Braintrust Set up alerts](https://www.braintrust.dev/docs/admin/automations/alerts) — HIGH confidence
- [LangSmith webhook notifications for rules](https://docs.langchain.com/langsmith/webhooks) — HIGH confidence
- [LangSmith alerts webhook](https://docs.langchain.com/langsmith/alerts-webhook) — HIGH confidence
- [LangSmith Run schema reference](https://docs.smith.langchain.com/reference/python/schemas/langsmith.schemas.Run) — HIGH confidence
- [LangSmith automation rules](https://docs.smith.langchain.com/observability/how_to_guides/rules) — HIGH confidence
- [Amplitude custom monitor webhooks](https://amplitude.com/docs/admin/account-management/webhooks) — MEDIUM confidence (payload from community examples)
- [Amplitude cohort webhooks](https://amplitude.com/docs/data/destination-catalog/cohort-webhooks) — HIGH confidence
- [Amplitude community: monitor webhook payload fields](https://community.amplitude.com/data-instrumentation-57/getting-user-segment-labels-in-custom-monitor-webhook-1507) — MEDIUM confidence
- [Amplitude community: no webhook signature support](https://community.amplitude.com/data-instrumentation-57/security-webhook-for-custom-monitors-1506) — HIGH confidence
- [Arize Phoenix GitHub](https://github.com/Arize-ai/phoenix) — confirmed no outbound webhooks
- [LangSmith alerts announcement](https://blog.langchain.com/langsmith-alerts/) — MEDIUM confidence (supplementary)
