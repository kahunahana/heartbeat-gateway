# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2026-04-05

### Added
- **Braintrust adapter** — `/webhooks/braintrust` with permanent-passthrough signature verification, `logs` and `environment_update` event normalization, `is_test` delivery suppression
- **LangSmith adapter** — `/webhooks/langsmith` with `X-Langsmith-Secret` token auth (timing-safe), three payload shapes: run errors (Shape B kwargs), negative feedback (Shape A rules), alert threshold crossings; clean-run suppression for high-volume noise
- **Amplitude adapter** — `/webhooks/amplitude` with permanent-passthrough signature verification, `monitor_alert` → ACTIONABLE and `chart.annotation` → DELTA normalization, empty-charts guard
- **`gateway doctor` WARN** for Amplitude when `GATEWAY_REQUIRE_SIGNATURES=true` — advises IP allowlisting since Amplitude has no webhook signing
- `NormalizedEvent.source` Literal expanded to include `"braintrust"`, `"langsmith"`, `"amplitude"`
- 13 E2E integration tests covering full pipeline (POST → adapter → classifier → writer) for all three new adapters
- `gateway init` wizard sections for Braintrust (BTQL automation instructions), LangSmith (`X-Langsmith-Secret` header setup), and Amplitude (no-signing warning)
- `docs/adapters.md` documentation for all three new adapters

### Changed
- Adapter checkbox in `gateway init` switched to unchecked-by-default with empty-selection guard (UX fix: pre-checked caused Space to toggle OFF instead of ON)
- Test count: 236 passed, 1 xfailed (up from 187 at v0.3.0)

## [0.3.0] - 2026-04-02

### Added
- **`gateway doctor` command** — pre-flight config validator with 10 checks (secrets, paths, LLM connectivity, permissions)
- **`gateway init` wizard** — interactive `.env` configuration with TTY detection, inline UUID validation, merge-by-default, atomic write
- `AmplitudeWatchConfig`, `BraintrustWatchConfig`, `LangSmithWatchConfig` schema models (config foundation for v0.4.0 adapters)
- PostHog section in `gateway init` wizard

## [0.1.1] - 2026-03-21

### Fixed
- Dedup now works for URL-less events (e.g. CI failures) using title fingerprint fallback
- Audit log (`audit.log`) now written for every classified event (ACTIONABLE/DELTA/IGNORE)

### Added
- Integration test: PostHog insight threshold alert → ACTIONABLE
- Integration test: CI failure duplicate dedup verification
- Integration test: audit log written on ACTIONABLE event
- Phase 9: MCP server with `read_heartbeat`, `read_delta`, `read_soul`, `get_gateway_status` tools
- Adapter extensibility guide: complete 5-step checklist in `docs/adapters.md`

## [0.1.0] - 2026-03-19

### Added
- FastAPI webhook server with `/webhooks/linear`, `/webhooks/github`, `/webhooks/posthog`, and `/health` routes
- **Pre-filter**: zero-LLM-cost noise gate with always-drop list and repo/branch/project scoping
- **Webhook adapters**: `LinearAdapter`, `GitHubAdapter`, `PostHogAdapter` with HMAC-SHA256 signature verification
- **Classifier**: SOUL.md-aware LLM classification via LiteLLM returning `ACTIONABLE`, `DELTA`, or `IGNORE`
- **HeartbeatWriter**: writes to `HEARTBEAT.md` and `DELTA.md` with 5-minute URL-based deduplication window
- 94 tests across unit (86) and integration (8) suites; zero mocked LLM calls in integration tests
- Operator documentation: README quickstart, configuration reference, adapter setup guide, deployment guide
- `Dockerfile` and `docker-compose.yml` examples; Railway and Render deployment instructions
- `.env.example` with all `GATEWAY_*` configuration options
- `SOUL.md.example` annotated template showing the three classifier-read sections

[Unreleased]: https://github.com/kahunahana/heartbeat-gateway/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/kahunahana/heartbeat-gateway/releases/tag/v0.1.0
