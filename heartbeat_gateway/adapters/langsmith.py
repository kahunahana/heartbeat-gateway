import hmac
from datetime import datetime, timezone

from heartbeat_gateway import NormalizedEvent
from heartbeat_gateway.adapters.base import WebhookAdapter
from heartbeat_gateway.config.schema import GatewayConfig


class LangSmithAdapter(WebhookAdapter):
    def __init__(self, config: GatewayConfig) -> None:
        self.config = config

    def verify_signature(self, payload: bytes, headers: dict) -> bool:
        """Validates X-Langsmith-Secret custom header token.

        Returns True if no token configured (passthrough — same pattern as other adapters).
        LangSmith does not sign webhooks with HMAC — X-Langsmith-Secret is a static
        token the operator configures in LangSmith's webhook header UI.
        Uses hmac.compare_digest for timing-safe comparison to prevent timing attacks.
        """
        token = self.config.watch.langsmith.token
        if not token:
            return True
        incoming = headers.get("x-langsmith-secret", "")
        return hmac.compare_digest(token, incoming)

    def normalize(self, payload: dict, headers: dict) -> NormalizedEvent | None:
        """Dispatch across three payload shapes.

        Shape B (kwargs present): LangGraph agent webhook — run events.
          Clean runs (error falsy) are always dropped (LSMT-05).
          Error runs return NormalizedEvent with event_type="run.error".

        Alert (alert_rule_id present): threshold alerts.
          Returns NormalizedEvent with event_type="alert.threshold".

        Shape A (rule_id present): automation/rules webhook — feedback events.
          Note: feedback_stats contains aggregated scores; no individual comment
          field is available from LangSmith automation webhooks (by design).
          Returns NormalizedEvent only when at least one negative avg score found.

        Unknown shapes: returns None.
        """
        # Shape B: LangGraph agent webhook (kwargs discriminator)
        if "kwargs" in payload:
            error = payload.get("error")
            if not error:
                return None  # LSMT-05: always drop clean completions

            kwargs = payload.get("kwargs", {})
            error_msg = error.get("message", str(error)) if isinstance(error, dict) else str(error)
            name = kwargs.get("name", "")
            session = kwargs.get("session_name", "") or payload.get("thread_id", "")

            metadata = {
                "run_name": name,
                "session_name": session,
                "error_message": error_msg,
                "run_type": kwargs.get("run_type", ""),
            }
            return NormalizedEvent(
                source="langsmith",  # type: ignore[arg-type]  # Literal updated in Plan 02
                event_type="run.error",
                payload_condensed=self.condense(payload),
                raw_payload=payload,
                timestamp=datetime.now(tz=timezone.utc),
                metadata=metadata,
            )

        # Alert threshold (alert_rule_id discriminator)
        if "alert_rule_id" in payload:
            metadata = {
                "project_name": payload.get("project_name", ""),
                "alert_rule_name": payload.get("alert_rule_name", ""),
                "alert_rule_attribute": payload.get("alert_rule_attribute", ""),
                "triggered_metric_value": payload.get("triggered_metric_value"),
                "triggered_threshold": payload.get("triggered_threshold"),
            }
            return NormalizedEvent(
                source="langsmith",  # type: ignore[arg-type]  # Literal updated in Plan 02
                event_type="alert.threshold",
                payload_condensed=self.condense(payload),
                raw_payload=payload,
                timestamp=datetime.now(tz=timezone.utc),
                metadata=metadata,
            )

        # Shape A: Automation/Rules webhook (rule_id discriminator, feedback_stats)
        if "rule_id" in payload:
            feedback_stats = payload.get("feedback_stats", {})
            # Find first feedback key with negative avg score
            for key, stats in feedback_stats.items():
                avg = stats.get("avg")
                if avg is not None and avg < 0:
                    runs = payload.get("runs", [])
                    run_name = runs[0].get("name", "") if runs else ""
                    metadata = {
                        "feedback_key": key,
                        "feedback_score": avg,
                        "feedback_count": stats.get("n", 0),
                        "run_name": run_name,
                    }
                    return NormalizedEvent(
                        source="langsmith",  # type: ignore[arg-type]  # Literal updated in Plan 02
                        event_type="feedback",
                        payload_condensed=self.condense(payload),
                        raw_payload=payload,
                        timestamp=datetime.now(tz=timezone.utc),
                        metadata=metadata,
                    )
            return None  # rule_id present but no negative feedback — drop

        return None  # unrecognized shape

    def condense(self, payload: dict) -> str:
        """Return a deterministic <=240 char summary.

        Uses name+session (not webhook_sent_at) to preserve writer.py dedup determinism.
        """
        # Alert threshold shape
        if "alert_rule_id" in payload:
            project = payload.get("project_name", "")
            rule = payload.get("alert_rule_name", "")
            attr = payload.get("alert_rule_attribute", "")
            val = payload.get("triggered_metric_value", "")
            threshold = payload.get("triggered_threshold", "")
            return f"LangSmith: [{project}] alert '{rule}' — {attr} {val} > {threshold}"[:240]

        # Shape B: run events (kwargs nesting)
        kwargs = payload.get("kwargs", {})
        if kwargs:
            name = kwargs.get("name", "")
            session = kwargs.get("session_name", "") or payload.get("thread_id", "")
            error = payload.get("error")
            if error:
                err_msg = error.get("message", str(error)) if isinstance(error, dict) else str(error)
                return f"LangSmith: [{session}] '{name}' — error: {err_msg}"[:240]
            return f"LangSmith: [{session}] '{name}'"[:240]

        # Shape A: automation/rules (feedback)
        if "rule_id" in payload:
            feedback_stats = payload.get("feedback_stats", {})
            runs = payload.get("runs", [])
            run_name = runs[0].get("name", "") if runs else ""
            keys = ", ".join(feedback_stats.keys()) if feedback_stats else "none"
            return f"LangSmith: [automation] '{run_name}' — feedback: {keys}"[:240]

        return "LangSmith: unknown event"
