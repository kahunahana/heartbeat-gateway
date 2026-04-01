# Phase 3: Schema Foundation + PostHog Wizard — Research

**Researched:** 2026-04-01
**Domain:** Pydantic schema extension + questionary wizard refactor + pytest monkeypatching
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Adapter Checkbox — LOCKED**
- `gateway init` must present a `questionary.checkbox()` for adapter selection BEFORE running any adapter prompt sections
- Only show adapters whose prompt branches are fully implemented — no placeholders for future adapters
- After Phase 3: checkbox shows Linear, GitHub, PostHog
- After Phase 4: adds Braintrust. After Phase 5: adds LangSmith. After Phase 6: adds Amplitude.
- Unselected adapters are silently skipped — no prompts, no .env entries written for them
- User selects subset; wizard only runs those sections in order

**Help Link — LOCKED**
- After the checkbox (or at the end of the wizard), show:
  > "Don't see your adapter? https://github.com/kahunahana/heartbeat-gateway/blob/main/docs/adapters.md#adding-a-new-adapter"
- Source confirmed in CONTRIBUTING.md: adapter instructions live at `docs/adapters.md#adding-a-new-adapter`

**Wizard Refactor Scope — LOCKED**
- Existing Linear and GitHub prompt sections are NOT removed — they are gated behind the checkbox selection
- If user selects Linear → run existing Linear prompts. If not selected → skip.
- Same for GitHub and PostHog.
- Merge-by-default behavior (load existing .env values as prompt defaults) continues to apply per-adapter section

**PostHog Prompt Order — LOCKED**
- PostHog prompts run BEFORE the Linear section in the wizard sequence
- Checkbox order: PostHog, Linear, GitHub (or whatever makes UX sense — but PostHog before Linear)

**WatchConfig Inheritance — LOCKED**
- All three new classes (AmplitudeWatchConfig, BraintrustWatchConfig, LangSmithWatchConfig) inherit `BaseModel`, NOT `BaseSettings`
- Hard constraint — BaseSettings caused silent secret bypass in v0.2.0 regression

**Regression Tests — LOCKED**
- One regression test per new adapter: set env var via `monkeypatch.setenv`, instantiate `GatewayConfig()`, assert secret loaded correctly
- Test pattern: `monkeypatch.setenv` only, never mocked `GatewayConfig`

**Test Impact — LOCKED**
- `tests/cli/test_init.py` `_HAPPY_PATH_ANSWERS` must be updated to include PostHog answers
- All existing wizard tests must pass — the checkbox refactor cannot break existing Linear/GitHub test paths

### Claude's Discretion
- Exact questionary widget type for checkbox (questionary.checkbox vs questionary.select)
- Whether to show the adapter help link before or after the checkbox
- Internal function structure for the refactored init command
- Whether adapter sections are dispatched via a dict/registry or sequential if-branches

### Deferred Ideas (OUT OF SCOPE)
- Braintrust, LangSmith, Amplitude prompt sections — Phase 4/5/6 respectively
- Adapter ordering configurability — users cannot reorder the checkbox list in Phase 3
- "Skip all" / "Configure none" as explicit checkbox option — not required
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FOUND-01 | `WatchConfig` adds `AmplitudeWatchConfig` model — `secret` field (no-op for verification; exists for config symmetry; Amplitude does not sign webhooks) | Schema pattern confirmed from existing LinearWatchConfig/GitHubWatchConfig; BaseModel constraint verified |
| FOUND-02 | `WatchConfig` adds `BraintrustWatchConfig` model — `secret` field for HMAC-SHA256 verification | Same schema pattern; field name `secret` consistent with existing adapters |
| FOUND-03 | `WatchConfig` adds `LangSmithWatchConfig` model — `token` field for custom header auth (not HMAC) | Field name is `token` not `secret` — different from other adapters; env var will be `GATEWAY_WATCH__LANGSMITH__TOKEN` |
| FOUND-04 | `gateway init` wizard adds PostHog section — `project_id` + `secret` prompts before Linear section | PostHogWatchConfig already exists in schema.py with `project_id` and `secret` fields; env var names confirmed; wizard refactor pattern understood |
</phase_requirements>

---

## Summary

Phase 3 is a schema extension plus a wizard refactor. The schema side is straightforward: three new Pydantic BaseModel subclasses added to `schema.py`, then attached to `WatchConfig` via `Field(default_factory=...)`. The existing `PostHogWatchConfig` already exists and is fully wired — Phase 3 only adds it to the wizard prompts.

The wizard refactor is the more complex half. `commands/init.py` currently runs Linear and GitHub prompts unconditionally. Phase 3 inserts a `questionary.checkbox()` call that lets users select which adapters to configure, then gates each section behind the selection. The test mock strategy must be extended: `_make_questionary_mocks` in `test_init.py` does not currently handle `questionary.checkbox`, so a `_QUESTIONARY_CHECKBOX` patch target must be added.

The existing test suite (159 passed, 1 xfailed) runs clean. The checkbox refactor changes prompt count and order, which means `_HAPPY_PATH_ANSWERS` must gain PostHog answers and the mock infrastructure must handle the checkbox return value (a list, not a string). Existing tests that reference `_HAPPY_PATH_ANSWERS` directly will need updating to the new answer sequence.

**Primary recommendation:** Extend `_make_questionary_mocks` with a `mock_checkbox` function, add `questionary.checkbox` to the patch targets list, and include the checkbox answer (a list of adapter names) as the first item in `_HAPPY_PATH_ANSWERS`.

---

## Standard Stack

### Core (all already installed)

| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| pydantic | >=2.9.0 | BaseModel for new WatchConfig classes | Already in pyproject.toml |
| pydantic-settings | >=2.6.0 | GatewayConfig with env_nested_delimiter | Already in pyproject.toml |
| questionary | >=2.0.0 | Wizard prompts including checkbox | Already in pyproject.toml |
| python-dotenv | >=1.0.0 | dotenv_values + set_key for .env write | Already in pyproject.toml |
| click | >=8.1.0 | CLI group and command wiring | Already in pyproject.toml |

No new dependencies required for Phase 3.

**Installation:**
```bash
# No new installs — all dependencies already in pyproject.toml
```

---

## Architecture Patterns

### Existing schema.py Structure

The current `schema.py` is 61 lines. The pattern for all existing WatchConfig classes is identical:

```python
class LinearWatchConfig(BaseModel):
    model_config = {"extra": "ignore"}
    project_ids: list[str] = Field(default_factory=list)
    assignee_filter: str = "any"
    secret: str = ""

class WatchConfig(BaseModel):
    model_config = {"extra": "ignore"}
    linear: LinearWatchConfig = Field(default_factory=LinearWatchConfig)
    github: GitHubWatchConfig = Field(default_factory=GitHubWatchConfig)
    posthog: PostHogWatchConfig = Field(default_factory=PostHogWatchConfig)
```

Every nested class uses `model_config = {"extra": "ignore"}` and `Field(default_factory=ClassName)` in `WatchConfig`. This is the canonical pattern.

### Env Var Naming (CRITICAL — confirmed from CLAUDE.md and schema.py)

The pattern is `GATEWAY_WATCH__{ADAPTER_UPPER}__{FIELD_NAME}` using `env_nested_delimiter="__"`:

| Adapter | Field | Env Var |
|---------|-------|---------|
| linear | secret | `GATEWAY_WATCH__LINEAR__SECRET` |
| github | secret | `GATEWAY_WATCH__GITHUB__SECRET` |
| posthog | secret | `GATEWAY_WATCH__POSTHOG__SECRET` |
| posthog | project_id | `GATEWAY_WATCH__POSTHOG__PROJECT_ID` |
| amplitude | secret | `GATEWAY_WATCH__AMPLITUDE__SECRET` |
| braintrust | secret | `GATEWAY_WATCH__BRAINTRUST__SECRET` |
| langsmith | token | `GATEWAY_WATCH__LANGSMITH__TOKEN` |

Note: LangSmith uses `token` not `secret` per FOUND-03 — env var is `GATEWAY_WATCH__LANGSMITH__TOKEN`.

### PostHog: Already in schema.py

`PostHogWatchConfig` already exists in `schema.py` and is already wired in `WatchConfig`:

```python
class PostHogWatchConfig(BaseModel):
    model_config = {"extra": "ignore"}
    project_id: str = ""
    insight_ids: list[str] = Field(default_factory=list)
    secret: str = ""
```

The PostHog adapter (`adapters/posthog.py`) also already exists and uses `self.config.watch.posthog.secret` and `self.config.watch.posthog.project_id`. Phase 3 only needs to add the wizard prompts — no schema work for PostHog.

### New WatchConfig Classes Pattern

```python
# Source: schema.py existing pattern, verified against CLAUDE.md constraint
class AmplitudeWatchConfig(BaseModel):
    model_config = {"extra": "ignore"}
    secret: str = ""

class BraintrustWatchConfig(BaseModel):
    model_config = {"extra": "ignore"}
    secret: str = ""

class LangSmithWatchConfig(BaseModel):
    model_config = {"extra": "ignore"}
    token: str = ""  # NOT secret — per FOUND-03
```

Then in `WatchConfig`:
```python
class WatchConfig(BaseModel):
    model_config = {"extra": "ignore"}
    linear: LinearWatchConfig = Field(default_factory=LinearWatchConfig)
    github: GitHubWatchConfig = Field(default_factory=GitHubWatchConfig)
    posthog: PostHogWatchConfig = Field(default_factory=PostHogWatchConfig)
    amplitude: AmplitudeWatchConfig = Field(default_factory=AmplitudeWatchConfig)
    braintrust: BraintrustWatchConfig = Field(default_factory=BraintrustWatchConfig)
    langsmith: LangSmithWatchConfig = Field(default_factory=LangSmithWatchConfig)
```

### questionary.checkbox() API (verified from live library inspection)

```python
# Signature verified via uv run python -c "import questionary; help(questionary.checkbox)"
questionary.checkbox(
    message: str,
    choices: Sequence[str | Choice | dict],
    default: str | None = None,
    validate: Callable[[list[str]], bool | str] = lambda x: True,
    initial_choice: str | Choice | None = None,
    ...
) -> Question

# .ask() returns: list[str]  — the selected choice titles/values
# Example: ['PostHog', 'Linear', 'GitHub']
# Returns empty list [] if nothing selected
# Returns None if user presses Ctrl+C
```

### Wizard Refactor Pattern

Current init.py runs 8 prompts unconditionally. After refactor:

1. Core config prompts (unchanged — API key, workspace, soul_md, llm_model)
2. **NEW**: `questionary.checkbox()` — adapter selection — returns list of selected adapter names
3. **NEW**: Help link echoed (either here or after checkbox)
4. PostHog section — gated behind `"PostHog" in selected_adapters`
5. Linear section — gated behind `"Linear" in selected_adapters`
6. GitHub section — gated behind `"GitHub" in selected_adapters`

Dispatch pattern (Claude's discretion — sequential if-branches recommended over dict/registry for readability):

```python
selected_adapters = questionary.checkbox(
    "Which adapters do you want to configure?",
    choices=["PostHog", "Linear", "GitHub"],
).ask()
if selected_adapters is None:
    raise SystemExit(1)

click.echo(
    "  Don't see your adapter? "
    "https://github.com/kahunahana/heartbeat-gateway/blob/main/docs/adapters.md#adding-a-new-adapter"
)

if "PostHog" in selected_adapters:
    # ... posthog prompts
if "Linear" in selected_adapters:
    # ... existing linear prompts
if "GitHub" in selected_adapters:
    # ... existing github prompts
```

### Test Mock Infrastructure — CRITICAL FINDING

The existing `_make_questionary_mocks` in `test_init.py` patches only `questionary.text` and `questionary.password`. It does NOT handle `questionary.checkbox`. Adding checkbox requires:

1. A new patch target constant: `_QUESTIONARY_CHECKBOX = "heartbeat_gateway.commands.init.questionary.checkbox"`
2. `mock_checkbox` function added to `_make_questionary_mocks` (or a separate helper) that returns a mock Question whose `.ask()` returns a `list[str]`
3. The checkbox answer must be provided as the FIRST item in the answers sequence (before the 8 existing prompts), since checkbox is called before any adapter sections

Updated `_HAPPY_PATH_ANSWERS` after refactor (prompt order with checkbox):

```python
# Prompt order AFTER refactor (11 prompts total):
#   1. adapter selection (checkbox) → list
#   2. ANTHROPIC_API_KEY (password)
#   3. GATEWAY_WORKSPACE_PATH (text)
#   4. GATEWAY_SOUL_MD_PATH (text)
#   5. GATEWAY_LLM_MODEL (text)
#   6. POSTHOG_PROJECT_ID (text)
#   7. POSTHOG_SECRET (password)
#   8. LINEAR_SECRET (password)
#   9. LINEAR_PROJECT_IDS (text, UUID validate)
#  10. GITHUB_SECRET (password)
#  11. GITHUB_REPOS (text)
_HAPPY_PATH_ANSWERS = [
    ["PostHog", "Linear", "GitHub"],   # 1. adapter checkbox (list)
    "sk-ant-testkey",                   # 2. ANTHROPIC_API_KEY
    "/workspace",                       # 3. GATEWAY_WORKSPACE_PATH
    "/workspace/SOUL.md",              # 4. GATEWAY_SOUL_MD_PATH
    "claude-haiku-4-5-20251001",       # 5. GATEWAY_LLM_MODEL
    "ph-project-id-123",               # 6. POSTHOG_PROJECT_ID
    "phc_secret",                       # 7. POSTHOG_SECRET
    "my-linear-secret",                # 8. LINEAR_SECRET
    "550e8400-e29b-41d4-a716-446655440000",  # 9. LINEAR_PROJECT_IDS
    "my-github-secret",                # 10. GITHUB_SECRET
    "owner/repo",                       # 11. GITHUB_REPOS
]
```

Note: Core config prompts (API key, workspace, soul_md, llm_model) must come BEFORE the checkbox or AFTER — the CONTEXT.md says checkbox appears "BEFORE running any adapter prompt sections" but does not specify where relative to core config. Reasonable interpretation: core config first (it always applies regardless of adapter selection), then checkbox, then adapter sections.

**IMPORTANT:** The checkbox is a different question type than `text`/`password`. The `mock_checkbox` function must be patched separately at `questionary.checkbox`. It returns a mock whose `.ask()` returns `list[str]`, not `str`.

### Regression Test Pattern for New Schema Fields

```python
# From CLAUDE.md constraint — monkeypatch.setenv only, never mock GatewayConfig
def test_amplitude_config_loads_from_env(monkeypatch):
    monkeypatch.setenv("GATEWAY_WATCH__AMPLITUDE__SECRET", "amp-secret-xyz")
    config = GatewayConfig()
    assert config.watch.amplitude.secret == "amp-secret-xyz"

def test_braintrust_config_loads_from_env(monkeypatch):
    monkeypatch.setenv("GATEWAY_WATCH__BRAINTRUST__SECRET", "btst-secret-xyz")
    config = GatewayConfig()
    assert config.watch.braintrust.secret == "btst-secret-xyz"

def test_langsmith_config_loads_from_env(monkeypatch):
    monkeypatch.setenv("GATEWAY_WATCH__LANGSMITH__TOKEN", "ls-token-xyz")
    config = GatewayConfig()
    assert config.watch.langsmith.token == "ls-token-xyz"
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multi-select prompt | Custom ANSI checkbox UI | `questionary.checkbox()` | Already in dependencies; handles keyboard nav, terminal compat |
| Env var nested parsing | Manual `os.environ` parsing with `__` split | pydantic-settings `env_nested_delimiter="__"` | Already wired in GatewayConfig; adding fields to WatchConfig is sufficient |
| Atomic .env write | Custom file locking | `python-dotenv set_key()` | Already used in `_write_env()` |

**Key insight:** The schema pattern is so uniform that adding three new classes and three new `Field(default_factory=...)` lines is the entire schema work. The env var parsing is fully automatic via pydantic-settings once the fields exist.

---

## Common Pitfalls

### Pitfall 1: BaseSettings instead of BaseModel on nested classes
**What goes wrong:** GatewayConfig cannot load nested secrets from env vars — they become empty strings silently. This was the v0.2.0 regression.
**Why it happens:** `BaseSettings` subclasses instantiate independently via `default_factory` and bypass GatewayConfig's env loading.
**How to avoid:** Every new `*WatchConfig` class inherits `BaseModel`. Never `BaseSettings`. The regression tests catch this immediately if the wrong base is used.
**Warning signs:** `config.watch.amplitude.secret == ""` even when env var is set.

### Pitfall 2: Checkbox mock missing from test infrastructure
**What goes wrong:** Existing `_make_questionary_mocks` patches only `text` and `password`. When the refactored wizard calls `questionary.checkbox(...)`, the real questionary is called instead of a mock — which fails in non-TTY CliRunner.
**Why it happens:** The mock infrastructure was built before checkbox was needed.
**How to avoid:** Add `_QUESTIONARY_CHECKBOX` patch target and `mock_checkbox` alongside `mock_text` and `mock_password` in the setup helper. The checkbox answer (a list) must be consumed from the answers iterator before the text/password answers.
**Warning signs:** `AttributeError` or questionary prompt_toolkit errors in tests after refactor.

### Pitfall 3: _HAPPY_PATH_ANSWERS answer count mismatch
**What goes wrong:** Tests fail because the answer iterator is exhausted before all prompts complete, or has leftover answers, causing silent wrong-value bugs or `StopIteration`.
**Why it happens:** Changing prompt count or order without updating the answers list.
**How to avoid:** Add a comment block above `_HAPPY_PATH_ANSWERS` listing every prompt in order with its index. Update this comment alongside every answer list change.
**Warning signs:** `test_wizard_happy_path` exits 0 but `.env` has wrong values; or `next(answer_iter, default)` silently returns `default` for prompts that should have real values.

### Pitfall 4: PostHog .env prompts writing wrong env var names
**What goes wrong:** Wizard writes `GATEWAY_WATCH__POSTHOG__PROJECT_ID` but the field in PostHogWatchConfig is `project_id` — this should match. Risk is a typo in the key string.
**Why it happens:** Manual string construction of env var names.
**How to avoid:** Define env var name strings as constants at the top of init.py, or verify against schema.py field names. Test: after wizard run, check that `dotenv_values(".env")["GATEWAY_WATCH__POSTHOG__PROJECT_ID"]` exists.

### Pitfall 5: Checkbox answer is None on Ctrl+C — not an empty list
**What goes wrong:** `if "PostHog" in selected_adapters` raises `TypeError: argument of type 'NoneType' is not iterable`.
**Why it happens:** `questionary.checkbox(...).ask()` returns `None` when the user cancels (same behavior as `.text()` and `.password()`).
**How to avoid:** Always check `if selected_adapters is None: raise SystemExit(1)` immediately after `.ask()`. An empty list `[]` means user selected nothing — that is valid (skip all adapters).

---

## Code Examples

### Pattern 1: Adding a field to WatchConfig (verified from schema.py)
```python
# Source: heartbeat_gateway/config/schema.py — existing pattern
class AmplitudeWatchConfig(BaseModel):
    model_config = {"extra": "ignore"}
    secret: str = ""

# In WatchConfig:
amplitude: AmplitudeWatchConfig = Field(default_factory=AmplitudeWatchConfig)
```

### Pattern 2: questionary.checkbox() signature (verified from live library)
```python
# Source: uv run python -c "import questionary; help(questionary.checkbox)"
selected = questionary.checkbox(
    "Which adapters do you want to configure?",
    choices=["PostHog", "Linear", "GitHub"],
).ask()
# Returns: list[str] e.g. ['PostHog', 'Linear']
# Returns: None on Ctrl+C
# Returns: [] if user selects nothing and confirms
```

### Pattern 3: Mock checkbox in tests (extending existing test infrastructure)
```python
# Extend _make_questionary_mocks in tests/cli/test_init.py
_QUESTIONARY_CHECKBOX = "heartbeat_gateway.commands.init.questionary.checkbox"

def _make_questionary_mocks(monkeypatch, answers: list, checkbox_answers: list | None = None):
    # checkbox_answers: list of lists, one per checkbox() call
    checkbox_iter = iter(checkbox_answers or [])
    answer_iter = iter(answers)

    def mock_checkbox(message, choices, **kwargs):
        val = next(checkbox_iter, [c for c in choices])  # default: select all
        return _make_question(val)

    def mock_text(message, default="", validate=None):
        val = next(answer_iter, default or "")
        # ... validation as before
        return _make_question(val)

    def mock_password(message, validate=None):
        val = next(answer_iter, "")
        return _make_question(val)

    monkeypatch.setattr(_QUESTIONARY_CHECKBOX, mock_checkbox)
    monkeypatch.setattr(_QUESTIONARY_TEXT, mock_text)
    monkeypatch.setattr(_QUESTIONARY_PASSWORD, mock_password)
```

### Pattern 4: Regression test for schema env var loading
```python
# From CLAUDE.md: monkeypatch.setenv only, never mocked GatewayConfig
def test_amplitude_config_loads_from_env(monkeypatch):
    monkeypatch.setenv("GATEWAY_WATCH__AMPLITUDE__SECRET", "amp-secret-xyz")
    config = GatewayConfig()
    assert config.watch.amplitude.secret == "amp-secret-xyz"
```

---

## State of the Art

| Area | Current State | Notes |
|------|---------------|-------|
| PostHogWatchConfig | Already exists in schema.py | project_id, insight_ids, secret fields |
| PostHog adapter | Already exists and wired in app.py | No work needed |
| PostHog in wizard | Not yet added — Phase 3 deliverable | FOUND-04 |
| Amplitude/Braintrust/LangSmith schema | Not yet in schema.py | FOUND-01/02/03 |
| questionary checkbox in wizard | Not yet used | New in Phase 3 |
| Test mock for checkbox | Not yet in test_init.py | Must be added |

---

## Open Questions

1. **Where exactly does the checkbox appear relative to core config prompts?**
   - What we know: CONTEXT.md says checkbox appears "BEFORE running any adapter prompt sections"
   - What's unclear: Does "before adapter sections" mean before the entire wizard, or after core config (API key, workspace, etc.)?
   - Recommendation: Place checkbox AFTER core config (core config always applies), BEFORE any adapter sections. This matches UX convention: collect universal settings first, then let the user choose what to configure.

2. **Should `_make_questionary_mocks` be refactored or extended?**
   - What we know: The existing function signature takes a flat `answers: list` and dispatches by call order
   - What's unclear: Whether checkbox answers should be in the same flat list or a separate parameter
   - Recommendation: Separate `checkbox_answers` parameter (a list of lists) to avoid type ambiguity — checkbox returns `list[str]` while text/password return `str`. Keeping them in the same iterator would require the mock to detect type, which is fragile.

3. **Does adding new fields to WatchConfig break any existing tests?**
   - What we know: 159 tests pass currently. `WatchConfig` is instantiated in many tests via `GatewayConfig()`.
   - What's unclear: None — pydantic with `extra="ignore"` and `default_factory` means adding fields to WatchConfig is backward compatible. Existing tests pass even with new fields.
   - Recommendation: No concern here. Verified by the BaseModel + default_factory pattern.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` — `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/cli/test_init.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FOUND-01 | `GatewayConfig` loads `GATEWAY_WATCH__AMPLITUDE__SECRET` correctly | unit | `uv run pytest tests/test_schema.py::test_amplitude_config_loads_from_env -x` | ❌ Wave 0 |
| FOUND-02 | `GatewayConfig` loads `GATEWAY_WATCH__BRAINTRUST__SECRET` correctly | unit | `uv run pytest tests/test_schema.py::test_braintrust_config_loads_from_env -x` | ❌ Wave 0 |
| FOUND-03 | `GatewayConfig` loads `GATEWAY_WATCH__LANGSMITH__TOKEN` correctly | unit | `uv run pytest tests/test_schema.py::test_langsmith_config_loads_from_env -x` | ❌ Wave 0 |
| FOUND-04 | Wizard prompts for PostHog before Linear section | unit | `uv run pytest tests/cli/test_init.py::test_posthog_prompts_before_linear -x` | ❌ Wave 0 (new test in existing file) |
| FOUND-04 | Wizard happy path with PostHog answers passes | unit | `uv run pytest tests/cli/test_init.py::test_wizard_happy_path -x` | ✅ (update existing) |
| FOUND-04 | Checkbox selection gates adapter sections | unit | `uv run pytest tests/cli/test_init.py::test_checkbox_gates_adapters -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/cli/test_init.py tests/test_schema.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_schema.py` — covers FOUND-01, FOUND-02, FOUND-03 (regression tests for new WatchConfig fields)
- [ ] New test functions in `tests/cli/test_init.py` — covers FOUND-04 (PostHog wizard section, checkbox gating)
- [ ] No new framework install needed — pytest already configured

---

## Sources

### Primary (HIGH confidence)
- Direct file inspection: `heartbeat_gateway/config/schema.py` — confirmed existing WatchConfig pattern, PostHogWatchConfig existence
- Direct file inspection: `heartbeat_gateway/commands/init.py` — confirmed current wizard structure, 8-prompt sequence, section layout
- Direct file inspection: `tests/cli/test_init.py` — confirmed `_HAPPY_PATH_ANSWERS` structure (8 items), `_make_questionary_mocks` pattern, all 9 existing tests
- Direct file inspection: `heartbeat_gateway/adapters/posthog.py` — confirmed PostHog adapter accesses `config.watch.posthog.secret` and `config.watch.posthog.project_id`
- Live library inspection: `uv run python -c "import questionary; help(questionary.checkbox)"` — confirmed exact checkbox signature and return type
- Direct test run: `uv run pytest tests/cli/test_init.py -v` — 9 passed, confirmed baseline

### Secondary (MEDIUM confidence)
- PyPI questionary page + questionary readthedocs — confirmed checkbox returns `list[str]`, `None` on cancel
- questionary GitHub issue #49 — confirmed CliRunner + questionary requires patching, not stdin injection

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified as already installed; no new dependencies
- Schema pattern: HIGH — inspected directly from schema.py source
- Wizard structure: HIGH — inspected directly from commands/init.py source
- Test infrastructure: HIGH — inspected directly from test_init.py; confirmed live test run
- questionary checkbox API: HIGH — verified via live library help() output
- Pitfalls: HIGH for BaseModel constraint (documented in CLAUDE.md); HIGH for test mock gap (confirmed by inspection)

**Research date:** 2026-04-01
**Valid until:** 2026-05-01 (stable libraries, slow-moving codebase)
