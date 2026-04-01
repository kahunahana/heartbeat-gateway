# Handoff
Generated: 2026-04-01T00:00:00Z  |  Context: ~82%  |  Session: adapter-expansion

## Goal
Start v0.4.0 milestone: add Amplitude, Braintrust, and LangSmith webhook adapters plus PostHog gateway init section — research complete, requirements committed, roadmapper running.

## Completed
- v0.3.0 fully shipped: gateway doctor + gateway init wizard — 159 tests passing, pushed to origin/main (commit `c4fc39a`)
- v0.4.0 milestone started: PROJECT.md updated, STATE.md reset
- Arize Phoenix deferred: OSS product has no outbound webhooks; Arize AX (hosted/paid) deferred to future
- 4 parallel research agents completed: STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md written
- SUMMARY.md synthesized and committed (commit `faf9893`)
- REQUIREMENTS.md written with 22 requirements across 4 categories (commit `e92b78a`)
- Roadmapper complete — ROADMAP.md written, phases 3–6, 26/26 requirements mapped (commit `d3dad9d`)

## Remaining
1. **Phase 3** — Schema Foundation + PostHog wizard section (`/gsd:plan-phase 3`)
4. **Phase 4** — Braintrust Adapter (`/gsd:plan-phase 4`)
5. **Phase 5** — LangSmith Adapter (`/gsd:plan-phase 5`)
6. **Phase 6** — Amplitude Adapter (`/gsd:plan-phase 6`)

## Key Files
- `.planning/PROJECT.md` — v0.4.0 milestone goals + requirements
- `.planning/REQUIREMENTS.md` — 22 requirements: FOUND-01–04, AMP-01–07, BTST-01–07, LSMT-01–08
- `.planning/ROADMAP.md` — phases 3–6 (roadmapper writing this now)
- `.planning/research/SUMMARY.md` — synthesized research findings
- `.planning/research/STACK.md` — auth schemes per platform
- `.planning/research/FEATURES.md` — event types and payload shapes
- `.planning/research/ARCHITECTURE.md` — integration points, build order
- `.planning/research/PITFALLS.md` — platform-specific risks
- `heartbeat_gateway/adapters/base.py` — WebhookAdapter ABC (verify_signature + normalize + condense)
- `heartbeat_gateway/adapters/posthog.py` — reference adapter implementation
- `heartbeat_gateway/config/schema.py` — GatewayConfig with WatchConfig (add new watch models here)
- `heartbeat_gateway/app.py` — FastAPI routes + adapter wiring
- `heartbeat_gateway/commands/init.py` — wizard (add new adapter sections here)

## How to Resume
1. `cd C:\Users\chadk\projects\heartbeat-gateway`
2. Check `git log --oneline -5` — last commit should be `e92b78a` (requirements) or later (roadmap)
3. Check `.planning/ROADMAP.md` exists and has Phase 3–6
4. Run `uv run pytest -q` — should show 159 passed, 1 xfailed
5. Say `/gsd:plan-phase 3` to begin Phase 3 (Schema Foundation + PostHog wizard)

## Decisions & Context

**Adapter auth summary (critical for implementation):**
- Braintrust: HMAC-SHA256 — exact header name UNKNOWN; must look up `braintrust.dev/docs/guides/automations` as first step of Phase 4
- LangSmith: custom header token `X-Langsmith-Secret` — NOT HMAC; `verify_signature()` compares header value to configured token
- Amplitude: NO signing at all — `verify_signature()` is a permanent passthrough returning `True`; document this in adapter docstring

**Critical Braintrust pitfall:** Every automation save sends `is_test: true`. `normalize()` must return `None` as its FIRST action when `payload.get("details", {}).get("is_test") == True` — otherwise every config change creates a phantom HEARTBEAT entry.

**Critical dedup constraint:** `condense()` must NEVER include timestamps or IDs — the dedup window compares `payload_condensed` strings; non-deterministic condensing breaks deduplication.

**Schema pattern (v0.2.0 lesson):** All new `WatchConfig` subclasses must be `BaseModel`, not `BaseSettings`. Making them `BaseSettings` causes them to instantiate independently, bypassing `GatewayConfig`'s env loading — all secrets silently become empty strings.

**LangSmith dataset webhooks:** Do NOT exist as of 2026-04-01. Documented in REQUIREMENTS.md as out-of-scope. Do not add a requirement for it.

**Test isolation:** `uv` auto-loads `.env` from project root into subprocess env — delete any test `.env` after wizard testing or integration tests will fail with 401 (HMAC secrets leak into test env).

**Phase numbering:** v0.3.0 used Phases 1–2. v0.4.0 starts at Phase 3.

**28 commits ahead of origin at start of this session** — push before starting Phase 3 if needed.
