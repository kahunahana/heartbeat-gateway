# heartbeat-gateway

## What This Is

heartbeat-gateway is an open-source webhook gateway that replaces cron polling for AI agent workloads. It receives webhooks from Linear, GitHub, and PostHog, classifies each event against a plain-text `SOUL.md` file using an LLM, and writes actionable items to `HEARTBEAT.md` — the markdown task queue consumed by AI agents like OpenClaw and VikingBot. Designed for solo developers and small teams running AI agents on a VPS.

## Core Value

A developer can deploy heartbeat-gateway and have their AI agents receiving real-time, classified webhook events — instead of paying $86/month to poll for nothing — within 20 minutes.

## Requirements

### Validated

- ✓ Webhook ingestion from Linear, GitHub, PostHog — v0.2.0
- ✓ HMAC signature verification per adapter — v0.2.0
- ✓ Pre-filter scoping with zero LLM calls — v0.2.0
- ✓ LLM classification against SOUL.md (ACTIONABLE / DELTA / IGNORE) — v0.2.0
- ✓ HEARTBEAT.md writer with 5-minute dedup window — v0.2.0
- ✓ Audit log with full classification rationale — v0.2.0
- ✓ MCP server (read_heartbeat, read_delta, get_gateway_status, read_soul) — v0.2.0
- ✓ VPS deployment via systemd + Cloudflare tunnel — v0.2.0
- ✓ 134 passing tests, 1 intentional xfail — v0.2.0

### Active

- [ ] `gateway doctor` — pre-flight config validator that catches all known silent failure modes before first webhook
- [ ] `gateway init` — interactive setup CLI that guides users through `.env` configuration without requiring knowledge of Linear UUID formats or JSON syntax

### Out of Scope

- PostHog adapter (new source) — deferred to v0.3.0+ pending user feedback on whether demand exists
- Slack / PagerDuty / Sentry adapters — deferred; adapter interface is ready but demand unvalidated
- Web UI / dashboard — not aligned with markdown-as-API philosophy
- Multi-tenant / SaaS hosting — single-operator tool by design
- `gateway init` wizard for PostHog — deferred until PostHog adapter ships

## Context

- **Maintainer profile:** Solo technical PM (non-engineer). One maintainer. OSS project.
- **Target user:** Developer building AI agent systems on a VPS. Likely discovered via Medium post.
- **Deployment:** Python 3.11+, uv, systemd service, Cloudflare tunnel. Live at `https://hooks.kahako.ai`.
- **Current blocker to adoption:** Silent installation failures. Five bugs found during v0.2.0 hardening all share one trait — they produce no error, just wrong behavior. A new user has no way to know setup failed.
- **Publishing context:** Medium post about to drive traffic. LinkedIn post published. README updated. The next person who tries to install this needs a working path.
- **Known product gaps (documented in CLAUDE.md):** PG-1 (no init wizard), PG-2 (no doctor), PG-3 (no SOUL.md linter), PG-5 (MCP stdio transport unreliable over SSH).

## Constraints

- **Solo maintainer:** Every feature must have tests. No regressions. CI must stay green.
- **Python 3.11+, uv:** Stack is locked. No new runtime dependencies without strong justification.
- **Conventional Commits:** PR titles follow `feat:`, `fix:`, `docs:`, `chore:`, `test:` — enforced by convention.
- **litellm:** Pinned to `<1.82.7` pending BerriAI supply chain audit resolution (see BerriAI/litellm#24518).
- **No breaking changes to SOUL.md / HEARTBEAT.md interface:** Agents depend on these file formats.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Markdown as API (SOUL.md, HEARTBEAT.md) | Agents already read markdown; no API layer needed | ✓ Good |
| PreFilter before LLM | Cost reduction — LLM only fires on events that pass scoping | ✓ Good |
| BaseModel not BaseSettings for nested config | BaseSettings caused silent secret bypass (v0.2.0 regression) | ✓ Good |
| `payload_condensed` as dedup fingerprint | LLM output is non-deterministic; deterministic fingerprint required | ✓ Good |
| gateway doctor before gateway init | Doctor is tighter scope and unblocks Medium post readers immediately | — Pending |
| Plan doctor + wizard together | Complete onboarding story; doctor alone is only half the answer | — Pending |

---
*Last updated: 2026-03-25 after GSD initialization*
