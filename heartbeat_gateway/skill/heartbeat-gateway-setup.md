---
name: heartbeat-gateway-setup
description: Use when a user is setting up, configuring, or verifying heartbeat-gateway — fresh install, installed but not configured, or configured but not yet tested with real webhooks.
---

# heartbeat-gateway Setup

## Overview

heartbeat-gateway is a webhook-to-LLM classifier that translates events from GitHub, Linear, and PostHog into `HEARTBEAT.md` entries for AI agents to act on. This skill walks you through setup conversationally.

**Core mental model:** The classifier reads your `SOUL.md` to decide what matters. If SOUL.md doesn't say "CI failures on main are critical," they won't be flagged ACTIONABLE. Write SOUL.md first — it is the most important config.

---

## Step 0: Identify Your Scenario

Ask the user:

> "Which describes you best?
> 1. **Fresh install** — nothing set up yet
> 2. **Installed, not configured** — gateway runs but SOUL.md is a placeholder
> 3. **Configured, not verified** — secrets set but no real webhook tested end-to-end"

Route to the matching section below.

---

## Scenario 1: Fresh Install

### 1a. Platform

Ask: "Where are you deploying? (VPS / local dev / Railway / Render)"

For **VPS** (most common): all commands run as `root@<your-ip>` via SSH.
For **local dev**: replace VPS paths with local paths; skip systemd.

### 1b. Install

```bash
pip install git+https://github.com/kahunahana/heartbeat-gateway@main
# or, from clone:
uv sync
```

Verify:
```bash
curl http://localhost:8080/health
# → {"status":"ok","version":"0.1.1"}
```

### 1c. Draft SOUL.md (do this first — it drives signal quality)

Ask the user these 3 questions:

1. "What are you currently shipping? (e.g., 'fixing auth bugs, launching new billing flow')"
2. "Which events should wake up your agent? (e.g., 'CI failures on main, blocked Linear issues, error rate spikes')"
3. "What should be silently ignored? (e.g., 'stars, passing CI, comments on closed issues')"

Then generate a ready-to-paste SOUL.md:

```markdown
# SOUL

## Current Focus
{answer to Q1 — 1-2 sentences, present tense}

## Projects
- {primary project} — GitHub: {owner}/{repo}

## Watch
- GitHub: {owner}/{repo}, {branch} branch only
- Linear: all issues in {project name}
- PostHog: error rate thresholds only
- Alert on: {answer to Q2}

## Do Not Alert On
- {answer to Q3}
```

**Critical:** The classifier reads the **first 500 characters**. Lead with the most important context. Verify with:
```bash
head -c 500 /path/to/workspace/SOUL.md
```

Write it to your workspace path and set `GATEWAY_SOUL_MD_PATH` to point there.

### 1d. Generate .env

Ask: "Which platforms are you watching?" (GitHub / Linear / PostHog — pick all that apply)

Generate a ready-to-paste `.env` block using pydantic-settings **double-underscore** nested format:

```bash
# ── Required ──────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY=sk-ant-...           # Or GATEWAY_LLM_API_KEY if using LiteLLM alias
GATEWAY_WORKSPACE_PATH=/root/workspace
GATEWAY_SOUL_MD_PATH=/root/workspace/SOUL.md

# ── LLM (optional — defaults to Claude Haiku) ─────────────────────────────────
# GATEWAY_LLM_MODEL=claude-haiku-4-5-20251001

# ── GitHub (if watching GitHub) ───────────────────────────────────────────────
GATEWAY_WATCH__GITHUB__SECRET=<generate: python -c "import secrets; print(secrets.token_hex(32))">
GATEWAY_WATCH__GITHUB__REPOS=owner/repo
GATEWAY_WATCH__GITHUB__BRANCHES=main

# ── Linear (if watching Linear) ───────────────────────────────────────────────
GATEWAY_WATCH__LINEAR__SECRET=<generate: python -c "import secrets; print(secrets.token_hex(32))">
# GATEWAY_WATCH__LINEAR__PROJECT_IDS=proj-123,proj-456   # optional scoping

# ── PostHog (if watching PostHog) ─────────────────────────────────────────────
GATEWAY_WATCH__POSTHOG__SECRET=<generate: python -c "import secrets; print(secrets.token_hex(32))">
# GATEWAY_WATCH__POSTHOG__PROJECT_ID=proj-001            # optional scoping
```

⚠️ **Note the double underscores** (`GATEWAY_WATCH__GITHUB__SECRET`) — single underscore won't work. This is pydantic-settings' nested config format.

Generate each secret with:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```
Save secrets in your password manager — not in any markdown file.

### 1e. Start the service

**VPS (systemd — survives reboots):**
```bash
mkdir -p /root/workspace   # create workspace dir before starting
cat > /etc/systemd/system/heartbeat-gateway.service << 'EOF'
[Unit]
Description=heartbeat-gateway webhook processor
After=network.target

[Service]
Type=exec
User=root
WorkingDirectory=/root/heartbeat-gateway
EnvironmentFile=/root/heartbeat-gateway/.env
ExecStart=/root/.local/bin/uv run uvicorn heartbeat_gateway.app:create_app --factory --host 0.0.0.0 --port 8080
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable heartbeat-gateway
systemctl start heartbeat-gateway
```

**Local dev:**
```bash
uv run uvicorn heartbeat_gateway.app:create_app --factory --host 0.0.0.0 --port 8080
```

⚠️ **VPS firewall:** Port 8080 is now exposed to the internet. HMAC signature verification is the security gate — requests with invalid signatures return 401. Optionally restrict with UFW:
```bash
ufw allow 22/tcp && ufw allow 8080/tcp && ufw --force enable
```

Verify:
```bash
curl http://localhost:8080/health   # on VPS
curl http://<vps-ip>:8080/health    # from outside
```

### 1f. Register webhooks

For each platform the user is watching:

**GitHub:**
- Go to `https://github.com/{owner}/{repo}/settings/hooks` → Add webhook
- Payload URL: `http://<vps-ip>:8080/webhooks/github`
- Content type: `application/json`
- Secret: value of `GATEWAY_WATCH__GITHUB__SECRET`
- Events: Pull requests, Check runs, Pushes, Issues

**Linear:**
- Workspace Settings → Security & Integrations → Webhooks → Create webhook
  *(Linear UI path: top-left menu → Settings → API → Webhooks)*
- URL: `http://<vps-ip>:8080/webhooks/linear`
- Secret: value of `GATEWAY_WATCH__LINEAR__SECRET`
- Events: Issues, Comments

**PostHog:**
- Alerts → Create alert → set webhook URL to `http://<vps-ip>:8080/webhooks/posthog`
- Use `GATEWAY_WATCH__POSTHOG__SECRET` if PostHog supports webhook signing

### 1g. Verify end-to-end (see Scenario 3)

---

## Scenario 2: Installed, Not Configured

Gateway runs but SOUL.md has placeholder content. Go to **Step 1c** (SOUL.md draft) and then **Step 1d** (.env) to fill in real values. Then restart:
```bash
systemctl restart heartbeat-gateway
```

---

## Scenario 3: Configured, Not Verified

Test the full pipeline end-to-end:

**Step 1:** Send a test webhook
```bash
# GitHub — trigger a real event by pushing a trivial commit
git commit --allow-empty -m "test: trigger heartbeat verification" && git push

# Linear — move any issue to "Blocked" status in the UI

# PostHog — trigger a threshold alert (or send a manual webhook if you have the secret)
```

**Step 2:** Watch the logs
```bash
journalctl -u heartbeat-gateway -f   # VPS
# or: uv run uvicorn ... (watch stdout for local)
```

Expected log flow:
```
Received github webhook
Pre-filter: passed (not dropped)
Classifier: ACTIONABLE — "CI failure on main requires attention"
Writer: wrote to HEARTBEAT.md
```

**Step 3:** Verify HEARTBEAT.md was written
```bash
cat /root/workspace/HEARTBEAT.md
# → should show: - [ ] [GITHUB:...] {title}
cat /root/workspace/audit.log
# → should show JSONL record with classification, source, rationale
```

**Step 4:** Check GitHub delivery logs (if using GitHub)
- `https://github.com/{owner}/{repo}/settings/hooks` → Recent Deliveries
- All should show HTTP 200

**You're done when:** `HEARTBEAT.md` updates reliably on real events and `audit.log` records each classification. At that point, point your AI agent at the workspace directory and it will pick up tasks from HEARTBEAT.md automatically.

**If nothing appears in HEARTBEAT.md:**
1. Check audit.log — was the event classified IGNORE? If so, update SOUL.md to flag it.
2. Check logs for pre-filter drops — the event might be out of scope (wrong repo/branch).
3. Check logs for HMAC failures — secret in `.env` must exactly match the secret registered in the webhook provider.

---

## Quick Reference

| Env var | Purpose | Example |
|---------|---------|---------|
| `ANTHROPIC_API_KEY` | LLM API key | `sk-ant-...` |
| `GATEWAY_WORKSPACE_PATH` | Where HEARTBEAT.md lives | `/root/workspace` |
| `GATEWAY_SOUL_MD_PATH` | Where SOUL.md lives | `/root/workspace/SOUL.md` |
| `GATEWAY_WATCH__GITHUB__SECRET` | GitHub webhook HMAC secret | 32-byte hex |
| `GATEWAY_WATCH__GITHUB__REPOS` | Repos to watch | `owner/repo` |
| `GATEWAY_WATCH__LINEAR__SECRET` | Linear webhook HMAC secret | 32-byte hex |
| `GATEWAY_WATCH__POSTHOG__SECRET` | PostHog webhook HMAC secret | 32-byte hex |

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Liveness check |
| `POST /webhooks/github` | GitHub webhook receiver |
| `POST /webhooks/linear` | Linear webhook receiver |
| `POST /webhooks/posthog` | PostHog webhook receiver |

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Single underscore in env vars (`GATEWAY_WATCH_GITHUB_SECRET`) | Use double underscore: `GATEWAY_WATCH__GITHUB__SECRET` |
| SOUL.md too generic | The classifier only flags what SOUL.md says matters. Be specific. |
| Secret in `.env` doesn't match provider | Copy-paste exactly — no extra spaces or newlines |
| Port 8080 blocked by firewall | Run `ufw allow 8080/tcp` on VPS |
| HEARTBEAT.md not updated | Check `audit.log` — event may have been classified IGNORE |
