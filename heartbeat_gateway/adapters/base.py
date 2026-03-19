from abc import ABC, abstractmethod

from heartbeat_gateway import NormalizedEvent


class WebhookAdapter(ABC):
    @abstractmethod
    def verify_signature(self, payload: bytes, headers: dict) -> bool: ...

    @abstractmethod
    def normalize(self, payload: dict, headers: dict) -> NormalizedEvent | None:
        """Return None for unrecognized event types."""

    def condense(self, payload: dict) -> str:
        """Return a ≤60 token (~≤240 char) human-readable summary."""
        return str(payload)[:240]
