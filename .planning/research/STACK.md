# Technology Stack: v0.3.0 CLI Tooling

**Project:** heartbeat-gateway
**Milestone:** v0.3.0 — `gateway doctor` and `gateway init`
**Researched:** 2026-03-25
**Scope:** CLI tooling only. Does not cover the existing FastAPI pipeline.

---

## What This Research Covers

Two new Click subcommands added to an existing Python 3.11+ / Click application:

- `gateway doctor` — pre-flight config validator. Checks all env vars, file paths, secrets, and LLM reachability. Exits 0 if healthy, 1 if any check fails.
- `gateway init` — interactive setup wizard. Guides a new user through `.env` construction step by step, without requiring knowledge of Linear UUID formats or JSON array syntax.

---

## Current Stack Inventory (already in pyproject.toml)

| Library | Version Pinned | Role in v0.3.0 |
|---------|---------------|----------------|
| `pydantic>=2.9.0` | yes | Already models `GatewayConfig`. `doctor` reuses it for validation. |
| `pydantic-settings>=2.6.0` | yes | `GatewayConfig` is `BaseSettings`. `doctor` catches `ValidationError` from it. |
| `loguru>=0.7.0` | yes | Internal logging. Do not use for user-facing CLI output. |
| `python-dotenv` | **NOT in pyproject.toml** | Needed by `doctor` to read `.env` without contaminating `os.environ`. |

No Click dependency is declared in `pyproject.toml`. The project currently uses uvicorn's CLI entry point and a plain `main()` function. **Click must be added as an explicit dependency.**

---

## New Dependencies Required

### 1. `click>=8.1.0` — CLI framework

**Why Click, not Typer:**

The existing project has no Typer dependency and no type-hint-driven CLI surface. Typer is a wrapper over Click that shines for greenfield CLIs where you want auto-generated help from function signatures. For this project:

- The existing `main()` entry point in `app.py` is a plain function. The new CLI layer is being added on top, not replacing anything.
- Click's `@click.group()` + `add_command()` pattern is the correct idiom for adding `doctor` and `init` to an existing application without restructuring the whole app.
- Click 8.x is stable, battle-tested, and the most widely used Python CLI framework (38.7% of CLI projects as of 2025). Its decorator-based API is unambiguous and easy to test.
- Typer adds an extra dependency with no payoff here. The two commands have simple, well-defined argument surfaces.

**What NOT to do:** Do not use argparse. It produces inferior help output and has no composable group model.

**Version:** `click>=8.1.0`. Click 8.1 added shell completion improvements and is the stable baseline. Click 8.x has been stable since 2021 with no breaking changes expected.

---

### 2. `rich>=13.0.0` — Terminal output formatting

**Why rich:**

`gateway doctor` needs to render a structured health check report. The canonical UX pattern (established by Flutter, React Native, Homebrew, and npm) is a checklist of named checks with pass/fail indicators, followed by a summary. Rich provides exactly this:

- `rich.console.Console` for styled output
- `rich.table.Table` for the check report (check name | status | detail)
- Unicode symbols `[green]✓[/green]` and `[red]✗[/red]` for pass/fail
- `rich.panel.Panel` for summary boxes
- `rich.text.Text` for inline styled messages

Rich is already the de facto standard for Python CLI output formatting in 2025. It is a zero-friction addition — no behavioral side effects, no async concerns, no conflicts with Click.

**What NOT to do:** Do not use `click.echo()` with ANSI escape codes manually. Rich is the right abstraction. Do not use `rich-click` (the hybrid drop-in) — it reformats help text but adds complexity for no benefit in a two-command CLI.

**Version:** `rich>=13.0.0`. The library is at 14.3.3 as of February 2026 and follows semantic versioning with no breaking changes in the 13.x → 14.x transition for the features used here.

---

### 3. `questionary>=2.0.0` — Interactive prompts for `gateway init`

**Why questionary:**

`gateway init` is a wizard: it asks questions in sequence, adapts follow-up questions to prior answers, and writes a `.env` file at the end. The required interaction types are:

- **text** — free-form input with default values (e.g., `GATEWAY_WORKSPACE_PATH`)
- **password** — masked input for secrets (e.g., `ANTHROPIC_API_KEY`, webhook secrets)
- **confirm** — yes/no gates (e.g., "Do you use Linear?")
- **select** — single-choice lists (e.g., LLM model selection)

Questionary provides all of these with a clean, opinionated API. Built on top of `prompt_toolkit`, it handles terminal edge cases (keyboard interrupts, non-TTY environments) correctly.

**Alternatives considered:**

- `prompt_toolkit` directly: Too low-level for a wizard. Questionary is the right abstraction layer over it.
- `rich.prompt.Prompt`: Good for single-value prompts but has no select/multi-select/confirm primitives. Cannot drive a wizard flow.
- `PyInquirer`: Unmaintained since 2020. Do not use.
- `InquirerPy`: Active fork of PyInquirer. Viable, but questionary is lighter, has cleaner docs, and is more widely adopted.
- Click's built-in `click.prompt()` / `click.confirm()`: Functional but produces plain text with no styling. Insufficient UX for a wizard.

**Async concern:** `gateway init` runs as a synchronous Click command (not inside the FastAPI app). Questionary's synchronous API (`questionary.text(...).ask()`) is the correct choice here. No async needed.

**Maintenance status:** questionary 2.1.1 was released within the last three months (as of 2026-03-25). Actively maintained, MIT license, Python >=3.9.

**Version:** `questionary>=2.0.0`. The 2.x series introduced breaking API changes from 1.x; pin to 2.x to avoid regression risk.

---

### 4. `python-dotenv>=1.0.0` — Read `.env` without polluting environment

**Why needed for `doctor`:**

`gateway doctor` needs to read the user's `.env` file to validate its contents before the gateway is started — before `GatewayConfig` loads from the live environment. `dotenv_values(".env")` returns a plain `dict` without calling `os.environ.update()`, which is exactly right for a validator that should never silently modify the running environment.

This is distinct from `pydantic-settings`' `.env_file` support, which loads values into the settings object during instantiation. The doctor needs to inspect the raw `.env` key set (checking for missing required keys, detecting unknown keys) before attempting to construct `GatewayConfig`.

**Version:** `python-dotenv>=1.0.0`. The library is stable at 1.x. The `dotenv_values` function has been stable API for several major versions.

---

## Summary: What to Add to pyproject.toml

```toml
dependencies = [
    # ... existing dependencies unchanged ...
    "click>=8.1.0",
    "rich>=13.0.0",
    "questionary>=2.0.0",
    "python-dotenv>=1.0.0",
]
```

And a new entry point in `[project.scripts]`:

```toml
[project.scripts]
heartbeat-gateway = "heartbeat_gateway.app:main"
heartbeat-gateway-mcp = "heartbeat_gateway.mcp_server:main"
gateway = "heartbeat_gateway.cli:main"   # NEW — the Click group
```

---

## CLI Architecture Pattern

### Command structure

```
gateway                  ← click.group()  in heartbeat_gateway/cli.py
  ├── doctor             ← click.command() in heartbeat_gateway/commands/doctor.py
  └── init               ← click.command() in heartbeat_gateway/commands/init.py
```

The `gateway` group lives in a new `heartbeat_gateway/cli.py` module. Each command lives in its own file under `heartbeat_gateway/commands/`. Commands are registered via `cli.add_command()` — not inline decorators — so they can be tested in isolation without importing the full group.

### `gateway doctor` — Validator pattern

The doctor command follows the established industry pattern (Flutter `flutter doctor`, React Native `react-native doctor`, Homebrew `brew doctor`):

1. Run N named checks in sequence
2. Each check returns a result: PASS / WARN / FAIL + detail string
3. Render a table showing all check results
4. Print summary: "X checks passed, Y failed"
5. Exit code 0 if all PASS or WARN; exit code 1 if any FAIL

**Do not raise exceptions for failed checks.** Collect all results first, then render. A validator that crashes on the first failure is not useful.

**Check implementations use pydantic-settings directly.** The `doctor` should attempt `GatewayConfig()` construction inside a `try/except ValidationError` and surface the exact field errors from pydantic, not re-implement field validation logic.

**Exit code discipline:**
- `sys.exit(0)` — all checks pass
- `sys.exit(1)` — one or more checks failed
- This allows `gateway doctor && systemctl start heartbeat-gateway` to work correctly in shell scripts and systemd `ExecStartPre=` hooks.

### `gateway init` — Wizard pattern

1. Use `questionary.confirm()` to gate adapter sections (only ask Linear questions if user says they use Linear)
2. Use `questionary.password()` for all secret values — never echo secrets to terminal
3. Validate inputs inline: Linear project IDs must be UUID format; repos must be `owner/repo` format. Use questionary's `validate` parameter.
4. At the end: show a preview of the `.env` content to be written (with secrets masked), ask for confirmation, then write the file.
5. Never overwrite an existing `.env` without explicit confirmation.

---

## What NOT to Add

| Library | Why Not |
|---------|---------|
| `typer` | No benefit over Click for this scope. Adds a dependency for no gain. |
| `rich-click` | Reformats help text but adds complexity. Overkill for two commands. |
| `PyInquirer` | Unmaintained since 2020. |
| `InquirerPy` | Viable but questionary is lighter and better maintained for this scope. |
| `prompt_toolkit` (directly) | Too low-level. questionary is the right abstraction. |
| `click-params` | Specialized UUID/URL validators. Not worth a dependency — regex in questionary `validate` is sufficient. |

---

## Confidence Assessment

| Area | Confidence | Basis |
|------|------------|-------|
| Click as framework | HIGH | Official docs, 8.x stable, widely adopted, directly applicable to existing app structure |
| Rich for output | HIGH | Official docs (v14.3.3 current), de facto standard in 2025/2026 Python CLI ecosystem |
| Questionary for wizard | MEDIUM-HIGH | PyPI confirms v2.1.1, active maintenance, widely cited in 2025 guides; async concern verified as non-issue for sync CLI |
| python-dotenv for doctor | HIGH | Official docs, `dotenv_values` API is stable and purpose-built for this use case |
| Exit code conventions | HIGH | Industry standard; verified against Flutter, React Native, Homebrew patterns |
| Add Click to pyproject.toml | HIGH | Confirmed: no Click import exists anywhere in current codebase |

---

## Sources

- Click documentation (8.3.x): https://click.palletsprojects.com/en/stable/commands-and-groups/
- Click entry points: https://click.palletsprojects.com/en/latest/entry-points/
- Rich documentation (14.1.0): https://rich.readthedocs.io/en/stable/introduction.html
- Questionary documentation (2.0.1): https://questionary.readthedocs.io/
- Questionary GitHub (tmbo/questionary): https://github.com/tmbo/questionary
- python-dotenv (`dotenv_values`): https://pypi.org/project/python-dotenv/
- pydantic-settings docs: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- Flutter doctor UX pattern: https://docs.flutter.dev/reference/flutter-cli
- React Native doctor pattern: https://reactnative.dev/blog/2019/11/18/react-native-doctor
- Click vs Typer 2025: https://www.pyinns.com/tools/click-vs-typer
- Real Python Click guide: https://realpython.com/python-click/
