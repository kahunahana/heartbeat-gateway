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

1. **Create** `heartbeat_gateway/adapters/your_source.py` extending `WebhookAdapter`:

```python
from heartbeat_gateway import NormalizedEvent
from heartbeat_gateway.adapters.base import WebhookAdapter
from heartbeat_gateway.config.schema import GatewayConfig


class YourSourceAdapter(WebhookAdapter):
    def __init__(self, config: GatewayConfig) -> None:
        self.config = config

    def verify_signature(self, payload: bytes, headers: dict) -> bool:
        # Return True if no secret configured (dev mode)
        secret = self.config.watch.your_source.secret
        if not secret:
            return True
        # Implement HMAC verification matching your source's scheme
        ...

    def normalize(self, payload: dict, headers: dict) -> NormalizedEvent | None:
        # Return None for unrecognized event types
        event_type = self._classify(payload)
        if event_type is None:
            return None
        return NormalizedEvent(
            source="your_source",
            event_type=event_type,
            payload_condensed=self.condense(payload),
            raw_payload=payload,
            timestamp=...,
            metadata={},
        )

    def condense(self, payload: dict) -> str:
        return f"YourSource: {payload.get('summary', '')}"[:240]
```

2. **Add** a `YourSourceWatchConfig` to `heartbeat_gateway/config/schema.py` and include it in `WatchConfig`.

3. **Register** in `heartbeat_gateway/app.py`:
   - Import the adapter
   - Add `app.state.your_source_adapter = YourSourceAdapter(config)` in `create_app()`
   - Add a `@app.post("/webhooks/your_source")` route

4. **Add** event types to the `ALWAYS_DROP` list in `heartbeat_gateway/pre_filter.py` as needed.

5. **Write tests** in `tests/test_your_source.py` following the pattern in `tests/test_server.py`.
