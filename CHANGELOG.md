# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Dedup now works for URL-less events (e.g. CI failures) using title fingerprint fallback
- Audit log (`audit.log`) now written for every classified event (ACTIONABLE/DELTA/IGNORE)

### Added
- Integration test: PostHog insight threshold alert → ACTIONABLE
- Integration test: CI failure duplicate dedup verification
- Integration test: audit log written on ACTIONABLE event

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
