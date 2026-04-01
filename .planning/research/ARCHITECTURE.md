# Architecture Research: v0.4.0 Adapters

**Milestone:** v0.4.0 — Amplitude, Braintrust, Arize Phoenix, LangSmith adapters
**Researched:** 2026-03-31
**Overall confidence:** HIGH for structural integration (codebase read directly); MEDIUM for per-platform webhook signatures (official docs partially accessible; platform-specific headers require validation during build)

---

## Existing Pattern (per adapter)

Reading the three existing adapters (Linear, GitHub, PostHog) reveals a tight, consistent pattern. Every adapter follows the same contract:

**File:** `heartbeat_gateway/adapters/{source}.py`
**Class:** `{Source}Adapter(WebhookAdapter)`
**Constructor:** `def __init__(self, config: GatewayConfig) -> None` — stores `self.config`
**Three methods:**
- `verify_signature(payload: bytes, headers: dict) -> bool` — reads secret from `config.watch.{source}.secret`; returns `True` if secret is empty (opt-in enforcement)
- `normalize(payload: dict, headers: dict) -> NormalizedEvent | None` — returns `None` for unrecognized event types
- `condense(payload: dict) -> str` — returns `<=240` char human-readable summary (deterministic, used as dedup fingerprint)

**Secret handling invariant:** If `self.config.watch.{source}.secret` is empty, `verify_signature` returns `True`. This is not a bug — it allows opt-in signature enforcement. The `require_signatures` flag in `GatewayConfig` + startup guard in `create_app` handle mandatory enforcement.

**NormalizedEvent fields set by every adapter:**
```python
NormalizedEvent(
    source="{source}",          # e.g. "amplitude"
    event_type="{category.action}",   # dot-separated, e.g. "alert.threshold"
    payload_condensed=self.condense(payload),   # deterministic, <=240 chars
    raw_payload=payload,
    timestamp=datetime,         # from payload or datetime.now(tz=timezone.utc) fallback
    metadata={"key": "value"},  # source-specific fields for pre_filter scoping
)
```

**What `app.py` does for each adapter:**
1. Stores adapter instance on `app.state.{source}_adapter` at startup
2. `_process_webhook(request, source)` uses `getattr(state, f"{source}_adapter")` — so the naming convention `{source}_adapter` is the coupling point
3. Route: `@app.post("/webhooks/{source}")`
4. Redirect: `@app.post("/webhook/{source}", include_in_schema=False)` → 308 to `/webhooks/{source}`

**What `pre_filter.py` does:**
- `ALWAYS_DROP` dict maps source names to lists of event_type strings that are dropped before any LLM call
- Source-specific scoping blocks check `event.source == "{source}"` then read config fields and compare against `event.metadata`

**Config pattern (schema.py):**
- One `{Source}WatchConfig(BaseModel)` class per adapter — MUST be `BaseModel` not `BaseSettings` (see CLAUDE.md constraint)
- Fields: `secret: str = ""` always present; plus source-specific scoping identifiers
- Registered on `WatchConfig` as `{source}: {Source}WatchConfig = Field(default_factory={Source}WatchConfig)`
- Env var: `GATEWAY_WATCH__{SOURCE}__{FIELD}` (double underscore delimiter from pydantic-settings)

**Test pattern:**
- `tests/adapters/test_{source}.py` — unit tests for normalize, signature pass/fail, always-drop events returning `None`
- `tests/fixtures/{source}_{event}.json` — raw payload fixtures
- Adapter tests do NOT use `pytest-asyncio` — adapters are synchronous

**Init wizard pattern (commands/init.py):**
- One section per adapter, introduced with a `click.echo("")` + section header comment block
- `questionary.password()` for secrets (masked input)
- `questionary.text()` for IDs/slugs
- Written to `.env` as `GATEWAY_WATCH__{SOURCE}__{FIELD}=value`

---

## Per-Adapter Integration Points

### Amplitude

**What Amplitude webhooks are:**
Amplitude has two distinct webhook mechanisms:
1. **Custom monitor alerts** — triggered when a behavioral metric crosses a threshold; payload includes `metric`, `change_str`, `direction`, `chart_url`, `what_happened`
2. **Experiment feature flag notifications** — triggered when a flag is created/updated/deleted/activated; payload includes `flagId`, `flagName`, `action`, `flag` (full JSON), `oldFlag` (full JSON)

**Signature mechanism:** Amplitude Experiment webhooks require a `signing_key` configured in the notification settings. The exact header name is not confirmed in public docs at this research date — LOW confidence. The signing key approach is confirmed (not HMAC-SHA256 with secret but a symmetric key). Custom monitor webhooks appear to use configurable headers (operator sets up to 5 custom headers at config time) rather than HMAC signatures.

**Recommended approach for signature:** Store secret as `GATEWAY_WATCH__AMPLITUDE__SECRET`; implement `verify_signature` to check a `X-Amplitude-Signature` header (to be confirmed against Amplitude docs during build — flag as needing validation). For monitor webhooks without a signing key, fall back to the existing empty-secret-means-passthrough pattern.

**New files:**
- `heartbeat_gateway/adapters/amplitude.py` — NEW

**Modified files:**
- `heartbeat_gateway/config/schema.py` — add `AmplitudeWatchConfig` and register on `WatchConfig`
- `heartbeat_gateway/app.py` — add import, instantiate `AmplitudeAdapter`, add route + redirect
- `heartbeat_gateway/pre_filter.py` — add `"amplitude"` to `ALWAYS_DROP`, add amplitude scoping block
- `heartbeat_gateway/commands/init.py` — add Amplitude section
- `tests/adapters/test_amplitude.py` — NEW
- `tests/fixtures/amplitude_*.json` — NEW (at minimum: monitor alert, experiment flag change)

**Schema additions:**
```python
class AmplitudeWatchConfig(BaseModel):
    model_config = {"extra": "ignore"}
    secret: str = ""           # signing key for Experiment flag webhooks
    project_id: str = ""       # Amplitude project ID for scoping
```

**Pre-filter additions:**
```python
ALWAYS_DROP["amplitude"] = [
    # No always-drop events identified; Amplitude only sends alert/flag events
    # (contrast with PostHog which fires on every pageview)
]
```
Scoping block: if `config.watch.amplitude.project_id` is set, check `event.metadata.get("project_id")` for a match, identical to PostHog project scoping.

**Event types to normalize:**
- `alert.threshold` — custom monitor threshold crossed
- `flag.updated` — Experiment flag created/updated/deleted/activated

**init wizard section:**
```
Section: "Amplitude adapter"
Prompts:
  1. questionary.password("Amplitude signing key (leave blank to skip Amplitude):")
     → GATEWAY_WATCH__AMPLITUDE__SECRET
  2. questionary.text("Amplitude project ID (leave blank to skip):")
     → GATEWAY_WATCH__AMPLITUDE__PROJECT_ID
```

---

### Braintrust

**What Braintrust webhooks are:**
Braintrust Automations fire webhooks when BTQL-filtered log conditions are met, or when prompt environments are updated. Confirmed payload structure:
```json
{
  "organization": {"id": "...", "name": "..."},
  "project": {"id": "...", "name": "..."},
  "automation": {
    "id": "...", "name": "...", "event_type": "logs",
    "btql_filter": "...", "interval_seconds": 60
  },
  "details": {
    "is_test": false,
    "message": "...",
    "time_start": "...", "time_end": "..."
  }
}
```
For `event_type = "environment_update"`, details adds: `environment`, `prompt`, `new_version`, `action` ("update" | "delete").

**Signature mechanism:** Braintrust confirms HMAC signature validation support for webhooks (added 2025). The specific header name is not confirmed at this research date — MEDIUM confidence it follows the `X-Braintrust-Signature` or `X-BT-Signature` convention. Must be validated against current Braintrust docs during build.

**New files:**
- `heartbeat_gateway/adapters/braintrust.py` — NEW

**Modified files:**
- `heartbeat_gateway/config/schema.py` — add `BraintrustWatchConfig` and register on `WatchConfig`
- `heartbeat_gateway/app.py` — add import, instantiate `BraintrustAdapter`, add route + redirect
- `heartbeat_gateway/pre_filter.py` — add `"braintrust"` to `ALWAYS_DROP`, add braintrust scoping block
- `heartbeat_gateway/commands/init.py` — add Braintrust section
- `tests/adapters/test_braintrust.py` — NEW
- `tests/fixtures/braintrust_*.json` — NEW (automation trigger, environment update)

**Schema additions:**
```python
class BraintrustWatchConfig(BaseModel):
    model_config = {"extra": "ignore"}
    secret: str = ""              # HMAC signing secret
    project_ids: list[str] = Field(default_factory=list)  # scope to specific Braintrust projects
```

**Pre-filter additions:**
```python
ALWAYS_DROP["braintrust"] = [
    # Test payloads (details.is_test == True) should be dropped
    # Handled in normalize() by returning None for is_test=True, not in ALWAYS_DROP
]
```
Scoping block: if `config.watch.braintrust.project_ids` is set, check `event.metadata.get("project_id")` against the list. Pattern mirrors Linear project_ids scoping exactly.

**Event types to normalize:**
- `eval.triggered` — automation matched logs (event_type == "logs")
- `prompt.updated` — environment update (event_type == "environment_update", action == "update")
- `prompt.deleted` — environment update (action == "delete")

**init wizard section:**
```
Section: "Braintrust adapter"
Prompts:
  1. questionary.password("Braintrust webhook secret (leave blank to skip Braintrust):")
     → GATEWAY_WATCH__BRAINTRUST__SECRET
  2. questionary.text("Braintrust project ID (leave blank to skip):")
     → GATEWAY_WATCH__BRAINTRUST__PROJECT_IDS (stored as JSON list, same as Linear)
```

---

### Arize Phoenix

**What Arize Phoenix webhooks are:**
Arize Phoenix is open-source and self-hosted. The webhook/alert notification capability is confirmed to exist (webhook, email, or Slack supported) but the specific payload schema and signature mechanism are NOT documented in any publicly accessible source found during this research. This is the most opaque of the four adapters.

**Confidence level: LOW for payload format and signature headers.** This adapter requires direct inspection of the Phoenix source code or running a local instance to capture a webhook payload before implementation can begin with confidence.

**Likely payload structure (inference from project domain, NOT confirmed):**
Phoenix monitors LLM traces and eval results. The most probable webhook trigger events are:
- Eval score anomaly (an eval metric crosses a configured threshold)
- Trace volume spike or drop

**Recommended pre-build step:** Before writing the adapter, open `https://github.com/Arize-ai/phoenix` and search for webhook-related code to find the payload schema. This is a low-effort research step that will de-risk the implementation.

**New files:**
- `heartbeat_gateway/adapters/arize_phoenix.py` — NEW

**Modified files:**
- `heartbeat_gateway/config/schema.py` — add `ArizePhoenixWatchConfig` and register on `WatchConfig`
- `heartbeat_gateway/app.py` — add import, instantiate `ArizePhoenixAdapter`, add route + redirect
- `heartbeat_gateway/pre_filter.py` — add `"arize_phoenix"` to `ALWAYS_DROP`, add scoping block
- `heartbeat_gateway/commands/init.py` — add Arize Phoenix section
- `tests/adapters/test_arize_phoenix.py` — NEW
- `tests/fixtures/arize_phoenix_*.json` — NEW

**Source name decision:** Use `"arize_phoenix"` (underscore) as the source string to keep it a valid Python identifier. Route is `/webhooks/arize-phoenix` (hyphen), adapter state key is `arize_phoenix_adapter`. This diverges slightly from `app.py`'s `getattr(state, f"{source}_adapter")` — the source string passed to `_process_webhook` must be `"arize_phoenix"`, not `"arize-phoenix"`. The route handler function name will use the underscore form.

**Schema additions:**
```python
class ArizePhoenixWatchConfig(BaseModel):
    model_config = {"extra": "ignore"}
    secret: str = ""           # signing secret (mechanism TBD during build)
    project_name: str = ""     # Phoenix project name for scoping
```

**Pre-filter additions:** Placeholder `ALWAYS_DROP["arize_phoenix"] = []` with a comment noting that always-drop events will be determined once the payload schema is confirmed.

**init wizard section:**
```
Section: "Arize Phoenix adapter"
Prompts:
  1. questionary.password("Arize Phoenix webhook secret (leave blank to skip):")
     → GATEWAY_WATCH__ARIZE_PHOENIX__SECRET
  2. questionary.text("Arize Phoenix project name (leave blank to skip):")
     → GATEWAY_WATCH__ARIZE_PHOENIX__PROJECT_NAME
```

---

### LangSmith

**What LangSmith webhooks are:**
LangSmith automation rules fire webhooks when traced runs match filter criteria. Two payload shapes exist:

1. **Run automation webhook** — full `Run` object sent as POST body, with additional fields appended: `webhook_sent_at`, `error`, and optionally `values`
2. **Alert webhook** — fields: `alert_rule_id` (UUID), `alert_rule_attribute` (error_count | feedback_score | latency), `triggered_metric_value`, `triggered_threshold`, `timestamp`

Headers are operator-configurable per webhook URL in the LangSmith UI (stored encrypted). There is no confirmed HMAC signing mechanism — LangSmith relies on operator-set custom headers for authentication rather than HMAC. This is the one adapter where `verify_signature` behavior diverges: with no HMAC, the method should verify that a configured shared token header is present, or return `True` if no token is configured.

**Confidence: MEDIUM** — payload structure confirmed from docs; header authentication mechanism confirmed as custom-header-based rather than HMAC.

**New files:**
- `heartbeat_gateway/adapters/langsmith.py` — NEW

**Modified files:**
- `heartbeat_gateway/config/schema.py` — add `LangSmithWatchConfig` and register on `WatchConfig`
- `heartbeat_gateway/app.py` — add import, instantiate `LangSmithAdapter`, add route + redirect
- `heartbeat_gateway/pre_filter.py` — add `"langsmith"` to `ALWAYS_DROP`, add scoping block
- `heartbeat_gateway/commands/init.py` — add LangSmith section
- `tests/adapters/test_langsmith.py` — NEW
- `tests/fixtures/langsmith_*.json` — NEW (run automation, alert)

**Schema additions:**
```python
class LangSmithWatchConfig(BaseModel):
    model_config = {"extra": "ignore"}
    secret: str = ""           # shared token for custom header auth (not HMAC)
    project_names: list[str] = Field(default_factory=list)  # LangSmith project scoping
```

**The `verify_signature` divergence:** Because LangSmith uses custom headers rather than HMAC, `verify_signature` should check for a configured shared token in a custom header (e.g., `X-LangSmith-Token`) rather than computing an HMAC. If `secret` is empty, return `True` as with all other adapters.

**Pre-filter additions:**
```python
ALWAYS_DROP["langsmith"] = [
    # No high-noise always-drop events identified; LangSmith only fires on
    # automation-matched runs — operator controls the filter via LangSmith rules
]
```
Scoping block: if `config.watch.langsmith.project_names` is set, check `event.metadata.get("project_name")` against the list.

**Event types to normalize:**
- `run.matched` — automation rule matched a run
- `alert.triggered` — metric threshold alert fired

**init wizard section:**
```
Section: "LangSmith adapter"
Prompts:
  1. questionary.password("LangSmith webhook token (leave blank to skip LangSmith):")
     → GATEWAY_WATCH__LANGSMITH__SECRET
     (Note in prompt: "Configure the same token as a custom header in LangSmith UI")
  2. questionary.text("LangSmith project name to watch (leave blank to skip):")
     → GATEWAY_WATCH__LANGSMITH__PROJECT_NAMES (stored as JSON list)
```

---

## gateway init Wizard Changes

The current wizard has 3 sections:
1. Core config (API key, workspace path, SOUL.md path, LLM model)
2. Linear adapter (secret + project UUID)
3. GitHub adapter (secret + repos)

v0.4.0 adds 5 new sections (PostHog was planned for v0.4.0 per PROJECT.md):

| Section | New prompts | Env vars written |
|---------|-------------|-----------------|
| PostHog | secret, project_id | `GATEWAY_WATCH__POSTHOG__SECRET`, `GATEWAY_WATCH__POSTHOG__PROJECT_ID` |
| Amplitude | signing key, project_id | `GATEWAY_WATCH__AMPLITUDE__SECRET`, `GATEWAY_WATCH__AMPLITUDE__PROJECT_ID` |
| Braintrust | secret, project_id | `GATEWAY_WATCH__BRAINTRUST__SECRET`, `GATEWAY_WATCH__BRAINTRUST__PROJECT_IDS` |
| Arize Phoenix | secret, project_name | `GATEWAY_WATCH__ARIZE_PHOENIX__SECRET`, `GATEWAY_WATCH__ARIZE_PHOENIX__PROJECT_NAME` |
| LangSmith | token, project_name | `GATEWAY_WATCH__LANGSMITH__SECRET`, `GATEWAY_WATCH__LANGSMITH__PROJECT_NAMES` |

**Total new prompts: 10** (2 per adapter × 5 adapters including PostHog)

**Placement in wizard flow:** Each new adapter section appends after the existing GitHub section. Section headers follow the existing pattern: `click.echo("")` + `click.echo("  {Adapter} adapter")` + instruction block. All secrets use `questionary.password()`. All IDs/names use `questionary.text()`.

**No changes to Section 1 (core config)** and no changes to existing Linear/GitHub sections. The wizard merges with existing `.env` values (`existing.get(...)` pattern) — new adapter sections will default to `""` or the existing value if already configured.

**require_signatures guard in app.py** will need to be extended to include the four new sources. Currently it only checks linear, github, posthog. Each new source with a configured secret must be added to the missing-secrets validation at startup.

---

## Recommended Build Order

### Phase 1: Schema Foundation
**Files changed:** `heartbeat_gateway/config/schema.py` only
**What:** Add all five `WatchConfig` subclasses (`AmplitudeWatchConfig`, `BraintrustWatchConfig`, `ArizePhoenixWatchConfig`, `LangSmithWatchConfig`) and register them on `WatchConfig`. Add PostHog init wizard section at the same time (it's already in the schema).
**Why first:** Every subsequent phase depends on config fields existing. Schema changes are additive — `extra = "ignore"` means existing env files are unaffected. Tests can run before any adapter code exists.
**Tests:** Verify that `GatewayConfig()` instantiates without error with new empty fields. Verify env var loading: `GATEWAY_WATCH__AMPLITUDE__SECRET=test` populates `config.watch.amplitude.secret`.

### Phase 2: Braintrust Adapter
**Why first adapter:** Braintrust has the most confirmed payload structure of the four. The webhook payload schema is fully documented (organization/project/automation/details envelope). HMAC support confirmed, header name needs verification but the pattern is standard. This makes it the lowest-risk first adapter to build, and building it establishes the test fixtures and adapter test pattern for subsequent adapters.
**Files:** `heartbeat_gateway/adapters/braintrust.py` (new), `app.py` (modified), `pre_filter.py` (modified), `tests/adapters/test_braintrust.py` (new), `tests/fixtures/braintrust_*.json` (new)
**init wizard:** Add Braintrust section to `commands/init.py`

### Phase 3: LangSmith Adapter
**Why second:** LangSmith payload structure is confirmed. The `verify_signature` divergence (custom header vs HMAC) is the only structural novelty — but it is a simpler case (check header value, no HMAC computation). Establishing this pattern second means the "non-HMAC adapter" case is tested before tackling the less-documented adapters.
**Files:** Same pattern as Phase 2 for LangSmith
**init wizard:** Add LangSmith section

### Phase 4: Amplitude Adapter
**Why third:** Two Amplitude webhook shapes (monitor alerts vs Experiment flags) require a `_classify` method that handles both, similar to how PostHog handles multiple payload types. The signing key mechanism needs validation but the payload structure is documented well enough to write the adapter. PostHog is a close analogue.
**Files:** Same pattern for Amplitude
**init wizard:** Add Amplitude section

### Phase 5: Arize Phoenix Adapter
**Why last:** Lowest confidence on payload schema and signature mechanism. Building it last means the adapter infrastructure is fully proven before tackling the most uncertain implementation. The phase should begin with a targeted source inspection (GitHub repo or local instance capture) before writing any code.
**Files:** Same pattern for Arize Phoenix
**init wizard:** Add Arize Phoenix section
**Phase-specific research flag:** Inspect `https://github.com/Arize-ai/phoenix` for webhook-related code before writing the adapter.

### Phase 6: PostHog init Wizard Section
**Why separate:** PostHog's adapter already exists. This phase adds only the PostHog prompts to `commands/init.py` and the PostHog secret to the `require_signatures` guard in `app.py`. No adapter code changes.
**Files:** `heartbeat_gateway/commands/init.py` (modified), `heartbeat_gateway/app.py` (minor guard extension), `tests/cli/test_init.py` (updated)

**Alternative ordering:** Phases 6 (PostHog wizard) and 1 (schema) could be bundled into a single "foundations" phase if the roadmapper prefers fewer total phases. The dependency graph permits it — PostHog wizard changes `init.py` only, schema changes `schema.py` only, no conflict.

---

## Shared vs Divergent Patterns

### What is identical across all 4 new adapters

- File layout: `heartbeat_gateway/adapters/{source}.py`, one class inheriting `WebhookAdapter`
- Constructor signature: `def __init__(self, config: GatewayConfig) -> None`
- Secret location: `self.config.watch.{source}.secret`
- Empty-secret passthrough in `verify_signature`
- `normalize()` returns `None` for unrecognized types
- `condense()` returns deterministic `<=240` char string
- `NormalizedEvent` constructor shape
- Route registration in `app.py`: one `@app.post("/webhooks/{source}")` + one redirect
- State key pattern: `app.state.{source}_adapter = {Source}Adapter(config)`
- Test file: `tests/adapters/test_{source}.py` with `tests/fixtures/{source}_*.json`
- Schema model: `{Source}WatchConfig(BaseModel)` with `secret: str = ""`
- Init wizard: password prompt for secret, text prompt for scoping ID

### What diverges

| Dimension | Amplitude | Braintrust | Arize Phoenix | LangSmith |
|-----------|-----------|------------|---------------|-----------|
| Signature mechanism | Custom signing key (format TBD) | HMAC-SHA256 (header name TBD) | Unknown — needs research | Custom header token (no HMAC) |
| HMAC computation | Maybe | Yes | Unknown | No |
| Payload envelope | Flat (monitor) or flag-centric (Experiment) | organization/project/automation/details | Unknown | Full Run object or alert fields |
| Always-drop events | None identified (low volume) | test payloads (is_test=True, handled in normalize) | Unknown | None (operator controls via rules) |
| Scoping field type | project_id (string) | project_ids (list) | project_name (string) | project_names (list) |
| Pre-filter pattern | PostHog-style (single ID equality) | Linear-style (list membership) | PostHog-style (single name equality) | Linear-style (list membership) |
| normalize complexity | Medium (two payload shapes) | Low (uniform envelope) | Unknown | Low (two payload shapes, documented) |
| Source name in app | `"amplitude"` | `"braintrust"` | `"arize_phoenix"` | `"langsmith"` |
| Route path | `/webhooks/amplitude` | `/webhooks/braintrust` | `/webhooks/arize-phoenix` | `/webhooks/langsmith` |

**The Arize Phoenix source name / route path divergence** (underscore in Python, hyphen in URL) is the one place the pattern breaks. The `_process_webhook(request, source)` function uses `source` to call `getattr(state, f"{source}_adapter")`, so the string passed must match the Python attribute name. The route handler for Arize Phoenix must pass `"arize_phoenix"` not `"arize-phoenix"`. This requires an explicit named function (not a lambda), consistent with how the other routes work.

### The LangSmith verify_signature structural divergence

All other adapters (existing and new) compute an HMAC over the payload and compare it to a signature header. LangSmith does not use HMAC — it relies on operator-set custom headers for auth. The `verify_signature` implementation for LangSmith should:
1. Read `self.config.watch.langsmith.secret`
2. If empty, return `True` (passthrough, same as all others)
3. If set, check that the incoming `headers` contain a specific header (e.g., `x-langsmith-token`) matching the configured secret
4. This approach is a shared-token check, not a signature check — the method name is the same but the semantics differ

This divergence is safe because `verify_signature` returns `bool` in all cases and the caller in `_process_webhook` does not care about the mechanism.

---

## Integration Point Summary (new vs modified files)

| File | Status | Changes |
|------|--------|---------|
| `heartbeat_gateway/config/schema.py` | MODIFIED | +4 WatchConfig subclasses, +4 fields on WatchConfig |
| `heartbeat_gateway/app.py` | MODIFIED | +4 imports, +4 adapter instantiations, +4 routes, +4 redirects, +4 entries in require_signatures guard |
| `heartbeat_gateway/pre_filter.py` | MODIFIED | +4 entries in ALWAYS_DROP dict, +4 scoping blocks |
| `heartbeat_gateway/commands/init.py` | MODIFIED | +5 wizard sections (PostHog + 4 new), +10 prompts |
| `heartbeat_gateway/adapters/amplitude.py` | NEW | AmplitudeAdapter |
| `heartbeat_gateway/adapters/braintrust.py` | NEW | BraintrustAdapter |
| `heartbeat_gateway/adapters/arize_phoenix.py` | NEW | ArizePhoenixAdapter |
| `heartbeat_gateway/adapters/langsmith.py` | NEW | LangSmithAdapter |
| `tests/adapters/test_amplitude.py` | NEW | |
| `tests/adapters/test_braintrust.py` | NEW | |
| `tests/adapters/test_arize_phoenix.py` | NEW | |
| `tests/adapters/test_langsmith.py` | NEW | |
| `tests/fixtures/amplitude_*.json` | NEW | 2+ fixtures |
| `tests/fixtures/braintrust_*.json` | NEW | 2+ fixtures |
| `tests/fixtures/arize_phoenix_*.json` | NEW | 2+ fixtures |
| `tests/fixtures/langsmith_*.json` | NEW | 2+ fixtures |

**No changes required to:**
- `heartbeat_gateway/adapters/base.py` — ABC is sufficient as-is
- `heartbeat_gateway/classifier.py` — source-agnostic
- `heartbeat_gateway/writer.py` — source-agnostic
- `heartbeat_gateway/mcp_server.py` — source-agnostic
- `heartbeat_gateway/prompts/classify.yaml` — source-agnostic
- `heartbeat_gateway/commands/doctor.py` — doctor validates config fields, new fields appear automatically via GatewayConfig loading

---

## Sources

- Codebase read directly: `app.py`, `pre_filter.py`, `config/schema.py`, `adapters/base.py`, `adapters/posthog.py`, `adapters/github.py`, `commands/init.py`
- Braintrust webhook payload structure: https://www.braintrust.dev/docs/guides/automations (confirmed via WebSearch)
- LangSmith webhook payload: https://docs.smith.langchain.com/observability/how_to_guides/alerts_webhook (confirmed via WebSearch)
- LangSmith run rules + webhook headers: https://changelog.langchain.com/announcements/set-up-webhook-notifications-for-run-rules
- Amplitude Experiment webhook payload: https://amplitude.com/docs/feature-experiment/notifications (confirmed via WebSearch)
- Amplitude custom monitor webhooks: https://amplitude.com/docs/admin/account-management/webhooks
- Arize Phoenix: webhook payload schema not found in public docs — LOW confidence; source inspection required before build
