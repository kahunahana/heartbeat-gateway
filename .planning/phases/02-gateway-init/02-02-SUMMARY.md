---
phase: 02-gateway-init
plan: 02
subsystem: cli
tags: [click, questionary, python-dotenv, tdd, wizard, init]

# Dependency graph
requires:
  - phase: 02-gateway-init, plan: 01
    provides: 9 xfail stubs (INIT-01 through INIT-09), init.py stub, cli.py registration
provides:
  - Full gateway init wizard — TTY gate, masked secrets, UUID validation, backup, atomic write
  - 9 passing tests (xfail decorators removed)
  - Human-verified live terminal behavior
affects: [Phase 2 complete — PG-1 closed; operator can run gateway init then gateway doctor]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "questionary prompts patched via monkeypatch.setattr on questionary.text/.password — CliRunner cannot drive prompt_toolkit on Windows"
    - "_is_tty() module-level helper wraps sys.stdin.isatty() — monkeypatchable; sys.stdin itself is replaced by CliRunner"
    - "strip().strip('\"\'') normalises user-pasted paths — Windows users habitually add quotes around paths with spaces"
    - "set_key(quote_mode='auto') from python-dotenv; _write_env() clears file first then upserts keys"

key-files:
  modified:
    - heartbeat_gateway/commands/init.py
    - tests/cli/test_init.py

key-decisions:
  - "UUID_V4_PATTERN defined as module-level constant in init.py — NOT imported from doctor.py to avoid cross-command coupling"
  - "_backup_env() runs unconditionally before any write — HMAC secrets unrecoverable if overwritten without backup"
  - "quote stripping added after human verify — questionary on Windows echoes user-typed quotes into the stored value"
  - "Completion message changed from prose to labelled command with uv run prefix — prose caused user to run 'Run:' as a shell command"
  - "doctor --env-file flag required because GatewayConfig (BaseSettings) reads from process env, not from .env in CWD by default"

requirements-completed: [INIT-01, INIT-02, INIT-03, INIT-04, INIT-05, INIT-06, INIT-07, INIT-08, INIT-09]

# Metrics
duration: ~30min (including human verify iteration)
completed: 2026-03-31
---

# Phase 2 Plan 02: gateway init wizard implementation Summary

**Full @click.command('init') wizard implemented, all 9 xfail stubs flipped to passing, human-verified in live terminal**

## Performance

- **Duration:** ~30 min (including human verify iteration)
- **Completed:** 2026-03-31
- **Tasks:** 3 (Task 1: implement, Task 2: flip stubs, Task 3: human verify)
- **Files modified:** 2

## Accomplishments

- Replaced `NotImplementedError` stub in `init.py` with full wizard: TTY gate, masked secret prompts, UUID v4 validation with inline re-prompt, timestamped `.env` backup, atomic write via python-dotenv `set_key`, and completion hint
- Removed all 9 `@pytest.mark.xfail` decorators from `test_init.py` — all tests pass against the implementation
- Human verify confirmed: UUID re-prompt works, secrets masked, backup created, `.env` written, doctor reads values correctly with `--env-file`
- Full suite: 159 passed, 1 xfailed (intentional race condition), 0 failed

## Task Commits

1. **Task 1: Implement gateway init wizard** — `765b83b`
2. **Task 2: Flip 9 xfail stubs to passing** — `7db4435`
3. **Task 3: Human verify + post-verify fixes** — this commit

## Files Created/Modified

- `heartbeat_gateway/commands/init.py` — Full wizard with quote-stripping path normalisation and `uv run` completion hint
- `tests/cli/test_init.py` — xfail decorators removed; all 9 tests passing

## Decisions Made

- `_is_tty()` module-level helper used instead of inline `sys.stdin.isatty()` — CliRunner replaces `sys.stdin` entirely, so the helper is the reliable patch point
- `questionary.text` and `questionary.password` patched with mock objects in tests — prompt_toolkit requires Win32 console APIs; `CliRunner(input=...)` cannot drive them on Windows
- `shutil.copy2()` for backup (preserves metadata timestamps) over `shutil.copy()`

## Deviations from Plan

### Found during human verify

**1. [Bug] Quoted path values stored literally**
- **Found during:** Task 3 human verify
- **Issue:** User typed `"C:\path with spaces"` with surrounding quotes; `strip()` only removes whitespace, leaving `"` embedded in the stored value; pydantic-settings received an invalid path
- **Fix:** `workspace_path.strip().strip("\"'")` and same for `soul_md_path`
- **Files modified:** `heartbeat_gateway/commands/init.py`

**2. [UX] Completion message formatted as prose, not shell command**
- **Found during:** Task 3 human verify
- **Issue:** `Run gateway doctor to verify your configuration.` — user attempted to run `Run:` as a shell command; also missing `uv run` prefix and `--env-file` flag required to load `.env`
- **Fix:** Replaced with: `Verify your configuration:\n  uv run heartbeat-gateway doctor --env-file .env`
- **Files modified:** `heartbeat_gateway/commands/init.py`

**3. [Environment] Test `.env` leaked into integration suite via uv auto-loading**
- **Found during:** Task 3 post-verify cleanup
- **Issue:** uv auto-loads `.env` from project root into subprocess env; `GATEWAY_WATCH__LINEAR__SECRET` from wizard test caused integration tests to get 401 (HMAC enforced, test payloads unsigned)
- **Fix:** Delete `.env` from project root after wizard testing; `.env` is gitignored
- **Carry-forward:** Integration test fixtures should explicitly zero secrets for robustness

---

**Total deviations:** 3 (2 bugs fixed, 1 environment note / carry-forward)
**Impact on plan:** All bugs fixed before commit. No scope change.

## Phase 2 Complete

- PG-1 (no onboarding wizard) — **CLOSED**
- PG-2 (no gateway doctor) — **CLOSED** (Phase 1)
- Both CLI commands (`init` + `doctor`) ship in v0.3.0
- New operator flow: `uv run heartbeat-gateway init` → `uv run heartbeat-gateway doctor --env-file .env` → deploy

---
*Phase: 02-gateway-init*
*Completed: 2026-03-31*
