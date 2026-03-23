# heartbeat-gateway

![Tests](https://img.shields.io/badge/tests-111%20passing-brightgreen)
![License](https://img.shields.io/badge/license-Apache--2.0-blue)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)

Event gateway that classifies webhooks from **Linear**, **GitHub**, and **PostHog** against your operator's `SOUL.md` and writes actionable items to `HEARTBEAT.md` — replacing cron polling with event-driven agent triggers for [OpenClaw](https://github.com/kahunahana/openclaw) and [VikingBot](https://github.com/kahunahana/vikingbot) agents.

```
Linear ──┐
GitHub ──┼──▶  /webhooks/{source}  ──▶  Adapter  ──▶  PreFilter  ──▶  Classifier (LLM)  ──▶  HEARTBEAT.md
PostHog ─┘                                                                 ▲
                                                                        SOUL.md
```

Every incoming event is:
1. **Verified** — HMAC signature checked per adapter
2. **Normalized** — condensed to a 240-char summary + structured metadata
3. **Pre-filtered** — repo/project/branch scoping with zero LLM calls
4. **Classified** — LLM reads SOUL.md context and returns `ACTIONABLE`, `DELTA`, or `IGNORE`
5. **Written** — actionable items land in `HEARTBEAT.md`; deltas go to `DELTA.md`

---

## Quickstart

### Step 1 — Install

```bash
git clone https://github.com/kahunahana/heartbeat-gateway
cd heartbeat-gateway
uv sync
```

### Step 2 — Configure SOUL.md

Create `~/workspace/SOUL.md` (the classifier reads the first 500 chars):

```markdown
## Current Focus

Phase 4: Webhook integration. Active branch: feature/webhooks.
Goal: ship Linear + GitHub adapters this sprint.

## Projects

- heartbeat-gateway (active)
- openclaw (planning)

## Watch

Escalate: CI failure on main, blocked issues in Linear team "Platform".
```

Then create a `.env` file in the project root:

```env
ANTHROPIC_API_KEY=sk-ant-...
GATEWAY_WORKSPACE_PATH=/home/youruser/workspace
GATEWAY_SOUL_MD_PATH=/home/youruser/workspace/SOUL.md
```

### Step 3 — Run

```bash
uv run uvicorn heartbeat_gateway.app:create_app --factory --host 0.0.0.0 --port 8080
```

Point your Linear, GitHub, and PostHog webhooks at:

| Source   | Local dev URL                              | Production URL (HTTPS required) |
|----------|--------------------------------------------|---------------------------------|
| Linear   | `http://localhost:8080/webhooks/linear`    | `https://your-host/webhooks/linear` |
| GitHub   | `http://localhost:8080/webhooks/github`    | `https://your-host/webhooks/github` |
| PostHog  | `http://localhost:8080/webhooks/posthog`   | `https://your-host/webhooks/posthog` |

> **Note:** The path is `/webhooks/` (plural). Using `/webhook/` (singular) will redirect automatically, but configure your webhook provider with the correct plural path to avoid the extra round-trip.

> **Production deployments:** Linear and PostHog require HTTPS. See [Deploying — Persistent Cloudflare Tunnel](docs/deploying.md#persistent-cloudflare-tunnel-recommended-for-vps) for the recommended setup.

Check health: `curl http://localhost:8080/health`

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    heartbeat-gateway                     │
│                                                         │
│  POST /webhooks/{source}                                │
│          │                                              │
│          ▼                                              │
│  ┌───────────────┐   verify_signature()                 │
│  │   Adapter     │   normalize() → NormalizedEvent      │
│  │ Linear/GH/PH  │   condense() → 240-char summary      │
│  └───────┬───────┘                                      │
│          │                                              │
│          ▼                                              │
│  ┌───────────────┐   always-drop list                   │
│  │   PreFilter   │   repo / project / branch scoping    │
│  └───────┬───────┘   (zero LLM calls)                  │
│          │                                              │
│          ▼                                              │
│  ┌───────────────┐   reads SOUL.md (first 500 chars)    │
│  │  Classifier   │   reads HEARTBEAT.md active tasks    │
│  │  (LiteLLM)    │   → ACTIONABLE / DELTA / IGNORE      │
│  └───────┬───────┘                                      │
│          │                                              │
│          ▼                                              │
│  ┌───────────────┐   ACTIONABLE → HEARTBEAT.md          │
│  │HeartbeatWriter│   DELTA      → DELTA.md              │
│  └───────────────┘   dedup window: 5 min               │
└─────────────────────────────────────────────────────────┘
```

---

## Configuration Reference

All settings use the `GATEWAY_` prefix as environment variables.

| Env Var                            | Default                         | Description                                        |
|------------------------------------|---------------------------------|----------------------------------------------------|
| `GATEWAY_WORKSPACE_PATH`           | `~/workspace`                   | Directory where `HEARTBEAT.md` and `DELTA.md` live |
| `GATEWAY_SOUL_MD_PATH`             | `~/workspace/SOUL.md`           | Path to your SOUL.md (first 500 chars fed to LLM)  |
| `GATEWAY_LLM_MODEL`                | `claude-haiku-4-5-20251001`     | LiteLLM model string (any provider)                |
| `ANTHROPIC_API_KEY`                | _(required)_                    | API key for the configured LLM model               |
| `GATEWAY_HEARTBEAT_MAX_ACTIVE_TASKS` | `20`                          | Max active tasks before writer warns               |
| `GATEWAY_AUDIT_LOG_PATH`           | `{workspace}/audit.log`         | JSONL audit log path (optional override)           |

See [docs/configuration.md](docs/configuration.md) for the full watch config reference.

---

## Example HEARTBEAT.md Output

```markdown
# Heartbeat Tasks

This file is managed by heartbeat-gateway.

## Active Tasks

<!-- heartbeat-gateway writes below this line -->
- [ ] [GITHUB:CI.FAILURE] CI failure on main — 3 tests failed in test_integration.py
      → https://github.com/kahunahana/heartbeat-gateway/actions/runs/12345 | 2025-01-15T14:32:00+00:00

- [ ] [LINEAR:ISSUE.STATUS_CHANGED] Auth bug moved to In Progress — needs review
      → https://linear.app/team/issue/PLT-42 | 2025-01-15T13:10:00+00:00

## Completed

<!-- Move completed tasks here or delete them -->
```

---

## Documentation

- [Configuration reference](docs/configuration.md)
- [Adapter setup (Linear, GitHub, PostHog)](docs/adapters.md)
- [Deploying (bare-metal, Docker, Railway)](docs/deploying.md)

---

## License

Apache-2.0 — see [LICENSE](LICENSE).
