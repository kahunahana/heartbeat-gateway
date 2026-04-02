from datetime import datetime, timezone

from heartbeat_gateway import NormalizedEvent
from heartbeat_gateway.adapters.base import WebhookAdapter
from heartbeat_gateway.config.schema import GatewayConfig


class BraintrustAdapter(WebhookAdapter):
    def __init__(self, config: GatewayConfig) -> None:
        self.config = config

    def verify_signature(self, payload: bytes, headers: dict) -> bool:
        """Always returns True. Braintrust does not sign webhook deliveries as of build date.
        Mitigation: restrict /webhooks/braintrust to Braintrust IP ranges via firewall rules."""
        return True

    def normalize(self, payload: dict, headers: dict) -> NormalizedEvent | None:
        if payload.get("details", {}).get("is_test") is True:
            return None

        automation = payload.get("automation", {})
        event_type = automation.get("event_type", "")
        project = payload.get("project", {})
        details = payload.get("details", {})

        if event_type == "logs":
            timestamp_str = details.get("time_end", "")
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                timestamp = datetime.now(tz=timezone.utc)

            metadata = {
                "project_name": project.get("name"),
                "automation_name": automation.get("name"),
                "count": details.get("count"),
                "message": details.get("message"),
            }

            return NormalizedEvent(
                source="braintrust",
                event_type="logs",
                payload_condensed=self.condense(payload),
                raw_payload=payload,
                timestamp=timestamp,
                metadata=metadata,
            )

        if event_type == "environment_update":
            timestamp = datetime.now(tz=timezone.utc)

            metadata = {
                "project_name": project.get("name"),
                "env_slug": details.get("environment", {}).get("slug"),
                "action": details.get("action"),
            }

            return NormalizedEvent(
                source="braintrust",
                event_type="environment_update",
                payload_condensed=self.condense(payload),
                raw_payload=payload,
                timestamp=timestamp,
                metadata=metadata,
            )

        return None

    def condense(self, payload: dict) -> str:
        automation = payload.get("automation", {})
        project = payload.get("project", {})
        details = payload.get("details", {})
        event_type = automation.get("event_type", "")
        project_name = project.get("name", "")
        name = automation.get("name", "")

        if event_type == "logs":
            count = details.get("count", "")
            return f"Braintrust: [{project_name}] '{name}' — {count} logs triggered"[:240]

        if event_type == "environment_update":
            env_slug = details.get("environment", {}).get("slug", "")
            action = details.get("action", "")
            return f"Braintrust: [{project_name}] env '{env_slug}' {action}"[:240]

        return f"Braintrust: [{project_name}] {event_type}"[:240]
