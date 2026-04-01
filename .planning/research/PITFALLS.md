# Pitfalls Research: v0.4.0 Adapters

**Project:** heartbeat-gateway v0.4.0
**Scope:** Adding Amplitude, Braintrust, Arize Phoenix, and LangSmith adapters; PostHog `gateway init` section
**Researched:** 2026-03-31
**Overall confidence:** MEDIUM-HIGH — grounded in codebase reading, official docs search, and community findings. Braintrust and LangSmith signature details are LOW confidence pending official verification.

---

## Per-Platform Risks

### Amplitude

#### AMPLITUDE-1: Amplitude Does Not Send HMAC Signatures (Critical)

**What goes wrong:** You implement `verify_signature()` looking for an `X-Amplitude-Signature` header or similar, find nothing, and either hard-fail all requests (401 every event) or silently skip verification and leave the endpoint unauthenticated.

**What the research found:** Amplitude's custom monitor webhooks have **no built-in signature mechanism**. Amplitude community confirms: "Right now when configuring a webhook in Amplitude, you can't specify any secure credentials. Whatever secrets are required to authenticate to your endpoint must be included on the webhook URL in plain text." An "Allow secure credentials to be specified" feature request has been open but unfulfilled.

**Consequence for this codebase:** The `verify_signature()` method on the Amplitude adapter must follow the same optional pattern used by all existing adapters — if `secret` is empty string, return `True`. But unlike Linear/GitHub/PostHog where a secret *can* be configured to verify real signatures, Amplitude has no server-side signing. Setting a secret in config has no effect on actual security — it just breaks all incoming Amplitude webhooks with 401s. The config field should still exist (for symmetry and future compatibility) but the adapter docs must note that Amplitude does not sign webhooks.

**Prevention:**
- `verify_signature()` must always return `True` when `self.config.watch.amplitude.secret` is empty (consistent with existing adapters).
- Do not attempt to read a signature header that doesn't exist — do not KeyError on missing headers.
- Add a comment in the adapter noting the limitation and pointing to the Amplitude community thread.
- If a secret is configured but Amplitude doesn't send one, the comparison will fail. Either: (a) treat Amplitude as signature-optional regardless of config, or (b) add a `require_amplitude_signature` flag that defaults False and warn in `gateway doctor`.

**Warning sign:** A test that passes a secret in config and expects 401 on unsolicited requests — this is correct security intent but cannot be verified via Amplitude's signature since Amplitude doesn't send one.

**Phase:** Phase implementing the Amplitude adapter.

---

#### AMPLITUDE-2: Amplitude Payload Uses a `charts` Array, Not a Single Event Object

**What goes wrong:** You write `normalize()` expecting a top-level `event_type` or `type` field, as with PostHog, but Amplitude's custom monitor webhook payload wraps everything in a `charts` array. Accessing `payload.get("type", "")` returns `""` and `normalize()` returns `None`, silently dropping all Amplitude events.

**What the payload looks like (MEDIUM confidence — inferred from docs):**
```json
{
  "charts": [
    {
      "header": "My Alert",
      "user_segment_idx": "1",
      "segment_value_label": null,
      "what_happened": "2022-10-13 14:00:00: 44.4 is lower than the threshold 55.0.",
      "chart_url": "https://app.amplitude.com/...",
      "rca_url": "https://app.amplitude.com/...",
      "metric": "...",
      "change_str": "...",
      "direction": "down"
    }
  ]
}
```

**Consequence:** `_classify()` on this payload must inspect `payload.get("charts", [])` — the outer envelope, not a `type` field. A single Amplitude webhook delivery can include multiple chart alerts in the same payload (batch delivery). The adapter must either normalize one event per chart entry or normalize to a single event with aggregate metadata.

**Prevention:**
- Test with a fixture that has `charts` as an array with two entries — verify the adapter handles both.
- The `condense()` method must pull from `charts[0]["header"]` or summarize all charts if multiple.
- If the `charts` array is empty (Amplitude test payloads may send empty arrays), `normalize()` must return `None` rather than crashing on index access.

**Warning sign:** `normalize()` returns `None` in tests but no assertion explains why — check whether `payload.get("charts")` is being accessed.

**Phase:** Phase implementing the Amplitude adapter.

---

#### AMPLITUDE-3: `what_happened` Is a Human-Readable String, Not Structured Data

**What goes wrong:** You try to parse `what_happened` (e.g., `"2022-10-13 14:00:00: 44.4 is lower than the threshold 55.0."`) as structured numeric data to populate `metadata["current_value"]` and `metadata["threshold_value"]`, which requires regex parsing of a sentence. This creates brittle code that breaks when Amplitude changes their message format.

**Prevention:**
- Store `what_happened` verbatim as `metadata["what_happened"]` — do not parse it.
- For `condense()`, use `charts[0]["header"]` as the alert name and `what_happened` truncated to fit the 240-char limit.
- Threshold and current values may appear separately in some payload variants (`metric`, `change_str`) — use those if present, fall back to `what_happened` raw string if not.

**Phase:** Phase implementing the Amplitude adapter.

---

### Braintrust

#### BRAINTRUST-1: `is_test` Payloads Must Be Dropped Before LLM

**What goes wrong:** Braintrust sends a test payload to your endpoint when you save an automation (to verify the URL is reachable). The `details.is_test` field is `true`. If the adapter does not check this, every time an operator saves a Braintrust automation, it creates a spurious HEARTBEAT.md or DELTA.md entry with fake data.

**What the research confirmed (HIGH confidence):** The Braintrust automation docs state: "Before saving or updating an automation, you can test it by selecting Test automation. For webhooks, Braintrust sends a test payload to your URL." The payload's `details.is_test` field will be `true` for these deliveries.

**Prevention:**
- In `normalize()`, check `payload.get("details", {}).get("is_test", False)`. If `True`, return `None`.
- This should happen *before* any other processing — the test payload is still a valid JSON structure that would otherwise normalize successfully.
- Write a unit test: provide a payload with `is_test: true` and assert `normalize()` returns `None`.

**Warning sign:** Integration test fixture written with `is_test: false` passes, but live testing creates phantom heartbeat entries when operator saves the automation in Braintrust UI.

**Phase:** Phase implementing the Braintrust adapter.

---

#### BRAINTRUST-2: Signature Verification Status Is Unconfirmed (Low Confidence)

**What goes wrong:** You implement `verify_signature()` with HMAC-SHA256 against an undocumented header name, get it wrong, and either 401 all real events or accept everything unauthenticated.

**What the research found (LOW confidence):** One AIR Release Notes source states "Webhook integrations in Braintrust now support HMAC signature validation," but no official Braintrust docs page returned specific header names or algorithm details from search. The Braintrust automations doc URL was found but WebFetch was denied. Header name (e.g., `X-Braintrust-Signature`) and algorithm are unverified.

**Prevention:**
- Before implementing `verify_signature()`, manually check https://www.braintrust.dev/docs/guides/automations and https://www.braintrust.dev/docs/admin/automations/alerts for the exact header name and HMAC algorithm.
- Implement as optional (return `True` when secret is empty) — consistent with all existing adapters.
- If the header name cannot be confirmed before implementation, set `verify_signature()` to always return `True` (optional-only) and add a `# TODO: verify header name from docs` comment. Do NOT guess at the header name — a wrong header name will silently accept all requests without verification.

**Warning sign:** `verify_signature()` always passes in tests even when an incorrect signature is provided — check that the header name being read actually matches what Braintrust sends.

**Phase:** Phase implementing the Braintrust adapter — requires manual docs check before coding.

---

#### BRAINTRUST-3: `automation.event_type` Is Not the Same as `NormalizedEvent.event_type`

**What goes wrong:** The Braintrust payload has `automation.event_type` (e.g., `"logs"`) which is the *category of log data* the automation monitors, not a meaningful event classification for heartbeat-gateway. Using this directly as `NormalizedEvent.event_type` gives you `"logs"` for every Braintrust event, making pre_filter scoping impossible and HEARTBEAT.md entries unreadable.

**What the payload structure looks like (MEDIUM confidence):**
```json
{
  "automation": { "event_type": "logs", "name": "High-Priority Factuality", "btql_filter": "..." },
  "details": { "message": "5 logs triggered automation in the last 1 hour", "count": 5 }
}
```

**Prevention:**
- Derive `NormalizedEvent.event_type` from `automation.name` or construct it as `f"braintrust.{automation['event_type']}"` (e.g., `"braintrust.logs"`).
- More useful: derive from whether the BTQL filter contains scoring terms (`scores.` prefix in `btql_filter`) → `"eval.score_threshold"`, or use `automation.name` as a slug.
- The `condense()` method should use `automation["name"]` + `details["message"]` — these are human-readable and informative.

**Phase:** Phase implementing the Braintrust adapter.

---

### Arize Phoenix

#### PHOENIX-1: Phoenix Open-Source Almost Certainly Has No Webhook Support (Critical)

**What goes wrong:** You spend time designing and implementing an Arize Phoenix adapter, only to discover that Phoenix (the open-source, self-hosted version) does not currently send outbound webhooks for alerting. You are building an adapter for a feature that doesn't exist in the target deployment context.

**What the research found (MEDIUM confidence):** Arize *AX* (the hosted enterprise platform) has alerting integrations for Slack, OpsGenie, and PagerDuty — but these are programmatically managed via GraphQL, not outbound webhooks to arbitrary URLs. Arize Phoenix (open-source, https://github.com/Arize-ai/phoenix) is the LLM observability tool relevant to the target user (solo developer on a VPS). No search results returned Phoenix outbound webhook support. The Phoenix roadmap (https://github.com/orgs/Arize-ai/projects/45) was found but not readable via search results. Phoenix's documented capabilities are: tracing, evaluation, datasets, experiments, playground, prompt management — no alerting/notification webhooks were found.

**Consequence:** If Phoenix does not send webhooks, there is no "Arize Phoenix adapter" to build — there is no event source. Building it anyway creates a dead code path that will never trigger.

**Prevention:**
- Before writing any Phoenix adapter code, verify: does Phoenix (open-source) send outbound HTTP webhooks when eval scores drop, traces fail, or monitors trigger? Check https://arize.com/docs/phoenix and the GitHub issues/roadmap.
- If Phoenix does not send webhooks today but the feature is on the roadmap, document this as a planned stub adapter with a clear `# Not implemented — Phoenix webhook feature not yet released` in the code.
- If Phoenix only supports Slack/PagerDuty and not generic webhooks, the adapter cannot be built as-is. The milestone scope should be revised or replaced with a different adapter.
- Do not build a Phoenix adapter based on the assumption that it works like Arize AX (the hosted product). They are architecturally separate products.

**Warning sign:** If you cannot find a single example of a Phoenix webhook payload in docs, GitHub issues, or community posts, the feature likely doesn't exist yet.

**Phase:** Phase scoping — must be validated before any Phoenix adapter work begins. High probability this scope item needs to be replaced or deferred.

---

#### PHOENIX-2: Arize AX vs Arize Phoenix Confusion

**What goes wrong:** Documentation found via web search blends Arize AX (hosted, enterprise) and Arize Phoenix (open-source, self-hosted). You implement an adapter based on Arize AX's GraphQL-based alerting API, which requires API keys, GQL queries, and polling — none of which fit the webhook-ingest model of heartbeat-gateway.

**Prevention:**
- Always distinguish: "Arize AX" (hosted product, different from Phoenix), "Arize Phoenix" (open-source observability tool).
- heartbeat-gateway's target user runs Phoenix self-hosted on a VPS. The relevant docs are at `arize.com/docs/phoenix`, not `arize.com/docs/ax`.
- If an alert integration feature exists only in Arize AX (not Phoenix), it's out of scope for this adapter.

**Phase:** Phase scoping and adapter implementation.

---

### LangSmith

#### LANGSMITH-1: LangSmith Uses Static Headers for Auth, Not HMAC Signing

**What goes wrong:** You implement `verify_signature()` looking for an HMAC signature header and find nothing, then conclude verification is impossible and mark the adapter signature-optional. You're correct — but for the wrong reason. LangSmith's authentication model is static headers (Bearer token), not request signing. Understanding this distinction matters for documenting how operators configure security.

**What the research found (MEDIUM confidence):** LangSmith allows configuring "static headers to include with all outbound webhook requests, useful for authentication, routing, or passing metadata." The operator sets a bearer token or custom header in the LangSmith UI — LangSmith sends that header with every webhook delivery. There is no HMAC signing of the payload.

**Consequence for the adapter:** `verify_signature()` cannot verify a cryptographic signature because there is none. The operator's security model is: configure LangSmith to send `Authorization: Bearer <token>`, then verify that header matches the expected token on the receiving end. This is different from HMAC but still provides authentication.

**Decision required:** The adapter can either (a) implement a simple bearer-token check by reading a configured `Authorization` header value, or (b) implement as always-optional (return `True`). Option (a) is more useful but requires a different config field (`token` vs `secret`). Option (b) is consistent but leaves the endpoint open. Document the tradeoff and decide before coding.

**Warning sign:** Calling `hmac.new(secret.encode(), payload, hashlib.sha256)` in the LangSmith adapter — this produces a signature that LangSmith never sends, so the comparison will always fail when a secret is configured.

**Phase:** Phase implementing the LangSmith adapter.

---

#### LANGSMITH-2: LangSmith Webhook Payload Is a Run Object — Deeply Nested

**What goes wrong:** You expect a flat payload like PostHog's `{"type": "...", "project_id": "..."}`. Instead, LangSmith sends a full Run object with `kwargs` containing nested run data. `payload.get("type", "")` returns `""` and `normalize()` returns `None` for all events.

**What the payload structure looks like (MEDIUM confidence — from docs):**
```json
{
  "kwargs": {
    "run_type": "chain",
    "name": "ChatOpenAI",
    "inputs": { ... },
    "outputs": { ... },
    "error": null,
    "status": "success",
    "session_name": "my-project"
  },
  "values": { ... },
  "webhook_sent_at": "2024-01-15T14:00:00Z",
  "error": null
}
```

**Prevention:**
- `_classify()` must look at `payload.get("kwargs", {}).get("run_type", "")` and `payload.get("kwargs", {}).get("error")` to determine event type.
- A run with `error` non-null → `"run.failed"`. A run with `status == "success"` → probably `"run.completed"` (may be IGNORE depending on SOUL.md).
- The timestamp is `payload.get("webhook_sent_at", "")`, not a nested field.
- The `condense()` method should use `kwargs["name"]` + `kwargs["run_type"]` + `kwargs.get("session_name", "")` for a readable summary.
- Write the test fixture with the real nested structure, not a flat mock.

**Warning sign:** `normalize()` returning `None` for all LangSmith test fixtures — check whether `kwargs` is being accessed.

**Phase:** Phase implementing the LangSmith adapter.

---

#### LANGSMITH-3: LangSmith Sends Webhooks for Every Matching Run — Volume Risk

**What goes wrong:** An operator configures LangSmith automation rules to fire on all runs (default rule) and immediately floods heartbeat-gateway with hundreds of events per minute. The LLM classifier is called for each, running up costs. The dedup window (5 minutes, `payload_condensed`-based) may not catch volume spikes if each run has a unique name or session.

**Prevention:**
- The `_classify()` method should return `None` for `run_type` values that are not operationally interesting (`"retriever"`, `"embedding"`, `"prompt"`, `"parser"` may fire at high volume and produce little signal). Recommend only normalizing `"chain"` and `"tool"` run types with `error` non-null.
- Document in adapter docs that operators should configure narrow LangSmith automation rules (filter to runs with errors or specific projects).
- Pre-filter `ALWAYS_DROP` list for langsmith should include `"run.completed"` — only failures and feedback events should pass through.

**Phase:** Phase implementing the LangSmith adapter and pre_filter updates.

---

## Integration Risks

These pitfalls apply across all four new adapters and cut across schema, app.py wiring, and test isolation.

---

### INTEGRATION-1: Schema Registration — New Watch Config Models Must Be `BaseModel`, Not `BaseSettings`

**What goes wrong:** You add `AmplitudeWatchConfig`, `BraintrustWatchConfig`, `ArizePhoenixWatchConfig`, `LangSmithWatchConfig` as new nested config classes. If any of them inadvertently inherit from `BaseSettings` instead of `BaseModel`, they instantiate independently and bypass `GatewayConfig`'s `env_nested_delimiter` loading. All secrets silently become empty strings. No error is raised.

**Codebase evidence:** This was the root cause of the v0.2.0 security regression, documented in CLAUDE.md: "Nested models must be plain `BaseModel`. If you make them `BaseSettings`, they instantiate independently via `default_factory` and bypass `GatewayConfig`'s env loading entirely — all secrets silently become empty strings."

**Prevention:**
- Every new watch config class header must be `class AmplitudeWatchConfig(BaseModel):` — never `(BaseSettings)`.
- Add `model_config = {"extra": "ignore"}` consistent with existing watch configs.
- Add a regression test: set `GATEWAY_WATCH__AMPLITUDE__SECRET=test-secret` via `monkeypatch.setenv`, instantiate `GatewayConfig()`, assert `config.watch.amplitude.secret == "test-secret"`.
- Add each new config class to `WatchConfig` using `Field(default_factory=...)` — consistent with `linear`, `github`, `posthog` fields.

**Warning sign:** A test that sets an env var via `monkeypatch.setenv` but finds the config field is still empty string after `GatewayConfig()` instantiation — this is the v0.2.0 regression pattern.

**Phase:** All adapter phases — first task in each.

---

### INTEGRATION-2: `app.py` Wiring — Four New Adapters, Four New Routes, Eight New `app.state` Attributes

**What goes wrong:** You wire three of four new adapters but forget the fourth. Or you register `app.state.amplitude_adapter` but the route calls `getattr(state, "amplitude_adapter")` while the actual attribute was named `amplitude`. The error is a runtime `AttributeError` on first webhook delivery, not a startup error.

**Codebase pattern:** `app.py` uses `getattr(state, f"{source}_adapter")` where `source` is the URL path segment (e.g., `"/webhooks/amplitude"` → `source="amplitude"` → `state.amplitude_adapter`). The attribute name on `app.state` must be `{source}_adapter` exactly.

**Prevention:**
- Add `app.state.amplitude_adapter = AmplitudeAdapter(config)` etc. in `create_app()`.
- Add `@app.post("/webhooks/amplitude")` route that calls `_process_webhook(request, "amplitude")`.
- Add redirect alias `@app.post("/webhook/amplitude", include_in_schema=False)` → 308 to `/webhooks/amplitude`.
- Replicate the `require_signatures` check in `create_app()` for each new source — or consider whether the new adapters need to participate in that check at all (Amplitude cannot be verified; LangSmith uses bearer tokens).
- Integration test: POST to `/webhooks/amplitude` without adapter wired → catches `AttributeError` immediately.

**Phase:** All adapter phases — last task in each, after adapter implementation and tests pass.

---

### INTEGRATION-3: `pre_filter.py` — New Sources Need Explicit Scoping or They Scope Nothing

**What goes wrong:** You add four new adapter routes. None of the new sources have scoping logic in `pre_filter.py`. Every event from Amplitude, Braintrust, or LangSmith passes the pre-filter unconditionally and reaches the LLM classifier. If the operator did not intend to watch all Amplitude events, they have no way to scope them.

**Codebase pattern:** PostHog has `if event.source == "posthog": ... project_id scoping`. GitHub has repo and branch scoping. Linear has project_id scoping. New adapters without scoping logic are open-ended.

**Prevention:**
- Braintrust: scope by `automation.name` or `project.id`. Add `WatchConfig.braintrust.project_ids` and filter on `event.metadata["project_id"]`.
- LangSmith: scope by project (session_name) — add `WatchConfig.langsmith.projects`.
- Amplitude: scope by monitor name or project — add `WatchConfig.amplitude.project_id`.
- Arize Phoenix: defer until webhook support is confirmed.
- At minimum, add source-specific always-drop lists to `ALWAYS_DROP` in `pre_filter.py` for high-volume event types that should never reach the LLM.

**Phase:** Each adapter phase — pre_filter scoping should be implemented alongside the adapter, not deferred.

---

### INTEGRATION-4: Test Fixtures Must Reflect Real Payload Structure

**What goes wrong:** You write test fixtures using intuited field names (`{"event": "run.failed", "project": "my-project"}`) rather than the actual platform's payload schema. The adapter tests pass against these fake fixtures, but in production the real payloads have completely different structure and `normalize()` returns `None` for everything.

**Codebase evidence:** The PostHog fixture (`posthog_threshold_alert.json`) had to exactly match what PostHog actually sends, including the nested `insight` object and `threshold.value` sub-object. The `posthog.py` adapter contains:
```python
raw_threshold = payload.get("threshold")
threshold_value = raw_threshold.get("value") if isinstance(raw_threshold, dict) else raw_threshold
```
This `isinstance` guard exists because PostHog can send `threshold` as either a dict or a scalar — discovered only from real payload inspection.

**Prevention:**
- For each new adapter, find a real payload example in official docs before writing the fixture. If no official example exists, note it explicitly and mark the fixture as approximate.
- Write fixtures in `tests/fixtures/` as: `amplitude_monitor_alert.json`, `braintrust_automation_trigger.json`, `langsmith_run_failed.json`.
- Include a "drop" fixture for each adapter (e.g., `amplitude_test_delivery.json` with `charts: []`, `braintrust_test_delivery.json` with `is_test: true`) to verify the always-drop path.

**Phase:** Each adapter phase — fixture creation before adapter implementation.

---

### INTEGRATION-5: `condense()` Must Produce Stable, Deterministic Output for Dedup

**What goes wrong:** `condense()` includes a timestamp, run ID, or any value that changes between redeliveries of the same event. The dedup window in `writer.py` fingerprints on `payload_condensed`. If the fingerprint changes each time, duplicate entries are written to HEARTBEAT.md.

**Codebase evidence:** This was the exact production bug fixed in commit `d36ca0c` — LLM-generated titles were non-deterministic, causing every redelivery to create a duplicate entry. The fix moved the fingerprint to the deterministic adapter-generated `condense()` output.

**Prevention:**
- `condense()` for each new adapter must use only stable fields: project name, automation name, run name, alert name. Never include: timestamps, counts, IDs that change per delivery, LLM output.
- Specifically for Braintrust: use `automation["name"]` not `details["count"]` or `details["time_start"]` in the condensed string.
- Specifically for LangSmith: use `kwargs["name"]` + `kwargs["session_name"]` not `webhook_sent_at`.
- Test: call the adapter twice with the same payload but different timestamps — assert `condense()` returns identical strings both times.

**Phase:** Each adapter phase — verified during unit tests of `condense()`.

---

### INTEGRATION-6: PostHog Init Wizard Section — Answer Count Must Match Prompt Count

**What goes wrong:** Adding PostHog prompts to the `gateway init` wizard adds N new prompts to the ordered sequence. All existing `test_init.py` tests use `_HAPPY_PATH_ANSWERS` — a list where each entry corresponds to exactly one prompt in order. Adding PostHog prompts without updating `_HAPPY_PATH_ANSWERS` causes `next(answer_iter, ...)` to return the default for every PostHog prompt (empty string), silently producing an incomplete config.

**Codebase evidence:** `test_init.py` lines 67-85 show the ordered answer list. The comment explicitly lists 8 prompts by number. Adding PostHog prompts (likely: project_id + secret = 2 more prompts) means `_HAPPY_PATH_ANSWERS` needs exactly 2 new entries at the correct position in the list.

**Prevention:**
- Update `_HAPPY_PATH_ANSWERS` in `test_init.py` every time a prompt is added to `init.py`.
- Add a comment in `init.py` listing all prompts in order (as `test_init.py` already does for 8 prompts).
- Add a test that checks the final `.env` written by the wizard contains `GATEWAY_WATCH__POSTHOG__SECRET` and `GATEWAY_WATCH__POSTHOG__PROJECT_ID` — if the answer iterator ran out, these will be absent.

**Warning sign:** PostHog-related env vars are absent from the `.env` written in `test_wizard_happy_path` even though the PostHog prompts were added.

**Phase:** PostHog init wizard phase.

---

## Carry-Forward Issues from v0.3.0

Issues documented in the previous milestone that remain active constraints for v0.4.0 work.

### CARRY-1: `require_signatures` Check in `create_app()` Does Not Include PostHog (and Now 4 More Sources)

**What goes wrong:** `app.py` line 78-90 checks `config.watch.linear.secret` and `config.watch.github.secret` when `require_signatures=True`, but not `config.watch.posthog.secret`. Adding four new adapters that are also not in this check means the `require_signatures` enforcement is increasingly incomplete.

**Prevention:** When adding each new adapter, also add it to the `require_signatures` check in `create_app()`. PostHog was missed in v0.3.0 — catch it now. Amplitude is a special case (it has no signing) — it may need to be excluded from this enforcement by design.

**Phase:** All adapter phases.

---

### CARRY-2: `BaseModel` Nested Config Regression Is a Permanent Risk

The `BaseModel`-not-`BaseSettings` constraint must be verified for every new config class added. This has no automated guard in the codebase. If a future contributor adds a new nested watch config as a `BaseSettings` subclass — possibly by copy-pasting from some online Pydantic example — it will silently zero out all secrets for that adapter.

**Prevention:** Add a regression test to `test_app.py` or `tests/adapters/` that instantiates `GatewayConfig` from env vars and checks that all four new watch config secrets actually load. This test will catch the regression immediately.

**Phase:** All adapter phases — one test per new adapter.

---

### CARRY-3: Windows questionary Patch Pattern Must Be Followed for Any New Init Prompts

**What goes wrong:** A new prompt type is added to `init.py` (e.g., `questionary.select()` for choosing between Amplitude and Braintrust watching modes), but `_make_questionary_mocks()` in `test_init.py` only patches `questionary.text` and `questionary.password`. The new prompt type is not patched, causing tests to hang on Windows or fail with `prompt_toolkit` terminal errors.

**Codebase evidence:** `test_init.py` lines 8-12 document the explicit reason for patching: "questionary uses prompt_toolkit which requires Windows console APIs. On non-TTY environments (CliRunner, CI), we patch questionary.text and questionary.password."

**Prevention:**
- Any new questionary call type added to `init.py` must have a corresponding patch in `_make_questionary_mocks()` and `_TTY_PATCH`.
- If `questionary.select()` is added (e.g., for choosing which adapters to configure), add `_QUESTIONARY_SELECT = "heartbeat_gateway.commands.init.questionary.select"` and patch it.
- Do not add `questionary.confirm()` calls without patching.

**Phase:** PostHog init wizard phase (and any future init wizard work).

---

### CARRY-4: uv `.env` Auto-Loading Can Contaminate Integration Tests

**What goes wrong:** The project root contains a `.env` file with real credentials (ANTHROPIC_API_KEY, LINEAR secrets). When running `uv run pytest`, uv automatically loads the `.env` file into the environment. Integration tests that call `GatewayConfig()` without explicit env isolation will pick up these real credentials. Tests that assert `config.watch.linear.secret == ""` (testing the no-secret path) will fail because the real secret is present.

**Why this is v0.4.0 relevant:** Four new adapters each add new env vars. If a `.env` on the developer's machine contains `GATEWAY_WATCH__AMPLITUDE__SECRET`, tests that expect the empty-secret code path will fail locally but pass in CI.

**Prevention:**
- Adapter unit tests (`tests/adapters/test_amplitude.py` etc.) must use the `make_config()` pattern from `test_posthog.py`: construct `GatewayConfig` directly with explicit arguments, never call `GatewayConfig()` with no arguments in unit tests.
- Integration tests that need a clean config must use `monkeypatch.delenv("GATEWAY_WATCH__AMPLITUDE__SECRET", raising=False)` before calling `GatewayConfig()`.
- Follow the established `config` fixture in `test_integration.py` lines 27-30: always pass `workspace_path` and `soul_md_path` explicitly via `tmp_path`.

**Phase:** All adapter phases — consistent across all new adapter test files.

---

## Phase-Specific Warnings

| Phase / Topic | Pitfall | Mitigation |
|---------------|---------|------------|
| Amplitude adapter | No HMAC signing — secret config has no security effect | Document limitation; always-optional verification |
| Amplitude adapter | `charts` array wrapper — flat payload assumptions break | Access `payload["charts"][0]`, handle empty array |
| Amplitude adapter | `what_happened` is a sentence, not structured data | Store verbatim; do not parse numerics from it |
| Braintrust adapter | `is_test: true` payloads from save events | Return `None` from `normalize()` when `details.is_test == True` |
| Braintrust adapter | Signature header name unconfirmed | Check official docs before coding; do not guess header name |
| Braintrust adapter | `automation.event_type` is not a useful NormalizedEvent type | Derive event type from `automation.name` + error presence |
| Arize Phoenix adapter | Phoenix OSS may not support outbound webhooks | Verify webhook feature exists before writing any code |
| Arize Phoenix adapter | AX vs Phoenix product confusion in docs | Always check `arize.com/docs/phoenix`, not `arize.com/docs/ax` |
| LangSmith adapter | No HMAC — static Bearer token auth model | Consider bearer-token check instead of HMAC in `verify_signature()` |
| LangSmith adapter | Deeply nested `kwargs` wrapper | Access `payload["kwargs"]["run_type"]` not `payload["type"]` |
| LangSmith adapter | High delivery volume for all runs | Drop `run.completed` from pre_filter; only pass errors |
| All adapters | `BaseSettings` nested config regression | Every new config class must be `BaseModel`, not `BaseSettings` |
| All adapters | `app.py` wiring incomplete | Add adapter, route, state attribute, and require_signatures check |
| All adapters | Unstable `condense()` breaks dedup | Never include timestamps, IDs, or counts in condensed output |
| All adapters | Fake fixtures diverge from real payloads | Source fixtures from official docs examples before writing tests |
| PostHog init section | Answer count mismatch in test_init.py | Update `_HAPPY_PATH_ANSWERS` when adding new prompts |
| PostHog init section | New questionary prompt types not patched | Patch every new prompt type in `_make_questionary_mocks()` |
| All phases | uv .env auto-loading contaminates unit tests | Never call `GatewayConfig()` with no args in unit tests |

---

## Sources

**Codebase (HIGH confidence):**
- `heartbeat_gateway/adapters/posthog.py` — `isinstance(raw_threshold, dict)` guard pattern; optional HMAC pattern
- `heartbeat_gateway/app.py` — `getattr(state, f"{source}_adapter")` wiring pattern; `require_signatures` check
- `heartbeat_gateway/config/schema.py` — `BaseModel` vs `BaseSettings` constraint live in code
- `heartbeat_gateway/pre_filter.py` — `ALWAYS_DROP` dict structure; scoping pattern
- `tests/adapters/test_posthog.py` — `make_config()` pattern; `WatchConfig` direct construction
- `tests/cli/test_init.py` — questionary patching pattern; `_HAPPY_PATH_ANSWERS` ordering
- `heartbeat_gateway/CLAUDE.md` — BaseSettings regression docs; dedup fingerprint constraint; SOUL.md scope rules

**Amplitude (MEDIUM confidence):**
- [Webhooks for custom monitors — Amplitude Docs](https://amplitude.com/docs/admin/account-management/webhooks)
- [Security webhook for custom monitors — Amplitude Community](https://community.amplitude.com/data-instrumentation-57/security-webhook-for-custom-monitors-1506)
- [Allow secure credentials — Amplitude Community (feature request)](https://community.amplitude.com/ideas/allow-secure-credentials-to-be-specified-for-custom-webhook-url-1531) — confirms no HMAC signing as of research date

**Braintrust (MEDIUM confidence, signature details LOW confidence):**
- [Automations — Braintrust Docs](https://www.braintrust.dev/docs/guides/automations) — payload structure, `is_test` field, test delivery behavior

**LangSmith (MEDIUM confidence):**
- [Use webhooks — LangSmith Docs](https://docs.langchain.com/langsmith/use-webhooks) — static header auth model; `kwargs` wrapper structure; `webhook_sent_at` field
- [Webhook notifications — LangChain Changelog](https://changelog.langchain.com/announcements/set-up-webhook-notifications-for-run-rules) — run rule automation trigger

**Arize Phoenix (LOW confidence for webhook support status):**
- [Arize Phoenix GitHub](https://github.com/Arize-ai/phoenix) — no webhook notification feature found in documented capabilities
- [Alerting Integrations — Arize AX Docs](https://arize.com/docs/ax/observe/production-monitoring/alerting-integrations) — AX (not Phoenix) supports Slack, OpsGenie, PagerDuty — not generic webhooks
- [Arize Phoenix Roadmap](https://github.com/orgs/Arize-ai/projects/45) — found but not readable; may contain webhook plans

**General patterns (HIGH confidence from codebase):**
- `d36ca0c` commit referenced in CLAUDE.md — LLM-generated titles causing dedup failure; `payload_condensed` fix
- v0.2.0 BaseSettings regression documented in CLAUDE.md — direct codebase evidence
