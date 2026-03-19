from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass
class NormalizedEvent:
    source: Literal["linear", "github", "posthog"]
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
    url: str | None = None
    priority: Literal["high", "normal"] = "normal"

    def to_markdown(self) -> str:
        source_tag = f"{self.source.upper()}:{self.event_type.upper()}"
        line = f"- [ ] [{source_tag}] {self.title}"
        details = f"      → {self.url} | {self.timestamp.isoformat()}"
        return f"{line}\n{details}"
