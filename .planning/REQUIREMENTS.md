# Requirements: heartbeat-gateway v0.3.0

**Defined:** 2026-03-25
**Core Value:** A developer can deploy heartbeat-gateway and have AI agents receiving real-time classified webhook events within 20 minutes.

## v1 Requirements

### CLI Foundation

- [x] **CLI-01**: `heartbeat-gateway` bare invocation (no subcommand) continues to start the server — zero breaking change
- [x] **CLI-02**: Click added as explicit dependency in `pyproject.toml` (currently transitive only — fragile)
- [x] **CLI-03**: New `heartbeat_gateway/cli.py` entry point wires Click group; existing `app.py` untouched

### gateway doctor

- [x] **DOC-01**: `gateway doctor` runs all checks and exits 0 only if no FAIL-level issues found
- [x] **DOC-02**: Each check carries a `fix_hint` string shown inline on failure — not just "FAIL" with no guidance
- [x] **DOC-03**: Default output shows only WARN and FAIL; `--verbose` flag shows all checks including PASS
- [x] **DOC-04**: Check — config loads without `ValidationError` (catches nested BaseSettings regression)
- [x] **DOC-05**: Check — SOUL.md exists at configured path and is readable
- [x] **DOC-06**: Check — Anthropic API key present and matches `sk-ant-` prefix format
- [x] **DOC-07**: Check — HMAC secrets non-empty for each configured source (Linear, GitHub, PostHog)
- [x] **DOC-08**: Check — Linear `project_ids` parseable as valid UUID format (not just non-empty string)
- [x] **DOC-09**: Check — body size limit is ≥ 512KB (guards against 10KB regression)
- [x] **DOC-10**: Check — SOUL.md content linter warns if scoping patterns detected (repo names, UUIDs in SOUL.md — these belong in pre_filter)
- [x] **DOC-11**: Doctor tests use `monkeypatch.setenv` + `CliRunner` — no mocked `GatewayConfig` (guards against BaseSettings test blind spot)
- [x] **DOC-12**: `gateway doctor` accepts `--env-file <path>` flag for users with multiple environments

### gateway init

- [ ] **INIT-01**: `gateway init` detects non-TTY environment at startup and exits with a clear error message
- [ ] **INIT-02**: Wizard displays Linear UUID discovery instructions (Cmd+K → "Copy model UUID") before prompting for UUID input
- [ ] **INIT-03**: Linear project UUID input validated against UUID format regex before accepting — re-prompts on failure
- [ ] **INIT-04**: All secret/key inputs are masked (no terminal echo)
- [ ] **INIT-05**: Running `gateway init` when `.env` already exists creates a timestamped backup before writing
- [ ] **INIT-06**: All values validated in-memory before any file write (atomic: write only if all valid)
- [ ] **INIT-07**: Completion output shows next-step hint: `Run gateway doctor to verify your configuration`
- [ ] **INIT-08**: Questionary and python-dotenv added as explicit dependencies in `pyproject.toml`
- [ ] **INIT-09**: Init tests use `CliRunner` with `input=` for non-interactive test execution

## v2 Requirements

### Future phases

- **PG-05**: MCP server HTTP/SSE transport (replaces stdio — fixes SSH reliability issue)
- **DOC-RERUN**: `gateway init --rerun` prefills wizard from existing `.env` values
- **DOC-FIX**: `gateway doctor --fix` auto-remediates WARN-level issues where safe to do so
- **ADAPTER-SLACK**: Slack adapter (implement `verify_signature`, `normalize`, `condense`)
- **ADAPTER-SENTRY**: Sentry adapter
- **ADAPTER-PD**: PagerDuty adapter

## Out of Scope

| Feature | Reason |
|---------|--------|
| PostHog adapter | No active PostHog project to validate against; demand unconfirmed |
| Web UI / dashboard | Contradicts markdown-as-API design philosophy |
| OAuth browser flow in `gateway init` | Breaks SSH-only VPS target; secrets must be pasted |
| TUI framework (textual, urwid) | Break in tmux/SSH — exactly where gateway runs |
| Network connectivity tests in `gateway doctor` | Adds latency, creates false confidence, out of scope for config validation |
| Multi-tenant / SaaS | Single-operator tool by design |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CLI-01 | Phase 1 | Complete |
| CLI-02 | Phase 1 | Complete |
| CLI-03 | Phase 1 | Complete |
| DOC-01 | Phase 1 | Complete |
| DOC-02 | Phase 1 | Complete |
| DOC-03 | Phase 1 | Complete |
| DOC-04 | Phase 1 | Complete |
| DOC-05 | Phase 1 | Complete |
| DOC-06 | Phase 1 | Complete |
| DOC-07 | Phase 1 | Complete |
| DOC-08 | Phase 1 | Complete |
| DOC-09 | Phase 1 | Complete |
| DOC-10 | Phase 1 | Complete |
| DOC-11 | Phase 1 | Complete |
| DOC-12 | Phase 1 | Complete |
| INIT-01 | Phase 2 | Pending |
| INIT-02 | Phase 2 | Pending |
| INIT-03 | Phase 2 | Pending |
| INIT-04 | Phase 2 | Pending |
| INIT-05 | Phase 2 | Pending |
| INIT-06 | Phase 2 | Pending |
| INIT-07 | Phase 2 | Pending |
| INIT-08 | Phase 2 | Pending |
| INIT-09 | Phase 2 | Pending |

**Coverage:**
- v1 requirements: 24 total
- Mapped to phases: 24
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-25*
*Last updated: 2026-03-25 after Plan 02 execution — DOC-01 through DOC-12 complete*
