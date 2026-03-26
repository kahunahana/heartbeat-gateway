# Domain Pitfalls: `gateway doctor` and `gateway init`

**Domain:** CLI config validator + interactive setup wizard for a Python webhook gateway
**Project:** heartbeat-gateway v0.3.0
**Researched:** 2026-03-25
**Overall confidence:** HIGH — grounded in actual codebase structure, real v0.2.0 failure modes, and verified CLI tooling behavior

---

## Critical Pitfalls

Mistakes that cause rewrites, silent failures, or first-time users abandoning the project.

---

### CRITICAL-1: Shallow Checks That Report "Present" Not "Valid"

**What goes wrong:** `gateway doctor` checks that a config key exists and reports a green checkmark. The key is present but wrong — a secret that fails HMAC verification, a project UUID that doesn't match any Linear project, an API key that's been rotated. The user sees "all checks passed" and then wonders why no events are classified.

**Why it happens:** Checking presence is three lines of code. Checking validity requires actually calling the service or simulating the behavior. Teams default to the easy check.

**Consequences:** The entire value proposition of `gateway doctor` is destroyed. Silent failure is the exact problem it was built to prevent. A doctor that says "your HMAC secret is set" when the secret is wrong gives the user false confidence that is worse than no doctor at all.

**For heartbeat-gateway specifically:**
- `GATEWAY_WATCH__LINEAR__SECRET` can be a non-empty string that is still wrong (wrong workspace, rotated key). The check must verify it is a plausible format (non-whitespace, reasonable length), not just `len(secret) > 0`.
- `GATEWAY_WATCH__LINEAR__PROJECT_IDS` is a JSON array of UUIDs. "Present" is not enough — the doctor must confirm each entry parses as a valid UUID (version 4, 36-char format), not just that the env var is non-empty.
- `ANTHROPIC_API_KEY` / `GATEWAY_LLM_API_KEY` must start with `sk-ant-` for Anthropic. Checking non-empty lets a placeholder like `YOUR_API_KEY_HERE` pass.
- `GATEWAY_SOUL_MD_PATH` must point to a file that **exists and is readable**, not just that the path string is non-empty.
- `GATEWAY_WORKSPACE_PATH` must be a directory with write permission — doctor must attempt `os.access(path, os.W_OK)`, not just `path.exists()`.

**Prevention:** For every check, ask: "If this value is present but wrong, does the check catch it?" Use a tiered check model — format validation, then existence/accessibility, then live connectivity where feasible.

**Detection:** Write a test where a plausible-but-wrong value is provided (e.g., a valid-format UUID that is not a real project). Doctor should fail, not pass.

**Phase relevance:** Phase 1 (gateway doctor implementation) — this is the primary design constraint.

---

### CRITICAL-2: No Fix Instructions in Output — Diagnosis Without Treatment

**What goes wrong:** Doctor reports `FAIL: SOUL.md not found at /root/workspace/SOUL.md` and stops. The user does not know what to do next.

**Why it happens:** It is easier to report the problem than to write the remediation text. Developers assume users will figure it out.

**Consequences:** Non-technical users (the explicit target: "developer who found this via a Medium post") abandon the setup. The problem is especially acute here because the errors are setup errors, not code errors — users need operational guidance, not stack traces.

**Real-world pattern:** `flutter doctor` and `brew doctor` both succeed because they output the exact command to fix each failure. `flutter doctor` outputs: `Run: flutter pub get`. `brew doctor` outputs: `Run: brew update && brew upgrade`. The command is in the fix message.

**For heartbeat-gateway specifically:**
- `SOUL.md not found` → fix message must say: `Copy the example: cp SOUL.md.example /root/workspace/SOUL.md`
- `ANTHROPIC_API_KEY missing` → fix message must say: `Add to your .env: ANTHROPIC_API_KEY=sk-ant-...` and point to `https://console.anthropic.com`
- `LINEAR project_ids empty` → fix message must say: In Linear, press Cmd+K → "Copy model UUID" on your project page, then add `GATEWAY_WATCH__LINEAR__PROJECT_IDS=["your-uuid-here"]`
- `BaseSettings env nested delimiter` loaded wrong → fix message must explain the double-underscore syntax explicitly

**Prevention:** Each check result struct must carry a `fix_hint: str` field. Never emit a FAIL without a `fix_hint`. Tests should assert on `fix_hint` being non-empty for every failure case.

**Detection:** Review every FAIL output path and confirm it includes a next action, not just a description of the problem.

**Phase relevance:** Phase 1 (gateway doctor), applies to every check.

---

### CRITICAL-3: `gateway init` Overwrites Existing `.env` Without Confirmation

**What goes wrong:** A user who has already configured the gateway runs `gateway init` again (to add GitHub after only setting up Linear). The wizard silently overwrites the `.env` file, losing the existing configuration.

**Why it happens:** The simplest implementation writes a new file at the end. Developers building wizards focus on the happy path (first-time user with no existing config) and forget the re-run case.

**Consequences:** Credentials lost, gateway broken. The user cannot easily recover the overwritten secrets. This is especially bad for HMAC secrets, which were generated on the Linear/GitHub side and cannot be retrieved again.

**Prevention:**
1. On wizard start, check if `.env` exists. If so, prompt: "An existing .env was found. Merge new values into it (recommended) or overwrite it entirely?"
2. Default to merge. Never default to overwrite.
3. Before writing anything, create a timestamped backup: `.env.backup.2026-03-25T12-00-00`
4. Use a merge strategy: read existing values, only prompt for keys that are not already set (unless user explicitly asks to update a key).

**Detection:** Run `gateway init` twice. Confirm that the second run offers a merge choice and does not silently overwrite the first run's values.

**Phase relevance:** Phase 2 (gateway init implementation).

---

### CRITICAL-4: Interactive Prompts That Break in Non-TTY Environments

**What goes wrong:** `gateway init` is run inside a `screen` session, via SSH with a non-interactive shell, or piped as part of a setup script. Click's `click.prompt()` raises a `UsageError` or hangs indefinitely because there is no TTY attached.

**Why it happens:** `click.prompt()` and `getpass` require a TTY. Non-interactive shells (systemd `ExecStartPre=`, CI pipelines, `docker run` without `-it`, SSH sessions without PTY allocation) do not provide one. This affects the target deployment context directly — heartbeat-gateway users run everything over SSH on a VPS.

**For heartbeat-gateway specifically:** The target user is SSH-ing into their VPS to run setup. If they are inside `tmux` or `screen`, TTY detection may behave differently depending on how the session was attached. The `gateway init` wizard must detect `sys.stdin.isatty()` at startup and emit a clear error: "This command requires an interactive terminal. Run it directly in an SSH session, not inside a script or pipe."

**Prevention:**
1. Check `sys.stdin.isatty()` at the start of `gateway init`. If False, exit with a clear message and exit code 1.
2. Do not attempt to fall back to non-interactive mode silently — partial wizard runs that write incomplete config are worse than no run.
3. Document in the README that `gateway init` must be run in an interactive terminal, not as part of a startup script.
4. `gateway doctor` must not have interactive prompts at all — it is purely read-only and must work in any context, including systemd's `ExecStartPre`.

**Detection:** `echo "" | gateway init` should fail with a clear message, not hang or crash with a traceback.

**Phase relevance:** Phase 2 (gateway init). Also applies to any future interactive subcommands.

---

### CRITICAL-5: The Linear UUID Problem — Asking Users for Something They Cannot Find

**What goes wrong:** The `gateway init` wizard asks: "Enter your Linear project IDs (comma-separated UUIDs):" and the user stares at the screen with no idea what a UUID is, where to find it, or whether to enter the project name instead.

**Why it happens:** Developers know what a UUID looks like. Target users often don't. The wizard was designed by someone who already knew the answer.

**Consequences:** Setup abandonment. This is the single highest-friction step in the entire onboarding because it requires the user to context-switch from the terminal to the Linear UI, navigate to a specific place, and perform a non-obvious action (Cmd+K → "Copy model UUID").

**For heartbeat-gateway specifically:**
The `GATEWAY_WATCH__LINEAR__PROJECT_IDS` env var expects a JSON array of UUIDs in version 4 format (e.g., `["550e8400-e29b-41d4-a716-446655440000"]`). New users will try to enter the project name, the team name, or the project URL instead.

**Prevention — multi-step approach:**
1. Before asking for UUIDs, display a framed instruction block:
   ```
   How to find your Linear Project UUID:
   1. Open Linear in your browser
   2. Navigate to your project
   3. Press Cmd+K (Mac) or Ctrl+K (Windows/Linux)
   4. Type "Copy" and select "Copy model UUID"
   5. Paste the UUID below

   It looks like this: 550e8400-e29b-41d4-a716-446655440000
   ```
2. Validate the input as a UUID (match against `^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$`) before accepting it.
3. If validation fails, show: "That doesn't look like a UUID. It should be 36 characters with hyphens, like: 550e8400-..." Do not accept non-UUID input.
4. Support comma-separated input for multiple projects, but validate each UUID individually.
5. Consider offering an optional Linear API key path that auto-discovers project UUIDs via `GET https://api.linear.app/graphql` — but treat this as a stretch goal, not core.

**Detection:** Enter "My Project" instead of a UUID. Wizard must reject it with a helpful message and re-prompt.

**Phase relevance:** Phase 2 (gateway init). This is the highest-UX-risk step in the entire wizard.

---

## Moderate Pitfalls

Mistakes that degrade reliability or cause confusion but do not block the core path.

---

### MODERATE-1: Wrong Exit Codes Break Scripted Deployments

**What goes wrong:** `gateway doctor` exits with code 0 even when checks fail, because the developer forgot that exit codes need explicit handling. Or it exits 1 on warnings that should be advisory, breaking scripts that treat any non-zero as fatal.

**Why it happens:** Python defaults to exit 0. Click uses `sys.exit()` only if you call it. Developers test interactively and don't notice the exit code.

**For heartbeat-gateway specifically:** A user running `gateway doctor && systemctl start heartbeat-gateway` must have the systemd start blocked when doctor fails. If doctor exits 0 on failure, the service starts with broken config, producing silent failures — the exact problem being solved.

**Prevention:**
- Exit 0: all checks pass (or only advisory warnings remain)
- Exit 1: one or more checks fail (config is broken)
- Exit 2: doctor itself failed to run (permission error, import failure)
- Test exit codes explicitly in pytest with `CliRunner` checking `result.exit_code`

**Detection:** Run `gateway doctor` with a deliberately broken config and `echo $?`. Must return 1.

**Phase relevance:** Phase 1 (gateway doctor).

---

### MODERATE-2: Tests That Mock the Config and Miss Real Loading Failures

**What goes wrong:** Tests for `gateway doctor` mock `load_config()` to return a pre-built `GatewayConfig` object. The doctor tests pass. But the real failure mode — `GatewayConfig()` raises a `ValidationError` when the env var `GATEWAY_WATCH__LINEAR__PROJECT_IDS` contains malformed JSON — is never tested because the config loading itself was bypassed.

**Why it happens:** Mocking config is the natural unit test approach. It isolates the check logic. But it also skips the most common failure path for real users.

**For heartbeat-gateway specifically:** The `BaseModel` / `BaseSettings` constraint (documented in CLAUDE.md) is itself a source of silent failures. `GatewayConfig()` can succeed but return empty secrets if nested models are accidentally promoted to `BaseSettings`. A test that mocks `GatewayConfig` entirely will never catch a regression on this constraint.

**Prevention:**
1. At least one integration-level test per doctor check should load config from actual env vars (using `monkeypatch.setenv`) rather than a pre-built object.
2. Add a specific test: set `GATEWAY_WATCH__LINEAR__PROJECT_IDS=not-valid-json`, call `load_config()`, confirm it raises or doctor catches and reports it.
3. Add a specific test: set `GATEWAY_WATCH__LINEAR__SECRET` on a nested model that accidentally became `BaseSettings`, confirm the value actually loads.

**Detection:** Remove all config mocks from doctor tests. How many break? Any that break reveal tests that weren't actually testing real behavior.

**Phase relevance:** Phase 1 (gateway doctor), ongoing.

---

### MODERATE-3: `gateway init` Input Is Written Before Validation

**What goes wrong:** The wizard collects all inputs, writes them to `.env`, then validates. If an API key fails format validation, the file has already been partially written with other values.

**Why it happens:** "Collect all inputs, then write" seems like a clean flow. Validation is often added as an afterthought after the write logic is in place.

**Consequences:** The `.env` file exists with some correct values and some invalid/placeholder values. When `gateway doctor` runs, it finds a partial config and reports failures on the values written without validation. The user is confused about what is correct and what is not.

**Prevention:** Validate all inputs before writing anything to disk. The flow must be:
1. Collect and validate all values in memory
2. Show a summary: "About to write these values to .env — confirm?"
3. Write atomically on confirmation

This also reduces the chance of partial writes from Ctrl+C interrupts during the wizard.

**Phase relevance:** Phase 2 (gateway init).

---

### MODERATE-4: SOUL.md Check Is Too Shallow

**What goes wrong:** `gateway doctor` checks that `SOUL.md` exists and is non-empty. It does not check whether SOUL.md contains scoping rules (Linear project UUIDs, branch names, repo filters) that belong in `pre_filter` instead. Users who follow the wrong pattern have a config that works but produces non-deterministic classifications — and no check warns them.

**Why it happens:** Checking file existence is easy. Checking content semantics requires knowing the domain rules.

**For heartbeat-gateway specifically:** CLAUDE.md explicitly documents this failure mode: "SOUL.md should contain: Current Focus, Projects, Watch escalation rules, Do Not Alert rules. SOUL.md must NOT contain: Linear project UUIDs, branch names, repo filters." Doctor (or a future SOUL.md linter as noted in PG-3) should warn when SOUL.md contains patterns that look like UUIDs or `repo:` / `branch:` prefixes.

**Prevention:** Add a SOUL.md content check that warns (not fails) when it detects:
- UUIDs matching `[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}` patterns
- Lines starting with `repo:`, `branch:`, `project_id:`

This is an advisory check (exit 0 with warning), not a hard failure.

**Phase relevance:** Phase 1 (gateway doctor), intersects with PG-3.

---

## Minor Pitfalls

Mistakes that reduce quality or create friction but are recoverable.

---

### MINOR-1: Doctor Output That Looks Like a Log, Not a Report

**What goes wrong:** Doctor emits output that looks like application log lines:
```
2026-03-25 12:00:00 INFO Checking API key...
2026-03-25 12:00:00 INFO API key found
2026-03-25 12:00:00 INFO Checking SOUL.md...
2026-03-25 12:00:00 ERROR SOUL.md not found
```
The user has to read every line to find the failure. There is no summary.

**Prevention:** Use a structured output format modeled after `flutter doctor`:
```
gateway doctor
  [OK]   ANTHROPIC_API_KEY — present, valid sk-ant- prefix
  [OK]   SOUL.md — found at /root/workspace/SOUL.md (847 chars)
  [FAIL] GATEWAY_WATCH__LINEAR__PROJECT_IDS — empty (no events will be scoped)
         Fix: Add at least one Linear project UUID. See docs/linear-setup.md
  [WARN] GATEWAY_WORKSPACE_PATH — directory exists but audit log is not configured

1 failure, 1 warning. Run 'gateway doctor --fix' for remediation steps.
```
Failures and warnings are immediately scannable. The summary line at the bottom tells the user the outcome without reading every check.

**Phase relevance:** Phase 1 (gateway doctor) — output format design.

---

### MINOR-2: `gateway init` Feels Like an Afterthought vs. First-Class Feature

**What goes wrong:** The wizard is bolted onto the CLI as a single `click.command()` that prompts for 8 values in sequence, with no grouping, no progress indication, no sense of what is optional vs. required. Users have no idea when it will end or whether they can skip sections.

**Prevention:**
1. Structure the wizard in sections (Anthropic config, Linear config, GitHub config, workspace paths) with section headers.
2. Mark optional steps explicitly: "(optional — press Enter to skip)"
3. Show a progress indicator: "Step 2 of 4"
4. At the end, show a summary of what was written and what was skipped.
5. The wizard should feel like it was built by someone who respects the user's time, not like `read -p "Enter API key: "` scripted into Python.

**Phase relevance:** Phase 2 (gateway init) — UX design.

---

### MINOR-3: `require_signatures=False` Is Not Flagged as a Security Warning

**What goes wrong:** `gateway doctor` sees `GATEWAY_REQUIRE_SIGNATURES=false` (or the default `False`) and reports no warning. A user who never sets up HMAC secrets is running an unauthenticated webhook endpoint open to the internet. Doctor silently accepts this.

**Prevention:** Add an advisory warning (not a failure) when:
- `require_signatures` is False
- AND at least one adapter (Linear, GitHub) has a non-empty `repos` or `project_ids` config
This indicates the user intends to receive webhooks but has not enabled signature verification.

Warning message: "GATEWAY_REQUIRE_SIGNATURES is False. Any request to your webhook endpoint will be processed. Set LINEAR and GitHub secrets to enable HMAC verification."

**Phase relevance:** Phase 1 (gateway doctor).

---

## Phase-Specific Warnings

| Phase / Topic | Likely Pitfall | Mitigation |
|---------------|---------------|------------|
| Phase 1: doctor check logic | Shallow presence checks that miss invalid-but-set values | Build a tiered check: format → existence → accessibility. Test with wrong-format values. |
| Phase 1: doctor output | Log-style output that buries failures | Use `[OK]` / `[FAIL]` / `[WARN]` structured lines with fix hints |
| Phase 1: doctor exit codes | Exit 0 on failure breaks `doctor && systemctl start` patterns | Explicitly test `result.exit_code` in CliRunner tests |
| Phase 1: doctor test mocking | Mocking `load_config()` skips real validation failure paths | Add at least one `monkeypatch.setenv` integration test per check |
| Phase 2: init overwrite | Silent `.env` overwrite on re-run destroys existing credentials | Detect existing file, default to merge, always create backup |
| Phase 2: init UUID input | Users enter project names, not UUIDs | Display how-to block before the prompt, validate UUID format, re-prompt on failure |
| Phase 2: init TTY | Wizard hangs or crashes in non-interactive shells (SSH, screen, pipe) | Check `sys.stdin.isatty()` at startup and exit cleanly if False |
| Phase 2: init write timing | Partial writes from validation-after-write pattern | Collect and validate all inputs in memory before any disk write |
| Both: SOUL.md | Doctor ignores SOUL.md content semantics (scoping rules in wrong place) | Advisory check for UUID patterns and scoping keywords in SOUL.md |
| Both: security posture | `require_signatures=False` silently accepted | Warn when signatures are disabled but adapters are configured |

---

## Sources

- heartbeat-gateway CLAUDE.md and schema.py — direct codebase evidence for BaseSettings regression, UUID format requirements, SOUL.md scope constraints
- [Flutter Doctor design — Medium](https://mailharshkhatri.medium.com/flutter-doctor-diagnosing-setup-problems-768bcf783ae4) — structured `[OK]`/`[FAIL]`/`[WARN]` output pattern with fix hints
- [Homebrew/brew diagnostic.rb](https://github.com/Homebrew/brew/blob/master/Library/Homebrew/diagnostic.rb) — fix-hint-per-check pattern
- [Click non-TTY issues — pallets/click #906](https://github.com/pallets/click/issues/906) — `getpass` / prompt failure without TTY
- [Linear UUID discovery — Linear Docs](https://linear.app/docs/api-and-webhooks) — Cmd+K "Copy model UUID" as the canonical path
- [Linear GraphQL API](https://developers.linear.app/docs/graphql/webhooks) — programmatic UUID discovery alternative
- [Pydantic Settings docs](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) — nested delimiter behavior that caused v0.2.0 regression
- [pytest mocking anti-patterns — pytest-with-eric](https://pytest-with-eric.com/mocking/pytest-common-mocking-problems/) — over-mocking misses integration failure paths
- [gemini-cli doctor issue #18692](https://github.com/google-gemini/gemini-cli/issues/18692) — real-world evidence of doctor commands lacking specific error context
- [Claude Code doctor issue #5563](https://github.com/anthropics/claude-code/issues/5563) — "show specific JSON parsing errors" — generic errors not actionable enough
