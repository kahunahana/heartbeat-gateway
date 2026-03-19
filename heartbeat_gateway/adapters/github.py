import hashlib
import hmac
from datetime import datetime, timezone

from heartbeat_gateway import NormalizedEvent
from heartbeat_gateway.adapters.base import WebhookAdapter
from heartbeat_gateway.config.schema import GatewayConfig


class GitHubAdapter(WebhookAdapter):
    def __init__(self, config: GatewayConfig) -> None:
        self.config = config

    def verify_signature(self, payload: bytes, headers: dict) -> bool:
        secret = self.config.watch.github.secret
        if not secret:
            return True
        sig = headers.get("x-hub-signature-256") or headers.get("X-Hub-Signature-256", "")
        expected = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, sig)

    def normalize(self, payload: dict, headers: dict) -> NormalizedEvent | None:
        gh_event = headers.get("x-github-event") or headers.get("X-GitHub-Event", "")
        event_type, metadata = self._extract_event(gh_event, payload)
        if event_type is None:
            return None

        timestamp_str = (
            payload.get("pull_request", {}).get("updated_at")
            or payload.get("check_run", {}).get("completed_at")
            or payload.get("head_commit", {}).get("timestamp")
            or payload.get("review", {}).get("submitted_at")
            or ""
        )
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            timestamp = datetime.now(tz=timezone.utc)

        return NormalizedEvent(
            source="github",
            event_type=event_type,
            payload_condensed=self.condense(payload),
            raw_payload=payload,
            timestamp=timestamp,
            metadata=metadata,
        )

    def _extract_event(self, gh_event: str, payload: dict) -> tuple[str | None, dict]:
        repo = payload.get("repository", {}).get("full_name", "")
        meta: dict = {"repo": repo}

        if gh_event == "pull_request":
            pr = payload.get("pull_request", {})
            meta.update(
                pr_number=pr.get("number"),
                pr_title=pr.get("title", ""),
                pr_url=pr.get("html_url"),
                branch=pr.get("base", {}).get("ref", ""),
                commit_sha=pr.get("merge_commit_sha") or pr.get("head", {}).get("sha", ""),
            )
            action = payload.get("action", "")
            if action == "opened":
                return "pr.opened", meta
            if action == "closed" and pr.get("merged"):
                return "pr.merged", meta
            if action == "closed":
                return "pr.closed", meta
            if action == "review_requested":
                return "pr.review_requested", meta
            return None, meta

        if gh_event == "check_run":
            if payload.get("action") != "completed":
                return None, meta
            check_run = payload.get("check_run", {})
            conclusion = check_run.get("conclusion", "")
            meta.update(
                workflow_name=check_run.get("name", ""),
                ci_conclusion=conclusion,
                branch=check_run.get("check_suite", {}).get("head_branch", ""),
                commit_sha=check_run.get("head_sha", ""),
            )
            if conclusion == "failure":
                return "ci.failure", meta
            if conclusion == "success":
                return "ci.success", meta
            return None, meta

        if gh_event == "push":
            ref = payload.get("ref", "")
            branch = ref.replace("refs/heads/", "")
            meta.update(branch=branch, commit_sha=payload.get("after", ""))
            return f"push.{branch}", meta

        if gh_event == "issues":
            issue = payload.get("issue", {})
            meta.update(
                pr_number=issue.get("number"),
                pr_title=issue.get("title", ""),
                pr_url=issue.get("html_url"),
            )
            action = payload.get("action", "")
            if action == "opened":
                return "issue.opened", meta
            if action == "closed":
                return "issue.closed", meta
            return None, meta

        if gh_event == "pull_request_review":
            review = payload.get("review", {})
            pr = payload.get("pull_request", {})
            state = review.get("state", "").lower()
            meta.update(
                pr_number=pr.get("number"),
                pr_title=pr.get("title", ""),
                pr_url=pr.get("html_url"),
                branch=pr.get("base", {}).get("ref", ""),
            )
            if state == "approved":
                return "pr_review.approved", meta
            if state == "changes_requested":
                return "pr_review.changes_requested", meta
            return None, meta

        return None, meta

    def condense(self, payload: dict) -> str:
        repo = payload.get("repository", {}).get("full_name", "")

        if "check_run" in payload:
            check_run = payload["check_run"]
            workflow = check_run.get("name", "")[:30]
            conclusion = check_run.get("conclusion", "")
            branch = check_run.get("check_suite", {}).get("head_branch", "")
            return f"GitHub: CI '{workflow}' {conclusion} on {branch} — {repo}"[:240]

        if "pull_request" in payload and "review" not in payload:
            pr = payload["pull_request"]
            n = pr.get("number", "")
            title = pr.get("title", "")[:40]
            action = payload.get("action", "")
            action_str = "merged" if (action == "closed" and pr.get("merged")) else action
            return f"GitHub: PR #{n} '{title}' {action_str} — {repo}"[:240]

        if "review" in payload:
            review = payload["review"]
            pr = payload.get("pull_request", {})
            n = pr.get("number", "")
            state = review.get("state", "")
            return f"GitHub: PR #{n} review {state} — {repo}"[:240]

        if "issue" in payload and "pull_request" not in payload:
            issue = payload["issue"]
            n = issue.get("number", "")
            title = issue.get("title", "")[:40]
            action = payload.get("action", "")
            return f"GitHub: Issue #{n} '{title}' {action} — {repo}"[:240]

        if "ref" in payload or "pusher" in payload:
            ref = payload.get("ref", "")
            branch = ref.replace("refs/heads/", "")
            return f"GitHub: push to {branch} — {repo}"[:240]

        return f"GitHub: event — {repo}"[:240]
