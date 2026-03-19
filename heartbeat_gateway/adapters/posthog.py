import hashlib
import hmac
from datetime import datetime, timezone

from heartbeat_gateway import NormalizedEvent
from heartbeat_gateway.adapters.base import WebhookAdapter
from heartbeat_gateway.config.schema import GatewayConfig


class PostHogAdapter(WebhookAdapter):
    def __init__(self, config: GatewayConfig) -> None:
        self.config = config

    def verify_signature(self, payload: bytes, headers: dict) -> bool:
        secret = self.config.watch.posthog.secret
        if not secret:
            return True
        sig = headers.get("posthog-signature") or headers.get("PostHog-Signature", "")
        expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, sig)

    def normalize(self, payload: dict, headers: dict) -> NormalizedEvent | None:
        event_type = self._classify(payload)
        if event_type is None:
            return None

        timestamp_str = payload.get("timestamp", "")
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            timestamp = datetime.now(tz=timezone.utc)

        insight = payload.get("insight", {})
        raw_threshold = payload.get("threshold")
        threshold_value = raw_threshold.get("value") if isinstance(raw_threshold, dict) else raw_threshold

        metadata = {
            "insight_name": insight.get("name"),
            "threshold_value": threshold_value,
            "current_value": payload.get("current_value"),
            "flag_key": payload.get("properties", {}).get("$feature_flag"),
            "project_id": payload.get("project_id"),
        }

        return NormalizedEvent(
            source="posthog",
            event_type=event_type,
            payload_condensed=self.condense(payload),
            raw_payload=payload,
            timestamp=timestamp,
            metadata=metadata,
        )

    def _classify(self, payload: dict) -> str | None:
        payload_type = payload.get("type", "")
        event = payload.get("event", "")

        if payload_type == "insight_threshold_alert":
            return "insight.threshold"
        if payload_type == "error_spike":
            return "error.spike"
        if event == "$feature_flag_called":
            flag_key = payload.get("properties", {}).get("$feature_flag", "unknown")
            return f"feature_flag.{flag_key}"
        return None

    def condense(self, payload: dict) -> str:
        payload_type = payload.get("type", "")

        if payload_type == "insight_threshold_alert":
            name = payload.get("insight", {}).get("name", "")
            current = payload.get("current_value", "")
            threshold = payload.get("threshold", {}).get("value", "")
            return f"PostHog: insight '{name}' threshold crossed — {current} vs {threshold}"[:240]

        if payload_type == "error_spike":
            event = payload.get("event", "")
            count = payload.get("count", "")
            return f"PostHog: error spike in '{event}' — {count} occurrences"[:240]

        flag_key = payload.get("properties", {}).get("$feature_flag", "")
        if flag_key:
            return f"PostHog: feature flag '{flag_key}' called"[:240]

        event = payload.get("event", payload.get("type", "unknown"))
        return f"PostHog: {event}"[:240]
