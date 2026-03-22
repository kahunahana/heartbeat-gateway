# Adapter Setup

heartbeat-gateway ships three adapters. Each adapter:
1. Verifies the webhook HMAC signature
2. Normalizes the raw payload into a `NormalizedEvent`
3. Produces a ≤240-character condensed summary for the classifier

---

## Linear

**Webhook URL:** `https://your-gateway.example.com/webhooks/linear`

### Setup in Linear

1. Open Linear → Settings → API → Webhooks → **New webhook**
2. Set URL to your gateway's `/webhooks/linear` endpoint
3. Select events: **Issues** and **Comments**
4. Copy the signing secret and set `GATEWAY_WATCH__LINEAR__SECRET` in your `.env`

### Events Handled

| `event_type`              | Trigger |
|---------------------------|---------|
| `issue.created`           | New issue created |
| `issue.updated`           | Issue fields changed (non-status) |
| `issue.status_changed`    | Issue state transition (e.g. Todo → In Progress) |
| `issue.priority_changed`  | Issue priority changed |
| `comment.created`         | New comment on an issue |

All other Linear event types are dropped by the pre-filter before reaching the classifier.

### Scoping

```env
# Watch only these Linear project IDs (empty = watch all)
GATEWAY_WATCH__LINEAR__PROJECT_IDS=["proj_abc123","proj_def456"]

# Restrict to issues assigned to you
GATEWAY_WATCH__LINEAR__ASSIGNEE_FILTER=self
```

### Condensed Summary Examples

```
Linear: [Platform] Fix auth token refresh [Todo→In Progress]
Linear: [Platform] comment on 'Fix auth token refresh'
Linear: [Backend] Add retry middleware
```

---

## GitHub

**Webhook URL:** `https://your-gateway.example.com/webhooks/github`

### Setup in GitHub

1. Open repo → Settings → Webhooks → **Add webhook**
2. Set Payload URL to your gateway's `/webhooks/github` endpoint
3. Content type: `application/json`
4. Select events: **Pull requests**, **Check runs**, **Pushes**, **Issues**, **Pull request reviews**
5. Copy the secret and set `GATEWAY_WATCH__GITHUB__SECRET` in your `.env`

For org-wide coverage, set the webhook at the organization level instead.

### Events Handled

| `event_type`                   | GitHub Event        | Trigger |
|--------------------------------|---------------------|---------|
| `pr.opened`                    | `pull_request`      | PR opened |
| `pr.merged`                    | `pull_request`      | PR merged (closed + merged) |
| `pr.closed`                    | `pull_request`      | PR closed without merging |
| `pr.review_requested`          | `pull_request`      | Review requested on PR |
| `pr_review.approved`           | `pull_request_review` | PR approved |
| `pr_review.changes_requested`  | `pull_request_review` | Changes requested on PR |
| `ci.failure`                   | `check_run`         | CI check completed with `failure` |
| `ci.success`                   | `check_run`         | CI check completed with `success` |
| `push.{branch}`                | `push`              | Push to any branch (e.g. `push.main`) |
| `issue.opened`                 | `issues`            | GitHub issue opened |
| `issue.closed`                 | `issues`            | GitHub issue closed |

The following GitHub events are **always dropped** (pre-filter, zero LLM calls):
`watch`, `star`, `fork`, `ping`, `gollum`, `member`, `public`, `repository`

### Scoping

```env
# Only watch specific repos (owner/repo format). Empty = watch all.
GATEWAY_WATCH__GITHUB__REPOS=["kahunahana/heartbeat-gateway"]

# Only watch specific branches for push/CI events
GATEWAY_WATCH__GITHUB__BRANCHES=["main","release"]

# Only watch specific CI workflow names
GATEWAY_WATCH__GITHUB__CI_WORKFLOWS=["test","build"]
```

### Condensed Summary Examples

```
GitHub: CI 'test' failure on main — kahunahana/heartbeat-gateway
GitHub: PR #42 'Add retry middleware' merged — kahunahana/heartbeat-gateway
GitHub: PR #43 review approved — kahunahana/heartbeat-gateway
```

### Manual Testing

GitHub always sends `X-GitHub-Event` and `X-Hub-Signature-256` on real webhooks, but curl requests omit them by default — causing events to be silently ignored.

**Step 1 — Compute the HMAC signature:**

```bash
PAYLOAD='{"action":"opened","pull_request":{"title":"Test PR","head":{"ref":"feature/test"},"base":{"ref":"main"},"number":1,"html_url":"https://github.com/owner/repo/pull/1"},"repository":{"full_name":"owner/repo"}}'
SECRET=your-webhook-secret

SIG=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" | awk '{print "sha256="$2}')
```

**Step 2 — Send the request:**

```bash
curl -X POST http://localhost:8080/webhooks/github \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: pull_request" \
  -H "X-Hub-Signature-256: $SIG" \
  -d "$PAYLOAD"
```

**Other common `X-GitHub-Event` values for testing:**

| Event | `X-GitHub-Event` value |
|-------|------------------------|
| Pull request | `pull_request` |
| CI check run | `check_run` |
| Push | `push` |
| Issue | `issues` |
| PR review | `pull_request_review` |

> **Tip:** If the gateway returns `{"status":"ignored","reason":"unrecognized_event_type"}`, the adapter returned `None` — check that `X-GitHub-Event` matches one of the handled events above and that the payload structure is correct.

---

## PostHog

**Destination URL:** `https://your-gateway.example.com/webhooks/posthog`

PostHog uses "Destinations" (formerly webhooks) for event-driven notifications.

### Setup in PostHog

1. Open PostHog → Data Pipeline → Destinations → **New destination** → Webhook
2. Set URL to your gateway's `/webhooks/posthog` endpoint
3. Configure which events or insights trigger the destination
4. Set a signing secret and add `GATEWAY_WATCH__POSTHOG__SECRET` to your `.env`

For **insight threshold alerts**: PostHog → Insights → Alert → configure threshold → set destination URL.

### Events Handled

| `event_type`                  | PostHog Trigger |
|-------------------------------|-----------------|
| `insight.threshold`           | Insight metric crossed a configured threshold |
| `error.spike`                 | Error event count spike detected |
| `feature_flag.{flag_key}`     | Feature flag called (e.g. `feature_flag.new-checkout`) |

The following PostHog event types are **always dropped** before classification:
`$pageview`, `$autocapture`, `$pageleave`, `$set`, `$identify`

### Condensed Summary Examples

```
PostHog: insight 'Daily Active Users' threshold crossed — 1250 vs 1000
PostHog: error spike in '$exception' — 142 occurrences
PostHog: feature flag 'new-checkout' called
```

---

## Adding a New Adapter

Each adapter requires changes to 5 files. Work in this order:

### Step 1 — Create `heartbeat_gateway/adapters/{name}.py`

Must subclass `WebhookAdapter` and implement:
- `verify_signature(payload: bytes, headers: dict) -> bool`
  - Return `True` if no secret configured (dev-friendly default)
  - Use `hmac.new(secret.encode(), payload, hashlib.sha256)` for HMAC verification
- `normalize(payload: dict, headers: dict) -> NormalizedEvent | None`
  - Return `None` for unrecognized event types (handled gracefully by server)
  - Set `payload_condensed` to max 240 chars — this is what the LLM sees
- `condense(payload: dict) -> str`
  - Produce the 240-char condensed summary used in `normalize()`

### Step 2 — Add WatchConfig in `heartbeat_gateway/config/schema.py`

```python
class {Name}WatchConfig(BaseSettings):
    model_config = {"extra": "ignore"}
    secret: str = ""
    # Add platform-specific scoping fields here (e.g., project_ids, repos)
```

Add to `WatchConfig`:
```python
{name}: {Name}WatchConfig = Field(default_factory={Name}WatchConfig)
```

### Step 3 — Add scoping rules in `heartbeat_gateway/pre_filter.py`

If the platform supports scoping (project IDs, repos, etc.), add a scoping check in `PreFilter.should_drop()`. Pattern: `if watched and event_value and event_value not in watched: return True, "out_of_scope"`.

### Step 4 — Wire into `heartbeat_gateway/app.py`

In `create_app()`:
```python
from heartbeat_gateway.adapters.{name} import {Name}Adapter
app.state.{name}_adapter = {Name}Adapter(config)
```

Add route:
```python
@app.post("/webhooks/{name}")
async def {name}_webhook(request: Request):
    return await _process_webhook(request, "{name}")
```

### Step 5 — Add tests

- `tests/fixtures/{name}_{event_type}.json` — real webhook payload examples
- `tests/test_integration.py` — at minimum one ACTIONABLE and one always-drop test

### Always-drop list

Add platform-specific noise events to `PreFilter.ALWAYS_DROP` in `pre_filter.py`:
```python
"{name}": ["{high-volume-event-type}", ...]
```
