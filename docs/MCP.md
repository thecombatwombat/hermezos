# MCP (Model Context Protocol)

Expose HermezOS to IDE agents (Cursor, Windsurf, etc.) via an MCP stdio server.

## One-time setup

Ensure the CLI is on your PATH and provides the `mcp` subcommand:

```bash
hermez --help
hermez mcp --help
```

## Cursor / Windsurf settings

Add to your IDE settings:

```json
{
  "mcpServers": {
    "HermezOS": { "command": "hermez", "args": ["mcp"] }
  }
}
```

Restart the IDE; it will connect to the HermezOS MCP server.

## Using the tools

Ask your IDE agent something like:

> "Call `hermez.pack` with path: `.` json: `true` limit: `10` and summarize the resulting rules for this task."

HermezOS typically exposes tools such as:

* `hermez.pack` – build a deterministic pack for the current repo/path.
* `hermez.add_rule` – (if available) create a new rule scaffold.

## Troubleshooting

* **No connection?** Run `hermez mcp` in a terminal to confirm it starts without errors.
* **No rules found?** Add at least one rule (see Quickstart), then run `hermez validate`.
* **Agent can’t find the command?** Ensure `pipx` shims directory is on your PATH.