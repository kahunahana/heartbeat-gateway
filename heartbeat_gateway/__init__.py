from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass
class NormalizedEvent:
    source: Literal["linear", "github", "posthog", "braintrust", "langsmith", "amplitude"]
    event_type: str
    payload_condensed: str
    raw_payload: dict
    timestamp: datetime
    metadata: dict = field(default_factory=dict)


@dataclass
class HeartbeatEntry:
    source: str
    event_type: str
    title: str
    timestamp: datetime
    payload_condensed: str = ""  # stable fingerprint from adapter — used for dedup
    url: str | None = None
    priority: Literal["high", "normal"] = "normal"

    def to_markdown(self) -> str:
        source_tag = f"{self.source.upper()}:{self.event_type.upper()}"
        line = f"- [ ] [{source_tag}] {self.title}"
        condensed_part = f" | ref:{self.payload_condensed}" if self.payload_condensed else ""
        details = f"      → {self.url} | {self.timestamp.isoformat()}{condensed_part}"
        return f"{line}\n{details}"
