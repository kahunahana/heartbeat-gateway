# Roadmap: heartbeat-gateway v0.3.0

**Goal:** Close PG-1 and PG-2 so a new user can go from zero to verified configuration in 20 minutes, with no silent failures.

---

## Phase 1: CLI Foundation + gateway doctor

**Goal:** Wire the Click CLI group and deliver a fully functional `gateway doctor` command that validates all known silent failure modes with structured output, fix hints, and correct exit code discipline. Existing `heartbeat-gateway` entry point must remain unbroken.

**Requirements:** CLI-01, CLI-02, CLI-03, DOC-01, DOC-02, DOC-03, DOC-04, DOC-05, DOC-06, DOC-07, DOC-08, DOC-09, DOC-10, DOC-11, DOC-12

**Plans:** 2 plans

Plans:
- [ ] 01-01-PLAN.md — CLI foundation: Click group + pyproject.toml entry point + Wave 0 test stubs
- [ ] 01-02-PLAN.md — gateway doctor: 9 checks, rich output, --verbose, --env-file, tests flipped green

**Delivers:**
- `heartbeat_gateway/cli.py` — Click group with `invoke_without_command=True` fallback to uvicorn
- `heartbeat_gateway/commands/doctor.py` — DoctorRunner with 9 checks, each returning `CheckResult(name, status, message, fix_hint)`
- All four new explicit dependencies in `pyproject.toml`: click, rich, questionary, python-dotenv
- `tests/cli/test_doctor.py` — CliRunner-based tests using `monkeypatch.setenv`, not mocked GatewayConfig

**Constraints:**
- `commands/doctor.py` and `cli.py` must NOT import from `app.py`
- Every FAIL-level check must have a non-empty `fix_hint`
- Click group must be wired BEFORE any check logic is written (Step 1 → Step 2 → Step 3 build order)
- Bare `heartbeat-gateway` must still start uvicorn (no breaking change)

---

## Phase 2: gateway init

**Goal:** Deliver a fully functional `gateway init` wizard that guides users through `.env` configuration with TTY detection, inline UUID validation, merge-by-default `.env` handling, and atomic write after in-memory validation. Completion message directs user to `gateway doctor`.

**Requirements:** INIT-01, INIT-02, INIT-03, INIT-04, INIT-05, INIT-06, INIT-07, INIT-08, INIT-09

**Delivers:**
- `heartbeat_gateway/commands/init.py` — sequential questionary wizard with conditional adapter sections
- TTY detection at startup (exits cleanly if `sys.stdin.isatty()` is False)
- Linear UUID instruction block + inline v4 UUID regex validation with re-prompt on failure
- Timestamped `.env` backup before any overwrite; merge-by-default on re-run
- All inputs validated in-memory before any disk write (atomic write)
- `tests/cli/test_init.py` — CliRunner tests using `input=` for non-interactive execution

**Constraints:**
- Phase 2 depends on Phase 1 (Click group must exist; doctor must be trusted before init ships)
- TTY detection is the FIRST thing `gateway init` does — before any prompts
- UUID v4 regex: `^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$`
- `.env` backup must exist BEFORE any write, even on explicit confirm
- Do NOT add TUI frameworks (textual, urwid) — they break in tmux/SSH

---

## Phase Ordering Rationale

Doctor before init: `gateway init`'s completion message ("run `gateway doctor` to verify") requires doctor to be complete and trusted. A broken or absent doctor makes the init wizard's final instruction meaningless.

CLI group before everything: `cli.py` is the single prerequisite for both commands. Wire it and verify the existing entry point still works before writing a single check or prompt.

SOUL.md linter in doctor (Phase 1): PG-3 folds into doctor at zero additional cost. Two product gaps close for the price of one feature.

---

*Roadmap created: 2026-03-25*
*Source: REQUIREMENTS.md + .planning/research/SUMMARY.md*
*Plans added: 2026-03-25*
