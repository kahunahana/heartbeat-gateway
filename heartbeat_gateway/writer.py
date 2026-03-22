import json
from datetime import datetime, timezone

from filelock import FileLock
from loguru import logger

from heartbeat_gateway import HeartbeatEntry, NormalizedEvent
from heartbeat_gateway.config.schema import GatewayConfig

HEARTBEAT_TEMPLATE = """# Heartbeat Tasks

This file is managed by heartbeat-gateway.
Add tasks manually or let the gateway write them from webhook events.

## Active Tasks

<!-- heartbeat-gateway writes below this line -->

## Completed

<!-- Move completed tasks here or delete them -->
"""

ACTIVE_TASKS_MARKER = "<!-- heartbeat-gateway writes below this line -->"
DEDUP_WINDOW_MINUTES = 5


class HeartbeatWriter:
    def __init__(self, config: GatewayConfig) -> None:
        self._config = config
        self._heartbeat_path = config.workspace_path / "HEARTBEAT.md"
        self._delta_path = config.workspace_path / "DELTA.md"
        self._audit_path = config.audit_log_path or config.workspace_path / "audit.log"
        self._lock = FileLock(str(self._heartbeat_path.resolve()) + ".lock")

    def heartbeat_file_exists(self) -> bool:
        return self._heartbeat_path.exists()

    def write_actionable(self, entry: HeartbeatEntry) -> None:
        self._ensure_heartbeat_exists()
        with self._lock:
            content = self._heartbeat_path.read_text(encoding="utf-8")

            if self._is_duplicate(entry, content):
                logger.debug(f"Skipping duplicate entry: {entry.source} {entry.event_type}")
                return

            marker_pos = content.find(ACTIVE_TASKS_MARKER)
            if marker_pos == -1:
                logger.warning("HEARTBEAT.md missing write marker — appending at end")
                content += f"\n{entry.to_markdown()}\n"
            else:
                insert_pos = marker_pos + len(ACTIVE_TASKS_MARKER)
                content = content[:insert_pos] + f"\n{entry.to_markdown()}" + content[insert_pos:]

            self._heartbeat_path.write_text(content, encoding="utf-8")
            logger.info(f"Wrote actionable task: {entry.title}")

    def write_delta(self, event: NormalizedEvent) -> None:
        timestamp = event.timestamp.isoformat()
        line = f"- [{timestamp}] [{event.source.upper()}:{event.event_type.upper()}] {event.payload_condensed}\n"
        with self._delta_path.open("a", encoding="utf-8") as f:
            f.write(line)

    def write_audit(self, event: NormalizedEvent, classification: str, rationale: str) -> None:
        record = {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "source": event.source,
            "event_type": event.event_type,
            "classification": classification,
            "rationale": rationale,
            "condensed": event.payload_condensed,
        }
        with self._audit_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def read_active_tasks(self) -> str:
        if not self._heartbeat_path.exists():
            return ""
        content = self._heartbeat_path.read_text(encoding="utf-8")
        marker_pos = content.find(ACTIVE_TASKS_MARKER)
        if marker_pos == -1:
            return ""
        active_section = content[marker_pos + len(ACTIVE_TASKS_MARKER) :]
        completed_pos = active_section.find("## Completed")
        if completed_pos != -1:
            active_section = active_section[:completed_pos]
        # Return up to ~300 tokens worth (~1200 chars)
        return active_section.strip()[:1200]

    def _ensure_heartbeat_exists(self) -> None:
        self._heartbeat_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._heartbeat_path.exists():
            self._heartbeat_path.write_text(HEARTBEAT_TEMPLATE, encoding="utf-8")
            return

        content = self._heartbeat_path.read_text(encoding="utf-8")
        if ACTIVE_TASKS_MARKER in content:
            return

        heading = "## Active Tasks"
        heading_pos = content.find(heading)
        if heading_pos == -1:
            logger.warning(
                "HEARTBEAT.md exists but has no '## Active Tasks' heading — "
                "add '## Active Tasks' to enable automatic task injection"
            )
            return

        insert_pos = heading_pos + len(heading)
        content = content[:insert_pos] + f"\n\n{ACTIVE_TASKS_MARKER}" + content[insert_pos:]
        self._heartbeat_path.write_text(content, encoding="utf-8")
        logger.info("Injected write marker into existing HEARTBEAT.md")

    def _is_duplicate(self, entry: HeartbeatEntry, content: str) -> bool:
        """Check if an identical entry is already in the active tasks section."""
        # URL-based dedup — most reliable when a URL is present
        if entry.url and f"→ {entry.url}" in content:
            return True
        # Title fingerprint dedup — covers URL-less events (e.g. CI failures)
        # Matches the format produced by HeartbeatEntry.to_markdown(): [SOURCE:TYPE] title
        fingerprint = f"[{entry.source.upper()}:{entry.event_type.upper()}] {entry.title}"
        return fingerprint in content
