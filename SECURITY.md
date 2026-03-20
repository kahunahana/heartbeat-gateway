# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅        |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Use [GitHub's private vulnerability reporting](https://github.com/kahunahana/heartbeat-gateway/security/advisories/new) to report confidentially.

Please include:
- A description of the vulnerability and its potential impact
- Steps to reproduce
- Affected version(s)
- Any suggested mitigations

We will acknowledge your report within 48 hours and aim to publish a fix within 14 days for confirmed issues.

## Webhook Secrets

heartbeat-gateway receives webhooks from Linear, GitHub, and PostHog over public HTTP endpoints. **Always configure signing secrets for all three adapters** to prevent event injection:

```env
GATEWAY_WATCH__LINEAR__SECRET=your-linear-webhook-secret
GATEWAY_WATCH__GITHUB__SECRET=your-github-webhook-secret
GATEWAY_WATCH__POSTHOG__SECRET=your-posthog-webhook-secret
```

Without secrets, anyone who can reach your endpoint can write arbitrary entries to `HEARTBEAT.md`. Signature verification is skipped only when a secret is absent — this is intentional for local development but **must not be used in production**.

## API Key Handling

- `ANTHROPIC_API_KEY` (and other LLM provider keys) are loaded from environment variables via pydantic-settings
- Keys are never written to disk, logged, or included in LLM prompts
- `.env` is in `.gitignore` — never commit a file containing real credentials

## Network Exposure

heartbeat-gateway binds to `0.0.0.0` by default. In production:
- Run behind a reverse proxy (nginx, Caddy, Traefik) that terminates TLS
- Restrict inbound traffic to known webhook source IP ranges where possible (Linear, GitHub, PostHog publish their IP lists)
- Use the `/health` endpoint for load balancer checks only — do not expose it as a public API
