"""gateway doctor — pre-flight config validator.

CONSTRAINT: Do NOT import from heartbeat_gateway.app. Import only from
heartbeat_gateway.config.schema and heartbeat_gateway.config.loader.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

EXPECTED_MIN_BODY_BYTES = 512 * 1024  # 512 KB — replicated from app.py; do NOT import from app.py


class CheckStatus(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass
class CheckResult:
    name: str
    status: CheckStatus
    message: str
    fix_hint: str = ""  # MUST be non-empty when status == FAIL


class DoctorRunner:
    """Runs all gateway doctor checks and formats results."""

    def __init__(self, verbose: bool = False) -> None:
        self.verbose = verbose

    def run(self) -> list[CheckResult]:
        """Run all checks. Returns list of CheckResult in check order."""
        raise NotImplementedError("Implemented in Plan 02")

    def print_results(self, results: list[CheckResult]) -> None:
        """Render results to terminal using rich."""
        raise NotImplementedError("Implemented in Plan 02")
