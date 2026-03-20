# Configuration Reference

heartbeat-gateway is configured entirely through environment variables (or a `.env` file in the project root). All top-level settings use the `GATEWAY_` prefix.

---

## Top-Level Settings (`GatewayConfig`)

| Env Var                              | Type       | Default                       | Description |
|--------------------------------------|------------|-------------------------------|-------------|
| `GATEWAY_WORKSPACE_PATH`             | `Path`     | `~/workspace`                 | Directory where `HEARTBEAT.md`, `DELTA.md`, and `audit.log` are written. Created automatically if absent. |
| `GATEWAY_SOUL_MD_PATH`               | `Path`     | `~/workspace/SOUL.md`         | Path to the operator SOUL.md. The classifier reads the **first 500 characters** as context for every event. |
| `GATEWAY_LLM_MODEL`                  | `str`      | `claude-haiku-4-5-20251001`   | LiteLLM model string. Any LiteLLM-supported provider works (Anthropic, OpenAI, Gemini, local Ollama, etc.). |
| `ANTHROPIC_API_KEY`                  | `str`      | _(required)_                  | API key for the configured LLM. Rename to `OPENAI_API_KEY` etc. when switching providers. |
| `GATEWAY_HEARTBEAT_MAX_ACTIVE_TASKS` | `int`      | `20`                          | Soft limit on active tasks in HEARTBEAT.md before the writer logs a warning. Does not block writes. |
| `GATEWAY_AUDIT_LOG_PATH`             | `Path`     | `{workspace}/audit.log`       | Override the JSONL audit log location. Each line is a JSON record of every classification decision. |

---

## Watch Settings

Watch settings scope which events reach the classifier. Events outside the configured scope are dropped **before** any LLM call — zero cost.

### Linear (`LinearWatchConfig`)

Set these as a JSON object in `GATEWAY_WATCH` or use a `.env` file (see below).

| Field            | Type        | Default  | Description |
|------------------|-------------|----------|-------------|
| `project_ids`    | `list[str]` | `[]`     | Linear project IDs to watch. Empty list = watch all projects. |
| `assignee_filter`| `str`       | `"any"`  | `"self"` restricts to issues assigned to the configured user; `"any"` passes all. |
| `secret`         | `str`       | `""`     | Webhook signing secret from Linear settings. Empty = signature verification disabled (dev only). |

### GitHub (`GitHubWatchConfig`)

| Field          | Type        | Default      | Description |
|----------------|-------------|--------------|-------------|
| `repos`        | `list[str]` | `[]`         | Repos to watch in `owner/repo` format. Empty list = watch all repos. |
| `ci_workflows` | `list[str]` | `[]`         | CI workflow names to watch. Empty list = watch all workflows. |
| `branches`     | `list[str]` | `["main"]`   | Branches to watch for push and CI events. |
| `secret`       | `str`       | `""`         | Webhook signing secret from GitHub repo settings. |

### PostHog (`PostHogWatchConfig`)

| Field         | Type        | Default | Description |
|---------------|-------------|---------|-------------|
| `project_id`  | `str`       | `""`    | PostHog project ID. Empty = accept from any project. |
| `insight_ids` | `list[str]` | `[]`    | Insight IDs to watch for threshold alerts. Empty = watch all. |
| `secret`      | `str`       | `""`    | PostHog webhook signing secret. |

---

## .env File Example

Create `.env` in the project root. `uv run` loads it automatically via pydantic-settings.

```env
# Required
ANTHROPIC_API_KEY=sk-ant-api03-...

# Paths
GATEWAY_WORKSPACE_PATH=/home/agent/workspace
GATEWAY_SOUL_MD_PATH=/home/agent/workspace/SOUL.md

# LLM
GATEWAY_LLM_MODEL=claude-haiku-4-5-20251001

# Limits
GATEWAY_HEARTBEAT_MAX_ACTIVE_TASKS=20
```

---

## Switching LLM Providers

`GATEWAY_LLM_MODEL` accepts any [LiteLLM model string](https://docs.litellm.ai/docs/providers):

```env
# OpenAI
GATEWAY_LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...

# Gemini
GATEWAY_LLM_MODEL=gemini/gemini-1.5-flash
GEMINI_API_KEY=...

# Local Ollama
GATEWAY_LLM_MODEL=ollama/llama3.2
# No API key required
```

---

## Audit Log Format

When `GATEWAY_AUDIT_LOG_PATH` is set (or at the default location), every classification decision is appended as a JSON line:

```json
{"timestamp": "2025-01-15T14:32:00+00:00", "source": "github", "event_type": "ci.failure", "classification": "ACTIONABLE", "rationale": "CI failed on main — blocking current work", "condensed": "GitHub: CI 'test' failure on main — kahunahana/heartbeat-gateway"}
```

Fields: `timestamp`, `source`, `event_type`, `classification` (`ACTIONABLE`/`DELTA`/`IGNORE`), `rationale`, `condensed`.
