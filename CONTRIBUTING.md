# Contributing to heartbeat-gateway

Thank you for your interest in contributing. This document covers setup, workflow, and expectations.

## Getting Started

**Requirements:** Python 3.11+, [uv](https://docs.astral.sh/uv/)

```bash
git clone https://github.com/kahunahana/heartbeat-gateway
cd heartbeat-gateway
uv sync --extra dev
```

## Running Tests

```bash
uv run pytest
```

Tests are split into unit tests (adapters, pre-filter, classifier, writer, server) and integration tests (`tests/test_integration.py`) that run the full pipeline with real file I/O and a mocked LLM. All 94 tests must pass before merging.

## Code Style

We use [ruff](https://docs.astral.sh/ruff/) for linting and formatting (line length: 120, target: Python 3.11):

```bash
uv run ruff check .       # lint
uv run ruff format .      # format
uv run ruff format --check .  # CI check (no writes)
```

Both checks run in CI on every push and PR. Fix violations before opening a PR.

## Adding a New Adapter

See [docs/adapters.md](docs/adapters.md#adding-a-new-adapter) for the full adapter interface and registration steps.

New adapters require:
- `verify_signature(payload: bytes, headers: dict) -> bool` — HMAC verification; `True` when no secret is configured
- `normalize(payload: dict, headers: dict) -> NormalizedEvent | None` — returns `None` for unrecognized events
- Unit tests with at minimum: valid event normalization, signature verification pass/fail, always-drop events returning `None`
- An integration test fixture JSON in `tests/fixtures/`
- Documentation additions to `docs/adapters.md`

## Pull Request Guidelines

- **One logical change per PR** — keep scope tight
- **All CI checks must pass** before requesting review
- **New features need tests**; bug fixes should include a regression test
- **Update `CHANGELOG.md`** under `[Unreleased]` with a brief summary
- PR titles should follow [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`, `chore:`, `test:`

## Reporting Bugs

Use the [bug report issue template](.github/ISSUE_TEMPLATE/bug_report.md). Include:
- heartbeat-gateway version
- Python version and OS
- Minimal reproduction steps
- Actual vs. expected behavior

## Suggesting Features

Use the [feature request issue template](.github/ISSUE_TEMPLATE/feature_request.md). The most impactful contributions are new adapters (Jira, Slack, PagerDuty, Sentry) and improvements to the classifier prompt.

## License

By contributing, you agree that your contributions will be licensed under the [Apache-2.0 license](LICENSE).
