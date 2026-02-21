# requestrepo-mcp

MCP server for [`requestrepo`](https://github.com/adrgs/requestrepo-lib).

## Scope

- Full requestrepo tool surface (requests, sharing, DNS, files, ping)
- Default `stdio` transport, optional `streamable-http`
- Confirm-gated mutations (`confirm=true`)
- JSON-safe bytes envelope for binary fields

Full parameter docs are in `TOOLS.md`.

## Install

```bash
python -m pip install -e .
```

For local development:

```bash
python -m pip install -e ".[dev]"
```

## Configuration

- `REQUESTREPO_TOKEN` (optional)
- `REQUESTREPO_ADMIN_TOKEN` (optional)
- `REQUESTREPO_HOST` (default `requestrepo.com`)
- `REQUESTREPO_PORT` (default `443`)
- `REQUESTREPO_PROTOCOL` (default `https`)
- `REQUESTREPO_VERIFY` (default `true`)
- `REQUESTREPO_DEFAULT_TIMEOUT_SECONDS` (default `30`)
- `REQUESTREPO_MAX_BYTES` (default `65536`)

Auth behavior:
- If `REQUESTREPO_TOKEN` is set, it is used.
- Otherwise a new session is created, optionally with `REQUESTREPO_ADMIN_TOKEN`.

## Run

```bash
requestrepo-mcp --transport stdio
```

```bash
requestrepo-mcp --transport streamable-http --host 127.0.0.1 --port 8000 --streamable-http-path /mcp
```

## Install In AI Clients

### Codex

With token (optional, recommended if you already have one):

```bash
codex mcp add requestrepo --env REQUESTREPO_TOKEN=your-token -- requestrepo-mcp --transport stdio
```

Without token (creates a new session automatically):

```bash
codex mcp add requestrepo -- requestrepo-mcp --transport stdio
```

Check config:

```bash
codex mcp get requestrepo
```

Autostart note:
- Codex starts `stdio` servers automatically.
- If startup fails, register with an absolute executable path:

```bash
codex mcp add requestrepo --env REQUESTREPO_TOKEN=your-token -- /absolute/path/to/requestrepo-mcp --transport stdio
```

### Claude Code / Claude Desktop

```json
{
  "mcpServers": {
    "requestrepo": {
      "command": "requestrepo-mcp",
      "args": ["--transport", "stdio"],
      "env": {
        "REQUESTREPO_TOKEN": "your-token"
      }
    }
  }
}
```

### Cursor

```json
{
  "mcpServers": {
    "requestrepo": {
      "command": "requestrepo-mcp",
      "args": ["--transport", "stdio"],
      "env": {
        "REQUESTREPO_TOKEN": "your-token"
      }
    }
  }
}
```

### VS Code (Copilot Agent)

`.vscode/mcp.json`:

```json
{
  "servers": {
    "requestrepo": {
      "type": "stdio",
      "command": "requestrepo-mcp",
      "args": ["--transport", "stdio"],
      "env": {
        "REQUESTREPO_TOKEN": "your-token"
      }
    }
  }
}
```

## Tool Summary

- `session_info`
- `list_requests`
- `wait_for_request`
- `delete_request`
- `delete_all_requests`
- `share_request`
- `get_shared_request`
- `list_dns`
- `add_dns`
- `remove_dns`
- `update_dns`
- `list_files`
- `get_file`
- `set_file`
- `update_files`
- `ping`

Mutation tools require `confirm=true`.

## Testing

```bash
pytest -q
```

CI runs tests on push and pull requests (see `.github/workflows/ci.yml`).
