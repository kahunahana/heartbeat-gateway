from heartbeat_gateway import NormalizedEvent
from heartbeat_gateway.config.schema import GatewayConfig

# Event types that are never actionable for an autonomous dev agent.
# Running before any LLM call — zero cost.
ALWAYS_DROP: dict[str, list[str]] = {
    "linear": [
        "Issue.viewed",
        "Comment.viewed",
        "Reaction.create",
        "Cycle.updated",
        "WorkflowState.update",
    ],
    "github": [
        "watch",
        "star",
        "fork",
        "ping",
        "gollum",
        "member",
        "public",
        "repository",
    ],
    "posthog": [
        "$pageview",
        "$autocapture",
        "$pageleave",
        "$set",
        "$identify",
    ],
}


class PreFilter:
    def should_drop(self, event: NormalizedEvent, config: GatewayConfig) -> tuple[bool, str]:
        """Return (should_drop, reason). Stateless — same input always same output."""

        # 1. Always-drop list
        always_drop_for_source = ALWAYS_DROP.get(event.source, [])
        if event.event_type in always_drop_for_source:
            return True, f"always_drop:{event.event_type}"

        # 2. GitHub repo scoping
        if event.source == "github":
            watched_repos = config.watch.github.repos
            event_repo = event.metadata.get("repo", "")
            if watched_repos and event_repo and event_repo not in watched_repos:
                return True, f"repo_not_watched:{event_repo}"

            # Branch scoping for push and CI events only — not PRs, whose branches are ephemeral
            BRANCH_SCOPED_EVENTS = {"push", "ci.failure", "ci.success"}
            watched_branches = config.watch.github.branches
            event_branch = event.metadata.get("branch", "")
            if (
                event.event_type in BRANCH_SCOPED_EVENTS
                and event_branch
                and watched_branches
                and event_branch not in watched_branches
            ):
                return True, f"branch_not_watched:{event_branch}"

        # 3. Linear project scoping
        if event.source == "linear":
            watched_projects = config.watch.linear.project_ids
            event_project = event.metadata.get("project_id", "")
            if watched_projects and (not event_project or event_project not in watched_projects):
                return True, f"project_not_watched:{event_project or 'unassigned'}"

        # 4. PostHog project scoping
        if event.source == "posthog":
            configured_project = config.watch.posthog.project_id
            event_project = event.metadata.get("project_id", "")
            if configured_project and event_project and event_project != configured_project:
                return True, f"posthog_project_mismatch:{event_project}"

        return False, ""
