# Phase 1: CLI Foundation + gateway doctor — Research

**Researched:** 2026-03-25
**Domain:** Python CLI subcommand wiring (Click) + config validator (gateway doctor)
**Confidence:** HIGH — project-level research confirmed against direct codebase inspection

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CLI-01 | `heartbeat-gateway` bare invocation (no subcommand) continues to start the server | `invoke_without_command=True` on Click group + `ctx.invoke(serve)` pattern; confirmed against app.py `main()` |
| CLI-02 | Click added as explicit dependency in `pyproject.toml` | Click 8.3.1 confirmed present transitively via uvicorn/litellm; not in dependencies block — must add `click>=8.1.0` |
| CLI-03 | New `heartbeat_gateway/cli.py` entry point wires Click group; existing `app.py` untouched | New file only; pyproject.toml entry point changes from `heartbeat_gateway.app:main` to `heartbeat_gateway.cli:cli` |
| DOC-01 | `gateway doctor` runs all checks and exits 0 only if no FAIL-level issues | `sys.exit(1)` on any FAIL; WARN-only exits 0; tested with `CliRunner.result.exit_code` |
| DOC-02 | Each check carries a `fix_hint` string shown inline on failure | Check result tuple is `(passed: bool, message: str, fix_hint: str)`; tests assert `fix_hint != ""` for every FAIL |
| DOC-03 | Default output shows only WARN and FAIL; `--verbose` flag shows all checks | `@click.option("--verbose", is_flag=True)` on doctor command; DoctorRunner filters PASS results unless verbose |
| DOC-04 | Check — config loads without `ValidationError` | `try: GatewayConfig() except ValidationError as e:` — surfaces nested BaseSettings failure; integration test uses `monkeypatch.setenv` not mocked config |
| DOC-05 | Check — SOUL.md exists at configured path and is readable | `config.soul_md_path.exists() and os.access(config.soul_md_path, os.R_OK)` |
| DOC-06 | Check — Anthropic API key present and matches `sk-ant-` prefix format | `config.llm_api_key.startswith("sk-ant-")` — format validation, not just non-empty |
| DOC-07 | Check — HMAC secrets non-empty for each configured source | Linear and GitHub secrets checked; WARN (not FAIL) when empty unless `require_signatures=True` |
| DOC-08 | Check — Linear `project_ids` parseable as valid UUID format | Regex `^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$` against each entry in `config.watch.linear.project_ids` |
| DOC-09 | Check — body size limit is ≥ 512KB | `MAX_BODY_BYTES` is defined in `app.py`; doctor replicates the constant check — import the constant or hardcode 512*1024 |
| DOC-10 | Check — SOUL.md content linter warns if scoping patterns detected | Regex scan for UUID patterns and lines matching `repo:`, `branch:`, `project_id:` prefixes in SOUL.md content |
| DOC-11 | Doctor tests use `monkeypatch.setenv` + `CliRunner` — no mocked `GatewayConfig` | `runner.invoke(cli, ["doctor"], env={...})` or `monkeypatch.setenv` in pytest; at least one full-stack config load per check |
| DOC-12 | `gateway doctor` accepts `--env-file <path>` flag | `@click.option("--env-file", type=click.Path(exists=True))` passed to `load_dotenv` before `GatewayConfig()` construction |
</phase_requirements>

---

## Summary

Phase 1 installs the Click group dispatch layer and delivers a fully functional `gateway doctor` command. The foundation work is a one-time setup: create `heartbeat_gateway/cli.py`, update the pyproject.toml entry point from `heartbeat_gateway.app:main` to `heartbeat_gateway.cli:cli`, and declare all four new dependencies explicitly. From that point forward, every check in `gateway doctor` can be developed and tested independently.

The doctor command must survive its primary failure mode: giving users false confidence by checking presence instead of validity. Every check in this phase has a concrete validity criterion — not just "is the key set?" but "does the key start with `sk-ant-`?" and "does each UUID parse?" and "does the workspace path pass `os.access(path, os.W_OK)`?" The check result data structure — a tuple of `(passed, message, fix_hint)` — must be defined and enforced from the first check written. Once the structure is set, all 8+ checks follow the same pattern.

The testing discipline is the other critical constraint: tests must use `monkeypatch.setenv` and `CliRunner`, not mocked `GatewayConfig`. The reason is documented in CLAUDE.md: the v0.2.0 security regression occurred because `BaseModel` vs `BaseSettings` on nested models caused secrets to silently become empty strings. A test that bypasses real config loading cannot catch a regression of this type.

**Primary recommendation:** Wire the Click group first (Step 1), update pyproject.toml (Step 2), then build all doctor check logic (Step 3), then wire doctor into the group (Step 4). Never skip steps or combine them — each step is independently verifiable.

---

## Standard Stack

### Core (Phase 1 only)

| Library | Version | Purpose | Status in pyproject.toml |
|---------|---------|---------|--------------------------|
| `click` | `>=8.1.0` | Click group, `@click.command`, `@click.option`, `CliRunner` | Transitive via uvicorn/litellm — must become explicit |
| `rich` | `>=13.0.0` | `[OK]`/`[FAIL]`/`[WARN]` structured output, summary panel | Not present — add as explicit dependency |
| `python-dotenv` | `>=1.0.0` | `dotenv_values(path)` reads `.env` into plain dict without touching `os.environ` | Not present — add as explicit dependency |
| `questionary` | `>=2.0.0` | Needed by Phase 2 init wizard — declare now per STATE.md decision | Not present — add as explicit dependency |

All four are declared in Phase 1 per the STATE.md decision: "All four new deps (click, rich, questionary, python-dotenv) declared as explicit in pyproject.toml."

### Already Present (reuse directly)

| Library | Version | How Phase 1 Uses It |
|---------|---------|---------------------|
| `pydantic>=2.9.0` | in pyproject.toml | `ValidationError` caught by DOC-04 check |
| `pydantic-settings>=2.6.0` | in pyproject.toml | `GatewayConfig` (BaseSettings) loaded by doctor; `env_nested_delimiter="__"` is the critical behavior |
| `pytest>=8.3.0` | dev dependency | CliRunner-based tests, `monkeypatch.setenv` |

### Installation

```bash
# Add to pyproject.toml dependencies block, then:
uv sync
```

---

## Architecture Patterns

### Recommended Project Structure (new files only)

```
heartbeat_gateway/
├── cli.py                    # NEW: Click group + serve subcommand + doctor registration
├── commands/
│   ├── __init__.py           # NEW: empty package marker
│   └── doctor.py             # NEW: DoctorRunner + 8 check functions
├── app.py                    # UNCHANGED
└── config/
    ├── schema.py             # UNCHANGED
    └── loader.py             # UNCHANGED (load_config() already exists)

tests/
└── cli/
    ├── __init__.py           # NEW: empty package marker
    └── test_doctor.py        # NEW: CliRunner tests + monkeypatch.setenv
```

### Pattern 1: Click Group with invoke_without_command (CLI-01, CLI-03)

The existing `heartbeat-gateway` entry point currently points to `heartbeat_gateway.app:main`. After Phase 1 it must point to `heartbeat_gateway.cli:cli`. Bare `heartbeat-gateway` (no subcommand) must still start uvicorn.

```python
# heartbeat_gateway/cli.py
import click

@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """heartbeat-gateway — event-driven webhook gateway for AI agents."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(serve)


@cli.command()
def serve() -> None:
    """Start the uvicorn server (default when no subcommand given)."""
    import uvicorn
    uvicorn.run("heartbeat_gateway.app:create_app", factory=True, host="0.0.0.0", port=8080)
```

pyproject.toml change:

```toml
[project.scripts]
heartbeat-gateway = "heartbeat_gateway.cli:cli"       # was: heartbeat_gateway.app:main
heartbeat-gateway-mcp = "heartbeat_gateway.mcp_server:main"  # unchanged
```

### Pattern 2: DoctorRunner Check Data Structure (DOC-01, DOC-02)

Every check function returns a named tuple. The planner must enforce this structure for all 8+ checks — no exceptions.

```python
# heartbeat_gateway/commands/doctor.py
from dataclasses import dataclass
from enum import Enum

class CheckStatus(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"

@dataclass
class CheckResult:
    name: str
    status: CheckStatus
    message: str
    fix_hint: str = ""   # MUST be non-empty when status == FAIL
```

### Pattern 3: Doctor Command Wiring (DOC-01, DOC-03, DOC-12)

```python
# heartbeat_gateway/commands/doctor.py

import click
from heartbeat_gateway.config.loader import load_config

@click.command("doctor")
@click.option("--verbose", is_flag=True, help="Show all checks including passing ones.")
@click.option("--env-file", type=click.Path(exists=True), default=None,
              help="Path to .env file to load before checking config.")
def doctor(verbose: bool, env_file: str | None) -> None:
    """Run pre-flight config checks and report health status."""
    if env_file:
        from dotenv import load_dotenv
        load_dotenv(env_file, override=True)

    runner = DoctorRunner(verbose=verbose)
    results = runner.run()
    runner.print_results(results)
    failed = [r for r in results if r.status == CheckStatus.FAIL]
    raise SystemExit(1 if failed else 0)
```

### Pattern 4: Config Loading in Doctor (DOC-04)

The first check must attempt actual config construction via `GatewayConfig()`. This is the only way to catch the BaseSettings nested-model regression. Check functions receive the constructed config — they never call `GatewayConfig()` themselves.

```python
def check_config_loads() -> CheckResult:
    """DOC-04: Config loads without ValidationError."""
    from pydantic import ValidationError
    from heartbeat_gateway.config.schema import GatewayConfig
    try:
        config = GatewayConfig()
        return CheckResult(
            name="Config loads",
            status=CheckStatus.PASS,
            message="GatewayConfig loaded successfully",
        )
    except ValidationError as e:
        return CheckResult(
            name="Config loads",
            status=CheckStatus.FAIL,
            message=f"Config validation failed: {e.error_count()} error(s)",
            fix_hint=f"Check env vars. First error: {e.errors()[0]['loc']} — {e.errors()[0]['msg']}",
        )
```

### Pattern 5: CliRunner Tests with monkeypatch.setenv (DOC-11)

```python
# tests/cli/test_doctor.py
from click.testing import CliRunner
from heartbeat_gateway.cli import cli

def test_doctor_fails_when_api_key_missing(tmp_path, monkeypatch):
    """DOC-06: API key check fails when ANTHROPIC_API_KEY not set."""
    soul = tmp_path / "SOUL.md"
    soul.write_text("## Current Focus\nship it")
    monkeypatch.setenv("GATEWAY_WORKSPACE_PATH", str(tmp_path))
    monkeypatch.setenv("GATEWAY_SOUL_MD_PATH", str(soul))
    # deliberately NOT setting ANTHROPIC_API_KEY

    runner = CliRunner()
    result = runner.invoke(cli, ["doctor"], catch_exceptions=False)

    assert result.exit_code == 1
    assert "FAIL" in result.output
    # fix_hint must be present
    assert "ANTHROPIC_API_KEY" in result.output

def test_doctor_exits_0_with_valid_config(tmp_path, monkeypatch):
    """DOC-01: Exit 0 when all checks pass."""
    soul = tmp_path / "SOUL.md"
    soul.write_text("## Current Focus\nship it")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-api03-test")
    monkeypatch.setenv("GATEWAY_WORKSPACE_PATH", str(tmp_path))
    monkeypatch.setenv("GATEWAY_SOUL_MD_PATH", str(soul))

    runner = CliRunner()
    result = runner.invoke(cli, ["doctor"], catch_exceptions=False)

    assert result.exit_code == 0
```

### Pattern 6: Rich Output Formatting (DOC-03, MINOR-1 avoidance)

```python
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()

def print_results(results: list[CheckResult], verbose: bool) -> None:
    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    table.add_column("status", style="bold", width=6)
    table.add_column("name")
    table.add_column("message")

    failures = 0
    warnings = 0
    for r in results:
        if r.status == CheckStatus.FAIL:
            failures += 1
            table.add_row("[red][FAIL][/red]", r.name, r.message)
            if r.fix_hint:
                table.add_row("", "", f"[dim]Fix: {r.fix_hint}[/dim]")
        elif r.status == CheckStatus.WARN:
            warnings += 1
            table.add_row("[yellow][WARN][/yellow]", r.name, r.message)
        elif verbose:
            table.add_row("[green][ OK ][/green]", r.name, r.message)

    console.print(table)
    total = len(results)
    passed = total - failures - warnings
    console.print(f"{passed} passed, {warnings} warned, {failures} failed")
```

### Anti-Patterns to Avoid

- **Import app.py from cli.py or doctor.py:** Pulls in FastAPI, uvicorn, all adapters. Makes commands untestable. `doctor.py` imports only `config.schema` and `config.loader`.
- **Call GatewayConfig() inside individual check functions:** Config is loaded once at the `doctor` command level and passed to DoctorRunner. Individual check functions accept `config: GatewayConfig` as a parameter.
- **Mock GatewayConfig in tests:** Bypasses the BaseSettings loading path that caused the v0.2.0 regression. Use `monkeypatch.setenv` so config loads from actual env vars.
- **Exit 0 on FAIL:** Breaks `gateway doctor && systemctl start heartbeat-gateway`. Use `raise SystemExit(1 if failed else 0)` explicitly — do not rely on Click's default.
- **Fat cli.py:** All doctor logic lives in `commands/doctor.py`. `cli.py` imports and registers the command; it contains no check logic.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Structured terminal output with colors | ANSI escape code strings | `rich.console.Console` + markup | TTY detection, NO_COLOR, Windows terminal compatibility all handled |
| Reading .env file | Manual file parsing | `dotenv_values(path)` from `python-dotenv` | Returns plain dict without mutating `os.environ` — safe for a validator |
| CLI option parsing | argparse or manual sys.argv | Click decorators | Group/subcommand dispatch, auto-help, testing via CliRunner |
| UUID format validation | Custom string splitting | `re.match(UUID_V4_PATTERN, value)` | One regex, one line — no dependency needed here |

---

## Complete Check List (All 8+ Checks)

This is the definitive list for the planner to assign to tasks. Each check maps to one or more requirements.

| Check # | Name | Requirement | Status Level | Logic | fix_hint trigger |
|---------|------|-------------|--------------|-------|------------------|
| 1 | Config loads | DOC-04 | FAIL on ValidationError | `try: GatewayConfig()` in isolation first | Yes — show first error's field + message |
| 2 | API key format | DOC-06 | FAIL if missing/wrong prefix | `config.llm_api_key.startswith("sk-ant-")` | Yes — "Set ANTHROPIC_API_KEY=sk-ant-... in .env" |
| 3 | SOUL.md exists | DOC-05 | FAIL if missing | `config.soul_md_path.exists() and os.access(..., os.R_OK)` | Yes — "Create SOUL.md at configured path" |
| 4 | Workspace writable | (implied by DOC-09 intent) | FAIL if not writable | `config.workspace_path.is_dir() and os.access(..., os.W_OK)` | Yes — "Create directory or fix permissions" |
| 5 | Linear project IDs are UUIDs | DOC-08 | FAIL if non-UUID entries | Regex each entry in `config.watch.linear.project_ids` | Yes — UUID format + Cmd+K instruction |
| 6 | HMAC secrets non-empty | DOC-07 | WARN if empty; FAIL if `require_signatures=True` | `config.watch.linear.secret` and `config.watch.github.secret` | Yes — "Set GATEWAY_WATCH__LINEAR__SECRET in .env" |
| 7 | Body size limit | DOC-09 | FAIL if below 512KB threshold | Check `MAX_BODY_BYTES` constant: replicate `512 * 1024` as the expected minimum | Yes — explains regression |
| 8 | SOUL.md content linter | DOC-10 | WARN if scoping patterns found | Regex scan for UUID-like strings and `repo:` / `branch:` / `project_id:` prefixes in SOUL.md content | Yes — "Move scoping rules to pre_filter.py" |
| 9 | Require-signatures advisory | MINOR-3 from PITFALLS.md | WARN | `not config.require_signatures and (linear_secret_set or github_secret_set)` | No — advisory only |

**Note on Check 7 (DOC-09):** `MAX_BODY_BYTES` is defined in `app.py`. Doctor must NOT import from `app.py`. Either replicate the constant (`EXPECTED_MIN_BODY_BYTES = 512 * 1024`) in `doctor.py`, or move the constant to `config/schema.py` and import from there. Replication is simpler and avoids the app.py import constraint.

---

## Common Pitfalls

### Pitfall 1: Shallow Checks (CRITICAL-1)

**What goes wrong:** Check reports PASS because value is present, not because value is valid.
**Why it happens:** Presence check is three lines. Validity check requires knowing the format.
**How to avoid:** For every check, the test suite must include a "plausible but wrong" value case. `ANTHROPIC_API_KEY=my-real-key` (no sk-ant- prefix) must FAIL. `LINEAR__PROJECT_IDS=["not-a-uuid"]` must FAIL. `GATEWAY_WORKSPACE_PATH=/root` (read-only directory) must FAIL.
**Warning signs:** Test only has a "missing value" case and an "all good" case — no "present but invalid" case.

### Pitfall 2: FAIL Without fix_hint (CRITICAL-2)

**What goes wrong:** Doctor reports FAIL with no guidance. User doesn't know what to do.
**Why it happens:** Easy to forget the hint when writing check logic.
**How to avoid:** Enforce in tests: every FAIL branch must assert `result.fix_hint != ""`. Add a meta-test that iterates all check functions with failure inputs and verifies fix_hint.
**Warning signs:** Any FAIL output path that doesn't also output a "Fix:" line.

### Pitfall 3: Mocking GatewayConfig in Tests (MODERATE-2)

**What goes wrong:** Tests pass but real config loading bugs go undetected.
**Why it happens:** `monkeypatch.setenv` is slightly more setup work than mocking.
**How to avoid:** Use `monkeypatch.setenv` + `CliRunner` or `monkeypatch.setenv` + `runner.invoke(..., env={...})`. At minimum, the DOC-04 integration test must set `GATEWAY_WATCH__LINEAR__PROJECT_IDS=not-valid-json` and confirm doctor catches it.
**Warning signs:** Any test file that imports `from unittest.mock import patch` and patches `GatewayConfig`.

### Pitfall 4: Wrong Exit Code (MODERATE-1)

**What goes wrong:** Doctor exits 0 even when checks fail.
**Why it happens:** Click defaults to exit 0; `sys.exit` must be called explicitly.
**How to avoid:** Use `raise SystemExit(1 if failed else 0)` at the end of the doctor command. Test with `assert result.exit_code == 1` for failure cases.
**Warning signs:** Any CliRunner test that doesn't assert on `result.exit_code`.

### Pitfall 5: Importing app.py from CLI Commands

**What goes wrong:** `doctor.py` imports `from heartbeat_gateway.app import create_app`. Tests require a running FastAPI app to run at all.
**Why it happens:** MAX_BODY_BYTES lives in app.py and DOC-09 needs it.
**How to avoid:** Replicate the constant in doctor.py (`EXPECTED_MIN_BODY_BYTES = 512 * 1024`). Never import from app.py in commands/.
**Warning signs:** Any import of `heartbeat_gateway.app` in `cli.py` or `commands/`.

---

## Code Examples

### DOC-08: Linear UUID validation

```python
# heartbeat_gateway/commands/doctor.py
import re
UUID_V4_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)

def check_linear_project_ids(config: GatewayConfig) -> CheckResult:
    ids = config.watch.linear.project_ids
    if not ids:
        return CheckResult(
            name="Linear project IDs",
            status=CheckStatus.WARN,
            message="No Linear project IDs configured — all Linear events will pass pre-filter",
            fix_hint="Set GATEWAY_WATCH__LINEAR__PROJECT_IDS=[\"your-uuid\"] in .env",
        )
    invalid = [id_ for id_ in ids if not UUID_V4_RE.match(id_.strip().lower())]
    if invalid:
        return CheckResult(
            name="Linear project IDs",
            status=CheckStatus.FAIL,
            message=f"{len(invalid)} entry/entries are not valid UUID v4: {invalid[:2]}",
            fix_hint="In Linear: Cmd+K → 'Copy model UUID' on your project page. Format: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx",
        )
    return CheckResult(name="Linear project IDs", status=CheckStatus.PASS,
                       message=f"{len(ids)} valid UUID(s) configured")
```

### DOC-10: SOUL.md content linter

```python
UUID_PATTERN = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
SCOPE_PATTERN = re.compile(r"^\s*(repo:|branch:|project_id:)", re.MULTILINE)

def check_soul_md_content(config: GatewayConfig) -> CheckResult:
    path = config.soul_md_path
    if not path.exists():
        return CheckResult(name="SOUL.md content", status=CheckStatus.FAIL,
                           message="SOUL.md not found — skipping content check",
                           fix_hint=f"Create SOUL.md at {path}")
    content = path.read_text()
    warnings = []
    if UUID_PATTERN.search(content):
        warnings.append("UUID-like strings found — these belong in GATEWAY_WATCH__LINEAR__PROJECT_IDS, not SOUL.md")
    if SCOPE_PATTERN.search(content):
        warnings.append("Scoping directives found (repo:/branch:/project_id:) — these belong in pre_filter.py")
    if warnings:
        return CheckResult(
            name="SOUL.md content",
            status=CheckStatus.WARN,
            message="; ".join(warnings),
            fix_hint="Move scoping rules to pre_filter.py — SOUL.md is for priority/action rules only (see CLAUDE.md)",
        )
    return CheckResult(name="SOUL.md content", status=CheckStatus.PASS,
                       message=f"No scoping anti-patterns detected ({len(content)} chars)")
```

### DOC-04: Config loads integration test pattern

```python
# tests/cli/test_doctor.py — integration-level test that catches BaseSettings regression
def test_doctor_catches_malformed_linear_project_ids(tmp_path, monkeypatch):
    """DOC-11: monkeypatch.setenv must be used so real config loading is exercised."""
    soul = tmp_path / "SOUL.md"
    soul.write_text("## Current Focus\ntest")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-api03-test")
    monkeypatch.setenv("GATEWAY_WORKSPACE_PATH", str(tmp_path))
    monkeypatch.setenv("GATEWAY_SOUL_MD_PATH", str(soul))
    monkeypatch.setenv("GATEWAY_WATCH__LINEAR__PROJECT_IDS", "not-valid-json")

    runner = CliRunner()
    result = runner.invoke(cli, ["doctor"], catch_exceptions=False)

    # Doctor must catch the ValidationError from GatewayConfig() and report it as FAIL
    assert result.exit_code == 1
    assert "FAIL" in result.output
```

---

## Build Order (Strict)

This is the mandatory step sequence. Each step is independently verifiable before the next begins.

**Step 1: Create `heartbeat_gateway/commands/__init__.py` and `heartbeat_gateway/cli.py`**
- Wire Click group with `invoke_without_command=True`
- Add `serve` subcommand that calls `uvicorn.run(...)`
- Verify: `uv run heartbeat-gateway serve` starts server; `uv run heartbeat-gateway` (no args) also starts server
- Do NOT add doctor command yet

**Step 2: Update `pyproject.toml`**
- Change entry point: `heartbeat-gateway = "heartbeat_gateway.cli:cli"`
- Add four explicit dependencies: `click>=8.1.0`, `rich>=13.0.0`, `questionary>=2.0.0`, `python-dotenv>=1.0.0`
- Run `uv sync` — verify no resolution conflicts
- Verify: existing `heartbeat-gateway` behavior unchanged after reinstall

**Step 3: Create `heartbeat_gateway/commands/doctor.py` with all check logic**
- Define `CheckStatus`, `CheckResult`, `DoctorRunner`
- Implement all 9 checks (see Complete Check List above)
- Unit-test each check function in isolation (no CLI runner needed yet)
- Verify: each check returns correct status for pass/fail/warn cases

**Step 4: Wire doctor into `cli.py` and add `tests/cli/`**
- `from heartbeat_gateway.commands.doctor import doctor` and `cli.add_command(doctor)`
- Create `tests/cli/__init__.py` and `tests/cli/test_doctor.py`
- Write CliRunner tests using `monkeypatch.setenv`
- Verify: `uv run pytest tests/cli/` passes; `uv run heartbeat-gateway doctor --help` works

---

## Exact Files to Create/Modify

| File | Action | Content |
|------|--------|---------|
| `heartbeat_gateway/commands/__init__.py` | CREATE | Empty — package marker |
| `heartbeat_gateway/commands/doctor.py` | CREATE | `CheckStatus`, `CheckResult`, `DoctorRunner`, 9 check functions, `doctor` Click command |
| `heartbeat_gateway/cli.py` | CREATE | Click `cli` group, `serve` command, `doctor` command registration |
| `tests/cli/__init__.py` | CREATE | Empty — package marker |
| `tests/cli/test_doctor.py` | CREATE | CliRunner tests for all DOC-* requirements |
| `pyproject.toml` | MODIFY | Entry point + four new explicit dependencies |

**Files that must NOT be modified:** `heartbeat_gateway/app.py`, `heartbeat_gateway/config/schema.py`, `heartbeat_gateway/config/loader.py`

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.3.x |
| Config file | `pyproject.toml` — `[tool.pytest.ini_options]` with `testpaths = ["tests"]` |
| Quick run command | `uv run pytest tests/cli/ -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CLI-01 | Bare `heartbeat-gateway` starts uvicorn | unit (mock uvicorn.run) | `uv run pytest tests/cli/test_cli.py::test_bare_invocation_starts_server -x` | Wave 0 |
| CLI-02 | Click is explicit in pyproject.toml | static check (grep) | `uv run pytest tests/cli/test_cli.py::test_click_explicit_dependency -x` | Wave 0 |
| CLI-03 | cli.py entry point wires group; app.py untouched | unit | `uv run pytest tests/cli/test_cli.py::test_entry_point_is_cli -x` | Wave 0 |
| DOC-01 | Exit 0 only if no FAIL | unit | `uv run pytest tests/cli/test_doctor.py::test_exit_code_1_on_fail -x` | Wave 0 |
| DOC-02 | fix_hint non-empty on FAIL | unit | `uv run pytest tests/cli/test_doctor.py::test_fix_hint_present_on_every_fail -x` | Wave 0 |
| DOC-03 | Default hides PASS; --verbose shows all | unit | `uv run pytest tests/cli/test_doctor.py::test_verbose_flag -x` | Wave 0 |
| DOC-04 | Config ValidationError caught | integration | `uv run pytest tests/cli/test_doctor.py::test_doctor_catches_config_error -x` | Wave 0 |
| DOC-05 | SOUL.md exists check | unit | `uv run pytest tests/cli/test_doctor.py::test_soul_md_missing_fails -x` | Wave 0 |
| DOC-06 | API key format check | unit | `uv run pytest tests/cli/test_doctor.py::test_api_key_wrong_prefix_fails -x` | Wave 0 |
| DOC-07 | HMAC secrets check | unit | `uv run pytest tests/cli/test_doctor.py::test_hmac_secret_empty_warns -x` | Wave 0 |
| DOC-08 | UUID format validation | unit | `uv run pytest tests/cli/test_doctor.py::test_invalid_uuid_fails -x` | Wave 0 |
| DOC-09 | Body size limit check | unit | `uv run pytest tests/cli/test_doctor.py::test_body_size_check -x` | Wave 0 |
| DOC-10 | SOUL.md content linter | unit | `uv run pytest tests/cli/test_doctor.py::test_soul_md_uuid_pattern_warns -x` | Wave 0 |
| DOC-11 | Tests use monkeypatch.setenv, not mock | integration | `uv run pytest tests/cli/test_doctor.py::test_doctor_catches_malformed_project_ids -x` | Wave 0 |
| DOC-12 | --env-file flag loads specified file | unit | `uv run pytest tests/cli/test_doctor.py::test_env_file_flag -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/cli/ -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green (`uv run pytest` + `uv run ruff check .` + `uv run ruff format --check .`) before verification

### Wave 0 Gaps

All test files are new — none exist yet:

- [ ] `tests/cli/__init__.py` — empty package marker
- [ ] `tests/cli/test_cli.py` — covers CLI-01, CLI-02, CLI-03
- [ ] `tests/cli/test_doctor.py` — covers DOC-01 through DOC-12
- [ ] `heartbeat_gateway/commands/__init__.py` — empty package marker
- [ ] `heartbeat_gateway/commands/doctor.py` — implementation
- [ ] `heartbeat_gateway/cli.py` — implementation

No framework install needed — pytest 8.3.x already in dev dependencies.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `heartbeat-gateway = "heartbeat_gateway.app:main"` | `heartbeat-gateway = "heartbeat_gateway.cli:cli"` | Phase 1 | Enables subcommands; bare invocation preserved via `invoke_without_command` |
| No CLI subcommands | Click group with serve/doctor | Phase 1 | PG-2 closed |
| Click transitive-only | Click explicit in pyproject.toml | Phase 1 | Fragile dependency resolved |
| No output formatting library | `rich` for structured [OK]/[FAIL]/[WARN] | Phase 1 | Scannable output vs log-style noise |

---

## Open Questions

1. **Where does MAX_BODY_BYTES live for DOC-09?**
   - What we know: Currently defined in `app.py` as `MAX_BODY_BYTES = 512 * 1024`. Doctor cannot import from `app.py`.
   - What's unclear: Should the planner move this constant to `config/schema.py` (one source of truth) or replicate it in `doctor.py`?
   - Recommendation: Replicate as `EXPECTED_MIN_BODY_BYTES = 512 * 1024` in `doctor.py`. Moving it to schema.py is a larger refactor that risks touching app.py and breaking the phase constraint. Replication is safe, explicit, and documented in-code.

2. **Does `--env-file` (DOC-12) override or supplement the current environment?**
   - What we know: `python-dotenv`'s `load_dotenv(path, override=False)` supplements; `override=True` replaces existing env vars.
   - What's unclear: User intent when running `gateway doctor --env-file .env.staging` — probably wants staging values to take precedence.
   - Recommendation: Use `override=True` so the specified file's values win. Document in `--help` text.

---

## Sources

### Primary (HIGH confidence)

- `heartbeat_gateway/app.py` — current `main()` body; `MAX_BODY_BYTES = 512 * 1024`; confirmed app.py must not be imported
- `heartbeat_gateway/config/schema.py` — `GatewayConfig` fields, `AliasChoices` for `ANTHROPIC_API_KEY`, nested model structure, `env_nested_delimiter="__"`
- `heartbeat_gateway/config/loader.py` — `load_config()` is `return GatewayConfig()` — one line
- `pyproject.toml` — confirmed: no `click`, `rich`, `questionary`, `python-dotenv` in dependencies; entry point is `heartbeat_gateway.app:main`
- `tests/test_app.py` — existing `monkeypatch.setenv` pattern confirmed; `test_secrets_loaded_from_environment_variables` is the regression guard reference
- `.planning/research/ARCHITECTURE.md` — Click group pattern, build order, component boundary rules
- `.planning/research/STACK.md` — all four dependency justifications
- `.planning/research/PITFALLS.md` — all CRITICAL-* and MODERATE-* pitfalls, phase-specific warnings table
- `.planning/research/FEATURES.md` — complete check list, MVP recommendations, anti-features
- `.planning/REQUIREMENTS.md` — all CLI-* and DOC-* requirements verbatim
- `.planning/config.json` — `nyquist_validation: true` confirmed

### Secondary (MEDIUM confidence)

- `.planning/research/SUMMARY.md` — cross-cutting themes, phase ordering rationale, confidence assessment
- `CLAUDE.md` (project root) — BaseSettings nested-model constraint, SOUL.md scope rules, known product gaps

---

## Metadata

**Confidence breakdown:**

| Area | Level | Reason |
|------|-------|--------|
| Standard stack | HIGH | All four deps verified against pyproject.toml; Click 8.3.1 confirmed transitive |
| Architecture | HIGH | Codebase read directly; app.py:main() body confirmed; schema.py field names confirmed |
| Check implementations | HIGH | All check logic derived from actual config schema fields and CLAUDE.md constraints |
| Test patterns | HIGH | Existing `monkeypatch.setenv` pattern in tests/test_app.py confirms approach |
| Build order | HIGH | Derived from actual Click group dependency constraint |
| Pitfalls | HIGH | Grounded in v0.2.0 regression documented in CLAUDE.md and test_app.py regression guard |

**Research date:** 2026-03-25
**Valid until:** 2026-06-25 (stable APIs — Click 8.x, Rich 13+, pydantic-settings 2.x all stable)
