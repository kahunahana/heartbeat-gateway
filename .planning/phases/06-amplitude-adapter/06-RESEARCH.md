# Phase 6: Amplitude Adapter - Research

**Researched:** 2026-04-04
**Domain:** Amplitude webhook adapter — no-signature passthrough, monitor_alert normalization, chart annotation normalization
**Confidence:** HIGH

## Summary

Phase 6 implements the Amplitude webhook adapter — the third and final new adapter in v0.4.0. The implementation pattern is well-understood: the codebase has two complete no-signature-verification predecessors (Braintrust and LangSmith) and a fully-established adapter skeleton. Amplitude is simpler than LangSmith (no multi-shape dispatch, no suppression logic) and nearly identical to Braintrust in its passthrough architecture.

The core engineering challenge is the monitor alert payload shape. Amplitude wraps alert data inside a `charts` array: `payload["charts"][0]["header"]` is the deterministic condensed string source. Using `what_happened` (the alternative field) is prohibited because it embeds a timestamp, which would break writer.py's dedup fingerprinting on redelivery.

The only novel piece compared to prior adapters is the `gateway doctor` warning: when `GATEWAY_REQUIRE_SIGNATURES=true` and `GATEWAY_WATCH__AMPLITUDE__SECRET` is set, doctor must warn the operator that the secret has no security effect. This is a surgical addition to `_check_hmac_secrets()` — it does NOT add Amplitude to the require_signatures enforcement block in `create_app()`.

**Primary recommendation:** Mirror the Braintrust adapter structure exactly. Two event branches (`monitor_alert` → ACTIONABLE candidate, `chart.annotation` → DELTA candidate), `None` fallthrough for unknowns. `condense()` uses `charts[0]["header"]`, not `what_happened`.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AMP-01 | `verify_signature()` always returns `True`; docstring states no-signing limitation and advises IP allowlisting | Established by STATE.md decision + Braintrust precedent; exact docstring wording pattern from braintrust.py |
| AMP-02 | Normalizes `monitor_alert` events — metric name, current value, threshold value → ACTIONABLE candidate | Amplitude payload shape confirmed from additional_context constraints; `charts` array access pattern prescribed |
| AMP-03 | Normalizes `chart.annotation` events — annotation text, chart name → DELTA candidate | Amplitude annotation webhook shape documented in constraints |
| AMP-04 | Returns `None` for unrecognized event types | Standard adapter pattern — all adapters end with `return None` |
| AMP-05 | `/webhooks/amplitude` route wired in `app.py`; `AmplitudeAdapter` registered in app state; pre-filter integration | `create_app()` pattern fully documented; `AmplitudeWatchConfig` already in schema.py (FOUND-01 complete) |
| AMP-06 | `gateway init` includes Amplitude section — secret prompt with no-signing warning displayed inline | Init wizard section pattern established; existing wizard structure in `commands/init.py` |
| AMP-07 | Unit tests + fixture JSON in `tests/fixtures/` + `docs/adapters.md` updated | Test file structure and fixture naming convention established from braintrust/langsmith |
</phase_requirements>

---

## Standard Stack

### Core (already installed — no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `fastapi` | existing | Route registration | Already in use |
| `pydantic` / `pydantic-settings` | existing | Config model (`AmplitudeWatchConfig`) | Already in schema.py — FOUND-01 complete |
| `questionary` | existing | Init wizard interactive prompts | Already used for all adapter sections |
| `click` | existing | CLI command structure | Already used |
| `pytest` | existing | Unit tests | Established test framework |

**No new dependencies required for Phase 6.**

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `datetime` / `timezone` | stdlib | Timestamp normalization | Amplitude monitor_alert payload may or may not include a timestamp field; fall back to `datetime.now(tz=timezone.utc)` |

**Installation:** None needed.

---

## Architecture Patterns

### Recommended Project Structure

```
heartbeat_gateway/adapters/amplitude.py     # New file — AmplitudeAdapter
tests/adapters/test_amplitude.py            # New file — unit tests
tests/fixtures/amplitude_monitor_alert.json # New fixture
tests/fixtures/amplitude_annotation.json    # New fixture
tests/fixtures/amplitude_unknown.json       # Optional — for drop test
```

Files modified:
```
heartbeat_gateway/__init__.py               # Add 'amplitude' to NormalizedEvent.source Literal
heartbeat_gateway/app.py                    # Import adapter, register state, add route, add to require_signatures exclusion comment
heartbeat_gateway/commands/init.py          # Add Amplitude section (checkbox + secret prompt with warning)
heartbeat_gateway/commands/doctor.py        # Add gateway doctor WARN when require_signatures=true + amplitude secret set
docs/adapters.md                            # Add Amplitude section
```

### Pattern 1: Permanent-Passthrough Adapter (Braintrust precedent)

**What:** `verify_signature()` always returns `True`, no HMAC logic, docstring explains why.
**When to use:** Platform sends no signature header (confirmed for Amplitude and Braintrust).

```python
# Source: heartbeat_gateway/adapters/braintrust.py (existing)
def verify_signature(self, payload: bytes, headers: dict) -> bool:
    """Always returns True. Amplitude does not sign webhook deliveries.
    Mitigation: restrict /webhooks/amplitude to Amplitude IP ranges via firewall rules."""
    return True
```

### Pattern 2: Two-branch normalize with charts array access

**What:** Dispatch on `event_type` field. `monitor_alert` branch accesses `payload.get("charts", [])` and extracts `charts[0]["header"]` for `condense()`. Returns `None` for empty charts array and unknown event types.

```python
def normalize(self, payload: dict, headers: dict) -> NormalizedEvent | None:
    event_type = payload.get("event_type", "")

    if event_type == "monitor_alert":
        charts = payload.get("charts", [])
        if not charts:
            return None
        # ... extract metric name, current value, threshold value from charts[0]
        return NormalizedEvent(
            source="amplitude",
            event_type="monitor_alert",
            payload_condensed=self.condense(payload),
            raw_payload=payload,
            timestamp=datetime.now(tz=timezone.utc),
            metadata=metadata,
        )

    if event_type == "chart.annotation":
        # ... extract annotation text, chart name
        return NormalizedEvent(
            source="amplitude",
            event_type="chart.annotation",
            payload_condensed=self.condense(payload),
            raw_payload=payload,
            timestamp=datetime.now(tz=timezone.utc),
            metadata=metadata,
        )

    return None  # AMP-04: drop unrecognized event types
```

### Pattern 3: condense() uses charts[0]["header"], not what_happened

**What:** `condense()` must use `charts[0]["header"]` as the deterministic summary field.
**Why:** `what_happened` embeds a timestamp string — every redelivery produces a different fingerprint, causing writer.py to create duplicate entries. This is the same dedup determinism constraint that was applied to Braintrust (`condense()` uses automation name not time/count fields — STATE.md decision 04-01).

```python
def condense(self, payload: dict) -> str:
    event_type = payload.get("event_type", "")
    if event_type == "monitor_alert":
        charts = payload.get("charts", [])
        header = charts[0].get("header", "") if charts else ""
        return f"Amplitude: monitor alert — {header}"[:240]

    if event_type == "chart.annotation":
        # ... use annotation text and chart name, not a timestamp field
        return f"Amplitude: [{chart_name}] annotation — {annotation_text}"[:240]

    return f"Amplitude: {event_type}"[:240]
```

### Pattern 4: NormalizedEvent.source Literal update

**What:** `heartbeat_gateway/__init__.py` must add `'amplitude'` to the `source` Literal.
**When:** Done in the same task that creates the adapter file (before route wiring).

Current Literal (from `__init__.py`):
```python
source: Literal["linear", "github", "posthog", "braintrust", "langsmith"]
```

Must become:
```python
source: Literal["linear", "github", "posthog", "braintrust", "langsmith", "amplitude"]
```

Note: LangSmith used `type: ignore` temporarily until Plan 02 updated this Literal. For Amplitude, both changes should happen in the same plan (no cross-plan dependency).

### Pattern 5: require_signatures exclusion in app.py

**What:** Amplitude must NOT be added to the `require_signatures` enforcement block — it cannot be enforced. Add a comment extending the existing exclusion explanation.

Current code in `create_app()`:
```python
# braintrust excluded from require_signatures — verify_signature is permanent passthrough
# langsmith excluded from require_signatures — verify_signature uses token header, not HMAC
```

Extend to:
```python
# braintrust excluded from require_signatures — verify_signature is permanent passthrough
# langsmith excluded from require_signatures — verify_signature uses token header, not HMAC
# amplitude excluded from require_signatures — verify_signature is permanent passthrough (no signing)
```

### Pattern 6: gateway doctor WARN for Amplitude + require_signatures

**What:** When `GATEWAY_REQUIRE_SIGNATURES=true` AND `config.watch.amplitude.secret` is non-empty, emit a `WARN` (not FAIL — there's no fix to enforce). This is a new check alongside the existing `_check_hmac_secrets()` or as a separate method.

The constraint from additional_context: "add `gateway doctor` warning when `GATEWAY_REQUIRE_SIGNATURES=true` and Amplitude secret is configured."

This is a WARN because the operator has done something harmless but misleading — they configured a secret they believe will secure Amplitude, but it has no effect. Doctor surfaces this misunderstanding.

```python
# In doctor.py _check_hmac_secrets() or as a new dedicated check:
if config.require_signatures and config.watch.amplitude.secret:
    results.append(
        CheckResult(
            name="Amplitude signature (no-op)",
            status=CheckStatus.WARN,
            message=(
                "GATEWAY_REQUIRE_SIGNATURES=true and GATEWAY_WATCH__AMPLITUDE__SECRET is set, "
                "but Amplitude does not sign webhook deliveries — the secret has no security effect"
            ),
            fix_hint=(
                "Restrict /webhooks/amplitude to Amplitude IP ranges via firewall rules instead. "
                "See docs/adapters.md#amplitude for details."
            ),
        )
    )
```

### Pattern 7: Init wizard Amplitude section

**What:** Add "Amplitude" to the checkbox choices and handle it with a no-signing warning + secret prompt (password-masked for consistency, even though it has no security effect).

Placement in checkbox: Alphabetical relative to existing choices. Current order: PostHog, Braintrust, LangSmith, Linear, GitHub. Amplitude would insert before Braintrust:

```
PostHog, Amplitude, Braintrust, LangSmith, Linear, GitHub
```

Or maintain the build-order convention (new adapters added after existing ones) — follow the pattern from LangSmith (05-03 decision: "LangSmith placed between Braintrust and Linear in checkbox — consistent with adapter build order"). Amplitude was built last, so it may follow LangSmith.

**Recommendation:** Add Amplitude before Braintrust (alphabetical). This is discretionary — the planner should pick one and be consistent.

```python
if "Amplitude" in selected_adapters:
    click.echo("")
    click.echo("  Amplitude webhook setup")
    click.echo("  Note: Amplitude does not sign webhook deliveries.")
    click.echo("  The secret below is stored for future use only — it is NOT verified.")
    click.echo("  Secure this endpoint with IP allowlisting instead.")
    click.echo("  Amplitude monitor alerts → /webhooks/amplitude")
    click.echo("")

    amplitude_secret = questionary.password(
        "Amplitude webhook secret (leave blank to skip):",
    ).ask()
    if amplitude_secret is None:
        raise SystemExit(1)
    if amplitude_secret.strip():
        answers["GATEWAY_WATCH__AMPLITUDE__SECRET"] = amplitude_secret.strip()
```

### Anti-Patterns to Avoid

- **Using `what_happened` in condense():** This field embeds a timestamp. Every redelivery produces a different fingerprint. Use `charts[0]["header"]` instead.
- **Adding Amplitude to `require_signatures` enforcement:** The `create_app()` block raises `ValueError` for unconfigured sources. Amplitude must never be added — it can never satisfy HMAC enforcement.
- **Accessing `charts[0]` without empty-array guard:** Amplitude can send `"charts": []`. Always guard: `charts = payload.get("charts", [])`, then `if not charts: return None` (or return a minimal event — see below).
- **Importing from app.py in doctor.py:** This constraint exists in doctor.py's module docstring. The Amplitude secret check must read from `config.watch.amplitude.secret` directly (config is already passed to `_check_hmac_secrets()`).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Timing-safe comparison | Custom string compare | `hmac.compare_digest` | Not needed here (passthrough), but don't add it unnecessarily either |
| Payload fixture construction | Inline dict in tests | JSON fixture file in `tests/fixtures/` | Established convention; all other adapters use fixture files |
| Webhook route | Custom FastAPI handler | `_process_webhook(request, "amplitude")` | Shared handler; adapter is looked up from `app.state` by source name |

---

## Common Pitfalls

### Pitfall 1: Empty charts array not guarded
**What goes wrong:** `charts[0]` raises `IndexError`; server returns 500 instead of graceful drop.
**Why it happens:** Amplitude may send `"charts": []` in some monitor configurations.
**How to avoid:** Always: `charts = payload.get("charts", [])` then check `if not charts:` before indexing.
**Warning signs:** Any test that doesn't pass an empty-charts fixture; 500 errors in smoke test.

### Pitfall 2: condense() uses what_happened
**What goes wrong:** Every webhook redelivery gets a unique fingerprint (timestamp embedded in `what_happened`). Writer creates duplicate HEARTBEAT entries.
**Why it happens:** `what_happened` looks like the "main summary" but is actually a human-readable sentence with embedded time.
**How to avoid:** Use `charts[0]["header"]` exclusively in condense(). This is the stable metric identifier.
**Warning signs:** Duplicate entries in HEARTBEAT.md after redelivering the same monitor alert payload.

### Pitfall 3: Adding 'amplitude' as NormalizedEvent.source without updating Literal
**What goes wrong:** `mypy`/type-checker error; ruff may flag it.
**Why it happens:** The LangSmith adapter was originally written with `type: ignore` because the Literal update was deferred to Plan 02. Amplitude should avoid this pattern — both changes belong in Plan 01.
**How to avoid:** Update `source` Literal in `__init__.py` in the same plan as creating `amplitude.py`.

### Pitfall 4: Amplitude not excluded from require_signatures enforcement
**What goes wrong:** When `GATEWAY_REQUIRE_SIGNATURES=true` and no amplitude secret is set, `create_app()` raises `ValueError` listing "amplitude" — but there is no secret that can be configured that would actually enable enforcement.
**Why it happens:** Copy-paste from Linear/GitHub checks without reading the exclusion comment.
**How to avoid:** Do not add amplitude to the `missing` list in `create_app()`. Only add the exclusion comment.

### Pitfall 5: Init wizard checkbox ordering inconsistency
**What goes wrong:** "Amplitude" appears in the wrong position, breaking the alphabetical or build-order convention.
**How to avoid:** Choose one convention and apply it. Existing: build-order (PostHog, Braintrust, LangSmith, Linear, GitHub). Amplitude was built last — append after LangSmith, before Linear is reasonable. Alternatively, full alphabetical: Amplitude, Braintrust, GitHub, LangSmith, Linear, PostHog. Either is acceptable; pick one.

---

## Code Examples

Verified patterns from existing codebase:

### Amplitude monitor_alert payload shape (from additional_context constraints)
```json
{
  "event_type": "monitor_alert",
  "charts": [
    {
      "header": "DAU Monitor - 2025-05-12",
      "body": "Current value: 850. Threshold: 1000.",
      "url": "https://analytics.amplitude.com/..."
    }
  ],
  "what_happened": "DAU Monitor crossed threshold at 2025-05-12T11:00:00Z"
}
```

Key fields:
- `payload.get("event_type")` — discriminator field
- `payload.get("charts", [])` — always guard for empty array
- `charts[0]["header"]` — stable metric identifier for condense(); do NOT use `what_happened`
- `charts[0].get("body", "")` — contains "Current value: X. Threshold: Y." — parse or store raw

### Amplitude chart.annotation payload shape (inferred from docs/AMP-03)
```json
{
  "event_type": "chart.annotation",
  "annotation": {
    "label": "Deploy v2.3.0",
    "description": "Production deployment"
  },
  "chart": {
    "name": "Daily Active Users"
  }
}
```

Key fields:
- `payload.get("annotation", {}).get("label", "")` — annotation text
- `payload.get("chart", {}).get("name", "")` — chart name

### Fixture file naming convention (from tests/fixtures/)
```
amplitude_monitor_alert.json     # AMP-02 test
amplitude_annotation.json        # AMP-03 test
amplitude_unknown.json           # AMP-04 test (optional — can use inline dict)
```

### Test class structure (mirroring test_braintrust.py)
```python
# Source: tests/adapters/test_braintrust.py (existing pattern)
from heartbeat_gateway.config.schema import AmplitudeWatchConfig, GatewayConfig, WatchConfig

def make_config(**amplitude_kwargs) -> GatewayConfig:
    return GatewayConfig(
        workspace_path=Path("/tmp"),
        soul_md_path=Path("/tmp/SOUL.md"),
        llm_api_key="test",
        watch=WatchConfig(amplitude=AmplitudeWatchConfig(**amplitude_kwargs)),
    )

class TestAmplitudeAdapterSignature:
    def test_verify_always_true_no_secret(self) -> None: ...
    def test_verify_always_true_with_any_headers(self) -> None: ...

class TestAmplitudeAdapterNormalize:
    def test_normalizes_monitor_alert(self, monitor_alert_payload) -> None: ...
    def test_empty_charts_returns_none(self) -> None: ...
    def test_normalizes_annotation(self, annotation_payload) -> None: ...
    def test_unrecognized_event_returns_none(self) -> None: ...

class TestAmplitudeAdapterCondense:
    def test_condense_uses_header_not_what_happened(self) -> None: ...
    def test_condense_le_240(self) -> None: ...
    def test_condense_deterministic(self) -> None: ...
```

### app.py route addition pattern (from existing routes)
```python
# Source: heartbeat_gateway/app.py (existing)
app.state.amplitude_adapter = AmplitudeAdapter(config)

@app.post("/webhooks/amplitude")
async def amplitude_webhook(request: Request):
    return await _process_webhook(request, "amplitude")

@app.post("/webhook/amplitude", include_in_schema=False)
async def redirect_amplitude():
    return RedirectResponse(url="/webhooks/amplitude", status_code=308)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| HMAC for all adapters | Passthrough for no-signing platforms (Braintrust, Amplitude) | Phase 4 (Braintrust) | Pattern established; Amplitude follows it |
| `type: ignore` on NormalizedEvent.source | Update Literal in same plan as adapter | Phase 5 LangSmith used workaround | Amplitude should do it cleanly in Plan 01 |
| Pre-checked adapter checkbox | Unchecked-by-default with empty-selection guard | Phase 4 smoke test (04-03) | Init wizard already correct; Amplitude checkbox entry must be unchecked by default |

**Deprecated/outdated:**
- `type: ignore` on `source="amplitude"` — the LangSmith workaround is no longer needed because the Literal update now happens in Plan 01 of each adapter's phase. Do not carry this forward.

---

## Open Questions

1. **Exact Amplitude monitor_alert payload field names for current value / threshold**
   - What we know: `charts` array wraps alerts; `charts[0]["header"]` is stable; `charts[0]["body"]` likely contains value and threshold as human-readable text.
   - What's unclear: Whether `charts[0]` has structured fields like `current_value` / `threshold_value` in addition to `body`, or whether these must be parsed from body text.
   - Recommendation: Design metadata to store `charts[0].get("body", "")` as a raw string (`metric_body`), plus `charts[0].get("header", "")` as `metric_header`. Do not attempt to parse numeric values from body text — store raw and let the classifier interpret.

2. **chart.annotation exact field structure**
   - What we know: AMP-03 requires annotation text and chart name in the NormalizedEvent.
   - What's unclear: Whether Amplitude uses `annotation.label` + `chart.name` or a flatter structure.
   - Recommendation: Build the fixture assuming the nested structure above. If smoke test shows a different shape, adjust. The fixture is the source of truth for this adapter since Amplitude's webhook docs are not deeply documented in Context7.

3. **Init wizard Amplitude placement in checkbox list**
   - What we know: Current list is PostHog, Braintrust, LangSmith, Linear, GitHub.
   - What's unclear: Whether to insert Amplitude alphabetically (before Braintrust) or at the end of the "new adapter" group (after LangSmith, before Linear).
   - Recommendation: Insert after LangSmith (build-order convention) — consistent with the STATE.md decision that placed LangSmith between Braintrust and Linear.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | `pyproject.toml` (pytest config present) |
| Quick run command | `uv run pytest tests/adapters/test_amplitude.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AMP-01 | verify_signature always returns True | unit | `uv run pytest tests/adapters/test_amplitude.py::TestAmplitudeAdapterSignature -x` | ❌ Wave 0 |
| AMP-02 | monitor_alert normalizes to NormalizedEvent with metadata | unit | `uv run pytest tests/adapters/test_amplitude.py::TestAmplitudeAdapterNormalize::test_normalizes_monitor_alert -x` | ❌ Wave 0 |
| AMP-03 | chart.annotation normalizes to NormalizedEvent | unit | `uv run pytest tests/adapters/test_amplitude.py::TestAmplitudeAdapterNormalize::test_normalizes_annotation -x` | ❌ Wave 0 |
| AMP-04 | unrecognized event returns None | unit | `uv run pytest tests/adapters/test_amplitude.py::TestAmplitudeAdapterNormalize::test_unrecognized_event_returns_none -x` | ❌ Wave 0 |
| AMP-05 | /webhooks/amplitude route returns 200 and processes event | unit (app) | `uv run pytest tests/test_app.py -x -k amplitude` | ❌ Wave 0 |
| AMP-06 | gateway init includes Amplitude section | unit (cli) | `uv run pytest tests/cli/ -x -k amplitude` | ❌ Wave 0 |
| AMP-07 | condense ≤240, deterministic, no timestamp in condensed | unit | `uv run pytest tests/adapters/test_amplitude.py::TestAmplitudeAdapterCondense -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/adapters/test_amplitude.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green + ruff clean before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/adapters/test_amplitude.py` — covers AMP-01, AMP-02, AMP-03, AMP-04, AMP-07
- [ ] `tests/fixtures/amplitude_monitor_alert.json` — covers AMP-02
- [ ] `tests/fixtures/amplitude_annotation.json` — covers AMP-03
- [ ] Route test additions to `tests/test_app.py` — covers AMP-05
- [ ] CLI test additions to `tests/cli/` — covers AMP-06

*(Framework install not needed — pytest already present)*

---

## Sources

### Primary (HIGH confidence)
- `heartbeat_gateway/adapters/braintrust.py` — passthrough verify_signature pattern, two-branch normalize, condense() dedup constraint
- `heartbeat_gateway/adapters/langsmith.py` — NormalizedEvent source Literal update timing pattern
- `heartbeat_gateway/app.py` — route wiring, require_signatures exclusion comment pattern, app.state registration
- `heartbeat_gateway/commands/init.py` — init wizard section structure, questionary.password usage, checkbox pattern
- `heartbeat_gateway/commands/doctor.py` — `_check_hmac_secrets()` structure for WARN addition
- `heartbeat_gateway/__init__.py` — NormalizedEvent Literal that needs 'amplitude' added
- `heartbeat_gateway/config/schema.py` — AmplitudeWatchConfig already defined (FOUND-01 complete)
- `.planning/STATE.md` — Amplitude verify_signature is permanent passthrough decision; condense() uses header not timestamp decision
- `.planning/REQUIREMENTS.md` — AMP-01 through AMP-07 spec

### Secondary (MEDIUM confidence)
- Phase additional_context constraints — monitor payload wraps alerts in `charts` array; `condense()` must use `charts[0]["header"]`; empty array must be handled; doctor warning when require_signatures + amplitude secret configured

### Tertiary (LOW confidence — needs fixture validation)
- Amplitude chart.annotation payload field structure — inferred from AMP-03 description; exact field names (`annotation.label`, `chart.name`) unconfirmed until smoke test

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all libraries already in use
- Architecture patterns: HIGH — two complete adapter precedents in the same codebase; pattern is mechanical
- Pitfalls: HIGH — all pitfalls derived from existing codebase decisions (STATE.md, commit history, CLAUDE.md)
- Amplitude payload shape: MEDIUM — `charts` array and `charts[0]["header"]` confirmed by constraints; exact sub-fields for annotation payload need smoke test validation

**Research date:** 2026-04-04
**Valid until:** 2026-05-04 (stable internal codebase; no external API dependency on Amplitude's SDK)
