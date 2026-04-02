# Phase 4: Braintrust Adapter — Research

**Researched:** 2026-04-01
**Domain:** Braintrust automation webhooks, HMAC-SHA256 verification, FastAPI route registration, Click/questionary wizard extension
**Confidence:** MEDIUM — payload structure confirmed from official docs; HMAC header name is the critical unresolved item (documented below)

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BTST-01 | `BraintrustAdapter.verify_signature()` uses HMAC-SHA256; exact header name confirmed at build time from `braintrust.dev/docs/guides/automations` | **UNCONFIRMED** — see Critical Open Question below; the API schema has no `secret` field in webhook action config; HMAC support announced March 2026 but header name not yet in public docs |
| BTST-02 | `normalize()` returns `None` as first action when `payload.get("details", {}).get("is_test") == True` | Confirmed — `is_test` lives at `details.is_test` in logs event payload; must be first check |
| BTST-03 | Normalizes `logs` events with failing scores — score name, value, project name → ACTIONABLE | Confirmed — payload fields identified: `project.name`, `automation.btql_filter`, `details.message`, `details.count` |
| BTST-04 | Normalizes `environment_update` events — env name, change type → DELTA | Confirmed — payload fields: `details.environment.slug`, `details.action` ("update" or "delete") |
| BTST-05 | `/webhooks/braintrust` route wired in `app.py`; `BraintrustAdapter` registered; pre-filter integration | Follows identical pattern to PostHog: register in `create_app()`, add route, use `_process_webhook(request, "braintrust")` |
| BTST-06 | `gateway init` includes Braintrust section — secret prompt + BTQL automation setup instructions | Follows PostHog/Linear wizard pattern; checkbox gains "Braintrust" entry; BTQL example must be shown inline |
| BTST-07 | Unit tests + fixture JSON + `docs/adapters.md` updated | Follows test_posthog.py / test_github.py pattern exactly |
</phase_requirements>

---

## Summary

Phase 4 builds `BraintrustAdapter` — the first new adapter in v0.4.0. Braintrust sends webhooks from its automation system when BTQL-filtered log conditions match or when environment configs change. The payload has a clean, uniform envelope (`organization` / `project` / `automation` / `details`) that is consistent across event types.

The primary technical challenge for this phase is the **HMAC signature header name**, which is not yet documented in Braintrust's public API docs as of research date (2026-04-01). Braintrust's March 2026 release notes confirm HMAC signing support was added, but the specific HTTP header name and whether a `secret` field even appears in the automation config UI is not determinable from docs alone. This must be resolved by inspecting the live Braintrust UI before writing `verify_signature`.

Everything else is well-understood. The payload shapes are documented with concrete JSON examples. The `is_test` check is structurally straightforward — it lives at `details.is_test` and is `True` on every automation save. The adapter follows the established `WebhookAdapter` subclass pattern used by `PostHogAdapter` and `GitHubAdapter`. The wizard extension follows the `questionary.checkbox` pattern established in Phase 3. The route registration follows the exact template in `app.py`.

**Primary recommendation:** Before any code is written for BTST-01, check `braintrust.dev/docs/admin/automations/alerts` for a current "Signing" or "Security" section, OR create a test automation in the Braintrust UI and look for a signing secret field. If Braintrust does not provide webhook signing at all, `verify_signature` should be a permanent passthrough (same pattern as AmplitudeAdapter per AMP-01), with a docstring stating this explicitly and advising IP allowlisting as mitigation.

---

## Critical Open Question: HMAC Header Name

**Status: UNCONFIRMED — must resolve before writing `verify_signature`**

### What was found

- Braintrust's `docs/admin/automations/alerts.md` documents the webhook payload structure in full but contains **no mention** of signature verification, signing secrets, or authentication headers.
- The `create-project_automation` API schema shows webhook config accepts only `{ "type": "webhook", "url": "string" }` — **no `secret` or `signing_key` field** in the API schema.
- Braintrust AIR release notes (March 5, 2026) state: "Webhook integrations now support HMAC signature validation to provide stronger request authentication. Updated documentation is available to support webhook implementation." — but the referenced updated documentation is not yet indexed or publicly accessible as of research date.
- No third-party blog posts, GitHub code examples, or community discussion found that name the Braintrust webhook HMAC header.

### Possible outcomes

| Scenario | Probability | Implication for BTST-01 |
|----------|-------------|------------------------|
| HMAC feature exists, header is `X-Braintrust-Signature` or similar | MEDIUM | Use that header; verify with `hmac.compare_digest` |
| HMAC feature exists but secret is UI-only (not in API schema) | MEDIUM | May need UI inspection; header still unknown |
| HMAC feature is not yet available for `braintrust.dev` product (only for AIR platform) | MEDIUM | Permanent passthrough — same as AmplitudeAdapter |

### Resolution protocol

Before writing `verify_signature`:
1. Log in to `braintrust.dev`, navigate to a project → Configuration → Alerts → create/edit a webhook automation.
2. Check whether a "Signing Secret" or similar field appears in the webhook action config.
3. If yes: look for header documentation inline or in updated docs. The header is almost certainly `X-Braintrust-Signature` or `Braintrust-Signature` by naming convention.
4. If no signing field exists: implement `verify_signature` as a permanent passthrough identical to `AmplitudeAdapter`, with docstring noting no signing is available and advising IP allowlisting.

**Do not default to a header name guess.** A wrong header name causes all requests to be silently accepted without verification (same security failure mode as always returning `True` — but worse because it looks like it's checking).

---

## Standard Stack

### Core (all already present in pyproject.toml)

| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| FastAPI | current | Route registration | Follow existing `_process_webhook` pattern |
| Pydantic | v2 | Config model (`BraintrustWatchConfig`) | Already in schema.py — Phase 3 complete |
| `hmac` + `hashlib` | stdlib | HMAC-SHA256 signature verification | Same imports as `github.py` and `posthog.py` |
| questionary | current | Wizard prompts | `questionary.password()` for secret; same pattern as PostHog section |
| click | current | CLI echo for setup instructions | `click.echo()` for inline BTQL example |

### No new dependencies required

Phase 4 introduces zero new packages. All required libraries are already in the project.

---

## Architecture Patterns

### Adapter Class Structure

Follow `PostHogAdapter` exactly — it is the cleanest existing adapter template:

```python
# Source: heartbeat_gateway/adapters/posthog.py
import hashlib
import hmac
from datetime import datetime, timezone

from heartbeat_gateway import NormalizedEvent
from heartbeat_gateway.adapters.base import WebhookAdapter
from heartbeat_gateway.config.schema import GatewayConfig


class BraintrustAdapter(WebhookAdapter):
    def __init__(self, config: GatewayConfig) -> None:
        self.config = config

    def verify_signature(self, payload: bytes, headers: dict) -> bool:
        secret = self.config.watch.braintrust.secret
        if not secret:
            return True
        # TODO: replace "x-braintrust-signature" with confirmed header name
        sig = headers.get("x-braintrust-signature", "")
        expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, sig)

    def normalize(self, payload: dict, headers: dict) -> NormalizedEvent | None:
        # BTST-02: is_test check MUST be first action
        if payload.get("details", {}).get("is_test") is True:
            return None
        # ... event type dispatch
```

### Payload Envelope (confirmed from `braintrust.dev/docs/admin/automations/alerts.md`)

All Braintrust webhook payloads share this envelope:

```json
{
  "organization": { "id": "...", "name": "..." },
  "project":      { "id": "...", "name": "..." },
  "automation": {
    "id": "...",
    "name": "...",
    "description": "...",
    "event_type": "logs" | "environment_update",
    "btql_filter": "...",
    "interval_seconds": 3600,
    "url": "..."
  },
  "details": { /* varies by event_type */ }
}
```

### Log Alert Payload — `details` object

```json
{
  "is_test": false,
  "message": "High-Priority Factuality: 5 logs triggered alert in the last 1 hour",
  "time_start": "2025-05-12T10:00:00.000Z",
  "time_end":   "2025-05-12T11:00:00.000Z",
  "count": 5,
  "related_logs_url": "https://braintrust.dev/app/..."
}
```

**Key note:** `is_test: true` is sent on every automation save — it is not a real event. `normalize()` must return `None` immediately when `details.is_test is True`.

BTQL filter example that produces failing-score logs events: `metadata.priority = 0 AND scores.Factuality < 0.9`

The score name and value are NOT directly in the payload — they are embedded in the BTQL filter string in `automation.btql_filter`. To surface score name and value in the ACTIONABLE entry, extract from `automation.btql_filter` or use `details.message` as the human-readable summary.

### Environment Update Payload — `details` object

```json
{
  "environment": { "slug": "production" },
  "prompt":      { "id": "...", "slug": "summarizer" },
  "new_version": "v3.2.1",
  "action": "update"
}
```

**Key note:** Environment alerts have **no `is_test` field** — the Braintrust docs explicitly state testing is unavailable for environment alerts. Do not check `is_test` for `environment_update` events; it will simply be absent.

### Event Type Detection

```python
event_type = payload.get("automation", {}).get("event_type", "")
# "logs" → ACTIONABLE candidate
# "environment_update" → DELTA candidate
# anything else → return None
```

### `condense()` Implementation — Dedup Constraint

Per STATE.md constraint: **use `automation["name"]`, not `details["count"]` or `details["time_start"]`**.

```python
def condense(self, payload: dict) -> str:
    automation = payload.get("automation", {})
    project = payload.get("project", {})
    name = automation.get("name", "")[:40]
    project_name = project.get("name", "")[:30]
    event_type = automation.get("event_type", "")

    if event_type == "logs":
        count = payload.get("details", {}).get("count", "")
        return f"Braintrust: [{project_name}] '{name}' — {count} logs triggered"[:240]

    if event_type == "environment_update":
        env_slug = payload.get("details", {}).get("environment", {}).get("slug", "")
        action = payload.get("details", {}).get("action", "")
        return f"Braintrust: [{project_name}] env '{env_slug}' {action}"[:240]

    return f"Braintrust: [{project_name}] {event_type}"[:240]
```

### NormalizedEvent — `source` field

The `NormalizedEvent.source` field uses a `Literal` type in `__init__.py`:

```python
source: Literal["linear", "github", "posthog"]
```

**This Literal must be updated to include `"braintrust"`.** Without this, the dataclass will reject `source="braintrust"` at runtime. Update to:

```python
source: Literal["linear", "github", "posthog", "braintrust"]
```

### Route Registration in `app.py`

Follow the PostHog route pattern exactly:

```python
# In create_app():
from heartbeat_gateway.adapters.braintrust import BraintrustAdapter

app.state.braintrust_adapter = BraintrustAdapter(config)

@app.post("/webhooks/braintrust")
async def braintrust_webhook(request: Request):
    return await _process_webhook(request, "braintrust")

@app.post("/webhook/braintrust", include_in_schema=False)
async def redirect_braintrust():
    return RedirectResponse(url="/webhooks/braintrust", status_code=308)
```

### `gateway init` Wizard Extension

The checkbox in `init.py` must gain `"Braintrust"` as a selectable option. The Braintrust prompt section follows the PostHog pattern — masked password prompt + inline setup instructions.

```python
# Add to checkbox choices list (after "PostHog", before "Linear"):
questionary.Choice("Braintrust", checked=False),

# New section gated behind "Braintrust" in selected_adapters:
if "Braintrust" in selected_adapters:
    click.echo("")
    click.echo("  Braintrust automation setup")
    click.echo("  Create an alert automation in Braintrust:")
    click.echo("  Project → Configuration → Alerts → New Alert")
    click.echo("  Action: Webhook → URL: <your-gateway>/webhooks/braintrust")
    click.echo("  Example BTQL filter: metadata.priority = 0 AND scores.Factuality < 0.9")
    click.echo("")

    braintrust_secret = questionary.password(
        "Braintrust webhook signing secret (leave blank to skip):",
    ).ask()
    if braintrust_secret is None:
        raise SystemExit(1)
    if braintrust_secret.strip():
        answers["GATEWAY_WATCH__BRAINTRUST__SECRET"] = braintrust_secret.strip()
```

**Checkbox order:** PostHog, Braintrust, Linear, GitHub — add Braintrust after PostHog per phase-ordering convention (newest adapters appear first in the list per CONTEXT.md from Phase 3).

### Test Pattern — `test_braintrust.py`

Mirror `tests/adapters/test_posthog.py` exactly:

```python
# Source: established pattern from test_posthog.py
from heartbeat_gateway.adapters.braintrust import BraintrustAdapter
from heartbeat_gateway.config.schema import GatewayConfig, BraintrustWatchConfig, WatchConfig

def make_config(**braintrust_kwargs) -> GatewayConfig:
    return GatewayConfig(
        workspace_path=Path("/tmp"),
        soul_md_path=Path("/tmp/SOUL.md"),
        llm_api_key="test",
        watch=WatchConfig(braintrust=BraintrustWatchConfig(**braintrust_kwargs)),
    )
```

**Required test cases (BTST-07):**
1. `is_test: true` → `normalize()` returns `None` immediately
2. `logs` event → normalizes with project name, automation name, count
3. `environment_update` event → normalizes with env slug and action
4. Unrecognized `event_type` → `normalize()` returns `None`
5. Valid HMAC signature → `verify_signature()` returns `True`
6. Invalid HMAC signature → `verify_signature()` returns `False`
7. No secret configured → `verify_signature()` always returns `True`
8. `condense()` output is deterministic (same payload = same output, no timestamps)
9. `condense()` output ≤ 240 chars

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| HMAC comparison | `expected == actual` string comparison | `hmac.compare_digest()` — timing-safe |
| Secret-absent guard | Complex logic | `if not secret: return True` — established pattern in every adapter |
| Payload size limit | Custom check in adapter | Already enforced in `_process_webhook` (512 KB) |
| Event dedup | Custom dedup in adapter | `writer.py` handles dedup via `payload_condensed` fingerprint |

---

## Common Pitfalls

### Pitfall 1: `is_test` Check Not First
**What goes wrong:** `normalize()` processes the payload, creates a `NormalizedEvent`, and writes a HEARTBEAT entry for every automation save.
**Why it happens:** Developer puts event_type routing before the `is_test` guard.
**How to avoid:** BTST-02 requires `is_test` check as the absolute first line of `normalize()` — before any other logic.
**BTST-02 exact requirement:** `if payload.get("details", {}).get("is_test") is True: return None`

### Pitfall 2: Wrong Header Name for `verify_signature`
**What goes wrong:** Wrong header means `sig` is always empty string, and `hmac.compare_digest(expected, "")` always returns `False` → every request returns 401. OR developer hard-codes the wrong header and `verify_signature` silently returns `True` for all requests because nothing matches.
**Why it happens:** Header name is unconfirmed in docs.
**How to avoid:** Resolve the open question first. Do not use a guessed header name.

### Pitfall 3: `NormalizedEvent.source` Literal Not Updated
**What goes wrong:** `NormalizedEvent(source="braintrust", ...)` raises a Pydantic/dataclass type error at runtime.
**Why it happens:** `__init__.py` has `source: Literal["linear", "github", "posthog"]` — "braintrust" not in the Literal.
**How to avoid:** Update the Literal in `__init__.py` as part of BTST-05.

### Pitfall 4: `condense()` Using `details["count"]` or `details["time_start"]`
**What goes wrong:** Duplicate alert deliveries create duplicate HEARTBEAT entries because the dedup fingerprint changes with count or time window values.
**Why it happens:** Developer uses the most "informative" fields instead of stable fields.
**How to avoid:** STATE.md constraint is explicit — use `automation["name"]`, which is stable across all deliveries of the same alert condition.

### Pitfall 5: `environment_update` Checked for `is_test`
**What goes wrong:** Code path calls `payload.get("details", {}).get("is_test")` for env update events — not wrong, but Braintrust docs confirm `is_test` is absent for env updates. Test fixture must NOT include `is_test` to avoid masking this difference.
**Why it happens:** Developer applies identical `is_test` check to both event types without reading docs.
**How to avoid:** `is_test` check applies correctly to `logs` events. For `environment_update`, the field is simply absent — the `is True` comparison safely handles the `None` case.

### Pitfall 6: Test Init Wizard — `_HAPPY_PATH_ANSWERS` Not Updated
**What goes wrong:** Existing `test_init.py` tests fail because the answer count no longer matches after Braintrust section is added to the wizard.
**Why it happens:** `_HAPPY_PATH_ANSWERS` is positional — adding a prompt shifts all subsequent answers.
**How to avoid:** Update `_HAPPY_PATH_ANSWERS` to include Braintrust secret answer at the correct position. Checkbox default in `_make_questionary_mocks` must include `"Braintrust"` only if the test exercises the Braintrust section; existing tests that use `checkbox_answer=["GitHub"]` etc. are unaffected.

---

## Code Examples

### Complete `logs` Fixture JSON

```json
{
  "organization": {
    "id": "org-abc123",
    "name": "my-org"
  },
  "project": {
    "id": "proj-def456",
    "name": "production-eval"
  },
  "automation": {
    "id": "c5b32408-8568-4bff-9299-8cdd56979b67",
    "name": "High-Priority Factuality",
    "description": "Alert on factuality scores for priority logs",
    "event_type": "logs",
    "btql_filter": "metadata.priority = 0 AND scores.Factuality < 0.9",
    "interval_seconds": 3600,
    "url": "https://braintrust.dev/app/my-org/p/production-eval/configuration/alerts?aid=..."
  },
  "details": {
    "is_test": false,
    "message": "High-Priority Factuality: 5 logs triggered alert in the last 1 hour",
    "time_start": "2025-05-12T10:00:00.000Z",
    "time_end": "2025-05-12T11:00:00.000Z",
    "count": 5,
    "related_logs_url": "https://braintrust.dev/app/my-org/p/production-eval/logs?search=..."
  }
}
```

### `is_test` Fixture JSON (for BTST-02 test)

```json
{
  "organization": { "id": "org-abc123", "name": "my-org" },
  "project":      { "id": "proj-def456", "name": "production-eval" },
  "automation": {
    "id": "c5b32408-8568-4bff-9299-8cdd56979b67",
    "name": "High-Priority Factuality",
    "event_type": "logs"
  },
  "details": {
    "is_test": true,
    "message": "This is a test delivery",
    "time_start": "2025-05-12T10:00:00.000Z",
    "time_end": "2025-05-12T11:00:00.000Z",
    "count": 0,
    "related_logs_url": ""
  }
}
```

### `environment_update` Fixture JSON

```json
{
  "organization": { "id": "org-abc123", "name": "my-org" },
  "project":      { "id": "proj-def456", "name": "production-eval" },
  "automation": {
    "id": "d7e43519-9679-5cgg-0300-9dee67080c78",
    "name": "Production Environment Changes",
    "description": "Alert when production environment is updated",
    "event_type": "environment_update"
  },
  "details": {
    "environment": { "slug": "production" },
    "prompt":      { "id": "prompt-789", "slug": "summarizer" },
    "new_version": "v3.2.1",
    "action": "update"
  }
}
```

### HMAC Signing Pattern (if signing confirmed)

```python
# Source: established pattern from heartbeat_gateway/adapters/github.py
import hashlib
import hmac

def verify_signature(self, payload: bytes, headers: dict) -> bool:
    secret = self.config.watch.braintrust.secret
    if not secret:
        return True
    # Replace with CONFIRMED header name after UI inspection
    sig = headers.get("x-braintrust-signature", "")
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)
```

### Permanent Passthrough Pattern (if no signing available)

```python
# Source: REQUIREMENTS.md AMP-01 pattern — use if Braintrust confirms no webhook signing
def verify_signature(self, payload: bytes, headers: dict) -> bool:
    """Always returns True. Braintrust does not sign webhook deliveries.
    Mitigation: restrict /webhooks/braintrust to Braintrust IP ranges via firewall."""
    return True
```

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (current) |
| Config file | `pyproject.toml` (pytest section) |
| Quick run command | `uv run pytest tests/adapters/test_braintrust.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BTST-01 | HMAC valid sig → True; invalid → False; no secret → True | unit | `uv run pytest tests/adapters/test_braintrust.py::TestBraintrustAdapterSignature -x` | ❌ Wave 0 |
| BTST-02 | `is_test: true` → normalize() returns None immediately | unit | `uv run pytest tests/adapters/test_braintrust.py::TestBraintrustAdapterNormalize::test_is_test_returns_none -x` | ❌ Wave 0 |
| BTST-03 | `logs` event → ACTIONABLE with project name + score info | unit | `uv run pytest tests/adapters/test_braintrust.py::TestBraintrustAdapterNormalize::test_normalizes_logs_event -x` | ❌ Wave 0 |
| BTST-04 | `environment_update` event → DELTA with env slug + action | unit | `uv run pytest tests/adapters/test_braintrust.py::TestBraintrustAdapterNormalize::test_normalizes_environment_update -x` | ❌ Wave 0 |
| BTST-05 | Route returns 401 on invalid sig; 200 on valid | integration | `uv run pytest tests/test_app.py -k braintrust -x` | ❌ Wave 0 |
| BTST-06 | `gateway init` Braintrust section writes `GATEWAY_WATCH__BRAINTRUST__SECRET` | unit | `uv run pytest tests/cli/test_init.py -k braintrust -x` | ❌ Wave 0 |
| BTST-07 | condense() ≤ 240 chars; deterministic output; unknown event → None | unit | `uv run pytest tests/adapters/test_braintrust.py -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/adapters/test_braintrust.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green + `uv run ruff check .` + `uv run ruff format --check .` before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/adapters/test_braintrust.py` — covers BTST-01, BTST-02, BTST-03, BTST-04, BTST-07
- [ ] `tests/fixtures/braintrust_logs_failing_scores.json` — covers BTST-03
- [ ] `tests/fixtures/braintrust_is_test.json` — covers BTST-02
- [ ] `tests/fixtures/braintrust_environment_update.json` — covers BTST-04
- [ ] Integration test additions to `tests/test_app.py` — covers BTST-05 (route + 401)
- [ ] Init wizard test update in `tests/cli/test_init.py` — covers BTST-06 (`_HAPPY_PATH_ANSWERS` + checkbox)

---

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|------------------|-------|
| No Braintrust support | BraintrustAdapter in v0.4.0 | First LLM eval platform adapter |
| `source: Literal["linear", "github", "posthog"]` | Must add `"braintrust"` | `__init__.py` Literal update required |
| Checkbox: PostHog, Linear, GitHub | Add Braintrust (Phase 4) | Per Phase 3 CONTEXT.md constraint |

---

## Open Questions

1. **Braintrust HMAC Header Name (BLOCKER for BTST-01)**
   - What we know: HMAC support announced March 2026; API schema has no `secret` field in webhook action; the `BraintrustWatchConfig.secret` field exists in schema.py (Phase 3 complete)
   - What's unclear: The exact HTTP header name Braintrust sends the signature in; whether signing is opt-in via a UI-only field not in the API schema
   - Recommendation: Inspect live Braintrust UI before writing `verify_signature`. If no signing field exists: implement permanent passthrough with IP allowlisting docstring (same as AMP-01).

2. **Score Name/Value in ACTIONABLE Entry (BTST-03)**
   - What we know: The Braintrust payload does NOT have a structured `score_name` or `score_value` field — BTQL filter text is at `automation.btql_filter`
   - What's unclear: Whether to parse the BTQL string to extract score info, or surface `details.message` (which contains a human-readable summary) as the title
   - Recommendation: Use `details.message` as the primary ACTIONABLE title — it is human-readable, not machine-parsed. Parsing BTQL is fragile. The BTST-03 success criterion says "score name, value, and project name visible" — `details.message` satisfies this since it contains the automation name which encodes the score context.

---

## Sources

### Primary (HIGH confidence)
- `https://braintrust.dev/docs/admin/automations/alerts.md` — Full webhook payload structure for both `logs` and `environment_update` events; `is_test` field confirmed at `details.is_test`; envelope fields confirmed
- `heartbeat_gateway/adapters/posthog.py` — Reference implementation for adapter pattern
- `heartbeat_gateway/adapters/github.py` — Reference implementation for HMAC verification pattern
- `heartbeat_gateway/__init__.py` — `NormalizedEvent` dataclass; `source` Literal constraint
- `heartbeat_gateway/app.py` — Route registration pattern; `_process_webhook` shared handler

### Secondary (MEDIUM confidence)
- `https://braintrust.dev/docs/api-reference/projectautomations/create-project_automation.md` — Webhook action schema; confirms no `secret` field in API (MEDIUM: absence of evidence vs. evidence of absence)
- `https://www.usebraintrust.com/air-release-notes` (March 5, 2026) — HMAC support announced; no header name disclosed

### Tertiary (LOW confidence)
- WebSearch results confirming HMAC announced but no header name found in any public source

---

## Metadata

**Confidence breakdown:**
- Payload structure (envelope, logs, env_update fields): HIGH — confirmed from official docs
- `is_test` field location (`details.is_test`): HIGH — confirmed from official docs
- HMAC header name: NOT CONFIRMED — must resolve before BTST-01
- Adapter class structure: HIGH — established codebase pattern
- Route registration pattern: HIGH — directly reading `app.py`
- Wizard extension pattern: HIGH — directly reading `commands/init.py` + Phase 3 test patterns
- Test patterns: HIGH — directly reading `tests/adapters/test_posthog.py`

**Research date:** 2026-04-01
**Valid until:** 2026-05-01 (HMAC docs may appear sooner — check braintrust.dev/docs/admin/automations/alerts for new signing section before building)
