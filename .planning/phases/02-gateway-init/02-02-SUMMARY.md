---
phase: 02-gateway-init
plan: 02
subsystem: cli
tags: [click, questionary, python-dotenv, tdd, gateway-init, wizard]

# Dependency graph
requires:
  - phase: 02-gateway-init
    plan: 01
    provides: xfail test stubs (INIT-01 through INIT-09), init.py stub
provides:
  - heartbeat_gateway/commands/init.py full implementation
  - 9 passing tests covering INIT-01 through INIT-09
  - gateway init wizard: TTY gate, prompts, UUID validation, backup, atomic write, doctor hint
affects: [human verification — Task 3 checkpoint]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_make_questionary_mocks() — patches questionary.text/.password with answer list; avoids prompt_toolkit Win32 console dependency in tests"
    - "_is_tty() module-level helper — separates TTY check from sys.stdin for testability"
    - "monkeypatch.chdir(tmp_path) redirects ENV_PATH = Path('.env') writes in tests"

key-files:
  created: []
  modified:
    - heartbeat_gateway/commands/init.py
    - tests/cli/test_init.py

key-decisions:
  - "questionary cannot use CliRunner input= on Windows — prompt_toolkit requires Win32 console APIs; solution: patch questionary.text/.password with mock objects"
  - "_is_tty() helper function enables monkeypatching TTY detection without sys.stdin replacement by CliRunner"
  - "UUID a1b2c3d4-e5f6-7890-abcd-ef1234567890 is not valid UUID v4 (third group must start with 4); replaced with 550e8400-e29b-41d4-a716-446655440000 in tests"

requirements-completed: [INIT-01, INIT-02, INIT-03, INIT-04, INIT-05, INIT-06, INIT-07, INIT-08, INIT-09]

# Metrics
duration: 14min
completed: 2026-03-26
---

# Phase 2 Plan 02: gateway init wizard implementation Summary

**Full gateway init wizard: TTY gate, questionary prompts, UUID v4 validation, timestamped backup, atomic .env write, gateway doctor completion hint — 9 INIT requirements fully tested**

## Performance

- **Duration:** ~14 min
- **Started:** 2026-03-26T07:21:50Z
- **Completed:** 2026-03-26T07:36:00Z (pending human verify)
- **Tasks completed:** 2 of 3 (Task 3 = human-verify checkpoint)
- **Files modified:** 2

## Accomplishments

- Replaced NotImplementedError stub in `heartbeat_gateway/commands/init.py` with full wizard implementation
- TTY gate (`_is_tty()`) as first action — exits 1 with error message when not a terminal
- Sequential questionary prompts for all 8 GatewayConfig fields in correct order
- Linear UUID discovery instruction block (Cmd+K / Copy model UUID) before UUID prompt
- UUID v4 validation with `_validate_linear_uuid()` — re-prompts on invalid, accepts blank to skip
- `questionary.password()` for ANTHROPIC_API_KEY, LINEAR_SECRET, GITHUB_SECRET — no echo in tests
- `_backup_env()` creates `.env.backup.YYYYMMDD_HHMMSS` unconditionally before any disk write
- `_write_env()` creates file then upserts keys via `set_key()` — atomic: only called after in-memory validation
- Completion message: "Run gateway doctor to verify your configuration."
- Updated `tests/cli/test_init.py` — removed all 9 `@pytest.mark.xfail` decorators, added `_make_questionary_mocks()` helper, all 9 tests passing

## Task Commits

| Task | Name | Commit |
|------|------|--------|
| 1 | Implement gateway init wizard | `765b83b` |
| 2 | Flip xfail stubs to passing tests | `7db4435` |
| 3 | Human verify live terminal wizard | _awaiting checkpoint approval_ |

## Files Created/Modified

- `heartbeat_gateway/commands/init.py` — Full wizard implementation (174 → reformatted)
- `tests/cli/test_init.py` — 9 passing tests, xfail removed, mock questionary helper added

## Decisions Made

- `_is_tty()` module-level helper chosen so TTY check can be patched independently of `sys.stdin` (CliRunner replaces `sys.stdin` entirely during invocation, so `monkeypatch.setattr("sys.stdin.isatty", ...)` doesn't reach the command body)
- `_make_questionary_mocks()` conftest-free helper — patches `questionary.text`/`questionary.password` with answer-list mock on Windows where `prompt_toolkit` requires Win32 console APIs not available in CliRunner
- UUID `a1b2c3d4-e5f6-7890-abcd-ef1234567890` in original stubs is NOT valid UUID v4 (third group must start with 4); test corrected to use `550e8400-e29b-41d4-a716-446655440000`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] CliRunner + monkeypatch.setattr("sys.stdin.isatty") incompatibility on Windows**
- **Found during:** Task 2 (flip xfail stubs)
- **Issue:** CliRunner replaces `sys.stdin` with a new `_NamedTextIOWrapper` object during `isolation()`. Monkeypatching `sys.stdin.isatty` on the original stdin object has no effect inside the running command. All 5 tests that used `monkeypatch.setattr("sys.stdin.isatty", lambda: True)` saw the TTY gate fail and exit 1.
- **Fix:** Added `_is_tty()` module-level helper in `init.py`. Tests patch `heartbeat_gateway.commands.init._is_tty` instead. The test stubs' setup (monkeypatch target) was updated; assertions were not changed.
- **Files modified:** `heartbeat_gateway/commands/init.py`, `tests/cli/test_init.py`
- **Commit:** `765b83b`, `7db4435`

**2. [Rule 1 - Bug] prompt_toolkit Win32 console requirement in tests**
- **Found during:** Task 2 exploration — `questionary.password()` / `questionary.text()` calls inside CliRunner raise `NoConsoleScreenBufferError` on Windows because prompt_toolkit needs Win32 console APIs
- **Fix:** Added `_make_questionary_mocks()` helper that patches `questionary.text` and `questionary.password` to return `MagicMock` Question objects feeding from an answer list. Validation callbacks are still invoked.
- **Files modified:** `tests/cli/test_init.py`
- **Commit:** `7db4435`

**3. [Rule 1 - Bug] Invalid UUID in stub tests (INIT-03)**
- **Found during:** Task 2 — `a1b2c3d4-e5f6-7890-abcd-ef1234567890` fails UUID v4 validation because the third group `7890` starts with 7, not 4 (v4 requires `4xxx`)
- **Fix:** Replaced with valid UUID v4 `550e8400-e29b-41d4-a716-446655440000` (same UUID used in the plan's Task 2 template)
- **Files modified:** `tests/cli/test_init.py`
- **Commit:** `7db4435`

---

**Total deviations:** 3 auto-fixed (Rule 1 - bugs/incompatibilities)
**Impact on plan:** Test infrastructure approach updated; no scope change; all 9 assertions remain intact.

## Verification

- `uv run pytest tests/cli/test_init.py -v` → 9 PASSED (no xfail)
- `uv run pytest` → 159 passed, 1 xfailed (race condition), 0 failed
- `uv run ruff check .` → clean
- `uv run ruff format --check .` → clean
- `python -c "from heartbeat_gateway.commands.init import UUID_V4_PATTERN; print('ok')"` → ok
- No import from `heartbeat_gateway.app` or `heartbeat_gateway.commands.doctor` — confirmed

## Awaiting

Task 3 (human-verify): Run `uv run heartbeat-gateway init` in a real terminal to verify TTY rendering, password masking, UUID re-prompt behavior, backup creation, and completion message.

---
## Self-Check: PASSED

- heartbeat_gateway/commands/init.py — FOUND
- tests/cli/test_init.py — FOUND
- .planning/phases/02-gateway-init/02-02-SUMMARY.md — FOUND
- Commit 765b83b — FOUND
- Commit 7db4435 — FOUND

---
*Phase: 02-gateway-init*
*Completed: 2026-03-26 (Tasks 1-2; Task 3 awaiting human verify)*
