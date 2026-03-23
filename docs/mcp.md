# MCP Server

heartbeat-gateway ships a second entry point — `heartbeat-gateway-mcp` — that exposes
the gateway's workspace files as MCP tools. This lets any MCP-compatible AI assistant
(Claude Desktop, Cursor, etc.) call into the gateway's outputs directly, without reading
files manually.

---

## Tools

| Tool | Description |
|------|-------------|
| `read_heartbeat` | Returns active tasks from `HEARTBEAT.md` (below the gateway marker) |
| `read_delta` | Returns the last N lines from `DELTA.md` (default: 20) |
| `read_soul` | Returns the full contents of `SOUL.md` |
| `get_gateway_status` | Returns workspace paths and file existence status |

---

## Running Locally

The simplest setup — run the MCP server on the same machine where your workspace files
live. This is the recommended path and works reliably with Claude Desktop.

**1. Set env vars and start the server:**

```bash
GATEWAY_WORKSPACE_PATH=/path/to/workspace \
GATEWAY_SOUL_MD_PATH=/path/to/workspace/SOUL.md \
uv run heartbeat-gateway-mcp
```

**2. Add to Claude Desktop config** (`~/Library/Application Support/Claude/claude_desktop_config.json`
on macOS, `%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "heartbeat-gateway": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/heartbeat-gateway", "heartbeat-gateway-mcp"],
      "env": {
        "GATEWAY_WORKSPACE_PATH": "/path/to/workspace",
        "GATEWAY_SOUL_MD_PATH": "/path/to/workspace/SOUL.md"
      }
    }
  }
}
```

Restart Claude Desktop. The four tools will appear in the tool picker.

---

## Remote VPS Setup (current limitation)

Running the MCP server on a remote VPS via SSH stdio is supported in principle but
has a known transport issue: the MCP stdio protocol requires a clean stdout channel,
and non-interactive SSH sessions can inject noise (shell startup output, SSH banners)
that corrupts the JSON-RPC stream before the first message is processed.

**Workaround:** Use `scp` to sync your workspace files locally, then run the MCP server
locally against the synced copy.

```bash
scp user@your-vps:/path/to/workspace/HEARTBEAT.md /local/workspace/HEARTBEAT.md
```

A robust remote transport (HTTP/SSE or a `FastMCP`-based rewrite) is planned for v0.3.0
alongside the `gateway doctor` setup validator (PG-2).

---

## Environment Variables

The MCP server reads the same env vars as the gateway:

| Variable | Default | Description |
|----------|---------|-------------|
| `GATEWAY_WORKSPACE_PATH` | `~/workspace` | Directory containing `HEARTBEAT.md` and `DELTA.md` |
| `GATEWAY_SOUL_MD_PATH` | `~/workspace/SOUL.md` | Path to `SOUL.md` |
