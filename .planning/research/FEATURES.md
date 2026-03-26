# Feature Landscape: `gateway doctor` and `gateway init`

**Domain:** Developer CLI tooling — config validator and interactive setup wizard
**Project:** heartbeat-gateway v0.3.0
**Researched:** 2026-03-25
**Overall confidence:** HIGH (npm doctor, expo doctor, wp-cli doctor, react-native doctor, fly launch, AlgoKit init — all directly inspected)

---

## `gateway doctor` — Pre-Flight Config Validator

### What Users Expect (Prior Art)

The doctor pattern is well-established: `brew doctor`, `npm doctor`, `react-native doctor`, `expo doctor`, `wp-cli doctor`. The common thread is a command that runs a named series of independent checks, reports PASS/WARN/FAIL per-check with human-readable messages, exits non-zero if any check fails, and tells you what to do next.

Key design insight from **expo doctor PR #34729 (2024):** Show only failing checks by default. When everything passes, say so with a summary count. Showing every green check in a long list buries the failures. Add `--verbose` to show all checks.

---

### Table Stakes

Features where absence makes the command feel broken or untrustworthy.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Named per-check output | Users need to know which check failed, not just "something is wrong" | Low | Each check has a short name: `api_key_present`, `soul_md_readable`, etc. |
| Three-state status: PASS / WARN / FAIL | `npm doctor`, `wp-cli doctor`, `expo doctor` all use this model. WARN = non-fatal but attention-needed. | Low | WARN for optional config; FAIL for blockers |
| Exit code 0 on all-pass, non-zero on any FAIL | Standard UNIX contract. Scripts that call `gateway doctor && start service` depend on this. `gh auth status` exit code bugs are still open issues years later — get this right from day one. | Low | WARN-only should also exit 0 |
| Actionable error messages | "HMAC secret is empty" is not enough. "Set GATEWAY_WATCH__LINEAR__SECRET in your .env and restart." is the minimum bar. React Native doctor shows a link to manual fix instructions when it can't auto-fix. | Low | Every FAIL message must include the env var name or file path to fix |
| Checks cover all five known silent failure modes | This is the whole reason the command exists. PG-2 was opened because those failures produce no error — just wrong behavior. A doctor that misses them is useless. | Medium | The five failure modes from v0.2.0 hardening must map to explicit checks |
| Summary line at end | "3 checks passed, 1 failed." Users scan to the bottom. `expo doctor` tweaked messaging to show totals so users get orientation even when verbose is off. | Low | Always print summary regardless of verbosity |
| Works without a running server | Doctor is a pre-flight tool. It must run before `uvicorn` starts. If it requires the server to be up, it fails at exactly the moment it's most needed. | Low | Pure config inspection, no HTTP calls |

### Differentiators

Features that make `gateway doctor` excellent rather than merely functional.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Check groups / categories | Group checks by concern: `[Environment]`, `[Files]`, `[Adapters]`, `[LLM]`. Expo and react-native doctor both use categories. Makes long output scannable. | Low | Four natural groups for heartbeat-gateway |
| SOUL.md content linter (PG-3) | Checks that SOUL.md exists, is non-empty, and does NOT contain env var patterns or UUIDs (the anti-pattern documented in CLAUDE.md). This is unique to heartbeat-gateway — no other tool does this. | Medium | Regex check for `GATEWAY_` patterns and UUID-like strings inside SOUL.md |
| Hint: "run gateway init" when env is missing | If `GATEWAY_WATCH__LINEAR__SECRET` is absent, doctor should say "Run `gateway init` to configure." Contextual next-step hints are what separate great CLIs from functional ones. | Low | Static hint text per check failure |
| `--fix` flag for auto-resolvable issues | React Native doctor auto-fixes what it can. For heartbeat-gateway this is narrow: creating missing directories (`GATEWAY_WORKSPACE_PATH` doesn't exist → offer to create it). Don't over-reach. | Medium | Only implement for 1-2 checks where fix is truly safe |
| `--json` output for CI/scripting | `gh auth status --json hosts` pattern. Makes doctor pipeable. Solo maintainer, so this is low priority — but it costs nothing if the check runner already returns structured data. | Low | If checks are data structures internally, JSON output is a thin wrapper |
| Check for HEARTBEAT.md write permissions | If the workspace path exists but isn't writable, the gateway will fail silently on first webhook. Brew doctor checks directory write permissions — this is the same idea. | Low | `os.access(path, os.W_OK)` |

### Anti-Features

Things to deliberately NOT build for `gateway doctor`.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Network connectivity tests (ping Anthropic API, test Linear webhook) | Adds latency, requires network, fails in CI, gives false confidence (key can be valid and quota-exhausted). npm doctor dropped network checks in later versions for similar reasons. | Validate key format/presence only; real connectivity is validated on first webhook |
| Auto-fix everything | React Native doctor auto-fixes only what is safe and clear. Auto-fix for secrets (rewriting .env) is dangerous — it's destructive and users lose context. | Fix only filesystem structure (create missing dirs); prompt user for everything else |
| Doctor as a long-running daemon / watch mode | Scope creep. This is a point-in-time diagnostic. | Stateless one-shot command only |
| Version compatibility matrix checks | Checking Python version, uv version, systemd version adds maintenance burden. The stack is locked (Python 3.11+). | Document requirements; let startup fail with an informative message |
| Scoring / percentage health score | Gamification of config state. Tools that do this (some SaaS health dashboards) get gamed or ignored. | Binary: pass all checks = green light. Any FAIL = red light. |

---

## `gateway init` — Interactive Setup Wizard

### What Users Expect (Prior Art)

The init wizard pattern is set by `fly launch`, `railway init`, `stripe login`, `create-react-app`, and AlgoKit init. The common contract: ask questions one at a time in a logical order, show defaults, validate answers inline, write a config file at the end, and confirm what was written. The user should be able to copy-paste the result and have a working system.

Key insight from AlgoKit init v2 architecture decision (2024): avoid technical jargon in question text. "What is your Linear webhook HMAC secret?" is better than "Enter value for GATEWAY_WATCH__LINEAR__SECRET". The env var name goes in the written file; the user doesn't need to know it during the wizard.

Key insight from `fly launch`: generate the config file (fly.toml / .env) and then show the user what was written. Don't just silently create it.

---

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Guided questions in logical order | Users arrive from a Medium post. They don't know what `GATEWAY_WATCH__LINEAR__SECRET` means. Questions must be ordered: workspace first, then LLM key, then adapter secrets. | Low | Order: workspace path → LLM model → Linear secret + project IDs → GitHub secret + repos |
| Password masking for secrets | Every secret input must mask characters. questionary supports `password()` prompt type. Showing a secret in plaintext while typing is a CWE-312 class mistake. | Low | Use `questionary.password()` or equivalent for all `_SECRET` and `_KEY` fields |
| Inline validation with re-prompt | If user enters a malformed value, re-prompt immediately with the reason. Don't write a bad .env. AlgoKit copies .env.template and prompts for empty values — same idea. | Medium | UUID format check for Linear project IDs; non-empty check for secrets |
| Default values shown and accepted on Enter | Standard wizard UX. `fly launch` defaults to nearest region. Show sane defaults: `GATEWAY_LLM_MODEL=claude-haiku-4-5-20251001`, workspace path = `~/workspace`. | Low | Pull defaults from `config/schema.py` where they already exist |
| Skip if .env already exists, with confirm-to-overwrite | CLIG best practice: idempotent operations. If `.env` exists, ask "Overwrite existing config?" before proceeding. Never silently clobber. AWS copilot-cli had an open issue about non-idempotent init for years. | Low | `os.path.exists(".env")` check before writing anything |
| Show what was written at the end | `fly launch` downloads the config file and confirms the path. Users need to see "Written to /path/to/.env" and the key names (not values) that were set. | Low | Print env var names written; never print secret values |
| Actionable next step printed on completion | "Now run: gateway doctor to verify your configuration." This is the single most-cited differentiator in CLI UX writing — tell the user what to do next. | Low | Static next-steps block at end |
| Works without the gateway running | Same constraint as doctor. Init is pre-deployment. | Low | Pure file write; no HTTP |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Linear UUID format helper | Linear project IDs are UUIDs. Users arriving from a Medium post don't know the format. A prompt that says "Enter UUID (format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)" with inline format validation is a small addition that eliminates a common misconfiguration. This is unique to heartbeat-gateway's domain. | Low | Regex validate UUID format; show example |
| Conditional adapter sections | If user says "I don't use GitHub webhooks," skip the GitHub section entirely. `fly launch` language scanners skip sections based on project type. AlgoKit init's bidirectional query design does this. Keeps the wizard short for users with one adapter. | Medium | Ask "Which adapters will you use?" as multi-select at start; skip unchecked sections |
| `--dry-run` flag | Print what would be written to stdout without writing the file. Useful for users who manage .env with a secrets manager (Vault, doppler) and want to see the template. | Low | Renders the env content to stdout with placeholder values |
| Re-run safety: prefill from existing .env | If user runs `gateway init` again (e.g., to add GitHub after Linear), prefill existing values so they don't have to re-enter them. Show current value, allow override or Enter-to-keep. | High | Parse existing .env before prompting; complexity warrants deferral |
| SOUL.md template creation | If SOUL.md doesn't exist at the configured path, offer to create a starter template with the correct structure and explicit warning not to add scoping rules. This directly prevents PG-3 (SOUL.md has no schema). | Medium | Write a templated SOUL.md if missing and user confirms |

### Anti-Features

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| PostHog adapter wizard | PostHog adapter doesn't exist yet (deferred in PROJECT.md). Building the wizard without the adapter is dead code. | Add PostHog wizard section when the adapter ships |
| OAuth / browser-based auth flow | `railway login` opens a browser tab. heartbeat-gateway uses static env var secrets. Browser flow adds dependency on a redirect server and breaks SSH-only VPS setups (the target environment). | Static env var entry only |
| Secret validation against live APIs (test LLM call on init) | Adds latency, spends quota, fails with network issues, and creates a misleading "all good" signal when quota is actually exhausted. Stripe CLI does validate on `stripe login` — but it's specifically an auth command where validation is the whole point. init is not an auth command. | Doctor checks format; first real webhook validates connectivity |
| Generating systemd unit files or Cloudflare tunnel config | These are infrastructure concerns outside the gateway's config boundary. fly launch generates fly.toml because Fly owns the infra layer. heartbeat-gateway doesn't own the VPS or tunnel. | Point to docs for systemd + tunnel setup |
| Interactive TUI (full-screen terminal UI) | textual/urwid-style apps require terminal capability detection, don't work well in tmux/SSH, and add a dependency. The target is a VPS over SSH. | Simple sequential prompt flow; no TUI framework |
| Saving answers to a non-.env format (YAML, TOML, JSON) | heartbeat-gateway reads `.env` via pydantic-settings. A different format would require config schema changes and adds a parallel config path. | Write `.env` only |

---

## Cross-Cutting Features (Both Commands)

| Feature | Applies To | Complexity | Notes |
|---------|------------|------------|-------|
| `--help` that explains what the command does, not just flags | Both | Low | CLIG standard: `--help` output should describe purpose, not just enumerate options |
| No color when stdout is not a TTY | Both | Low | Respect `NO_COLOR` env var and pipe detection. `rich` handles this automatically with `force_terminal` detection |
| Clear section headers in output | Both | Low | Rich `Console` panels or simple `---` separators; makes output readable in `journalctl` logs |
| Python 3.11+ only, no new runtime dependencies | Both | N/A | Constraint from PROJECT.md. Use `questionary` (already popular in Python CLI ecosystem) and `rich` (already used in Python tooling). Both are pure-Python, no native extensions. |

---

## Feature Dependencies

```
gateway init → writes .env
gateway doctor → reads .env (must exist before doctor runs, or doctor explains it's missing)
gateway doctor (SOUL.md linter) → requires SOUL.md path from config → requires .env
gateway init (SOUL.md template) → creates SOUL.md if missing → doctor SOUL.md check passes

Logical order for new users:
  gateway init → gateway doctor → start service
```

---

## MVP Recommendation

### `gateway doctor` MVP (unblocks Medium post readers)

Build these checks for v0.3.0:

1. `ANTHROPIC_API_KEY` present and non-empty
2. `GATEWAY_WORKSPACE_PATH` is set, exists, and is writable
3. `GATEWAY_SOUL_MD_PATH` is set and the file exists and is non-empty
4. At least one adapter secret is set (Linear or GitHub — not both required)
5. Linear `PROJECT_IDS` parses as valid JSON array of UUIDs (if Linear secret is set)
6. GitHub `REPOS` parses as valid JSON array of `owner/repo` strings (if GitHub secret is set)
7. SOUL.md does not contain `GATEWAY_` env var patterns (scope-creep anti-pattern)
8. `HEARTBEAT.md` parent directory exists and is writable

Exit code 0 = all pass. Exit code 1 = any FAIL. WARN = exits 0.
Show only failures by default. Add `--verbose` for all checks.
Print `gateway doctor` summary count always.
Print "Run `gateway init` to fix missing config." as footer if any FAIL.

### `gateway init` MVP

1. Multi-select: which adapters? (Linear, GitHub)
2. Workspace path (default: `~/workspace`)
3. SOUL.md path (default: `{workspace}/SOUL.md`)
4. LLM model (default: `claude-haiku-4-5-20251001`)
5. Anthropic API key (masked, required)
6. Linear section (if selected): HMAC secret (masked), project IDs (validated UUID array)
7. GitHub section (if selected): HMAC secret (masked), repos (validated `owner/repo` array)
8. Confirm-to-overwrite if `.env` exists
9. Write `.env`
10. Print key names written (not values)
11. Print next step: `gateway doctor`

### Defer to Later

- `--fix` flag on doctor (safe directory creation)
- `--json` output on doctor
- Re-run prefill from existing .env (high complexity)
- SOUL.md template creation in init
- PostHog wizard section (adapter doesn't exist yet)

---

## Sources

- [npm doctor — npm Docs](https://docs.npmjs.com/cli/v7/commands/npm-doctor/) — HIGH confidence (official)
- [Meet Doctor, a new React Native command](https://reactnative.dev/blog/2019/11/18/react-native-doctor) — HIGH confidence (official React Native blog)
- [expo doctor: Show only failed checks by default, add verbose option — PR #34729](https://github.com/expo/expo/pull/34729) — HIGH confidence (official repo)
- [WP-CLI doctor command](https://github.com/wp-cli/doctor-command) — HIGH confidence (official repo)
- [Default doctor diagnostic checks — WP-CLI](https://make.wordpress.org/cli/handbook/guides/doctor/doctor-default-checks/) — HIGH confidence (official docs)
- [Fly Launch overview — Fly Docs](https://fly.io/docs/reference/fly-launch/) — HIGH confidence (official docs)
- [AlgoKit init wizard v2 architecture decision 2024](https://developer.algorand.org/docs/get-details/algokit/architecture-decisions/2024-01-23_init-wizard-v2/) — HIGH confidence (official ADR)
- [Command Line Interface Guidelines — clig.dev](https://clig.dev/) — HIGH confidence (authoritative reference)
- [gh auth status exit code issues — GitHub CLI](https://github.com/cli/cli/issues/8845) — MEDIUM confidence (issue thread)
- [gh auth status: enable machine parsing — GitHub CLI](https://github.com/cli/cli/issues/9326) — MEDIUM confidence (issue thread)
- [questionary — PyPI](https://pypi.org/project/questionary/) — HIGH confidence (official)
- [Make "app init" idempotent — AWS copilot-cli issue #552](https://github.com/aws/copilot-cli/issues/552) — MEDIUM confidence (issue thread, pattern validation)
- [UX patterns for CLI tools — Lucas F. Costa](https://lucasfcosta.com/2022/06/01/ux-patterns-cli-tools.html) — MEDIUM confidence (practitioner post, widely cited)
