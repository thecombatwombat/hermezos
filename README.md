# HermezOS

*Messenger of Unwritten Rules*

HermezOS is a local-first knowledge registry and context packer that helps teams maintain and share development best practices, coding standards, and project-specific rules.

## Overview

HermezOS provides a structured way to:

- **Define Rules**: Author rule cards in YAML that capture development best practices
- **Pack Context**: Deterministically select and bundle relevant rules for any codebase
- **Integrate Seamlessly**: Use via CLI, Python library, or MCP (Model Context Protocol)

## Key Features

- **Local-First**: No network dependencies, works offline
- **Deterministic**: Stable SHA256 fingerprints ensure reproducible results
- **Typed & Tested**: Full type safety with comprehensive test coverage
- **Extensible**: Plugin architecture for custom detectors and actions
- **MCP Compatible**: Exposes tools for AI assistants and automation

## Quick Start

### One-Shot Setup

Get HermezOS up and running with a single command:

```bash
# Complete setup and test in one go
make install && hermez init && hermez validate && hermez pack --path . --json - | jq . | head -20
```

This will:
1. Install HermezOS with all dependencies
2. Initialize the project with default configuration
3. Validate the setup and built-in rules
4. Pack rules for the current directory and preview the output

### Installation & Setup

```bash
# Install with development dependencies
make install

# Initialize HermezOS in current directory
hermez init

# Validate configuration and rules
hermez validate

# Pack rules for current directory
hermez pack --path . --json -
```

### Add Your First Rule

```bash
# Add a rule interactively
hermez add android "Prefer Plugins DSL"

# Edit the generated YAML file to customize triggers and actions
```

### Pack Rules for Analysis

```bash
# Pack rules for current directory
hermez pack . --json -

# Filter by intent and language
hermez pack /path/to/project --intent best-practice --lang kotlin --limit 10
```

## Architecture

### Core Components

- **Rule Cards**: YAML-defined rules with triggers, detectors, and actions
- **Storage Layer**: File system-based storage with atomic writes
- **Packer Engine**: Deterministic rule selection and bundling
- **CLI Interface**: Command-line tools for all operations
- **MCP Server**: Stdio server for AI assistant integration

### Rule Selection Logic

Rules are selected through a multi-stage process:

1. **Scope Filtering**: Match repository patterns, file globs, and languages
2. **Trigger Evaluation**: ALL triggers must match (path/file existence)
3. **Detector Evaluation**: ANY detector can match (regex, file existence, path patterns)
4. **Deterministic Sorting**: Sort by status, severity, version, ID
5. **Limit Application**: Apply maximum rule count if specified

### Data Flow

```
Codebase ──→ Scope Match ──→ Trigger Eval ──→ Detector Eval ──→ Sort & Limit ──→ PackBundle
     │              │              │               │                │
     └─ File globs  └─ Path/file   └─ Regex/file   └─ Status/       └─ JSON with
         Languages       exists         exists      severity         fingerprints
```

## Rule Card Schema

Rule cards are authored in YAML with the following structure:

```yaml
schema_version: 1
id: RULE-android-plugins-dsl
name: Prefer Plugins DSL
version: 1
status: active                    # draft|active|deprecated
severity: warning                 # info|warning|error
domain: android
intent_tags: [gradle, best-practice]
scope:
  file_globs: ["*.gradle", "*.gradle.kts"]
  languages: [kotlin, groovy]
triggers:
  - type: path_contains
    value: ".gradle"
detectors:
  - type: regex
    pattern: apply\s+plugin:\s*['"]\w+['"]
action:
  type: manual
  steps:
    - Replace 'apply plugin: "com.android.application"' with plugins DSL
hint: Use plugins DSL for better performance
references:
  - doc_url: ./docs/android/gradle_plugins.md
provenance:
  author: Your Name
  created: "2024-01-15T10:00:00Z"
```

## CLI Reference

### Core Commands

```bash
hermez init                    # Initialize project
hermez add <domain> <name>     # Add new rule
hermez list [--domain <d>]     # List rules
hermez validate                # Validate all rules
hermez pack <path> [options]   # Pack rules for path
hermez doctor                  # Health check
```

### Pack Options

```bash
hermez pack /path/to/analyze \
  --intent best-practice \     # Filter by intent
  --lang kotlin \              # Filter by language
  --limit 10 \                 # Max rules to return
  --json -                     # JSON output to stdout
```

## Configuration

HermezOS is configured via `hermez.toml`:

```toml
[registry]
root_path = "registry"
default_schema_version = 1

[packer]
default_limit = 50
sort_keys = ["status", "severity", "version", "id"]
sort_orders = ["asc", "asc", "desc", "asc"]

[validation]
strict = true
allow_deprecated = false
```

## Python Library Usage

```python
from hermezos import RulePacker, FileSystemStorage, Config

# Initialize components
config = Config()
storage = FileSystemStorage(config.registry_root)
packer = RulePacker(storage, config)

# Pack rules
from hermezos.models import PackRequest
request = PackRequest(path="/path/to/project", intent_tags=["best-practice"])
bundle = packer.pack(request)

print(f"Packed {len(bundle.rules)} rules")
print(f"Fingerprint: {bundle.pack_fingerprint}")
```

## MCP Integration

HermezOS exposes MCP tools for AI assistants:

### Available Tools

- `hermez.pack`: Pack rules for analysis
- `hermez.add_rule`: Create new rule templates

### Usage with MCP Clients

```bash
# Run MCP server
python -m hermezos.mcp.server

# Or via CLI
hermez mcp
```

## Development

### Setup

```bash
# Install development dependencies
make install-dev

# Run tests
make test

# Format code
make fmt

# Type check
make typecheck
```

### Project Structure

```
hermezos/
├── src/hermezos/
│   ├── __init__.py
│   ├── models.py          # Pydantic models
│   ├── config.py          # Configuration management
│   ├── storage/           # Storage adapters
│   │   ├── __init__.py
│   │   └── filesystem.py
│   ├── packer.py          # Rule packing logic
│   ├── cli.py             # Command-line interface
│   └── mcp/               # MCP server
│       ├── __init__.py
│       └── server.py
├── registry/              # Rule storage
├── tests/                 # Test suite
├── docs/                  # Documentation
├── pyproject.toml         # Project configuration
└── Makefile               # Build automation
```

### Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=hermezos --cov-report=html

# Run specific test
pytest tests/test_packer.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

### Rule Contribution Guidelines

- Use descriptive, actionable rule names
- Include clear hints and step-by-step actions
- Add references to official documentation
- Test rules against real codebases
- Follow the established YAML schema

## License

MIT License - see LICENSE file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/hermezos/hermezos/issues)
- **Documentation**: [docs/](docs/)
- **Discussions**: [GitHub Discussions](https://github.com/hermezos/hermezos/discussions)

---

*HermezOS helps teams capture and share the unwritten rules that make their codebases great.*
