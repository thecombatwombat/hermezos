# HermezOS Documentation

Welcome to the HermezOS documentation. This guide will help you understand, set up, and use HermezOS effectively.

## What is HermezOS?

HermezOS is a local-first knowledge registry and context packer that helps development teams:

- **Capture Best Practices**: Define and share coding standards as structured rule cards
- **Automate Code Review**: Deterministically select relevant rules for any codebase
- **Integrate with Tools**: Use via CLI, Python library, or AI assistants (MCP)

## Quick Start

1. [Installation](installation.md)
2. [First Steps](getting-started.md)
3. [Writing Rules](authoring-rules.md)
4. [CLI Reference](cli-reference.md)

## Core Concepts

### Rule Cards

Rule cards are the fundamental unit of knowledge in HermezOS. Each card defines:

- **Scope**: What files/languages the rule applies to
- **Triggers**: Conditions that activate the rule
- **Detectors**: How to identify violations
- **Actions**: What to do when violations are found

### Packing

The packing process selects and bundles relevant rules:

1. **Scope Filtering**: Match repository patterns and file types
2. **Trigger Evaluation**: Check activation conditions
3. **Detector Evaluation**: Find actual violations
4. **Deterministic Sorting**: Ensure stable, reproducible results

### Fingerprints

Every rule and pack bundle has a stable SHA256 fingerprint for:

- **Caching**: Avoid redundant analysis
- **Integrity**: Detect rule changes
- **Reproducibility**: Ensure consistent results

## User Guides

- [Installation](installation.md)
- [Getting Started](getting-started.md)
- [Authoring Rules](authoring-rules.md)
- [CLI Reference](cli-reference.md)
- [Configuration](configuration.md)

## Developer Guides

- [Python Library](python-library.md)
- [MCP Integration](mcp-integration.md)
- [Extending HermezOS](extending.md)
- [Contributing](contributing.md)

## Domain-Specific Guides

- [Android Development](android/index.md)
- [Python Development](python/index.md)
- [Web Development](web/index.md)

## Reference

- [Rule Schema](schema-reference.md)
- [API Reference](api-reference.md)
- [Configuration Options](configuration.md)
- [Troubleshooting](troubleshooting.md)

## Community

- [GitHub Repository](https://github.com/hermezos/hermezos)
- [Issue Tracker](https://github.com/hermezos/hermezos/issues)
- [Discussions](https://github.com/hermezos/hermezos/discussions)

---

*Questions? Need help? Check out our [troubleshooting guide](troubleshooting.md) or [open an issue](https://github.com/hermezos/hermezos/issues).*