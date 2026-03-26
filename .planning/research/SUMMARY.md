# Project Research Summary

**Project:** heartbeat-gateway v0.3.0 — `gateway doctor` and `gateway init`
**Domain:** Python CLI subcommands — config validator and interactive setup wizard
**Researched:** 2026-03-25
**Confidence:** HIGH

## Executive Summary

heartbeat-gateway v0.3.0 closes two documented product gaps (PG-1 and PG-2) with two Click subcommands: `gateway doctor` pre-flight config validator and `gateway init` interactive setup wizard. Both commands follow well-established CLI patterns with a strong body of prior art — `flutter doctor`, `brew doctor`, `expo doctor`, `fly launch`, AlgoKit init — and the implementation surface is well-understood. The stack addition is four explicit dependencies (click, rich, questionary, python-dotenv) on top of infrastructure that is already present as transitive dependencies. The architecture is a thin `cli.py` dispatch layer over isolated `commands/doctor.py` and `commands/init.py` modules, keeping the existing FastAPI app untouched.

The two commands have a deliberate dependency ordering that mirrors the user's onboarding flow: `gateway init` writes the `.env`, `gateway doctor` validates it, then the service starts. This flow also collapses PG-3 (SOUL.md has no schema/linter) into `gateway doctor` at no additional cost — the SOUL.md content check belongs in doctor's check list, not as a separate command. Two product gaps close for the price of one feature.

The primary implementation risks are not technical — they are UX. Shallow checks that report "present" instead of "valid" destroy doctor's entire value proposition. The Linear UUID input step is the single highest-friction moment in the wizard, requiring an explicit instruction block and inline validation before the field is accepted. And `gateway init` must default to merge-not-overwrite on re-run with a timestamped backup, because the credentials it collects (HMAC secrets) cannot be recovered after overwrite. Getting these three things right is the difference between a command that users trust and one they ignore.

---

## Key Findings

### Recommended Stack

The project already has Click 8.3.1 available as a transitive dependency of uvicorn and litellm, but it is not declared as a direct dependency. This is the first thing to fix: add `click>=8.1.0` to `pyproject.toml` explicitly. The command surface is small and well-defined (two subcommands, simple argument surfaces), so Click's decorator-based API is the right choice — Typer adds a dependency for no gain here.

Three additional dependencies are required: `rich>=13.0.0` for structured terminal output (the `[OK]` / `[FAIL]` / `[WARN]` check table), `questionary>=2.0.0` for the interactive wizard prompts (text, password, confirm, select — all four are needed), and `python-dotenv>=1.0.0` so doctor can read the `.env` file via `dotenv_values()` without contaminating `os.environ`. All four are pure-Python, actively maintained, and have no conflicts with the existing stack.

**Core technologies:**
- `click>=8.1.0`: CLI group and subcommand dispatch — already present transitively, must be made explicit
- `rich>=13.0.0`: Structured `[OK]`/`[FAIL]`/`[WARN]` output table — de facto standard for Python CLI formatting in 2025/2026
- `questionary>=2.0.0`: Wizard prompts (text, password, confirm, select) — correct abstraction over prompt_toolkit for a sequential wizard flow
- `python-dotenv>=1.0.0`: `dotenv_values(".env")` returns a plain dict without side-effecting `os.environ` — purpose-built for doctor's validation use case

**Do not add:** Typer, rich-click, PyInquirer, InquirerPy, prompt_toolkit directly, click-params.

### Expected Features

**gateway doctor — must have (table stakes):**
- Named per-check output with three-state status: PASS / WARN / FAIL
- Every FAIL includes a `fix_hint` field with the exact env var name or command to fix it
- Checks cover all five known v0.2.0 silent failure modes (API key, workspace path, SOUL.md, Linear project IDs, GitHub repos)
- SOUL.md content linter (PG-3 folded in): WARN if SOUL.md contains UUID patterns or scoping keywords
- Exit code 0 on all-pass or WARN-only; exit code 1 on any FAIL
- Works without the server running — pure config inspection, no HTTP calls
- Summary line always printed: "X checks passed, Y failed"
- Show only failures by default; `--verbose` shows all checks

**gateway init — must have (table stakes):**
- Guided questions in logical order: workspace path → LLM model → API key → Linear secret + project IDs → GitHub secret + repos
- Password masking for all secret inputs (`questionary.password()`)
- Inline UUID format validation for Linear project IDs with a framed instruction block showing how to find the UUID in Linear
- Confirm-to-overwrite if `.env` exists; default to merge; create timestamped backup before any write
- Collect and validate all inputs in memory before writing anything to disk
- Show key names written at end (never values); print next step: `gateway doctor`
- TTY detection at startup: exit cleanly with a clear message if `sys.stdin.isatty()` returns False

**Should have (differentiators):**
- Check groups/categories in doctor output: `[Environment]`, `[Files]`, `[Adapters]`, `[LLM]`
- Advisory security warning when `GATEWAY_REQUIRE_SIGNATURES=false` but adapters are configured
- `--dry-run` flag on `gateway init` (renders .env content to stdout without writing)
- Conditional adapter sections in init wizard (skip Linear questions if user doesn't use Linear)
- SOUL.md template creation in init if SOUL.md doesn't exist at configured path

**Defer to later:**
- `--fix` flag on doctor (safe directory creation only)
- `--json` output on doctor (CI scripting)
- Re-run prefill from existing `.env` (high complexity — high value but warrants its own iteration)
- PostHog wizard section (adapter doesn't exist yet — would be dead code)
- Linear API key path that auto-discovers project UUIDs

### Architecture Approach

The architecture is a thin dispatch layer (`heartbeat_gateway/cli.py`) over isolated command modules (`heartbeat_gateway/commands/doctor.py`, `heartbeat_gateway/commands/init.py`). The existing `heartbeat-gateway` entry point must not break: use `invoke_without_command=True` on the Click group so bare `heartbeat-gateway` still starts uvicorn. The critical boundary rule is that `doctor.py` and `init.py` must never import from `app.py` — they depend only on `config/`. This keeps both commands testable without starting FastAPI or uvicorn. Config is loaded once at the `doctor()` command level and passed into each check function — check functions never call `GatewayConfig()` directly.

**Major components:**
1. `heartbeat_gateway/cli.py` — Click group, `serve`/`doctor`/`init` registration, `invoke_without_command` fallback
2. `heartbeat_gateway/commands/doctor.py` — `DoctorRunner` class, individual check functions returning `(passed: bool, message: str, fix_hint: str)`
3. `heartbeat_gateway/commands/init.py` — sequential questionary prompts, in-memory validation, atomic `.env` write with backup
4. `tests/cli/test_doctor.py` and `tests/cli/test_init.py` — Click `CliRunner`-based tests; use `monkeypatch.setenv` not mocked `GatewayConfig`

**Build order is fixed by dependency:** cli.py group must exist before doctor or init can be registered. Wire the group and `serve` first (Step 1), then update pyproject.toml entry point (Step 2), then build doctor logic (Step 3), then wire doctor (Step 4), then build init logic (Step 5), then wire init (Step 6).

### Critical Pitfalls

1. **Shallow checks that report "present" not "valid"** — Every check must validate format and accessibility, not just existence. `ANTHROPIC_API_KEY` must start with `sk-ant-`. `LINEAR__PROJECT_IDS` must parse as a JSON array of valid UUIDs. `GATEWAY_WORKSPACE_PATH` must pass `os.access(path, os.W_OK)`, not just `path.exists()`. Test each check with a plausible-but-wrong value — doctor must fail, not pass.

2. **No fix instructions on failures (diagnosis without treatment)** — Every FAIL output must carry a `fix_hint` with the exact command or env var name to fix it. Never emit a FAIL without a `fix_hint`. Tests must assert `fix_hint` is non-empty for every FAIL case. This is the most common failure mode in real-world doctor implementations (documented in gemini-cli #18692, Claude Code #5563).

3. **`gateway init` silently overwrites credentials on re-run** — Before writing anything, check if `.env` exists. Default to merge. Create a timestamped backup (`.env.backup.2026-03-25T12-00-00`). Credentials lost to overwrite (HMAC secrets) cannot be recovered from the Linear/GitHub side.

4. **Interactive prompts break in non-TTY environments** — Check `sys.stdin.isatty()` at the start of `gateway init`. If False, exit with a clear message and exit code 1. Target users run setup over SSH on a VPS; `tmux`, `screen`, and piped scripts are all plausible. Do not attempt a non-interactive fallback — a partial wizard that writes incomplete config is worse than no run.

5. **Tests that mock `GatewayConfig` miss real loading failures** — Use `monkeypatch.setenv` in at least one integration-level test per doctor check. The `BaseModel`/`BaseSettings` constraint (root cause of the v0.2.0 security regression) cannot be caught by tests that bypass config loading entirely. Specifically: set `GATEWAY_WATCH__LINEAR__PROJECT_IDS=not-valid-json`, call `load_config()`, confirm doctor catches and reports it.

---

## Implications for Roadmap

Based on research, the two commands are developed sequentially because `gateway doctor` must exist and be trusted before users can validate what `gateway init` produced. Within each command, the build order is fixed by the Click group dependency.

### Phase 1: CLI Foundation + gateway doctor

**Rationale:** Click group wiring is a prerequisite for both commands. Doctor must exist before init can be validated. Doctor also closes PG-2 and PG-3 simultaneously (the SOUL.md linter belongs here). Starting with doctor forces the check data structure — `(passed, message, fix_hint)` — to be defined correctly before init logic touches it.

**Delivers:** A fully functional `gateway doctor` command with 8 checks, structured output, exit code discipline, and the SOUL.md content linter. The existing `heartbeat-gateway` entry point continues working unchanged. pyproject.toml declares all four new explicit dependencies.

**Addresses:** All table-stakes features for doctor; SOUL.md linter (PG-3 folded in); advisory security warning for `require_signatures=false`.

**Avoids:** Shallow check pitfall (CRITICAL-1) by requiring `fix_hint` field on every check struct; exit code pitfall (MODERATE-1) by testing `result.exit_code` explicitly; test-mocking pitfall (MODERATE-2) by using `monkeypatch.setenv` for integration tests.

**Key implementation constraints:**
- Wire `cli.py` group before writing any check logic (build order Step 1 first)
- Every check function receives a `GatewayConfig` instance — never calls `GatewayConfig()` internally
- `commands/doctor.py` and `cli.py` must not import from `app.py`
- Click must be added as an explicit dependency in `pyproject.toml` regardless of transitive availability

### Phase 2: gateway init

**Rationale:** Init is only coherent once doctor exists to validate its output. The wizard's natural user flow (`gateway init` → `gateway doctor` → start service) requires doctor to be complete first. Init is also the higher-UX-risk command — the Linear UUID problem is the single highest-friction step in the entire onboarding and must be solved at design time, not discovered during implementation.

**Delivers:** A fully functional `gateway init` wizard with TTY detection, conditional adapter sections, inline UUID validation with instruction block, merge-by-default `.env` handling with timestamped backup, and atomic write after in-memory validation. Closes PG-1.

**Addresses:** All table-stakes features for init; Linear UUID instruction block; TTY detection; merge-not-overwrite `.env` handling.

**Avoids:** Init overwrite pitfall (CRITICAL-3) by defaulting to merge and creating timestamped backups; TTY pitfall (CRITICAL-4) by checking `sys.stdin.isatty()` at startup; partial-write pitfall (MODERATE-3) by collecting and validating all inputs in memory before writing; Linear UUID abandonment (CRITICAL-5) by showing the instruction block before the UUID prompt.

**Key implementation constraints:**
- TTY detection is the first thing `gateway init` does — before any prompts
- In-memory validation must be complete before any disk write
- `.env` backup must be created before any overwrite, even on explicit confirm
- UUID regex must be `^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$` (UUID v4)

### Phase Ordering Rationale

- Click group wiring is a single prerequisite that unblocks both commands — it must come first and be independently verified before any command logic is written
- Doctor before init because init's value statement ("use `gateway doctor` to verify your configuration") requires doctor to exist and be trusted
- SOUL.md linter belongs in doctor (Phase 1), not as a separate command — two product gaps close for the price of one
- Deferred features (`--fix`, `--json`, re-run prefill, SOUL.md template creation) are deliberately excluded from v0.3.0 to keep scope contained

### Research Flags

Phases with standard patterns (no additional research needed):
- **Phase 1 (doctor):** Click group pattern, CliRunner testing, rich output formatting — all well-documented with stable APIs. The check list is defined by v0.2.0 known failure modes already documented in CLAUDE.md.
- **Phase 2 (init):** questionary wizard pattern is well-documented. The main design question (Linear UUID UX) is answered by CRITICAL-5 in PITFALLS.md — instruction block + inline UUID validation + re-prompt on failure.

No phases require `/gsd:research-phase` during planning. Research is complete for both commands.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Click 8.3.1 confirmed installed; rich, questionary, python-dotenv all verified against official docs and current PyPI versions; all rationale grounded in direct codebase inspection |
| Features | HIGH | All prior art (npm doctor, expo doctor, react-native doctor, fly launch, AlgoKit init) directly inspected; feature list grounded in v0.2.0 known failure modes |
| Architecture | HIGH | Codebase read directly; Click group pattern confirmed against official docs; build order derived from actual dependency constraints in pyproject.toml |
| Pitfalls | HIGH | CRITICAL-1 through CRITICAL-5 grounded in actual v0.2.0 regressions (BaseSettings bug, dedup fingerprint bug) and real-world CLI issues (gemini-cli #18692, Claude Code #5563, Click TTY issue #906) |

**Overall confidence:** HIGH

### Gaps to Address

- **Re-run prefill complexity:** Loading and merging existing `.env` values before prompting is marked HIGH complexity and deferred. If user demand materializes post-launch, this is the right next addition to `gateway init` — the data structure to support it (in-memory dict of existing values) should be designed now even if the feature ships later.
- **`--fix` flag scope:** Research recommends limiting `--fix` to safe filesystem operations (creating missing directories). The exact set of checks where `--fix` is appropriate should be decided during Phase 1 implementation, not before. Err on the side of not auto-fixing.
- **questionary behavior in tmux/screen:** PITFALLS.md documents that TTY detection may behave differently inside `tmux` or `screen`. The `sys.stdin.isatty()` check is the correct approach, but edge cases may surface on first real deployment. Document as a known edge case and add a troubleshooting note to the README.

---

## Cross-Cutting Theme Summary

These seven themes emerged consistently across all four research files and represent the highest-leverage design decisions for v0.3.0:

1. **Wire `cli.py` first.** Click is available as a transitive dependency but not declared. The Click group is the prerequisite for everything else. Build it before writing a single line of doctor or init logic.

2. **SOUL.md linter folds into doctor.** PG-3 is not a separate command — it is a check inside `gateway doctor`. SOUL.md content validation (warn on UUID patterns, warn on scoping keywords) belongs in the `[Files]` check group. Two product gaps close for the price of one.

3. **The Linear UUID problem is the highest UX risk in gateway init.** Solve it at design time: show a framed instruction block before asking for UUIDs, validate UUID v4 format with regex, re-prompt on failure. Do not discover this during implementation.

4. **Shallow checks are the dominant failure mode for doctor commands.** Every check needs a `fix_hint` field and must validate values, not just presence. `ANTHROPIC_API_KEY` must start with `sk-ant-`. `PROJECT_IDS` must parse as JSON array of valid UUIDs. `WORKSPACE_PATH` must pass `os.access(path, os.W_OK)`.

5. **gateway init re-run must default to merge with backup.** Silent overwrite destroys HMAC secrets that cannot be recovered. Merge-by-default + timestamped backup is required behavior, not an enhancement.

6. **TTY detection is required.** Target users deploy over SSH on a VPS. `sys.stdin.isatty()` must be checked at `gateway init` startup. Exit cleanly with a clear message if False — do not attempt a non-interactive fallback.

7. **Tests must use `monkeypatch.setenv`, not mocked `GatewayConfig`.** Mocking `GatewayConfig` bypasses the `BaseModel`/`BaseSettings` constraint that caused the v0.2.0 security regression. At least one integration-level test per doctor check must load config from actual env vars to catch regressions on this constraint.

---

## Sources

### Primary (HIGH confidence)
- Click 8.3.x official documentation — groups, testing, entry points
- Rich documentation (v14.3.3) — Console, Table, Panel output formatting
- Questionary documentation (v2.1.1) — wizard prompt types, validate parameter
- python-dotenv `dotenv_values` API — official PyPI docs
- npm doctor — official npm docs
- React Native doctor — official React Native blog post
- expo doctor PR #34729 — "show only failing checks by default" design decision
- WP-CLI doctor — official docs and handbook
- Fly Launch — official Fly.io docs
- AlgoKit init v2 architecture decision record (2024) — bidirectional query design, jargon-free prompts
- CLIG (Command Line Interface Guidelines) — clig.dev authoritative reference
- heartbeat-gateway codebase — CLAUDE.md, schema.py, pyproject.toml read directly
- uv run pip show click — confirmed Click 8.3.1 installed as transitive dep

### Secondary (MEDIUM confidence)
- gh auth status exit code issues — GitHub CLI #8845, #9326 — pattern validation for exit code discipline
- Make "app init" idempotent — AWS copilot-cli #552 — pattern validation for re-run safety
- gemini-cli doctor issue #18692 — real-world evidence for fix-hint requirement
- Claude Code doctor issue #5563 — "show specific JSON parsing errors" — generic errors not actionable
- Click non-TTY issues — pallets/click #906 — TTY detection behavior
- Linear UUID discovery — Linear Docs, Cmd+K "Copy model UUID" path
- pytest mocking anti-patterns — pytest-with-eric — over-mocking pitfall documentation
- Flutter Doctor design — structured output pattern with fix hints
- UX patterns for CLI tools — Lucas F. Costa (practitioner post, widely cited)

---
*Research completed: 2026-03-25*
*Ready for roadmap: yes*
