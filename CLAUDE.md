# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync          # install dependencies
uv run main.py   # start the MCP server (listens at http://127.0.0.1:8000/mcp)
```

No test suite or linter is configured.

## Architecture

This is a single-file MCP server (`main.py`) that reads `tools.yaml` at startup and dynamically registers each entry as an MCP tool via `FastMCP`.

**Key flow:**
1. `load_tools()` parses `tools.yaml` and calls `make_tool_func()` for each tool definition.
2. `make_tool_func()` builds a Python function with a fully dynamic `inspect.Signature` (name, type annotations, defaults) derived from the YAML `parameters` list. This is what makes FastMCP generate the correct JSON schema for each tool.
3. Each generated function calls `run_shell()`, which runs the tool's `command` template with parameters substituted via `shlex.quote` for shell safety. All commands execute in `BASE_DIR` (the directory containing `main.py`), regardless of where the server was launched.
4. The server is started with `streamable-http` transport.

**Adding a tool** — edit `tools.yaml` only; no Python changes needed. Restart the server to pick up changes. Parameter `{placeholders}` in `command` strings must match `parameters[].name` entries.

**Type mapping** (`TYPE_MAP`): `string` → `str`, `integer` → `int`, `number` → `float`, `boolean` → `bool`. Parameters without a `default` are required.

## Client configuration

```json
{
  "mcpServers": {
    "mcp-bridge": {
      "url": "http://127.0.0.1:8000/mcp"
    }
  }
}
```
