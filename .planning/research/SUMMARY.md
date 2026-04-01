# Project Research Summary

**Project:** heartbeat-gateway v0.4.0 — Amplitude, Braintrust, LangSmith Adapter Expansion
**Domain:** Webhook gateway — LLM observability and product analytics adapters
**Researched:** 2026-03-31
**Confidence:** MEDIUM-HIGH

---

## Executive Summary

v0.4.0 expands heartbeat-gateway with three new webhook adapters — Amplitude, Braintrust, and LangSmith — plus a PostHog section in the `gateway init` wizard. Arize Phoenix has been confirmed out of scope: the open-source, self-hosted Phoenix product does not support outbound webhooks, confirmed independently by two parallel researchers across multiple sources. There is no Phoenix adapter to build. All three remaining platforms have real, documented webhook capabilities and integrate within the existing webhook-first architecture with no structural changes to the core pipeline (Adapter → PreFilter → Classifier → Writer).

The dominant implementation risk is authentication inconsistency across platforms. None of the three new adapters use the same auth model. Braintrust uses HMAC-SHA256 with a confirmed algorithm but an unconfirmed header name. LangSmith uses a static custom-header token with no HMAC computation. Amplitude signs nothing — its endpoint security is URL-only, and Amplitude engineering has confirmed no plans to change this. The existing `verify_signature` interface accommodates all three because the empty-secret passthrough already handles the no-signature case, but each adapter's documentation must set clear operator expectations. The Braintrust header name must be verified against live docs before `verify_signature` is coded — guessing silently breaks verification without raising errors.

The codebase pattern is well-established and tight. Each adapter adds one Python file and touches four existing files (`schema.py`, `app.py`, `pre_filter.py`, `commands/init.py`) plus a test file and two or more fixture JSON files. There are no architectural novelties for Braintrust or LangSmith. Amplitude has one structural quirk — its monitor payload wraps alerts in a `charts` array rather than a top-level `event_type` field — and LangSmith wraps the Run object under a `kwargs` key. Both are fully documented by research. Neither requires changes to the base class or pipeline.

---

## Key Findings

### Recommended Stack

No new dependencies are required. All three adapters are pure HTTP webhook integrations. The existing stack — FastAPI, pydantic, pydantic-settings, and Python stdlib `hmac`/`hashlib` — covers everything. The `WatchConfig` schema extension for each adapter follows the identical pattern used by Linear, GitHub, and PostHog. The critical constraint reinforced by this research is the `BaseModel`-not-`BaseSettings` requirement for all new `*WatchConfig` classes, which remains the highest-severity codebase-level risk.

**Core technologies (unchanged from v0.3.0):**
- FastAPI — route registration; adds four POST routes, no other changes
- pydantic-settings with `env_nested_delimiter="__"` — nested watch config loading via env vars
- Python stdlib `hmac` + `hashlib` — used for Braintrust HMAC verification; not used by Amplitude or LangSmith
- `questionary` — init wizard prompts; new sections follow the established patching pattern from v0.3.0

### Expected Features

**Must have (table stakes):**
- Amplitude `monitor.alert` — KPI threshold crossed; highest-value signal from Amplitude
- Braintrust `log.matched` — BTQL-filtered log automation fired; proxy for eval failures since Braintrust has no native eval-failure webhook
- Braintrust `is_test` suppression — every automation save fires a test payload; `normalize()` must return `None` when `details.is_test == true`
- LangSmith `run.error` — production run failed with an error; most common agent error signal
- LangSmith `alert.error_count` and `alert.feedback_score` — threshold-based batch alerting
- PostHog wizard section — existing adapter gets its missing init prompts (CARRY-1 fix)

**Should have (competitive):**
- Braintrust `prompt.deployed` — prompt version change in a named environment; useful for tracking model deployments
- LangSmith `alert.latency` — performance regression signal; classify as DELTA by default
- Amplitude `cohort.membership` — secondary payload type; classify as DELTA; recommend pre-filter drop unless SOUL.md specifically cares about cohort changes

**Defer to v2+:**
- Arize Phoenix adapter — confirmed no outbound webhook support in OSS product; no viable path within the webhook-first architecture
- LangSmith dataset change webhooks — confirmed gap against user expectation; LangSmith does not expose dataset changes as webhook events (see Gaps section)
- Amplitude Event Streaming adapter — high-volume raw events, not alert signals; violates webhook-first design intent
- Braintrust experiment/eval run webhooks — Braintrust does not expose these natively; only log-based BTQL filter automations fire webhooks

### Architecture Approach

The existing five-stage pipeline is unchanged. All three adapters integrate at the Adapter layer only. The `_process_webhook(request, source)` function in `app.py` uses `getattr(state, f"{source}_adapter")` — adapter state attribute names must match the source string exactly. No changes needed to classifier, writer, or MCP server. The `pre_filter.py` `ALWAYS_DROP` dict and per-source scoping blocks receive new entries for each adapter, following the established pattern.

**Files changed across v0.4.0:**

| File | Status | Changes |
|------|--------|---------|
| `heartbeat_gateway/config/schema.py` | Modified | +3 new WatchConfig subclasses, +3 fields on WatchConfig |
| `heartbeat_gateway/app.py` | Modified | +3 imports, +3 adapter instantiations, +3 routes, +3 redirects, +3 entries in require_signatures guard, PostHog added to guard |
| `heartbeat_gateway/pre_filter.py` | Modified | +3 ALWAYS_DROP entries, +3 scoping blocks |
| `heartbeat_gateway/commands/init.py` | Modified | +4 wizard sections (PostHog + 3 adapters), +8 prompts |
| `heartbeat_gateway/adapters/amplitude.py` | New | AmplitudeAdapter |
| `heartbeat_gateway/adapters/braintrust.py` | New | BraintrustAdapter |
| `heartbeat_gateway/adapters/langsmith.py` | New | LangSmithAdapter |
| `tests/adapters/test_amplitude.py` | New | |
| `tests/adapters/test_braintrust.py` | New | |
| `tests/adapters/test_langsmith.py` | New | |
| `tests/fixtures/amplitude_*.json` | New | min 2 fixtures |
| `tests/fixtures/braintrust_*.json` | New | min 2 fixtures |
| `tests/fixtures/langsmith_*.json` | New | min 2 fixtures |

No changes required to `base.py`, `classifier.py`, `writer.py`, `mcp_server.py`, or `classify.yaml`.

### Critical Pitfalls

1. **Braintrust `is_test: true` must return None from `normalize()`** — Every time an operator saves or updates a Braintrust automation, Braintrust sends a test payload with `details.is_test == true`. Failing to check this creates spurious HEARTBEAT.md entries on every UI save. Check `payload.get("details", {}).get("is_test", False)` as the first operation in `normalize()`. Fixture required: `braintrust_test_delivery.json` with `is_test: true`; must assert `normalize()` returns `None`.

2. **Amplitude `verify_signature` is a permanent passthrough — document it explicitly** — Amplitude confirmed they cannot send webhooks with credentials. The `verify_signature` method must return `True` regardless of whether a secret is configured, because Amplitude never sends a signature. Setting a secret in config would cause 401s on all incoming Amplitude events. The config field exists for symmetry and future compatibility only. The adapter docstring and wizard prompt must both state this limitation. Do not read an HMAC header that does not exist.

3. **Braintrust signature header name is unconfirmed — do not guess** — HMAC-SHA256 is confirmed (AIR release notes, July 2025). The exact header name is inferred as `x-braintrust-signature` from convention, not from verified docs. A wrong header name silently accepts all requests without verification. Before writing `verify_signature`, open `braintrust.dev/docs/guides/automations` and confirm the header name. If it cannot be confirmed, implement as passthrough with a `# TODO: verify header name from official docs` comment — do not ship a guessed header name.

4. **LangSmith payload nests under `kwargs` — flat payload assumptions break everything** — LangSmith automation rule webhooks wrap the Run object under a `kwargs` key. `payload.get("run_type", "")` returns empty string; `normalize()` returns None for all events. Access `payload.get("kwargs", {}).get("run_type", "")` and `payload.get("kwargs", {}).get("error")`. Write the fixture with the real nested structure before writing the adapter code.

5. **`BaseModel` not `BaseSettings` for all new WatchConfig classes** — All new `*WatchConfig` classes must inherit `BaseModel`, not `BaseSettings`. BaseSettings causes independent instantiation via `default_factory`, silently bypassing `GatewayConfig`'s env loading and zeroing all secrets. This is the v0.2.0 security regression pattern. Add a regression test for each adapter: set the env var via `monkeypatch.setenv`, instantiate `GatewayConfig()`, assert the secret loaded correctly.

6. **`condense()` must be deterministic — never include timestamps, counts, or run IDs** — The `writer.py` dedup fingerprint is `payload_condensed`. For Braintrust: use `automation["name"]`, not `details["count"]` or `details["time_start"]`. For LangSmith: use `kwargs["name"]` + `kwargs["session_name"]`, not `webhook_sent_at`. For Amplitude: use `charts[0]["header"]`, not `what_happened` (which embeds a timestamp). Two redeliveries of the same event must produce identical `condense()` output.

---

## Implications for Roadmap

### Resolved Build Order

Four researchers suggested conflicting orders. The synthesis is:

**Schema Foundation → Braintrust → LangSmith → Amplitude**

This matches the Architecture researcher's recommendation and is the order with the strongest rationale across all four files.

**Why Braintrust before LangSmith:** Braintrust has the most uniform payload envelope (`organization/project/automation/details` structure) and the most confirmed payload shape. It is the cleanest template for establishing fixture conventions. LangSmith is equally well-documented but has a structural novelty (`kwargs` nesting) that is easier to tackle after the first adapter baseline exists.

**Why LangSmith before Amplitude:** LangSmith's payload shapes (automation and alert) are confirmed from official docs. Its auth model (custom-header token, no HMAC) is unusual but simpler to implement correctly than Amplitude's no-auth-at-all limitation combined with a dual-shape payload (monitor alert vs cohort membership). Building Amplitude last means the infrastructure is proven before tackling its highest-complexity edge cases.

**Override of competing recommendations:** Stack (Braintrust first — adopted) and Architecture (same order — adopted) agree. Features (LangSmith first — overridden because Braintrust's uniform envelope is better as a first-adapter template). Pitfalls (Amplitude first because of no-HMAC — overridden because Amplitude is the most complex adapter and benefits from established infrastructure).

### Phase 1: Schema Foundation + PostHog Wizard

**Rationale:** Every adapter phase depends on config fields existing in `schema.py`. Bundling the PostHog wizard — which has no adapter code — saves a separate phase and fixes the CARRY-1 require_signatures gap that has been open since v0.3.0.
**Delivers:** Three new `*WatchConfig(BaseModel)` classes on `WatchConfig`; PostHog prompts in `gateway init`; PostHog entry in `require_signatures` guard; `_HAPPY_PATH_ANSWERS` in `test_init.py` updated.
**Avoids:** INTEGRATION-1 (BaseModel constraint), INTEGRATION-6 (wizard answer count mismatch), CARRY-1 (require_signatures gap), CARRY-3 (questionary patching for new prompt types).
**Files:** `schema.py`, `commands/init.py`, `app.py` (minor guard addition), `tests/cli/test_init.py`

### Phase 2: Braintrust Adapter

**Rationale:** Highest-confidence payload structure of the three new adapters. HMAC pattern is consistent with Linear/GitHub/PostHog, modulo the header name verification. Sets fixture and test structure baseline for subsequent phases.
**Delivers:** `BraintrustAdapter` with `log.matched` and `prompt.deployed` (update + delete) event types; pre-filter `project_ids` scoping (Linear-style list membership); `is_test` suppression in `normalize()`; Braintrust wizard section.
**Avoids:** BRAINTRUST-1 (`is_test` suppression), BRAINTRUST-2 (signature — requires pre-build header name verification), BRAINTRUST-3 (derive meaningful event_type from `automation.name`, not raw `automation.event_type` field), INTEGRATION-4 (real fixtures from official docs), INTEGRATION-5 (deterministic `condense()`).
**Pre-build gate:** Verify exact HMAC header name from `braintrust.dev/docs/guides/automations` before writing `verify_signature`. One URL lookup, not a research session.

### Phase 3: LangSmith Adapter

**Rationale:** Second adapter. Well-documented payload for both automation and alert shapes. Custom-header-token `verify_signature` (no HMAC computation) is the structural novelty — simpler to implement correctly than Braintrust's HMAC.
**Delivers:** `LangSmithAdapter` with `run.error`, `run.matched`, `alert.error_count`, `alert.latency`, and `alert.feedback_score` event types; pre-filter `project_names` scoping (Linear-style list membership); `run.completed` in `ALWAYS_DROP` to prevent volume flooding; LangSmith wizard section with `X-LangSmith-Token` header instruction.
**Avoids:** LANGSMITH-1 (static header auth, no HMAC), LANGSMITH-2 (`kwargs` nesting), LANGSMITH-3 (volume risk — `run.completed` in ALWAYS_DROP), INTEGRATION-5 (deterministic `condense()` using `kwargs["name"]` not `webhook_sent_at`).
**Operator instruction:** Direct operators to configure LangSmith's custom header feature to send `X-LangSmith-Token: <secret>`. Query-param auth (`?token=...`) is not recommended because the existing `_process_webhook` route architecture does not pass query params to `verify_signature`.

### Phase 4: Amplitude Adapter

**Rationale:** Most complex adapter: dual payload shapes (monitor alert and cohort membership), no auth signature, and the `what_happened` string-not-struct pitfall. Building it last means the infrastructure is proven and the test pattern is established.
**Delivers:** `AmplitudeAdapter` with `monitor.alert` and `cohort.membership` event types; `verify_signature` permanent passthrough with documented limitation; pre-filter `project_id` scoping (PostHog-style single-ID equality); Amplitude wizard section that explicitly notes Amplitude does not sign webhooks; `cohort.membership` in `ALWAYS_DROP` by default with documentation to remove if SOUL.md explicitly needs it.
**Avoids:** AMPLITUDE-1 (`verify_signature` passthrough — always returns `True`), AMPLITUDE-2 (`charts` array envelope — access `payload.get("charts", [])`, handle empty array), AMPLITUDE-3 (`what_happened` stored verbatim, not parsed for structured numerics).
**Note for `require_signatures` guard:** Amplitude should be excluded from the require_signatures enforcement because it cannot provide signatures. Add a `gateway doctor` warning when `GATEWAY_REQUIRE_SIGNATURES=true` and an Amplitude secret is configured — the configured secret has no security effect.

### Phase Ordering Rationale

- Schema must be Phase 1 because `app.py` adapter instantiation and `pre_filter.py` scoping both reference config fields that must exist at import time; schema changes are additive and do not affect existing behavior.
- PostHog wizard belongs in Phase 1 (not its own phase) because it touches only `init.py` and `test_init.py` — no overlap with any adapter file — and resolves a CARRY-1 debt.
- Braintrust before LangSmith because the `organization/project/automation/details` envelope is a cleaner template for establishing the fixture-first workflow before tackling `kwargs` nesting.
- LangSmith before Amplitude because LangSmith's payload is better documented and its auth model, while unusual, is simpler than Amplitude's no-auth-at-all combined with dual payload shapes.
- The `require_signatures` PostHog carry-forward (CARRY-1) is fixed in Phase 1 to prevent the gap from continuing to widen.

### Research Flags

Pre-build verification steps required (not full research phases):
- **Phase 2 (Braintrust):** Verify exact HMAC signature header name from `braintrust.dev/docs/guides/automations` before writing `verify_signature`. This is a single URL lookup.
- **Phase 3 (LangSmith):** Verify alert webhook and fleet webhook payload shapes match the FEATURES.md documentation before writing fixtures. The automation rule payload is confirmed; the alert shape needs one docs check against `docs.langchain.com/langsmith/alerts-webhook`.

Phases with standard patterns (no research needed):
- **Phase 1 (Schema + PostHog wizard):** Pure codebase work following the existing WatchConfig and wizard section patterns exactly.
- **Phase 4 (Amplitude):** Payload structure confirmed from multiple community sources; no-HMAC auth confirmed by Amplitude engineering. Fully specifiable from research.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | No new dependencies; existing stack confirmed sufficient via direct codebase read |
| Features | MEDIUM | Braintrust and LangSmith payload shapes confirmed from official docs; Amplitude monitor payload from community examples; cohort payload from official docs; Braintrust signature header LOW confidence |
| Architecture | HIGH | Codebase read directly by Architecture researcher; integration points fully specified; no structural pipeline changes needed |
| Pitfalls | MEDIUM-HIGH | Most pitfalls grounded in codebase evidence (v0.2.0 BaseSettings regression, dedup bug d36ca0c, test patterns); Braintrust header name and LangSmith auth mechanism are LOW confidence pending live verification |

**Overall confidence:** MEDIUM-HIGH for Braintrust and LangSmith; MEDIUM for Amplitude; HIGH for architecture and stack.

### Gaps to Address

- **Braintrust HMAC header name (blocker for Phase 2):** The exact header name for the HMAC signature is not confirmed. Must be looked up at `braintrust.dev/docs/guides/automations` before writing `verify_signature`. Do not guess. If the header cannot be confirmed, implement as passthrough with a TODO comment.

- **LangSmith fleet and alert webhook payloads (verify before Phase 3 fixtures):** The automation rule payload is confirmed. Fleet webhook and alert webhook shapes need one verification check against `docs.langchain.com/langsmith/fleet/webhooks` and `docs.langchain.com/langsmith/alerts-webhook` before writing test fixtures.

- **LangSmith dataset change webhooks — confirmed gap against user expectation:** Research from two independent researchers found no evidence that LangSmith exposes dataset changes as webhook events. GitHub issue langsmith-sdk#1516 ("Prompt Management Webhooks") suggests this feature set is still being expanded. This expectation should be flagged to the operator: dataset change notifications are not achievable via LangSmith webhooks as of 2026-03-31.

- **Amplitude `require_signatures` behavior decision:** When `config.watch.amplitude.secret` is set but Amplitude sends no signature, `verify_signature` must still return `True` (not `False`) to avoid breaking all incoming Amplitude events. The configured secret has no security effect. Recommendation: always return `True` for Amplitude regardless of config; add a `gateway doctor` warning when a secret is configured for Amplitude under `require_signatures=true`. Decide this explicitly before coding.

---

## Sources

### Primary (HIGH confidence)
- Heartbeat-gateway codebase (direct read) — `adapters/posthog.py`, `adapters/linear.py`, `app.py`, `pre_filter.py`, `config/schema.py`, `tests/cli/test_init.py`, `CLAUDE.md`
- Braintrust automations docs: https://www.braintrust.dev/docs/guides/automations — payload structure, `is_test` field, test delivery behavior
- LangSmith webhooks: https://docs.langchain.com/langsmith/webhooks — automation rule payload confirmed
- LangSmith alerts webhook: https://docs.langchain.com/langsmith/alerts-webhook — alert payload fields confirmed
- LangSmith run rules: https://docs.smith.langchain.com/observability/how_to_guides/rules — confirmed
- Amplitude community (no signing): https://community.amplitude.com/data-instrumentation-57/security-webhook-for-custom-monitors-1506 — confirmed by Amplitude engineering
- Arize Phoenix GitHub: https://github.com/Arize-ai/phoenix — confirmed no outbound webhooks in OSS product

### Secondary (MEDIUM confidence)
- Amplitude custom monitor webhook docs: https://amplitude.com/docs/admin/account-management/webhooks — monitor alert payload shape
- Amplitude cohort webhooks: https://amplitude.com/docs/data/destination-catalog/cohort-webhooks — cohort payload (HIGH confidence for this source)
- Amplitude community (payload fields): https://community.amplitude.com/data-instrumentation-57/getting-user-segment-labels-in-custom-monitor-webhook-1507
- LangSmith use-webhooks: https://docs.langchain.com/langsmith/use-webhooks — static header auth model, `kwargs` wrapper
- LangSmith changelog: https://changelog.langchain.com/announcements/set-up-webhook-notifications-for-run-rules — run rule webhook confirmed
- Braintrust alerts docs: https://www.braintrust.dev/docs/admin/automations/alerts — `environment_update` payload shape

### Tertiary (LOW confidence — needs live verification)
- Braintrust HMAC announcement: https://www.usebraintrust.com/air-release-notes (July 22, 2025) — confirms HMAC-SHA256 exists; header name unconfirmed
- Arize AX alerting integrations: https://arize.com/docs/ax/observe/production-monitoring/alerting-integrations — AX (not Phoenix OSS) webhook support; separate product, out of scope
- LangSmith langsmith-sdk GitHub issue #1516 — dataset/prompt management webhooks not yet available

---

*Research completed: 2026-03-31*
*Ready for roadmap: yes*
*Scope correction: Arize Phoenix deferred — OSS product confirmed no outbound webhook support. v0.4.0 scope is Amplitude + Braintrust + LangSmith adapters + PostHog wizard section only.*
