import hashlib
import hmac
from datetime import datetime, timezone

from heartbeat_gateway import NormalizedEvent
from heartbeat_gateway.adapters.base import WebhookAdapter
from heartbeat_gateway.config.schema import GatewayConfig


class LinearAdapter(WebhookAdapter):
    def __init__(self, config: GatewayConfig) -> None:
        self.config = config

    def verify_signature(self, payload: bytes, headers: dict) -> bool:
        secret = self.config.watch.linear.secret
        if not secret:
            return True
        sig = headers.get("linear-signature") or headers.get("x-linear-signature") or headers.get("X-Linear-Signature", "")
        expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, sig)

    def normalize(self, payload: dict, headers: dict) -> NormalizedEvent | None:
        action = payload.get("action", "")
        event_type_raw = payload.get("type", "")
        data = payload.get("data", {})
        updated_from = payload.get("updatedFrom", {})

        event_type = self._classify(action, event_type_raw, updated_from)
        if event_type is None:
            return None

        timestamp_str = payload.get("createdAt") or data.get("updatedAt") or data.get("createdAt", "")
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            timestamp = datetime.now(tz=timezone.utc)

        state = data.get("state", {})
        team = data.get("team", {})

        metadata = {
            "issue_url": data.get("url"),
            "issue_id": data.get("id"),
            "project_name": team.get("name"),
            "project_id": data.get("projectId") or data.get("team", {}).get("id"),
            "status_from": updated_from.get("stateName", "") if event_type == "issue.status_changed" else "",
            "status_to": state.get("name", ""),
            "assignee_id": data.get("assigneeId"),
            "priority": data.get("priority"),
        }

        return NormalizedEvent(
            source="linear",
            event_type=event_type,
            payload_condensed=self.condense(payload),
            raw_payload=payload,
            timestamp=timestamp,
            metadata=metadata,
        )

    def _classify(self, action: str, event_type_raw: str, updated_from: dict) -> str | None:
        if event_type_raw == "Issue":
            if action == "create":
                return "issue.created"
            if action == "update":
                if "stateId" in updated_from:
                    return "issue.status_changed"
                if "priority" in updated_from:
                    return "issue.priority_changed"
                return "issue.updated"
        if event_type_raw == "Comment" and action == "create":
            return "comment.created"
        return None

    def condense(self, payload: dict) -> str:
        data = payload.get("data", {})
        updated_from = payload.get("updatedFrom", {})
        action = payload.get("action", "")
        event_type_raw = payload.get("type", "")

        project = data.get("team", {}).get("name", "")
        title = data.get("title", "")

        if event_type_raw == "Comment":
            issue_title = data.get("issue", {}).get("title") or title
            summary = f"Linear: [{project}] comment on '{issue_title}'"
        elif action == "update" and "stateId" in updated_from:
            to_status = data.get("state", {}).get("name", "")
            from_status = updated_from.get("stateName", "")
            if from_status:
                summary = f"Linear: [{project}] {title} [{from_status}→{to_status}]"
            else:
                summary = f"Linear: [{project}] {title} →{to_status}"
        else:
            summary = f"Linear: [{project}] {title}"

        return summary[:240]
