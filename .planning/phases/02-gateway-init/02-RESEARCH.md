# Phase 2: gateway-init — Research

**Researched:** 2026-03-25
**Domain:** Click CLI wizard, questionary prompts, python-dotenv .env file management, TTY detection, atomic file writes
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INIT-01 | `gateway init` detects non-TTY environment at startup and exits with a clear error message | `sys.stdin.isatty()` pattern; CliRunner sets isatty=False by default — covered in testing section |
| INIT-02 | Wizard displays Linear UUID discovery instructions before prompting for UUID input | `questionary.print()` or `click.echo()` before UUID prompt; instruction text from `.env.example` |
| INIT-03 | Linear project UUID input validated against UUID format regex before accepting — re-prompts on failure | questionary `validate=` callback; UUID_V4_PATTERN already defined in doctor.py — reuse |
| INIT-04 | All secret/key inputs are masked (no terminal echo) | `questionary.password()` for masked input |
| INIT-05 | Running `gateway init` when `.env` already exists creates a timestamped backup before writing | `shutil.copy2()` + `datetime.now().strftime()` pattern; backup before any write |
| INIT-06 | All values validated in-memory before any file write (atomic: write only if all valid) | Collect answers dict, validate all fields, then write once |
| INIT-07 | Completion output shows next-step hint: `Run gateway doctor to verify your configuration` | `click.echo()` or `questionary.print()` at end |
| INIT-08 | Questionary and python-dotenv added as explicit dependencies in `pyproject.toml` | Already present in pyproject.toml — confirm in research |
| INIT-09 | Init tests use `CliRunner` with `input=` for non-interactive test execution | CliRunner `input=` string; `mix_stderr=False`; TTY mock pattern |
</phase_requirements>

---

## Summary

Phase 2 implements `gateway init` — a sequential, TTY-only wizard that walks the operator through configuring their `.env` file. The wizard collects values for all `GatewayConfig` fields (required and optional adapter sections), validates them in memory, backs up any existing `.env`, then writes atomically. The wizard ends by directing the user to `gateway doctor`.

The stack is entirely established from Phase 1: `questionary` (interactive prompts with validation), `python-dotenv` (`.env` read/write), `click` (command registration and TTY context), and `rich` (optional styled output). All four are already explicit dependencies in `pyproject.toml`. No new packages are needed.

The key implementation challenges are: (1) making TTY detection the first gate so the wizard never reaches questionary in non-interactive contexts, (2) wiring `questionary`'s `validate=` callback for inline UUID re-prompting rather than post-collection validation, and (3) guaranteeing the backup exists before any write path executes. Testing requires CliRunner's `input=` string injection to simulate the full prompt sequence without a real TTY.

**Primary recommendation:** Follow the doctor.py command structure exactly — standalone `@click.command("init")` in `heartbeat_gateway/commands/init.py`, registered via `cli.add_command(init)` in `cli.py`. Collect all answers into a dict, validate, write backup, write `.env`.

---

## Standard Stack

### Core

| Library | Version (pyproject.toml) | Purpose | Why Standard |
|---------|--------------------------|---------|--------------|
| questionary | `>=2.0.0` | Interactive terminal prompts (text, password, confirm, select) with inline validation | Purpose-built for wizard flows; works in SSH/tmux; no TUI overhead |
| python-dotenv | `>=1.0.0` | Read existing `.env` for merge-on-rerun; write final `.env` | Standard `.env` read/write library; `dotenv_values()` + `set_key()` API |
| click | `>=8.1.0` | Command group registration, TTY context, `sys.stdin` access | Already wired; consistent with doctor.py pattern |
| rich | `>=13.0.0` | Styled output for instruction blocks and completion message | Already imported in doctor.py; consistent UX |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `re` (stdlib) | stdlib | UUID v4 regex validation in validate callback | Always — regex already defined in doctor.py |
| `shutil` (stdlib) | stdlib | `shutil.copy2()` for timestamped `.env` backup | Always — preserves timestamps and permissions |
| `datetime` (stdlib) | stdlib | `datetime.now().strftime("%Y%m%d_%H%M%S")` for backup filename | Always |
| `sys` (stdlib) | stdlib | `sys.stdin.isatty()` for TTY detection | First line of the init command |
| `pathlib.Path` (stdlib) | stdlib | `.env` path handling; consistent with existing config code | Always |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| questionary | prompt_toolkit directly | questionary wraps prompt_toolkit with a cleaner API for wizard flows — no reason to go lower |
| questionary | InquirerPy | Both wrap prompt_toolkit; questionary is already pinned and tested in this project |
| questionary | click.prompt() | click.prompt() lacks inline re-prompt on validation failure — user gets a crash, not a retry |
| python-dotenv `set_key()` | Manual string writing | `set_key()` handles quoting and escaping; manual writing has edge cases with special chars in secrets |

**Installation:** No new packages required. `questionary>=2.0.0` and `python-dotenv>=1.0.0` are already explicit dependencies.

---

## Architecture Patterns

### Recommended Project Structure

```
heartbeat_gateway/
├── cli.py                    # add: cli.add_command(init) alongside doctor
└── commands/
    ├── __init__.py
    ├── doctor.py             # Phase 1 pattern reference
    └── init.py               # Phase 2 delivery

tests/
└── cli/
    ├── __init__.py
    ├── test_cli.py           # CLI-01, CLI-02, CLI-03
    ├── test_doctor.py        # DOC-01 through DOC-12
    └── test_init.py          # INIT-01 through INIT-09 (new)
```

### Pattern 1: TTY Detection First Gate

**What:** `sys.stdin.isatty()` check at the very top of the command body, before any questionary call.
**When to use:** Always — this is INIT-01 and is mandated as the first action in the command.

```python
# Source: Python stdlib sys module
import sys
import click

@click.command("init")
def init() -> None:
    """Interactive wizard to configure .env for heartbeat-gateway."""
    if not sys.stdin.isatty():
        click.echo("Error: gateway init requires an interactive terminal (TTY).")
        click.echo("Run this command directly in a terminal, not in a script or pipe.")
        raise SystemExit(1)
    # ... rest of wizard
```

**Testing TTY detection with CliRunner:**
CliRunner sets `isatty=False` by default. To test the TTY-detection branch: invoke without patching — the command must exit 1 immediately. To test the wizard flow: use `CliRunner(mix_stderr=False)` and patch `sys.stdin.isatty` to return `True`.

```python
# Source: Click testing docs
def test_tty_detection_exits(runner):
    result = runner.invoke(cli, ["init"])
    assert result.exit_code == 1
    assert "TTY" in result.output or "terminal" in result.output.lower()

def test_wizard_flow(runner, monkeypatch, tmp_path):
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    result = runner.invoke(cli, ["init"], input="sk-ant-test\n...\n")
    assert result.exit_code == 0
```

### Pattern 2: questionary Wizard with Inline Validation

**What:** Sequential `questionary.text()` / `questionary.password()` calls with `validate=` callbacks that re-prompt on failure.
**When to use:** All prompts that require format validation (UUID, non-empty secrets). `questionary.password()` for all secret/key inputs.

```python
# Source: questionary 2.x docs
import questionary
import re

UUID_V4_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)

def _validate_uuid(value: str) -> bool | str:
    """questionary validate= callback: return True to accept, str to show error and re-prompt."""
    if not value.strip():
        return True  # empty = skip Linear adapter
    if UUID_V4_PATTERN.match(value.strip()):
        return True
    return "Invalid UUID v4 format. Expected: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx"

linear_uuid = questionary.text(
    "Linear project UUID (leave blank to skip):",
    validate=_validate_uuid,
).ask()
```

**Key questionary API:**
- `questionary.text(message, validate=fn, default="")` — plain text input with optional validation
- `questionary.password(message, validate=fn)` — masked input (INIT-04)
- `questionary.confirm(message, default=True)` — yes/no prompt
- `questionary.print(message, style="bold")` — styled print without prompting (for instruction blocks)
- `.ask()` — execute the prompt; returns the value, or `None` if aborted (Ctrl-C)

**questionary with CliRunner `input=`:** questionary reads from stdin. When CliRunner provides `input="line1\nline2\n"`, each `\n`-delimited segment answers successive prompts in order. For `questionary.password()`, the same `input=` mechanism works — questionary does not verify that stdin is masked in test mode.

### Pattern 3: Merge-by-Default .env Handling

**What:** Load existing `.env` values first, use them as defaults in the wizard, then write back the merged result.
**When to use:** When `.env` already exists at the target path (INIT-05, INIT-06).

```python
# Source: python-dotenv docs
from dotenv import dotenv_values, set_key
from pathlib import Path
import shutil
from datetime import datetime

ENV_PATH = Path(".env")

def _load_existing_env() -> dict[str, str]:
    """Return existing .env values as a dict, or empty dict if no file."""
    if ENV_PATH.exists():
        return dict(dotenv_values(ENV_PATH))
    return {}

def _backup_env() -> None:
    """Create timestamped backup of existing .env before any write."""
    if ENV_PATH.exists():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = ENV_PATH.parent / f".env.backup.{ts}"
        shutil.copy2(ENV_PATH, backup_path)
        click.echo(f"Existing .env backed up to {backup_path}")

def _write_env(values: dict[str, str]) -> None:
    """Atomic write: backup first, then write all keys."""
    _backup_env()  # MUST come before any write
    # Write fresh file
    ENV_PATH.write_text("")  # create/truncate
    for key, value in values.items():
        set_key(str(ENV_PATH), key, value, quote_mode="auto")
```

**python-dotenv API reference:**
- `dotenv_values(path)` — returns `OrderedDict[str, str | None]` of all entries; does NOT modify environment
- `set_key(dotenv_path, key, value, quote_mode="auto")` — upserts a single key in the file
- `load_dotenv(path, override=True)` — loads into `os.environ` (used by doctor's `--env-file`; not needed in init write path)

### Pattern 4: In-Memory Validation Before Write (INIT-06)

**What:** Collect all wizard answers into a dict, run all validations, only then write. Any validation failure aborts the write.
**When to use:** Always — this is the atomic write guarantee.

```python
# Collect phase
answers = {}
answers["ANTHROPIC_API_KEY"] = questionary.password("Anthropic API key (sk-ant-...):").ask()
answers["GATEWAY_WORKSPACE_PATH"] = questionary.text("Workspace path:", default="~/workspace").ask()
# ... all fields

# Validate phase (in-memory, no disk writes yet)
errors = []
if not answers.get("ANTHROPIC_API_KEY", "").startswith("sk-ant-"):
    errors.append("ANTHROPIC_API_KEY must start with sk-ant-")
# ... other validations

if errors:
    for err in errors:
        click.echo(f"[red]Error:[/red] {err}")
    raise SystemExit(1)

# Write phase — only reached if validation passes
_backup_env()
_write_env(answers)
```

### Pattern 5: Registering init in cli.py

**What:** Mirror the doctor registration pattern exactly.
**When to use:** After `init.py` is complete.

```python
# heartbeat_gateway/cli.py — add these two lines after doctor registration
from heartbeat_gateway.commands.init import init  # noqa: E402
cli.add_command(init)
```

### Anti-Patterns to Avoid

- **Using `click.prompt()` for UUID validation:** click.prompt's `value_proc=` raises exceptions on failure rather than re-prompting gracefully. Use questionary's `validate=` callback instead.
- **Writing .env before backup:** backup must be created first. Even if the user confirms overwrite, INIT-05 requires backup to exist before any byte is written.
- **Importing from `app.py`:** Same constraint as doctor.py — `commands/init.py` must not import from `heartbeat_gateway.app`. Pull env var names from `heartbeat_gateway.config.schema` only if needed, or hardcode them as constants.
- **Using TUI frameworks (textual, urwid):** Explicitly out of scope; breaks in tmux/SSH.
- **Calling `questionary` without TTY check first:** questionary will hang or throw in non-TTY environments. TTY check gates entry before any questionary call.
- **`questionary.ask()` returning None on Ctrl-C:** Handle the `None` return: if `answer is None: raise SystemExit(1)` (user aborted).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Masked password input | Custom getpass wrapper | `questionary.password()` | Handles cross-platform masking, CliRunner `input=` compatibility |
| UUID re-prompt loop | `while True: input(); if valid: break` | `questionary.text(validate=fn)` | questionary handles the retry loop, error display, and `input=` injection in tests |
| .env file writing | String concatenation + `open().write()` | `python-dotenv set_key()` | Handles quoting special chars (spaces, `$`, `#`) in values |
| .env file reading | `open().readlines()` parsing | `dotenv_values()` | Handles all edge cases (comments, continuations, quoted values) |
| Backup filename generation | Custom timestamp logic | `datetime.now().strftime("%Y%m%d_%H%M%S")` | Standard pattern; no library needed but don't reinvent the format |

**Key insight:** The questionary `validate=` callback is the single most important pattern to get right. It eliminates all manual re-prompt loops and makes the INIT-03 requirement trivial.

---

## Common Pitfalls

### Pitfall 1: CliRunner does not set `isatty=True` by default

**What goes wrong:** Tests that invoke the wizard flow fail immediately with "TTY required" error, even when `input=` is provided.
**Why it happens:** `CliRunner()` creates a non-TTY stream. `sys.stdin.isatty()` returns `False` inside CliRunner by default.
**How to avoid:** Use `monkeypatch.setattr("sys.stdin.isatty", lambda: True)` in tests that exercise the wizard path. Keep the TTY-detection test separate (no patching needed — it should exit 1).
**Warning signs:** All wizard tests exit with code 1 and "TTY" in output.

### Pitfall 2: questionary blocks on None return from .ask()

**What goes wrong:** User presses Ctrl-C; `questionary.ask()` returns `None`; next line does `.strip()` on `None` → `AttributeError`.
**Why it happens:** questionary returns `None` on keyboard interrupt, not an exception.
**How to avoid:** After every `.ask()` call: `if answer is None: raise SystemExit(1)`. Or wrap in a helper that handles this.
**Warning signs:** `AttributeError: 'NoneType' object has no attribute 'strip'` during manual testing.

### Pitfall 3: python-dotenv `set_key()` called on non-existent file

**What goes wrong:** `set_key()` on a path that doesn't exist raises `FileNotFoundError` or silently creates a malformed file.
**Why it happens:** `set_key()` expects the file to exist already.
**How to avoid:** Before calling `set_key()`, ensure the file exists: `ENV_PATH.touch()` (creates empty file if not present). In the backup/write flow: `ENV_PATH.write_text("")` before `set_key()` loop.
**Warning signs:** Empty `.env` file or exception on first `set_key()` call.

### Pitfall 4: Backup happens inside conditional that can be skipped

**What goes wrong:** Backup only runs if user confirms overwrite, but INIT-05 requires backup to exist before ANY write.
**Why it happens:** Developer puts backup inside `if click.confirm("Overwrite?"):` block.
**How to avoid:** Backup unconditionally, before any write logic executes — even before asking the user whether to overwrite.
**Warning signs:** Backup file not found after failed init run.

### Pitfall 5: UUID regex reused from doctor.py via import

**What goes wrong:** `from heartbeat_gateway.commands.doctor import UUID_V4_PATTERN` introduces a cross-command dependency, making doctor a dependency of init.
**Why it happens:** DRY impulse — the regex is identical.
**How to avoid:** Replicate the pattern constant in `init.py` as a module-level constant (same approach as doctor.py replicated the body size constant from app.py). The constraint comment in doctor.py establishes this pattern.
**Warning signs:** If doctor.py import fails, init.py breaks for unrelated reasons.

### Pitfall 6: questionary validate= callback raises instead of returning str

**What goes wrong:** `validate=` callback raises an exception rather than returning an error string. questionary crashes instead of re-prompting.
**Why it happens:** Developer follows Python convention of raising `ValueError` for invalid input.
**How to avoid:** `validate=` must return `True` (accept), `False` (reject with no message), or a non-empty string (reject with that string as the error). Never raise.
**Warning signs:** `Exception` in test output rather than re-prompt behavior.

---

## Code Examples

Verified patterns from official sources and codebase:

### TTY Detection and Exit (INIT-01)

```python
# Source: Python stdlib sys; consistent with INIT-01 constraint spec
import sys
import click

@click.command("init")
def init() -> None:
    """Interactive wizard to configure .env for heartbeat-gateway."""
    if not sys.stdin.isatty():
        click.echo("Error: gateway init requires an interactive terminal (TTY).", err=True)
        click.echo("Run this command in a terminal. It cannot be piped or scripted.", err=True)
        raise SystemExit(1)
```

### UUID Validation Callback (INIT-03)

```python
# Source: questionary 2.x docs; UUID regex from ROADMAP.md constraint
import re

UUID_V4_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)

def _validate_linear_uuid(value: str) -> bool | str:
    if not value.strip():
        return True  # blank = skip Linear adapter
    if UUID_V4_PATTERN.match(value.strip()):
        return True
    return "Not a valid UUID v4. Expected format: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx"
```

### Masked Password Prompt (INIT-04)

```python
# Source: questionary 2.x API
api_key = questionary.password("Anthropic API key (sk-ant-...):").ask()
if api_key is None:
    raise SystemExit(1)  # User aborted
```

### Timestamped Backup (INIT-05)

```python
# Source: shutil + datetime stdlib
import shutil
from datetime import datetime
from pathlib import Path

def _backup_env(env_path: Path) -> Path | None:
    if not env_path.exists():
        return None
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = env_path.parent / f".env.backup.{ts}"
    shutil.copy2(env_path, backup)
    return backup
```

### Atomic Write Pattern (INIT-06)

```python
# Source: python-dotenv docs
from dotenv import set_key

def _write_env(env_path: Path, values: dict[str, str]) -> None:
    """Write all values to .env. Caller is responsible for backup."""
    env_path.write_text("")  # create/truncate
    for key, value in values.items():
        set_key(str(env_path), key, value, quote_mode="auto")
```

### CliRunner test with input injection (INIT-09)

```python
# Source: Click testing docs; doctor test pattern from test_doctor.py
from click.testing import CliRunner
from heartbeat_gateway.cli import cli

def test_init_tty_detection(monkeypatch, tmp_path):
    """INIT-01: exits 1 when not a TTY (default CliRunner behavior)."""
    runner = CliRunner()
    result = runner.invoke(cli, ["init"])
    assert result.exit_code == 1
    assert "terminal" in result.output.lower() or "tty" in result.output.lower()

def test_init_wizard_happy_path(monkeypatch, tmp_path):
    """INIT-06, INIT-07: completes and writes .env; shows doctor hint."""
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    env_path = tmp_path / ".env"
    monkeypatch.chdir(tmp_path)  # or pass env path via option

    runner = CliRunner()
    # input= answers prompts in order; \n = Enter (accept default or submit value)
    wizard_input = "\n".join([
        "sk-ant-testkey",       # API key
        str(tmp_path),          # workspace path
        str(tmp_path / "SOUL.md"),  # soul md path
        "claude-haiku-4-5-20251001",  # llm model
        "my-linear-secret",     # linear HMAC secret
        "550e8400-e29b-41d4-a716-446655440000",  # linear UUID
        "my-github-secret",     # github HMAC secret
        "owner/repo",           # github repo
        "",                     # accept defaults / skip remaining
    ]) + "\n"

    result = runner.invoke(cli, ["init"], input=wizard_input, catch_exceptions=False)
    assert result.exit_code == 0
    assert "gateway doctor" in result.output
```

### Linear UUID instruction block (INIT-02)

```python
# Pattern: click.echo instruction block before questionary prompt
click.echo("")
click.echo("  Linear project UUID")
click.echo("  Find it in Linear: press Cmd+K (or Ctrl+K), search 'Copy model UUID',")
click.echo("  then paste the UUID here. It looks like: 550e8400-e29b-41d4-a716-446655440000")
click.echo("  Leave blank to skip Linear adapter.")
click.echo("")
linear_uuid = questionary.text(
    "Linear project UUID (blank to skip):",
    validate=_validate_linear_uuid,
).ask()
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `click.prompt()` for validated input | `questionary.text(validate=fn)` | questionary 1.x → 2.x | Re-prompt on failure without manual loop |
| `open().write()` for .env files | `python-dotenv set_key()` | python-dotenv 1.0+ | Handles quoting edge cases |
| TUI frameworks (Textual, Urwid) for wizards | questionary (prompt_toolkit wrapper) | Ongoing | Works in SSH/tmux; no full-screen takeover |

**Deprecated/outdated:**
- `click.prompt(hide_input=True)`: Still works but doesn't re-prompt on validation failure. questionary.password() is preferred for this project's pattern.
- `dotenv.get_key()` for reading: `dotenv_values()` is cleaner when reading multiple keys at once.

---

## Open Questions

1. **Where does the .env file get written?**
   - What we know: The wizard writes to `.env` but the target path isn't specified in requirements.
   - What's unclear: Does it always write to `CWD/.env`, or does the user specify a path?
   - Recommendation: Default to `Path(".env")` in the current working directory (same convention as `.env.example`). Optionally accept `--env-file PATH` flag consistent with doctor's `--env-file` option.

2. **Which adapter sections are conditional?**
   - What we know: ROADMAP.md says "conditional adapter sections." Linear + GitHub are active adapters.
   - What's unclear: Whether PostHog adapter questions should appear (REQUIREMENTS.md marks PostHog as out of scope).
   - Recommendation: Include Linear and GitHub sections; skip PostHog entirely (consistent with requirements).

3. **Merge-by-default behavior on re-run**
   - What we know: INIT-05 requires backup on existing `.env`. ROADMAP.md says "merge-by-default on re-run."
   - What's unclear: Does merge mean pre-fill wizard defaults from existing values, or silently keep un-prompted keys?
   - Recommendation: Load existing `.env` via `dotenv_values()`, use as `default=` in questionary prompts. Keys not asked about (e.g., PostHog) are carried forward from existing file unchanged.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.3.0+ |
| Config file | `pyproject.toml` — `[tool.pytest.ini_options]` testpaths = ["tests"] |
| Quick run command | `uv run pytest tests/cli/test_init.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| INIT-01 | exits 1 with error when not a TTY | unit | `uv run pytest tests/cli/test_init.py::test_tty_detection_exits -x` | Wave 0 |
| INIT-02 | instruction block appears before UUID prompt | unit | `uv run pytest tests/cli/test_init.py::test_linear_uuid_instructions_displayed -x` | Wave 0 |
| INIT-03 | invalid UUID re-prompts; valid UUID accepted | unit | `uv run pytest tests/cli/test_init.py::test_uuid_validation_reprompts -x` | Wave 0 |
| INIT-04 | secrets do not echo in output | unit | `uv run pytest tests/cli/test_init.py::test_secret_not_in_output -x` | Wave 0 |
| INIT-05 | backup created before write when .env exists | unit | `uv run pytest tests/cli/test_init.py::test_backup_created_on_overwrite -x` | Wave 0 |
| INIT-06 | no write if any value invalid | unit | `uv run pytest tests/cli/test_init.py::test_atomic_write_on_valid_input -x` | Wave 0 |
| INIT-07 | completion message includes `gateway doctor` | unit | `uv run pytest tests/cli/test_init.py::test_completion_message_mentions_doctor -x` | Wave 0 |
| INIT-08 | questionary + python-dotenv in pyproject.toml | unit | `uv run pytest tests/cli/test_init.py::test_dependencies_declared -x` | Wave 0 |
| INIT-09 | CliRunner `input=` drives full wizard | integration | `uv run pytest tests/cli/test_init.py::test_wizard_happy_path -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/cli/test_init.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green (`uv run pytest` + `uv run ruff check .`) before marking phase complete

### Wave 0 Gaps

- [ ] `tests/cli/test_init.py` — all 9 INIT requirement tests (file does not exist yet)
- [ ] `heartbeat_gateway/commands/init.py` — command implementation (file does not exist yet)

Note: No new test infrastructure needed. pytest, CliRunner, and monkeypatch are already configured and proven in `test_doctor.py`.

---

## Sources

### Primary (HIGH confidence)

- `heartbeat_gateway/commands/doctor.py` — command structure, UUID_V4_PATTERN, import constraints, CheckResult pattern
- `heartbeat_gateway/cli.py` — Click group registration pattern; `cli.add_command()` usage
- `tests/cli/test_doctor.py` — CliRunner test pattern with monkeypatch.setenv; proven approach for this codebase
- `pyproject.toml` — confirmed questionary>=2.0.0 and python-dotenv>=1.0.0 are already explicit dependencies
- `.env.example` — canonical list of env var names the wizard must write; Linear UUID discovery instruction text
- `heartbeat_gateway/config/schema.py` — GatewayConfig fields; defines what the wizard must populate
- `.planning/REQUIREMENTS.md` — INIT-01 through INIT-09 definitions
- `.planning/ROADMAP.md` — phase constraints, UUID regex, TTY-first constraint

### Secondary (MEDIUM confidence)

- questionary 2.x API: `validate=` callback signature verified against project's existing dependency declaration and documented questionary behavior (returns `True`/`str`, not raises)
- python-dotenv `dotenv_values()` and `set_key()` API: verified against python-dotenv 1.x stable API

### Tertiary (LOW confidence)

- None — all critical patterns verified from project source or confirmed library version pins.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — questionary and python-dotenv already pinned in pyproject.toml; usage patterns from doctor.py reference
- Architecture: HIGH — direct parallel to doctor.py; same Click group, same import constraint, same CliRunner test approach
- Pitfalls: HIGH — TTY/CliRunner interaction is a known pattern; questionary None return and validate= signature are documented behaviors
- Test patterns: HIGH — test_doctor.py provides exact template; no new infrastructure required

**Research date:** 2026-03-25
**Valid until:** 2026-04-25 (stable libraries, internal codebase — low churn risk)
