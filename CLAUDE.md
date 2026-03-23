# CLAUDE.md — heartbeat-gateway

Agent context for working on this codebase. Read this before touching code.

---

## What This Project Does

heartbeat-gateway is an event-driven webhook gateway that replaces cron polling for AI
agent workloads. It receives webhooks from Linear, GitHub, and PostHog, classifies them
against the operator's `SOUL.md`, and writes actionable items to `HEARTBEAT.md` — the
task queue consumed by OpenClaw and VikingBot agents.

**The 20x cost story:** cron polling costs ~$86/month at 30-minute intervals; event-driven
classification costs ~$4.50/month.

---

## Pipeline Architecture

```
Webhook → Adapter → PreFilter → Classifier (LLM) → Writer
                        ↑                ↑
                  zero LLM calls      SOUL.md
```

Five stages, in order:

1. **Adapter** — verifies HMAC signature, normalizes payload to `NormalizedEvent`,
   condenses to a 240-char summary for the LLM
2. **PreFilter** — repo/project/branch scoping with zero LLM calls; always-drop list
3. **Classifier** — LiteLLM reads SOUL.md (first 500 chars) + active HEARTBEAT.md tasks;
   returns `ACTIONABLE`, `DELTA`, or `IGNORE`
4. **HeartbeatWriter** — ACTIONABLE → `HEARTBEAT.md`; DELTA → `DELTA.md`;
   5-minute dedup window using URL first, then `ref:{payload_condensed}` fingerprint

---

## Critical Architectural Constraints

### SOUL.md is for priority/action rules ONLY

SOUL.md tells the classifier *what matters* — not *what to watch*. Never add scoping
rules ("only watch issues in project X") to SOUL.md. That is pre_filter's job.

When SOUL.md contains scoping rules, the classifier becomes non-deterministic and
fights with the pre_filter. This mistake was made and reverted during v0.2.0 hardening.

**SOUL.md should contain:** Current Focus, Projects, Watch escalation rules, Do Not Alert rules.
**SOUL.md must NOT contain:** Linear project UUIDs, branch names, repo filters.

### PreFilter owns scoping

All repo/project/branch filtering lives in `pre_filter.py`. It runs before any LLM call.
If an event reaches the classifier, assume the pre_filter already validated it belongs.

### Nested config models must be BaseModel, not BaseSettings

`GatewayConfig` (pydantic-settings) uses `env_nested_delimiter="__"` to load nested
watch config from environment variables (e.g. `GATEWAY_WATCH__LINEAR__SECRET`).

Nested models (`WatchConfig`, `LinearWatchConfig`, etc.) must be plain `BaseModel`.
If you make them `BaseSettings`, they instantiate independently via `default_factory`
and bypass `GatewayConfig`'s env loading entirely — all secrets silently become empty
strings. This was the root cause of the v0.2.0 security regression.

### Dedup fingerprint must be deterministic

`writer.py` deduplicates using `payload_condensed` (the 240-char adapter summary).
This field must come from the adapter's deterministic logic — never from LLM output.
LLM-generated titles caused every redelivery to create a duplicate entry (fixed in
commit `d36ca0c`).

---

## Known Product Gaps

These are documented; do not "fix" them in the wrong layer.

| Gap | Status | Notes |
|-----|--------|-------|
| PG-1: No onboarding wizard | Future phase | `gateway init` CLI |
| PG-2: No `gateway doctor` command | Future phase | Pre-flight config validator |
| PG-3: SOUL.md has no schema | Future phase | Linter/template to prevent scope-creep |
| PG-4: `condense()` uses team name not project name | **Fixed in v0.2.0** | commit `e84290a` |

---

## Development Workflow

### Running the test suite

```bash
uv run pytest          # 133 passed, 1 xfailed (134 total)
uv run ruff check .    # lint
uv run ruff format .   # format
```

**The xfailed test is intentional.** It demonstrates a race condition. Do not fix it.

CONTRIBUTING.md says "94 tests" — that is out of date. Current count: 134.

### Before opening a PR

- All CI checks must pass (`pytest` + `ruff check` + `ruff format --check`)
- Bug fixes must include a regression test (red-green verified)
- New features need tests
- Update `CHANGELOG.md` under `[Unreleased]`
- PR title follows Conventional Commits: `feat:`, `fix:`, `docs:`, `chore:`, `test:`
- One logical change per PR

### Adding a new adapter

Required checklist (see `docs/adapters.md` for full interface):
1. `verify_signature(payload: bytes, headers: dict) -> bool`
2. `normalize(payload: dict, headers: dict) -> NormalizedEvent | None`
3. Unit tests: valid normalization, signature pass/fail, always-drop events return `None`
4. Integration test fixture JSON in `tests/fixtures/`
5. Documentation update in `docs/adapters.md`

---

## Config Quick Reference

All env vars use `GATEWAY_` prefix. Nested watch config uses `__` delimiter.

```env
ANTHROPIC_API_KEY=sk-ant-...
GATEWAY_WORKSPACE_PATH=/home/user/workspace
GATEWAY_SOUL_MD_PATH=/home/user/workspace/SOUL.md
GATEWAY_LLM_MODEL=claude-haiku-4-5-20251001
GATEWAY_WATCH__LINEAR__SECRET=...
GATEWAY_WATCH__LINEAR__PROJECT_IDS=["uuid-here"]
GATEWAY_WATCH__GITHUB__SECRET=...
GATEWAY_WATCH__GITHUB__REPOS=["owner/repo"]
```

Startup log confirms which values loaded — check `journalctl -u heartbeat-gateway` for
`Linear project_ids filter: [...]` on boot.

---

## VPS Deployment (live instance)

| Component | Detail |
|-----------|--------|
| Host | `root@<your-vps-ip>` |
| Service | `systemctl status heartbeat-gateway` |
| Public endpoint | `https://hooks.kahako.ai` (Cloudflare tunnel, survives reboots) |
| Health check | `curl http://localhost:8080/health` → `{"status":"ok","version":"0.2.0"}` |
| Audit log | `tail -f /root/.openclaw/workspace/audit.log` |
| HEARTBEAT.md | `/root/.openclaw/workspace/HEARTBEAT.md` |
| SOUL.md | `/root/workspace/SOUL.md` |
| OpenClaw | `cd /root/openclaw && docker compose ps` |
| OpenClaw UI | SSH tunnel: `ssh -L 18789:localhost:18789 root@<your-vps-ip>`, then `http://localhost:18789` |

---

## Key Files

| File | Purpose |
|------|---------|
| `heartbeat_gateway/app.py` | FastAPI app, routes, startup config log |
| `heartbeat_gateway/pre_filter.py` | Scoping — drops events before LLM |
| `heartbeat_gateway/classifier.py` | LLM classification, SOUL.md context |
| `heartbeat_gateway/writer.py` | HEARTBEAT.md writer, dedup logic |
| `heartbeat_gateway/adapters/linear.py` | Linear adapter |
| `heartbeat_gateway/mcp_server.py` | MCP server: `read_heartbeat`, `read_delta`, `get_gateway_status`, `read_soul` |
| `heartbeat_gateway/config/schema.py` | GatewayConfig — BaseModel/BaseSettings constraint lives here |
| `heartbeat_gateway/prompts/classify.yaml` | LLM prompt template |
