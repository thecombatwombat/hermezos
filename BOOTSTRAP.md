# HermezOS Bootstrap Guide

HermezOS now features a clean bootstrap system that eliminates dependency management headaches. The core system works out of the box, with optional features available on demand.

## Quick Start

```bash
# Install HermezOS (core functionality only)
pip install hermezos

# Use core features immediately
hermez init
hermez pack . --json

# Bootstrap optional features when needed
hermez bootstrap indexing
```

## Core vs Optional Features

### ✅ Core Features (Always Available)
- Rule management (`hermez add`, `hermez list`, `hermez validate`)
- Code analysis and packing (`hermez pack`)
- Project initialization (`hermez init`)
- Health checks (`hermez doctor`)

### 🔧 Optional Features (Bootstrap Required)

#### Graph Indexing (`hermez bootstrap indexing`)
- **Graphiti Integration**: Export rules to JSONL format or sync to live server
- **Kùzu Database**: Embedded graph database for rule prefiltering
- **Commands**: `hermez graph export`, `hermez graph sync`, `hermez graph doctor`

#### MCP Server (`hermez bootstrap mcp`)
- **Model Context Protocol**: AI assistant integration
- **Command**: `hermez mcp`

## Bootstrap Commands

### Show Available Features
```bash
hermez bootstrap
```

### Install Specific Feature
```bash
# Install graph indexing dependencies
hermez bootstrap indexing

# Install MCP server dependencies  
hermez bootstrap mcp

# Install all optional features
hermez bootstrap all
```

### Force Reinstall
```bash
hermez bootstrap indexing --force
```

## Dependency Management

### Core Dependencies (Always Installed)
- `pydantic` - Data validation and serialization
- `typer` - CLI framework
- `rich` - Terminal formatting
- `ruamel.yaml` - YAML processing
- `pyyaml` - YAML parsing

### Optional Dependencies (Bootstrap on Demand)

#### Indexing Extra (`hermezos[indexing]`)
- `requests` - HTTP client for Graphiti live mode
- `kuzu` - Embedded graph database

#### MCP Extra (`hermezos[mcp]`)
- `mcp` - Model Context Protocol support

#### All Extras (`hermezos[all]`)
- All optional dependencies combined

## Error Handling

When you try to use optional features without bootstrapping, you'll get helpful error messages:

```bash
$ hermez graph export
Graph indexing is disabled. Enable it in hermez.toml:

[graph]
enabled = true
driver = "graphiti"
```

If dependencies are missing, you'll see:
```
ImportError: The 'requests' library is required for Graphiti live mode.
Install it with: pip install 'hermezos[indexing]' or run: hermez bootstrap
```

## Configuration

After bootstrapping indexing, enable it in your `hermez.toml`:

```toml
[graph]
enabled = true
driver = "graphiti"  # or "kuzu"
mode = "export_only"  # or "live" for Graphiti
export_path = "graph"
```

## Verification

Check that everything is working:

```bash
# Verify core functionality
hermez doctor

# Verify indexing (after bootstrap)
hermez graph doctor

# Test end-to-end
hermez pack . --json
```

## Benefits

### 🚀 **Zero Friction Start**
- Install and use HermezOS immediately
- No complex dependency resolution
- Core features work out of the box

### 📦 **On-Demand Features**
- Only install what you need
- Clear feature boundaries
- Automatic dependency detection

### 🛠 **Developer Friendly**
- Helpful error messages with solutions
- Automatic guidance for next steps
- Force reinstall option for troubleshooting

### 🔄 **Backward Compatible**
- All existing functionality preserved
- Graceful fallbacks when features unavailable
- No breaking changes to existing workflows

## Troubleshooting

### "Feature already installed"
```bash
hermez bootstrap indexing --force
```

### "Unknown feature"
```bash
hermez bootstrap  # Shows available features
```

### Dependencies not working after bootstrap
```bash
# Verify installation
python -c "import requests, kuzu; print('Dependencies OK')"

# Force reinstall
hermez bootstrap indexing --force
```

---

*The bootstrap system ensures HermezOS "just works" while keeping advanced features optional and easy to enable.*