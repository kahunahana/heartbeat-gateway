from __future__ import annotations

from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

ACTIVE_TASKS_MARKER = "<!-- heartbeat-gateway writes below this line -->"


def read_heartbeat(workspace: Path) -> str:
    """Return active tasks from HEARTBEAT.md."""
    path = workspace / "HEARTBEAT.md"
    if not path.exists():
        return "HEARTBEAT.md not found at workspace path."
    content = path.read_text(encoding="utf-8")
    marker_pos = content.find(ACTIVE_TASKS_MARKER)
    if marker_pos == -1:
        return "No active tasks marker found in HEARTBEAT.md."
    active = content[marker_pos + len(ACTIVE_TASKS_MARKER):]
    completed_pos = active.find("## Completed")
    if completed_pos != -1:
        active = active[:completed_pos]
    return active.strip() or "No active tasks."


def read_delta(workspace: Path, max_lines: int = 20) -> str:
    """Return the last N lines from DELTA.md."""
    path = workspace / "DELTA.md"
    if not path.exists():
        return "DELTA.md not found at workspace path."
    lines = path.read_text(encoding="utf-8").splitlines()
    return "\n".join(lines[-max_lines:]) or "No delta entries."


def read_soul(soul_path: Path) -> str:
    """Return the contents of SOUL.md."""
    if not soul_path.exists():
        return "SOUL.md not found."
    return soul_path.read_text(encoding="utf-8")


def get_gateway_status(workspace: Path, soul_path: Path) -> str:
    """Return a summary of the gateway's current configuration."""
    heartbeat_path = workspace / "HEARTBEAT.md"
    delta_path = workspace / "DELTA.md"
    return (
        f"workspace: {workspace}\n"
        f"soul_md: {soul_path} ({'exists' if soul_path.exists() else 'MISSING'})\n"
        f"heartbeat_md: {heartbeat_path} ({'exists' if heartbeat_path.exists() else 'MISSING'})\n"
        f"delta_md: {delta_path} ({'exists' if delta_path.exists() else 'MISSING'})\n"
    )


def main() -> None:
    import os

    workspace = Path(os.getenv("GATEWAY_WORKSPACE_PATH", "~/workspace")).expanduser()
    soul_path = Path(os.getenv("GATEWAY_SOUL_MD_PATH", "~/workspace/SOUL.md")).expanduser()

    server = Server("heartbeat-gateway")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="read_heartbeat",
                description="Return active tasks from HEARTBEAT.md",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="read_delta",
                description="Return recent DELTA.md entries",
                inputSchema={"type": "object", "properties": {"max_lines": {"type": "integer", "default": 20}}},
            ),
            Tool(
                name="read_soul",
                description="Return current SOUL.md operator context",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="get_gateway_status",
                description="Return gateway workspace config and file status",
                inputSchema={"type": "object", "properties": {}},
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        if name == "read_heartbeat":
            return [TextContent(type="text", text=read_heartbeat(workspace))]
        if name == "read_delta":
            return [TextContent(type="text", text=read_delta(workspace, arguments.get("max_lines", 20)))]
        if name == "read_soul":
            return [TextContent(type="text", text=read_soul(soul_path))]
        if name == "get_gateway_status":
            return [TextContent(type="text", text=get_gateway_status(workspace, soul_path))]
        raise ValueError(f"Unknown tool: {name}")

    import asyncio

    asyncio.run(stdio_server(server))
