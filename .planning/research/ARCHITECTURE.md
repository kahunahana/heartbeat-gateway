# Architecture Patterns: CLI Subcommands for heartbeat-gateway

**Domain:** Python CLI subcommands added to an existing FastAPI + Click project
**Researched:** 2026-03-25
**Overall confidence:** HIGH (Click 8.3.1 confirmed installed, codebase read directly)

---

## Current State

The existing entry point is:

```
pyproject.toml → heartbeat_gateway.app:main
```

`main()` in `app.py` is a plain Python function that calls `uvicorn.run(...)` directly. It has no Click decorators. There is no group, no command dispatch, no subcommand infrastructure.

Click 8.3.1 is available in the environment as a transitive dependency of uvicorn and litellm. It is not pinned as a direct dependency.

---

## Recommended Architecture

### One `gateway` CLI group, three subcommands

```
gateway (Click group — heartbeat_gateway/cli.py)
  ├── serve     → runs the existing uvicorn server (wraps current main())
  ├── doctor    → pre-flight config validator
  └── init      → interactive setup wizard
```

The existing `heartbeat-gateway` script entry point **must not break**. The cleanest way to preserve it while adding subcommands is:

1. Create `heartbeat_gateway/cli.py` as the new CLI home.
2. Move the current `main()` body into a `serve` subcommand inside `cli.py`.
3. Change `pyproject.toml` to point `heartbeat-gateway = "heartbeat_gateway.cli:cli"`.
4. The `cli` object is the Click group. `gateway serve` replaces the bare `heartbeat-gateway` call.

**No breaking change path:** If bare `heartbeat-gateway` (no subcommand) must still start the server, use `invoke_without_command=True` on the group and call `serve` by default. This is the safer path during a transition.

```python
@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    if ctx.invoked_subcommand is None:
        # preserve existing behavior: just run the server
        ctx.invoke(serve)
```

This pattern means `heartbeat-gateway` (no args) still starts uvicorn. `heartbeat-gateway doctor` and `heartbeat-gateway init` invoke subcommands. Zero regression.

---

## Directory Structure

```
heartbeat_gateway/
  cli.py                      ← NEW: Click group + serve/doctor/init registration
  commands/
    __init__.py               ← NEW: empty, makes it a package
    doctor.py                 ← NEW: gateway doctor logic
    init.py                   ← NEW: gateway init logic
  app.py                      ← UNCHANGED: create_app() and FastAPI logic
  config/
    schema.py                 ← UNCHANGED: GatewayConfig
    loader.py                 ← UNCHANGED: load_config()

tests/
  cli/
    __init__.py               ← NEW
    test_doctor.py            ← NEW
    test_init.py              ← NEW
```

The `commands/` subpackage keeps doctor and init logic out of `cli.py`, which becomes a thin dispatch layer. Each command module owns its own logic and imports only what it needs.

---

## Component Boundaries

| Component | File | Responsibility | Imports |
|-----------|------|---------------|---------|
| CLI group | `cli.py` | Entry point, Click group, subcommand registration | `commands.doctor`, `commands.init`, `app.main` |
| serve command | `cli.py` | Thin wrapper that calls `uvicorn.run(...)` | `uvicorn` |
| doctor command | `commands/doctor.py` | Loads config, runs checks, prints pass/fail | `config.schema`, `config.loader` |
| init command | `commands/init.py` | Interactive prompts, writes `.env` | `click`, `config.schema` |
| config loader | `config/loader.py` | Instantiates `GatewayConfig()` from env | `config.schema` |
| GatewayConfig | `config/schema.py` | Pydantic-settings config model | pydantic |

**Key boundary rule:** `doctor.py` and `init.py` must never import from `app.py`. They depend only on `config/`. This keeps CLI commands testable without starting FastAPI or uvicorn.

---

## Data Flow

### gateway doctor

```
cli.py:doctor()
  → load_config() [config/loader.py]
      → GatewayConfig() reads env vars
  → DoctorRunner(config)
      → check_soul_md_exists(config.soul_md_path)
      → check_workspace_path(config.workspace_path)
      → check_llm_api_key(config.llm_api_key)
      → check_linear_secret(config.watch.linear.secret)
      → check_github_secret(config.watch.github.secret)
      → check_linear_project_ids_are_uuids(config.watch.linear.project_ids)
  → print results (pass/fail per check, exit code 1 if any fail)
```

Config loading is the only shared dependency with the existing app. Doctor does not touch the FastAPI app, adapters, classifier, or writer.

### gateway init

```
cli.py:init()
  → prompt for each config value (click.prompt / click.confirm)
  → validate format inline (UUID pattern for Linear project IDs)
  → write .env file to cwd or --output path
  → echo "Run 'gateway doctor' to verify your config"
```

Init does not load `GatewayConfig`. It produces an `.env` file. Doctor validates what init produced. This ordering is intentional.

### gateway serve (existing behavior)

```
cli.py:serve()
  → uvicorn.run("heartbeat_gateway.app:create_app", factory=True, host="0.0.0.0", port=8080)
```

Identical to the current `main()` body. No change in behavior.

---

## pyproject.toml Change

Only one line changes:

```toml
[project.scripts]
heartbeat-gateway = "heartbeat_gateway.cli:cli"    # was: heartbeat_gateway.app:main
heartbeat-gateway-mcp = "heartbeat_gateway.mcp_server:main"  # unchanged
```

Click must become an explicit direct dependency since it is currently only transitive:

```toml
dependencies = [
    ...
    "click>=8.1.0",
    ...
]
```

Pinning `>=8.1.0` captures the stable group/invoke API. Click's major version has been stable since 8.0 (2021); no upper bound needed.

---

## Build Order

Build in this sequence. Each step is independently testable before the next begins.

### Step 1: Create `heartbeat_gateway/cli.py` with the group and serve subcommand

What exists before this: nothing in cli.py.
What this enables: `heartbeat-gateway serve` works; `heartbeat-gateway` (no args) still starts the server via `invoke_without_command`.
Tests to write: `tests/cli/test_cli.py` — invoke with no args, invoke `serve`, confirm uvicorn is called (mock uvicorn.run).

### Step 2: Update pyproject.toml entry point and add click as explicit dep

No logic change. Just wiring. Run `uv sync` to verify no resolution conflicts.

### Step 3: Build `commands/doctor.py`

Implement each check as a standalone function returning `(passed: bool, message: str)`. A `DoctorRunner` class collects results and produces a final pass/fail summary. All checks operate on a `GatewayConfig` instance passed in — never call `GatewayConfig()` inside a check function. This makes checks unit-testable without env vars.

Checks to implement (based on known silent failure modes from CLAUDE.md and PROJECT.md):
- `GATEWAY_WORKSPACE_PATH` exists and is a directory
- `GATEWAY_SOUL_MD_PATH` exists and is readable
- `ANTHROPIC_API_KEY` or `GATEWAY_LLM_API_KEY` is set and non-empty
- `GATEWAY_WATCH__LINEAR__SECRET` is non-empty (warn if empty, not fail — signatures optional)
- `GATEWAY_WATCH__GITHUB__SECRET` is non-empty (same)
- `GATEWAY_WATCH__LINEAR__PROJECT_IDS` values match UUID4 format if provided
- `GATEWAY_WATCH__GITHUB__REPOS` values match `owner/repo` pattern if provided
- If `GATEWAY_REQUIRE_SIGNATURES=true`, all secrets must be present (fail, not warn)

### Step 4: Wire doctor into cli.py

Register `commands.doctor.doctor` with `cli.add_command(doctor)`.

### Step 5: Build `commands/init.py`

Implement interactive prompts in order: workspace path, SOUL.md path, LLM model, API key, Linear secret, Linear project IDs (with UUID format hint), GitHub secret, GitHub repos. Write collected values to `.env` using standard `KEY=value` format.

### Step 6: Wire init into cli.py

Register `commands.init.init` with `cli.add_command(init)`.

---

## Test Strategy

### Use Click's built-in CliRunner

Click ships `click.testing.CliRunner`. It does not require subprocess, does not start a real terminal, and integrates cleanly with pytest. This is the correct tool for CLI testing in this project.

```python
from click.testing import CliRunner
from heartbeat_gateway.cli import cli

def test_doctor_passes_with_valid_config(tmp_path):
    runner = CliRunner()
    soul = tmp_path / "SOUL.md"
    soul.write_text("## Current Focus\nship it")
    env = {
        "ANTHROPIC_API_KEY": "sk-test",
        "GATEWAY_WORKSPACE_PATH": str(tmp_path),
        "GATEWAY_SOUL_MD_PATH": str(soul),
    }
    result = runner.invoke(cli, ["doctor"], env=env)
    assert result.exit_code == 0
```

Key CliRunner parameters:
- `env={}` — sets environment variables for the invocation without monkeypatching
- `catch_exceptions=False` — lets exceptions propagate for easier debugging during development
- `mix_stderr=False` — keep stdout and stderr separate (Click 8.2+ default)

### Test file layout

```
tests/cli/
  __init__.py
  test_doctor.py    # test each check function individually + full invocation
  test_init.py      # test prompt flow with input="\n".join([...])
```

Each check function in `doctor.py` must be tested independently (unit test) before testing the full CLI invocation (integration test). This isolates failures.

For `gateway init`, use `runner.invoke(cli, ["init"], input="value1\nvalue2\n...")` to simulate user input through Click's prompt system.

### No async needed for CLI tests

`doctor` and `init` are synchronous. No `pytest-asyncio` or `AsyncMock` required. This is simpler than the existing `test_app.py` tests.

### Exit codes

- `gateway doctor`: exit 0 if all checks pass, exit 1 if any check fails. This enables `gateway doctor && systemctl start heartbeat-gateway` in setup scripts.
- `gateway init`: exit 0 on completion, exit 1 on user abort (Ctrl+C).
- `gateway serve`: exit code from uvicorn.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Importing app.py from CLI commands

**What:** `from heartbeat_gateway.app import create_app` inside `doctor.py` or `init.py`
**Why bad:** Pulls in FastAPI, uvicorn, all adapters, classifier. CLI commands become untestable without the full stack. Tests become slow and fragile.
**Instead:** Doctor and init import only `config.schema` and `config.loader`.

### Anti-Pattern 2: Calling GatewayConfig() inside check functions

**What:** Each check function calls `GatewayConfig()` to get the value it needs.
**Why bad:** Each call re-reads all environment variables. Behavior differs per-check if env changes mid-run. Untestable without full env setup per call.
**Instead:** Load config once at the `doctor()` command level, pass the `GatewayConfig` instance into each check function.

### Anti-Pattern 3: Making `cli.py` a fat module

**What:** All doctor logic and init logic written directly in `cli.py`
**Why bad:** `cli.py` becomes hard to read and test. Logic entangles with Click decorator machinery.
**Instead:** `cli.py` is thin dispatch only. All logic lives in `commands/`.

### Anti-Pattern 4: Skipping `click` as an explicit dependency

**What:** Relying on click being present as a transitive dep of uvicorn/litellm
**Why bad:** If litellm or uvicorn drop click (unlikely but possible), the CLI silently breaks on install. The dependency is invisible in `pyproject.toml`.
**Instead:** Add `click>=8.1.0` to `[project.dependencies]`.

### Anti-Pattern 5: Using subprocess to test CLI commands

**What:** `subprocess.run(["heartbeat-gateway", "doctor"])` in tests
**Why bad:** Requires the package to be installed; cannot monkeypatch; slow; fragile CI.
**Instead:** `CliRunner().invoke(cli, ["doctor"])` — no install required, fully in-process.

---

## Scalability Considerations

This is a single-operator tool. Scalability here means: how well does the CLI structure hold up as more commands are added?

The `commands/` subpackage pattern scales cleanly. Each new command (e.g., `gateway lint-soul`, `gateway status`) is a new file in `commands/` and a single `cli.add_command(...)` line in `cli.py`. No changes to existing command modules required.

If the command list grows beyond ~8 commands, Click supports command groups nested inside groups. That is not needed for v0.3.0.

---

## Sources

- Click 8.3.x official documentation (groups, testing) — confirmed via WebSearch, Click 8.3.1 installed
- Click testing module: `click.testing.CliRunner` — standard, stable API since Click 4.x
- Codebase: `heartbeat_gateway/app.py`, `config/schema.py`, `config/loader.py` — read directly
- Codebase: `pyproject.toml` — entry points and dependencies confirmed
- Transitive dependency chain: click required-by uvicorn, litellm (confirmed via `uv run pip show click`)
