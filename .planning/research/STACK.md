# Stack Research: v0.4.0 Adapters

**Project:** heartbeat-gateway
**Milestone:** v0.4.0 — Amplitude, Braintrust, Arize Phoenix, LangSmith adapters
**Researched:** 2026-03-31
**Scope:** Webhook infrastructure for four new adapters only. Existing stack (FastAPI, litellm, pydantic-settings, HMAC base class) is validated and unchanged.

---

## Per-Platform Webhook Support

### Amplitude

**Webhook support status:** PARTIAL — two distinct webhook systems with different security postures. Choose one.

**System 1: Custom Monitor Alerts**
- **What fires:** Threshold alerts on chart metrics when KPIs breach a configured value.
- **Auth/Signature:** NONE. Amplitude does not send HMAC signatures or any signature header for custom monitor webhooks. Community thread (October 2022) confirmed by Amplitude engineering: "we do not have the capability of sending webhooks with credentials." As of 2025 searches, this has not changed.
- **Header:** No signature header. Authentication is URL-only — the operator embeds a secret token as a query parameter in the webhook URL.
- **Payload shape:** JSON array under `"charts"` key. Each chart entry has: `header` (alert name), `user_segment_idx`, `segment_value_label`, `what_happened` (plain-text description with threshold value and timestamp), `chart_url`, `rca_url`.
- **Implication for adapter:** `verify_signature` must implement token-in-URL pattern. Extract a `?token=` or `?secret=` query param from the request URL (via FastAPI's `Request.query_params`) and compare against configured secret using `hmac.compare_digest`. If no secret configured, return `True` per base class convention.

**System 2: Webhooks Streaming (Event Destination)**
- **What fires:** Forward raw product analytics events or cohort membership changes in real time.
- **Auth:** Up to five custom headers configurable, but Amplitude does not generate or send a signing signature. Same limitation as System 1.
- **Relevance:** LOW for heartbeat-gateway. Streaming is a data-pipeline feature, not an alerting signal. The adapter should target System 1 (monitor alerts), not streaming.

**Quirk:** Amplitude's webhook URL must be publicly reachable. Operators using heartbeat-gateway behind a Cloudflare tunnel (`hooks.kahako.ai`) are already in the right shape.

**Confidence:** MEDIUM. Payload shape is confirmed from multiple Amplitude community posts and integration guides. No-signature limitation confirmed via Amplitude community (engineering response). Absence of a 2025 update announcing signatures was verified with multiple searches — treat as still accurate but flag for operator validation.

---

### Braintrust

**Webhook support status:** YES — native webhook automations for alert conditions on logs and experiments.

**What fires:**
- Automation conditions on log data (BTQL filter matches)
- Score thresholds
- Experiment results
- Environment/prompt deployment changes
- Human feedback annotations (via automation rule)

**Auth/Signature:** Braintrust added HMAC signature validation for webhooks (release noted in AIR Release Notes dated July 22, 2025). The exact header name and algorithm are not publicly documented in indexable form as of this research — the documentation mentions "updated documentation is available to support webhook implementation" but that page requires an authenticated session. Based on Braintrust's implementation patterns and industry convention:
- **Most likely header:** `x-braintrust-signature` (standard naming convention for platform-specific HMAC headers)
- **Algorithm:** HMAC-SHA256 (confirmed as the HMAC type from release note language)
- **REQUIRES VERIFICATION** before implementing. The adapter should be written with a configurable secret; if the actual header name differs, only one constant changes.

**Payload shape (confirmed):**
```json
{
  "organization": {"id": "...", "name": "..."},
  "project": {"id": "...", "name": "..."},
  "automation": {
    "id": "...",
    "name": "...",
    "description": "...",
    "event_type": "...",
    "btql_filter": "...",
    "interval_seconds": 300,
    "url": "https://..."
  },
  "details": {
    "is_test": false,
    "message": "...",
    "time_start": "...",
    "time_end": "...",
    "count": 5,
    "related_logs_url": "https://..."
  }
}
```

**Quirk:** Braintrust sends a test payload when you first configure a webhook. The adapter's `normalize()` should handle `is_test: true` by returning `None` to suppress test events from reaching HEARTBEAT.md.

**Configuration in Braintrust UI:** Navigate to Configuration > Automations tab in your project. Add automation, choose webhook, enter URL.

**Confidence:** MEDIUM-HIGH for payload shape (confirmed from automations docs). LOW for exact signature header name (inferred from pattern, not from official docs). Flag: must verify header name before writing `verify_signature`.

---

### Arize Phoenix

**Webhook support status:** NOT SUPPORTED in OSS (open-source, self-hosted) version as of 2025.

**Critical distinction:**
- **Arize Phoenix OSS** (`pip install arize-phoenix`, self-hosted) — does NOT have outgoing webhook alerts. It is a trace collection, visualization, and evaluation platform. There is no webhook/alerting system. No GitHub issues or PRs found for this feature.
- **Arize AX** (hosted SaaS) — DOES have alerting integrations (Slack, PagerDuty, custom webhooks). This is a separate paid product with different features.

**What Phoenix OSS does have:** REST API for span annotations (`POST /v1/span_annotations`). Phoenix receives data, it does not send it. You push traces into Phoenix; Phoenix does not push events out to your system.

**Implication for v0.4.0:** An Arize Phoenix adapter cannot be a webhook receiver because Phoenix OSS does not fire webhooks. There are three possible reframings:

1. **Drop from scope.** Phoenix OSS does not support outgoing webhooks. Build when/if a future version adds this feature. This is the honest answer.
2. **Poll Phoenix's REST API instead.** Phoenix has a REST API (and `arize-phoenix-client` Python package). A polling adapter could query `/v1/traces` or annotation endpoints on a schedule. This violates heartbeat-gateway's "webhook-first is the design constraint" per PROJECT.md and is explicitly out of scope.
3. **Target Arize AX only.** If the operator uses the hosted Arize AX platform (not self-hosted Phoenix), it does support webhook notifications. Document that the adapter requires Arize AX, not Phoenix OSS.

**Recommendation:** Reframe the adapter as "Arize AX" not "Arize Phoenix OSS." Document the distinction clearly in the adapter. If the target user is a solo developer using free-tier Phoenix OSS (the PROJECT.md persona), this adapter has no audience. Flag this for product decision before building.

**Python packages needed:** None for webhook reception. If a polling approach were chosen, `arize-phoenix-client>=1.31.0` would be relevant, but that is out of scope.

**Confidence:** HIGH for Phoenix OSS having no outgoing webhooks (verified via multiple searches, GitHub repo scan, official docs). MEDIUM for Arize AX having webhook support (multiple sources confirm alerting integrations exist, but exact webhook payload and signature scheme not verified).

---

### LangSmith

**Webhook support status:** YES — webhook notifications for automation rules.

**What fires:**
- Automation rules matching new runs (run failures, latency thresholds, error rates)
- Feedback annotations on runs
- Alert conditions configured in the LangSmith UI
- Prompt deployment changes (webhook added July 2024 per changelog)
- Fleet webhooks (agent fleet run completions)

**Auth/Signature:** LangSmith does NOT use HMAC-SHA256 signatures. Its documented security model is:
- **Primary pattern:** Secret as query parameter in the webhook URL (e.g., `https://hooks.kahako.ai/langsmith?secret=<token>`). LangSmith passes this through unchanged; the receiver extracts and validates it.
- **Secondary pattern:** Custom headers (per-URL, stored encrypted in LangSmith UI) — operator can configure arbitrary `Authorization: Bearer <token>` or similar.
- **No platform-generated signature header** has been found in documentation. LangSmith's API uses `x-api-key` for its own REST API, but this is not included in webhook outbound requests to the receiver.

**Header for our adapter:** Since LangSmith has no standard signature header, the adapter's `verify_signature` should:
1. Check `headers.get("authorization")` for a Bearer token if the operator configured a custom auth header.
2. Fall back to checking a configured `secret` against a `?secret=` query parameter — but this requires the FastAPI route to pass query params, which the current architecture does not do.
3. If neither is configured, return `True` (same as other adapters with no secret set).

**Architecture implication:** The current `verify_signature(payload: bytes, headers: dict)` signature does not include query parameters. LangSmith's query-parameter auth pattern requires access to `request.query_params`. The LangSmith adapter will need either: (a) a custom FastAPI route that extracts the query param and passes it as a synthetic header before calling the adapter, or (b) a convention where operators embed the secret as a custom `X-Langsmith-Secret` header instead of a query param — which LangSmith supports via its custom headers feature. Option (b) is cleaner and requires no changes to the existing route architecture. Document this as the recommended setup for LangSmith operators.

**Payload shape (confirmed):**
```json
{
  "run_id": "...",
  "run_name": "...",
  "run_type": "chain|llm|tool",
  "inputs": {...},
  "outputs": {...},
  "error": null,
  "start_time": "...",
  "end_time": "...",
  "kwargs": {
    "values": {...},
    "webhook_sent_at": "...",
    "error": null
  }
}
```
Fleet and alert webhooks have different payload shapes — verify at implementation time.

**Retry behavior:** LangSmith retries up to 2 times on connection failure or 5xx; does not retry on 4xx. Endpoint must respond within 5 seconds.

**Confidence:** MEDIUM-HIGH for webhook support and payload fields (confirmed via official docs URL: `docs.langchain.com/langsmith/webhooks`). MEDIUM for auth pattern (query-param pattern confirmed, custom header alternative inferred but consistent with LangSmith docs). LOW for exact payload schema of fleet and alert webhooks — verify at implementation time.

---

## New Dependencies

All four adapters are **pure HTTP webhook integrations**. No platform SDK is required.

| Package | Version | Why Needed | Already in pyproject.toml? |
|---------|---------|-----------|--------------------------|
| None required | — | All four adapters use standard HTTP + HMAC (or token comparison). Existing `hashlib`, `hmac` (stdlib) cover signature verification. | N/A |

**Confirmed already present for all adapter needs:**
- `fastapi>=0.115.0` — route registration
- `pydantic>=2.9.0` — NormalizedEvent
- `pydantic-settings>=2.6.0` — GatewayConfig nested config
- `hashlib` + `hmac` — stdlib, used by Linear and PostHog adapters today

**No new entries needed in pyproject.toml for the adapter code itself.**

The only possible addition is `arize-phoenix-client` if the Arize adapter is reframed as a polling adapter — but that is explicitly out of scope per PROJECT.md.

---

## Integration Notes

### schema.py changes required

Four new `*WatchConfig` classes and registration in `WatchConfig`, following the exact pattern of `LinearWatchConfig` and `PostHogWatchConfig`:

```python
class AmplitudeWatchConfig(BaseModel):
    model_config = {"extra": "ignore"}
    secret: str = ""  # embedded as ?secret= param or verified via custom header

class BraintrustWatchConfig(BaseModel):
    model_config = {"extra": "ignore"}
    project_ids: list[str] = Field(default_factory=list)
    secret: str = ""  # HMAC secret — header name TBD (likely x-braintrust-signature)

class ArizeWatchConfig(BaseModel):
    model_config = {"extra": "ignore"}
    secret: str = ""  # only relevant if targeting Arize AX (not Phoenix OSS)

class LangSmithWatchConfig(BaseModel):
    model_config = {"extra": "ignore"}
    project_names: list[str] = Field(default_factory=list)
    secret: str = ""  # operator sets this; configure LangSmith to send X-Langsmith-Secret header

class WatchConfig(BaseModel):
    # ... existing fields ...
    amplitude: AmplitudeWatchConfig = Field(default_factory=AmplitudeWatchConfig)
    braintrust: BraintrustWatchConfig = Field(default_factory=BraintrustWatchConfig)
    arize: ArizeWatchConfig = Field(default_factory=ArizeWatchConfig)
    langsmith: LangSmithWatchConfig = Field(default_factory=LangSmithWatchConfig)
```

**Critical constraint from CLAUDE.md:** All nested watch config classes must be `BaseModel`, not `BaseSettings`. Making them `BaseSettings` causes them to instantiate independently via `default_factory` and silently bypass `GatewayConfig`'s env loading (the v0.2.0 security regression). Do not deviate from this pattern.

### app.py changes required

Four new FastAPI routes following the existing pattern:

```python
@app.post("/amplitude")
@app.post("/braintrust")
@app.post("/arize")
@app.post("/langsmith")
```

Each route follows the same body as the existing `/linear`, `/github`, `/posthog` routes: read raw bytes, call adapter's `verify_signature`, parse JSON, call `normalize`, run through `PreFilter`, then `Classifier`.

**LangSmith-specific:** If the operator is using query-param auth (not recommended), the route for `/langsmith` would need `request: Request` and pass `request.query_params.get("secret")` as a synthetic header entry. Recommended alternative: instruct operators to configure LangSmith's custom header feature to send `X-Langsmith-Secret: <secret>`, which the adapter reads from `headers` normally.

### pre_filter.py changes required

Two adapters have scoping fields that PreFilter should enforce:
- **Braintrust:** `project_ids` filter — drop events not matching configured project IDs (same as Linear's `project_ids` pattern).
- **LangSmith:** `project_names` filter — drop events not matching configured project names.
- **Amplitude:** No natural scoping field in the alert payload beyond the alert name.
- **Arize:** No scoping needed (scope comes from the Arize AX monitor configuration).

### gateway init wizard additions (PostHog + new adapters)

Per PROJECT.md, the v0.4.0 milestone also adds a PostHog section to `gateway init`. Each new adapter needs a corresponding wizard section:
- `confirm("Do you use Amplitude?")` → prompt for secret (optional, since Amplitude doesn't sign requests — educate the operator)
- `confirm("Do you use Braintrust?")` → prompt for secret + project IDs
- `confirm("Do you use Arize AX?")` → prompt for secret (with note: requires Arize AX, not Phoenix OSS)
- `confirm("Do you use LangSmith?")` → prompt for secret + project names + instruction to configure `X-Langsmith-Secret` custom header in LangSmith UI

---

## Verdict

### Straightforward (build with confidence)

**Braintrust** — Webhook automation system is clearly documented, payload shape is confirmed, HMAC is confirmed (signature header name needs one lookup in the actual docs at build time). Follows the standard HMAC-SHA256 adapter pattern. Build normally; verify the exact header constant before writing `verify_signature`.

**LangSmith** — Webhook support is well-documented, payload shape partially confirmed. The auth quirk (no platform-generated signature) is a known pattern handled by directing operators to use custom headers. No architecture changes needed if operators follow the recommended custom-header setup. Build normally with the custom-header convention documented clearly.

### Requires product decision before building

**Amplitude** — Webhooks exist but have NO signature mechanism. The `verify_signature` implementation is token-in-URL or URL-trust-only. This is weaker security than every other adapter. The operator must understand this. Consider whether to document as "best-effort auth only" or to require operators to place a token in the URL and validate it. Either way: the adapter is buildable, but security expectations must be set clearly in documentation.

**Arize Phoenix** — As scoped (Phoenix OSS), this adapter is **not feasible**. Phoenix OSS does not fire outgoing webhooks. The adapter must be reframed as "Arize AX" (hosted platform) before building, or dropped from v0.4.0 scope. This is a scope correction that needs a product decision. Recommend: rename to `ArizeAXAdapter`, document the Phoenix OSS limitation prominently, and target Arize AX customers only.

---

## Open Questions (must resolve before implementation)

1. **Braintrust signature header name** — what exact header does Braintrust send the HMAC-SHA256 signature in? Check `braintrust.dev/docs/guides/automations` at build time. Likely `x-braintrust-signature` but not confirmed.
2. **Arize Phoenix vs Arize AX** — product decision: is the target user running Phoenix OSS (no webhook support) or Arize AX (webhook support)? This determines whether the adapter is buildable or should be dropped.
3. **Amplitude signature gap** — is "token in URL" acceptable security for this project's operator persona, or should the adapter document this as a known limitation?
4. **LangSmith fleet/alert webhook payloads** — payload shape confirmed for run rules; fleet and alert webhook shapes need verification against `docs.langchain.com/langsmith/fleet/webhooks` and `docs.langchain.com/langsmith/alerts-webhook`.

---

## Confidence Assessment

| Platform | Webhook Exists | Auth Scheme | Payload Shape | Overall |
|----------|----------------|-------------|---------------|---------|
| Amplitude | HIGH (yes, two systems) | HIGH (no signature — URL token only) | MEDIUM (custom monitor payload confirmed, streaming differs) | MEDIUM |
| Braintrust | HIGH | MEDIUM (HMAC-SHA256 confirmed, header name unconfirmed) | HIGH (structure documented) | MEDIUM-HIGH |
| Arize Phoenix OSS | HIGH (does NOT exist) | N/A | N/A | HIGH (no-op finding) |
| Arize AX | MEDIUM (yes, alerting integrations exist) | LOW (scheme not verified) | LOW (not documented publicly) | LOW |
| LangSmith | HIGH | MEDIUM-HIGH (no HMAC, custom header recommended) | MEDIUM (run rule payload partially confirmed) | MEDIUM-HIGH |

---

## Sources

- Amplitude webhooks (custom monitors): https://amplitude.com/docs/admin/account-management/webhooks
- Amplitude community (no signing secret): https://community.amplitude.com/data-instrumentation-57/security-webhook-for-custom-monitors-1506
- Amplitude cohort webhooks: https://amplitude.com/docs/data/destination-catalog/cohort-webhooks
- Braintrust automations docs: https://www.braintrust.dev/docs/guides/automations
- Braintrust alerts: https://www.braintrust.dev/docs/admin/automations/alerts
- Braintrust HMAC announcement: https://www.usebraintrust.com/air-release-notes (July 22, 2025)
- Arize Phoenix GitHub: https://github.com/Arize-ai/phoenix
- Arize AX alerting integrations: https://arize.com/docs/ax/observe/production-monitoring/alerting-integrations
- Arize Phoenix vs AX comparison: https://langfuse.com/faq/all/best-phoenix-arize-alternatives
- LangSmith webhooks: https://docs.langchain.com/langsmith/webhooks
- LangSmith use-webhooks: https://docs.langchain.com/langsmith/use-webhooks
- LangSmith alerts webhook: https://docs.langchain.com/langsmith/alerts-webhook
- LangSmith fleet webhooks: https://docs.langchain.com/langsmith/fleet/webhooks
- LangSmith changelog (webhook for run rules): https://changelog.langchain.com/announcements/set-up-webhook-notifications-for-run-rules
