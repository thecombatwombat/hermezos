# HermezOS Development Guide

## Quick Setup

```bash
# Clone and setup
git clone <repo>
cd hermezos
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install development dependencies
pip install -e ".[dev,indexing]"

# Install pre-commit hooks
pre-commit install

# Verify setup
hermez bootstrap
hermez pack . --json
```

## Pre-commit Hooks

The repository includes pre-commit hooks that automatically:

- **Format code** with Black and Ruff
- **Fix common issues** (trailing whitespace, end-of-file newlines)
- **Validate files** (YAML, TOML, JSON syntax)
- **Check bootstrap functionality** (core dependencies work)
- **Run core tests** (bootstrap and null index tests)

### How Pre-commit Works

**Important**: When hooks auto-fix files, the commit is blocked so you can review the changes.

```bash
# Normal workflow
git add .
git commit -m "your message"

# If hooks modify files, you'll see:
# black....................................................................Failed
# - files were modified by this hook

# Stage the auto-fixed files and commit again
git add .
git commit -m "your message"  # Now it should succeed
```

### Running Pre-commit Manually

```bash
# Run on all files
pre-commit run --all-files

# Run on staged files only
pre-commit run

# Skip hooks for emergency commits (not recommended)
git commit --no-verify -m "emergency fix"
```

### Expected Hook Behavior

- **Auto-fixes Applied**: Code formatting, import sorting, whitespace fixes
- **Linting Issues Reported**: Line length, code quality issues that need manual review
- **Functionality Verified**: Bootstrap system and core tests must pass

## Bootstrap System

HermezOS uses a clean bootstrap system for optional dependencies:

### Core Dependencies (Always Available)
- `pydantic`, `typer`, `rich`, `ruamel.yaml`, `pyyaml`

### Optional Dependencies (Bootstrap on Demand)
- **Indexing**: `requests`, `kuzu` - Install with `hermez bootstrap indexing`
- **MCP**: `mcp` - Install with `hermez bootstrap mcp`

### Development Workflow

```bash
# Core functionality always works
hermez pack . --json

# Bootstrap optional features when needed
hermez bootstrap indexing
hermez graph doctor

# Tests automatically handle missing dependencies
python -m pytest tests/test_bootstrap.py  # Always works
python -m pytest tests/test_kuzu_index.py  # Requires bootstrap
```

## Testing

```bash
# Core tests (always work)
python -m pytest tests/test_bootstrap.py tests/test_index_null.py

# Optional tests (require bootstrap)
python -m pytest tests/test_graph_export.py tests/test_kuzu_index.py

# All tests
python -m pytest
```

## Code Quality

The pre-commit hooks ensure:
- **Black** formatting (88 character line length)
- **Ruff** linting with auto-fixes
- **Bootstrap functionality** verification
- **Core test** execution

## Contributing

1. **Fork and clone** the repository
2. **Install dev dependencies**: `pip install -e ".[dev,indexing]"`
3. **Install pre-commit**: `pre-commit install`
4. **Make changes** and commit (hooks run automatically)
5. **Ensure tests pass**: `python -m pytest`
6. **Submit pull request**

The pre-commit hooks will catch most issues before they reach CI, ensuring a smooth development experience.
