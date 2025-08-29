# HermezOS Agent Interface

This document describes how AI agents and automation tools can integrate with HermezOS using the CLI and MCP (Model Context Protocol) interfaces.

## Cursor/Windsurf Quick Setup

Add this to your `settings.json` or `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "HermezOS": {
      "command": "hermez",
      "args": ["mcp"]
    }
  }
}
```

**Test Commands:**
```bash
# Test MCP server startup
hermez mcp

# Example tool call
hermez pack --path . --json -
```

## Overview

HermezOS provides two primary interfaces for agent integration:

1. **CLI Interface**: Command-line tools for scripting and automation
2. **MCP Interface**: Stdio-based protocol for AI assistants

## Quick Start for Agents

```bash
# Install HermezOS
make install

# Initialize project
hermez init

# Validate configuration
hermez validate

# Pack rules for analysis
hermez pack --path . --json -
```

## CLI Interface

### Basic Usage

```bash
# Initialize project
hermez init

# Pack rules for analysis
hermez pack /path/to/project --json - > rules.json

# Add new rule
hermez add android "Custom Rule"

# Validate rules
hermez validate

# List available rules
hermez list --json
```

### Exit Codes

HermezOS uses standard exit codes for automation:

- `0`: Success
- `1`: Validation error
- `2`: Bad usage/invalid arguments
- `3`: Packing failure
- `4`: I/O error

### JSON Output Format

All commands support `--json` flag for structured output:

```bash
# Pack command JSON output
{
  "pack_request": {
    "path": "/path/to/project",
    "intent_tags": ["best-practice"],
    "languages": ["kotlin"],
    "limit": 10
  },
  "rules": [
    {
      "rule": {
        "id": "RULE-android-plugins-dsl",
        "name": "Prefer Plugins DSL",
        "severity": "warning",
        "domain": "android",
        "action": {
          "type": "manual",
          "steps": ["Replace apply plugin with plugins DSL"]
        }
      },
      "fingerprint": "a1b2c3...",
      "triggered_by": ["path contains '.gradle'"],
      "detected_in": ["build.gradle"]
    }
  ],
  "pack_fingerprint": "d4e5f6...",
  "created_at": "2024-01-15T10:00:00Z",
  "total_rules": 1
}
```

### Automation Examples

#### Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Pack rules for staged files
hermez pack . --json - | jq '.rules[] | select(.rule.severity == "error") | .rule.name'

if [ $? -ne 0 ]; then
    echo "HermezOS validation failed"
    exit 1
fi
```

#### CI/CD Integration

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install HermezOS
        run: pip install git+https://github.com/hermezos/hermezos.git

      - name: Validate rules
        run: hermez validate

      - name: Pack rules
        run: hermez pack . --json - > hermez-report.json

      - name: Upload report
        uses: actions/upload-artifact@v3
        with:
          name: hermez-report
          path: hermez-report.json
```

#### GitHub Actions Integration

```yaml
name: HermezOS Analysis
on:
  pull_request:
    paths:
      - '**/*.gradle'
      - '**/*.gradle.kts'

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup HermezOS
        run: |
          pip install hermezos
          hermez init

      - name: Analyze Gradle files
        run: |
          hermez pack . --intent gradle --json - | jq -r '.rules[] | "- \(.rule.name): \(.rule.hint)"' >> $GITHUB_STEP_SUMMARY

      - name: Comment on PR
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const report = JSON.parse(fs.readFileSync('hermez-report.json', 'utf8'));

            let comment = '## HermezOS Analysis\n\n';
            comment += `Found ${report.total_rules} applicable rules:\n\n`;

            for (const match of report.rules) {
              const severity = match.rule.severity.toUpperCase();
              comment += `- **${match.rule.name}** (${severity})\n`;
              comment += `  ${match.rule.hint}\n\n`;
            }

            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: comment
            });
```

## MCP Interface

### Overview

HermezOS implements the Model Context Protocol (MCP) for seamless AI assistant integration. The MCP server runs as a stdio process and exposes tools that assistants can call.

### Starting the MCP Server

```bash
# Direct execution
python -m hermezos.mcp.server

# Via CLI (when implemented)
hermez mcp
```

### Server Implementation

The MCP server supports both native MCP library (when `modelcontextprotocol` is installed) and a stdio-based fallback shim. The server automatically detects which implementation to use:

- **Native MCP**: Uses the official `mcp` library for full protocol compliance
- **Stdio Shim**: JSON-RPC over stdio for basic compatibility

The server exposes two main tools:
- `hermez.pack`: Analyzes code and returns applicable rules
- `hermez.add_rule`: Creates new rule templates

### MCP Tools

#### `hermez.pack`

Packs rules for a given path with optional filtering.

**Parameters:**
- `path` (string, required): Path to analyze
- `intent_tags` (array, optional): Filter by intent tags
- `languages` (array, optional): Filter by programming languages
- `limit` (integer, optional): Maximum number of rules to return

**Example Call:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "hermez.pack",
    "arguments": {
      "path": "/path/to/project",
      "intent_tags": ["best-practice"],
      "languages": ["kotlin"],
      "limit": 5
    }
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "pack_request": { ... },
    "rules": [ ... ],
    "pack_fingerprint": "abc123...",
    "created_at": "2024-01-15T10:00:00Z",
    "total_rules": 3
  }
}
```

#### `hermez.add_rule`

Creates a new rule template.

**Parameters:**
- `domain` (string, required): Rule domain
- `name` (string, required): Rule name

**Example Call:**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "hermez.add_rule",
    "arguments": {
      "domain": "android",
      "name": "Custom Gradle Rule"
    }
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "path": "registry/android/custom-gradle-rule--RULE-android-custom-gradle-rule.yaml"
  }
}
```

### MCP Client Integration

#### Claude Desktop Integration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "hermezos": {
      "command": "python",
      "args": ["-m", "hermezos.mcp.server"],
      "env": {
        "PYTHONPATH": "/path/to/hermezos/src"
      }
    }
  }
}
```

#### Custom MCP Client

```python
import json
import subprocess
import sys
from typing import Dict, Any

class HermezMCPClient:
    def __init__(self):
        self.process = subprocess.Popen(
            [sys.executable, "-m", "hermezos.mcp.server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True
        )

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool."""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        # Send request
        self.process.stdin.write(json.dumps(request) + "\n")
        self.process.stdin.flush()

        # Read response
        response_line = self.process.stdout.readline()
        return json.loads(response_line)

# Usage
client = HermezMCPClient()

# Pack rules
result = client.call_tool("hermez.pack", {
    "path": "/path/to/project",
    "intent_tags": ["best-practice"]
})

print(f"Found {result['result']['total_rules']} rules")
```

### Error Handling

MCP errors follow standard JSON-RPC error format:

```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32000,
    "message": "Pack failed: Invalid path"
  },
  "id": 1
}
```

Common error codes:
- `-32000`: Generic server error
- `-32601`: Method not found
- `-32602`: Invalid parameters

## Best Practices for Agents

### 1. Use Appropriate Filtering

```bash
# Be specific about what you want
hermez pack . --intent security --lang python --limit 10
```

### 2. Handle Exit Codes

```bash
if ! hermez validate; then
    echo "Validation failed, checking what went wrong..."
    hermez doctor
    exit 1
fi
```

### 3. Cache Results

```bash
# Use fingerprints to avoid redundant work
FINGERPRINT=$(hermez pack . --json - | jq -r '.pack_fingerprint')

if [ "$FINGERPRINT" != "$LAST_FINGERPRINT" ]; then
    echo "Rules changed, updating analysis..."
    # Process new results
fi
```

### 4. Provide Context

When using MCP, provide clear context about what you're analyzing:

```python
# Good
result = client.call_tool("hermez.pack", {
    "path": "./src",
    "intent_tags": ["code-quality", "security"],
    "languages": ["python"]
})

# Better
result = client.call_tool("hermez.pack", {
    "path": "./src",
    "intent_tags": ["code-quality", "security"],
    "languages": ["python"]
})
# Then use the results to inform code review
```

### 5. Respect Severity Levels

```python
rules = result['result']['rules']
errors = [r for r in rules if r['rule']['severity'] == 'error']
warnings = [r for r in rules if r['rule']['severity'] == 'warning']

# Handle errors first, then warnings
for error in errors:
    print(f"CRITICAL: {error['rule']['name']}")
```

## Troubleshooting

### Common Issues

1. **"No rules found"**
   - Check if `registry/` directory exists and contains YAML files
   - Verify rule scope matches your target path
   - Use `hermez doctor` to diagnose

2. **MCP connection fails**
   - Ensure Python path includes HermezOS
   - Check MCP server logs for errors
   - Verify JSON-RPC message format

3. **Invalid rule format**
   - Run `hermez validate` to check rule syntax
   - Use `hermez list` to see loaded rules
   - Check YAML indentation and schema compliance

### Debug Mode

Enable debug logging:

```bash
export HERMEZ_LOG_LEVEL=DEBUG
hermez pack . --json -
```

## Indexing (Optional)

HermezOS supports optional graph indexing for enhanced rule discovery and analysis. Indexing is **disabled by default** to maintain local-first operation.

### Configuration

Add a `[graph]` section to your `hermez.toml`:

```toml
[graph]
enabled = false                    # Enable indexing
driver = "null"                   # null | graphiti | kuzu
mode = "export_only"              # export_only | live (graphiti only)
url = "http://localhost:8800"     # Graphiti server URL
api_key = ""                      # Graphiti API key
db_path = ".hermezos/kuzu"        # Kuzu database path
export_path = "graph"             # Graphiti export directory
```

### Graphiti Integration

#### Export Mode (Recommended)

Export rules to deterministic JSONL files for external processing:

```toml
[graph]
enabled = true
driver = "graphiti"
mode = "export_only"
export_path = "graph"
```

```bash
# Export all rules to graph/nodes.jsonl and graph/edges.jsonl
hermez graph export

# Files are sorted and deterministic for version control
git add graph/
```

#### Live Mode

Send rules directly to a Graphiti server:

```toml
[graph]
enabled = true
driver = "graphiti"
mode = "live"
url = "http://localhost:8800"
api_key = "your-api-key"
```

```bash
# Sync all rules to live server
hermez graph sync
```

### Kùzu Embedded Database

Use local graph database for rule prefiltering:

```toml
[graph]
enabled = true
driver = "kuzu"
db_path = ".hermezos/kuzu"
```

```bash
# Packer will automatically use index for prefiltering
hermez pack --path . --intent best-practice --json -

# Check database health
hermez graph doctor
```

### Graph Commands

```bash
# Export rules to JSONL (graphiti driver)
hermez graph export

# Sync rules to live server (graphiti + live mode)
hermez graph sync

# Check indexing configuration and health
hermez graph doctor
```

### Deterministic Behavior

- **Backward Compatible**: All existing commands work identically when indexing is disabled
- **Deterministic**: Same pack output unless index restricts candidates via prefiltering
- **Local-First**: No network calls unless explicitly configured for live mode
- **Safe Fallback**: Index failures fall back to normal operation with warnings

### Agent Integration

When indexing is enabled, the packer uses the index as an optional prefilter:

```python
# Python API example
from hermezos.config import Config
from hermezos.index import make_index
from hermezos.packer import RulePacker
from hermezos.storage.filesystem import FileSystemStorage

config = Config()
storage = FileSystemStorage(config.registry_root)
packer = RulePacker()
index = make_index(config)

try:
    rules = storage.list_rules()
    request = PackRequest(path=".", intent_tags=["security"])
    
    # Index prefilters candidates if enabled
    bundle = packer.pack(rules, request, index)
finally:
    index.close()
```

## Contributing

When adding new agent integrations:

1. Test with multiple HermezOS versions
2. Handle all exit codes appropriately
3. Provide clear error messages
4. Document any special requirements
5. Include example usage

---

*This interface enables AI agents to leverage HermezOS's knowledge registry for intelligent code analysis and improvement suggestions.*