from datetime import datetime, timezone

from heartbeat_gateway import NormalizedEvent
from heartbeat_gateway.adapters.base import WebhookAdapter
from heartbeat_gateway.config.schema import GatewayConfig


class AmplitudeAdapter(WebhookAdapter):
    def __init__(self, config: GatewayConfig) -> None:
        self.config = config

    def verify_signature(self, payload: bytes, headers: dict) -> bool:
        """Always returns True. Amplitude does not sign webhook deliveries.
        Mitigation: restrict /webhooks/amplitude to Amplitude IP ranges via firewall rules."""
        return True

    def normalize(self, payload: dict, headers: dict) -> NormalizedEvent | None:
        event_type = payload.get("event_type", "")

        if event_type == "monitor_alert":
            charts = payload.get("charts", [])
            if not charts:
                return None

            header = charts[0].get("header", "")
            body = charts[0].get("body", "")
            metadata = {
                "metric_header": header,
                "metric_body": body,
                "chart_url": charts[0].get("url", ""),
            }

            return NormalizedEvent(
                source="amplitude",
                event_type="monitor_alert",
                payload_condensed=self.condense(payload),
                raw_payload=payload,
                timestamp=datetime.now(tz=timezone.utc),
                metadata=metadata,
            )

        if event_type == "chart.annotation":
            annotation = payload.get("annotation", {})
            chart = payload.get("chart", {})
            metadata = {
                "annotation_label": annotation.get("label", ""),
                "annotation_description": annotation.get("description", ""),
                "chart_name": chart.get("name", ""),
            }

            return NormalizedEvent(
                source="amplitude",
                event_type="chart.annotation",
                payload_condensed=self.condense(payload),
                raw_payload=payload,
                timestamp=datetime.now(tz=timezone.utc),
                metadata=metadata,
            )

        return None

    def condense(self, payload: dict) -> str:
        event_type = payload.get("event_type", "")

        if event_type == "monitor_alert":
            charts = payload.get("charts", [])
            header = charts[0].get("header", "") if charts else ""
            return f"Amplitude: monitor alert — {header}"[:240]

        if event_type == "chart.annotation":
            label = payload.get("annotation", {}).get("label", "")
            chart_name = payload.get("chart", {}).get("name", "")
            return f"Amplitude: [{chart_name}] annotation — {label}"[:240]

        return f"Amplitude: {event_type}"[:240]
