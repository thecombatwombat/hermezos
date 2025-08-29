"""Command-line interface for HermezOS."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, List

import typer
from rich.console import Console
from rich.table import Table

from .config import Config
from .mcp.server import main as mcp_main
from .models import (
    Action,
    ActionType,
    PackRequest,
    Provenance,
    RuleCard,
    Scope,
    Severity,
    Status,
)
from .packer import RulePacker
from .storage.filesystem import FileSystemStorage

# Exit codes
EXIT_OK = 0
EXIT_VALIDATION_ERROR = 1
EXIT_BAD_USAGE = 2
EXIT_PACKING_FAILURE = 3
EXIT_IO_ERROR = 4

app = typer.Typer()
console = Console()


def get_storage(config: Config) -> FileSystemStorage:
    """Get storage instance from configuration."""
    return FileSystemStorage(config.registry_root)


def get_packer(config: Config) -> RulePacker:
    """Get packer instance from configuration."""
    return RulePacker()


def get_index(config: Config):
    """Get index adapter from configuration."""
    from .index import make_index
    return make_index(config)


@app.command()
def init(
    path: Path | None = typer.Option(
        None, "--path", help="Path to initialize (default: current directory)"
    ),
    force: bool = typer.Option(
        False, "--force", help="Overwrite existing configuration"
    ),
) -> None:
    """Initialize HermezOS in the current directory."""
    try:
        target_path = path or Path.cwd()

        # Check if already initialized
        config_path = target_path / "hermez.toml"
        registry_path = target_path / "registry"

        if config_path.exists() and not force:
            console.print(
                "[red]HermezOS already initialized. Use --force to overwrite.[/red]"
            )
            raise typer.Exit(EXIT_BAD_USAGE)

        # Create registry directory
        registry_path.mkdir(parents=True, exist_ok=True)

        # Create default configuration
        config_content = """# HermezOS Configuration
# This file contains default settings for the HermezOS knowledge registry

[registry]
# Root directory for rule cards
root_path = "registry"

# Default schema version for new rule cards
default_schema_version = 1

[packer]
# Default limit for pack operations
default_limit = 50

# Default sort order for rule selection
# Options: status, severity, version, id
sort_keys = ["status", "severity", "version", "id"]
sort_orders = ["asc", "asc", "desc", "asc"]

[validation]
# Enable strict validation
strict = true

# Allow deprecated rules in packs
allow_deprecated = false

[output]
# Default output format
format = "json"

# Pretty print JSON output
pretty = true

# Include fingerprints in output
include_fingerprints = true

[logging]
# Default log level
level = "INFO"

# Log format
format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
"""

        with open(config_path, "w") as f:
            f.write(config_content)

        # Create docs directory and sample documentation
        docs_path = target_path / "docs"
        docs_path.mkdir(parents=True, exist_ok=True)

        sample_doc_content = """# HermezOS Knowledge Registry

This directory contains documentation for HermezOS rules and best practices.

## Getting Started

1. Add rule cards to the `registry/` directory
2. Use `hermez validate` to check your rules
3. Use `hermez pack <path>` to analyze code and get rule recommendations

## Rule Card Format

Rule cards are YAML files that define coding standards, best
practices, and automated fixes.

See the [Rule Card Schema](./schemas/rulecard.json) for complete specification.
"""

        with open(docs_path / "index.md", "w") as f:
            f.write(sample_doc_content)

        # Create scripts directory and sample script
        scripts_path = target_path / "scripts"
        scripts_path.mkdir(parents=True, exist_ok=True)

        sample_script_content = """#!/bin/bash
# Sample HermezOS fix script
# This script demonstrates how to create automated fixes for rule violations

set -e

# Example: Fix a common issue
if [ $# -eq 0 ]; then
    echo "Usage: $0 <file>"
    exit 1
fi

FILE="$1"

# Add your fix logic here
echo "Applying fix to $FILE"

# Example fix: Replace old pattern with new pattern
# sed -i 's/old_pattern/new_pattern/g' "$FILE"

echo "Fix applied successfully"
"""

        sample_script_path = scripts_path / "sample_fix.sh"
        with open(sample_script_path, "w") as f:
            f.write(sample_script_content)

        # Make script executable
        import os

        os.chmod(sample_script_path, 0o755)

        # Create sample rule card
        sample_rule_content = """schema_version: 1
id: RULE-sample-hello-world
name: Hello World Sample Rule
version: 1
status: active
severity: info
domain: sample
intent_tags:
  - example
  - getting-started
scope:
  repo_patterns: []
  file_globs:
    - "*.txt"
    - "*.md"
  languages: []
triggers:
  - type: path_contains
    value: "."
detectors:
  - type: regex
    pattern: "TODO|FIXME"
    file_glob: "*.txt"
action:
  type: manual
  steps:
    - Review and address the TODO or FIXME comment
    - Consider breaking down large tasks into smaller, actionable items
    - Add proper documentation or implementation
hint: Found a TODO or FIXME comment that needs attention
retriable: false
references:
  - doc_url: ./docs/index.md
    note: Getting started guide
provenance:
  author: HermezOS CLI
  created: "2024-01-15T10:00:00Z"
  last_updated: "2024-01-15T10:00:00Z"
"""

        sample_domain_path = registry_path / "sample"
        sample_domain_path.mkdir(parents=True, exist_ok=True)

        with open(sample_domain_path / "RULE-sample-hello-world.yaml", "w") as f:
            f.write(sample_rule_content)

        console.print(f"[green]HermezOS initialized in {target_path}[/green]")
        console.print(f"[blue]Configuration: {config_path}[/blue]")
        console.print(f"[blue]Registry: {registry_path}[/blue]")
        console.print(f"[blue]Documentation: {docs_path}[/blue]")
        console.print(f"[blue]Scripts: {scripts_path}[/blue]")
        console.print("[green]Sample rule created: RULE-sample-hello-world[/green]")

    except typer.Exit:
        # Re-raise typer.Exit exceptions (preserve exit codes)
        raise
    except (OSError, PermissionError) as e:
        console.print(f"[red]Failed to initialize: {e}[/red]")
        raise typer.Exit(EXIT_IO_ERROR) from e
    except Exception as e:
        console.print(f"[red]Failed to initialize: {e}[/red]")
        raise typer.Exit(EXIT_IO_ERROR) from e


@app.command()
def add(
    domain: str = typer.Argument(..., help="Rule domain"),
    name: str = typer.Argument(..., help="Rule name"),
    path: Path | None = typer.Option(None, "--path", help="Path to HermezOS project"),
    status: Status = typer.Option(Status.DRAFT, "--status", help="Rule status"),
    severity: Severity = typer.Option(
        Severity.INFO, "--severity", help="Rule severity"
    ),
    description: str | None = typer.Option(
        None, "--description", help="Rule description"
    ),
) -> None:
    """Add a new rule card interactively."""
    try:
        config_path = path / "hermez.toml" if path else Path.cwd() / "hermez.toml"
        if not config_path.exists():
            console.print(
                f"[red]HermezOS project not found at {config_path.parent}[/red]"
            )
            raise typer.Exit(EXIT_BAD_USAGE)
        config = Config(config_path)
        storage = get_storage(config)

        # Generate rule ID
        slug = name.lower().replace(" ", "-").replace("_", "-")
        rule_id = f"RULE-{domain}-{slug}"

        # Check if rule already exists
        if storage.get_rule(rule_id):
            console.print(f"[red]Rule '{rule_id}' already exists[/red]")
            raise typer.Exit(EXIT_VALIDATION_ERROR)

        # Create basic rule structure
        rule = RuleCard(
            schema_version=config.get("registry.default_schema_version", 1),
            id=rule_id,
            name=name,
            version=1,
            status=status,
            severity=severity,
            domain=domain,
            intent_tags=[],
            scope=Scope(),
            triggers=[],
            detectors=[],
            action=Action(
                type=ActionType.MANUAL,
                steps=["Describe the manual steps to resolve this issue"],
                fix_command=None,
            ),
            hint=description or f"Review {name.lower()}",
            retriable=False,
            references=[],
            provenance=Provenance(
                author="CLI User",
                created=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                last_updated=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            ),
        )

        # Save the rule
        storage.save_card(rule)

        rule_path = storage._get_rule_path(rule_id)
        console.print(f"[green]Rule '{rule_id}' created at {rule_path}[/green]")
        console.print(
            "[yellow]Edit the YAML file to customize triggers, detectors, "
            "and actions[/yellow]"
        )

    except typer.Exit:
        # Re-raise typer.Exit exceptions (preserve exit codes)
        raise
    except (OSError, PermissionError) as e:
        console.print(f"[red]Failed to add rule: {e}[/red]")
        raise typer.Exit(EXIT_IO_ERROR) from e
    except Exception as e:
        console.print(f"[red]Failed to add rule: {e}[/red]")
        raise typer.Exit(EXIT_IO_ERROR) from e


@app.command()
def list(
    path: Path | None = typer.Option(None, "--path", help="Path to HermezOS project"),
    domain: str | None = typer.Option(None, "--domain", help="Filter by domain"),
    status: Status | None = typer.Option(None, "--status", help="Filter by status"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List rule cards."""
    try:
        config_path = path / "hermez.toml" if path else Path.cwd() / "hermez.toml"
        if not config_path.exists():
            console.print(
                f"[red]HermezOS project not found at {config_path.parent}[/red]"
            )
            raise typer.Exit(EXIT_BAD_USAGE)

        try:
            config = Config(config_path)
        except ValueError as e:
            console.print(f"[red]Configuration error: {e}[/red]")
            raise typer.Exit(EXIT_BAD_USAGE) from e

        storage = get_storage(config)

        rules = storage.list_rules(domain)

        if status:
            rules = [r for r in rules if r.status == status]

        if json_output:
            rules_data = [r.model_dump() for r in rules]
            console.print_json(json.dumps(rules_data, indent=2))
        else:
            table = Table(title="Rule Cards")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="white")
            table.add_column("Domain", style="green")
            table.add_column("Status", style="yellow")
            table.add_column("Severity", style="red")
            table.add_column("Version", style="blue")

            for rule in rules:
                table.add_row(
                    rule.id,
                    rule.name,
                    rule.domain,
                    rule.status.value,
                    rule.severity.value,
                    str(rule.version),
                )

            console.print(table)
            console.print(f"\nTotal: {len(rules)} rules")

    except typer.Exit:
        # Re-raise typer.Exit exceptions (preserve exit codes)
        raise
    except (OSError, PermissionError) as e:
        console.print(f"[red]Failed to list rules: {e}[/red]")
        raise typer.Exit(EXIT_IO_ERROR) from e
    except Exception as e:
        console.print(f"[red]Failed to list rules: {e}[/red]")
        raise typer.Exit(EXIT_IO_ERROR) from e


@app.command()
def validate(
    path: Path | None = typer.Option(None, "--path", help="Path to HermezOS project"),
    rule_id: str | None = typer.Option(None, "--rule", help="Validate specific rule"),
    strict: bool = typer.Option(
        True, "--strict/--no-strict", help="Enable strict validation"
    ),
    include_deprecated: bool = typer.Option(
        False, "--include-deprecated", help="Include deprecated rules in validation"
    ),
) -> None:
    """Validate rule cards."""
    try:
        config_path = path / "hermez.toml" if path else Path.cwd() / "hermez.toml"
        if not config_path.exists():
            console.print(
                f"[red]HermezOS project not found at {config_path.parent}[/red]"
            )
            raise typer.Exit(EXIT_BAD_USAGE)

        try:
            config = Config(config_path)
        except ValueError as e:
            console.print(f"[red]Configuration error: {e}[/red]")
            raise typer.Exit(EXIT_BAD_USAGE) from e

        storage = get_storage(config)

        # First check for invalid YAML files
        file_errors = storage.validate_all_files()
        if file_errors:
            console.print("[red]Invalid YAML files found:[/red]")
            for error in file_errors:
                console.print(f"  [red]- {error}[/red]")
            raise typer.Exit(EXIT_VALIDATION_ERROR)

        if rule_id:
            rule = storage.get_rule(rule_id)
            if not rule:
                console.print(f"[red]Rule '{rule_id}' not found[/red]")
                raise typer.Exit(EXIT_VALIDATION_ERROR)

            rules = [rule]
        else:
            rules = storage.list_rules()

        all_valid = True
        deprecated_count = 0

        for rule in rules:
            # Skip deprecated rules unless explicitly included
            if rule.status.value == "deprecated" and not include_deprecated:
                deprecated_count += 1
                continue

            errors = storage.validate_rule(rule)

            if errors:
                console.print(f"[red]✗ {rule.id}:[/red]")
                for error in errors:
                    console.print(f"  [red]- {error}[/red]")
                all_valid = False
            else:
                console.print(f"[green]✓ {rule.id}[/green]")

        # Warn about deprecated rules
        if deprecated_count > 0:
            console.print(
                f"\n[yellow]⚠ {deprecated_count} deprecated rule(s) found[/yellow]"
            )
            console.print(
                "[yellow]Use --include-deprecated to validate deprecated rules[/yellow]"
            )

        if not all_valid:
            console.print("\n[red]Validation failed[/red]")
            raise typer.Exit(EXIT_VALIDATION_ERROR)
        else:
            console.print("\n[green]All rules valid[/green]")

    except typer.Exit:
        # Re-raise typer.Exit exceptions (preserve exit codes)
        raise
    except (OSError, PermissionError) as e:
        console.print(f"[red]Validation failed: {e}[/red]")
        raise typer.Exit(EXIT_IO_ERROR) from e
    except Exception as e:
        console.print(f"[red]Validation failed: {e}[/red]")
        raise typer.Exit(EXIT_VALIDATION_ERROR) from e


@app.command()
def pack(
    path: str = typer.Argument(..., help="Path to analyze"),
    intent_tags: List[str] | None = typer.Option(
        None, "--intent", help="Filter by intent tags"
    ),
    languages: List[str] | None = typer.Option(
        None, "--lang", help="Filter by programming languages"
    ),
    limit: int | None = typer.Option(None, "--limit", help="Maximum number of rules"),
    include_deprecated: bool = typer.Option(
        False, "--include-deprecated", help="Include deprecated rules"
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    output_file: str = typer.Option(
        "-", "--output", help="Output file (default: stdout)"
    ),
    project_path: Path | None = typer.Option(
        None, "--project-path", help="Path to HermezOS project"
    ),
) -> None:
    """Pack rules for the given path."""
    try:
        config_path = (
            project_path / "hermez.toml" if project_path else Path.cwd() / "hermez.toml"
        )
        config = Config(config_path)
        storage = get_storage(config)
        packer = get_packer(config)

        # Get index adapter
        index = get_index(config)

        # Get all rules from storage
        rules = storage.list_rules()

        request = PackRequest(
            path=path,
            intent_tags=intent_tags,
            languages=languages,
            limit=limit,
            include_deprecated=include_deprecated,
            file_globs=None,
        )

        try:
            bundle = packer.pack(rules, request, index)
        finally:
            # Always close index
            if index:
                index.close()

        if json_output:
            bundle_data = bundle.model_dump()
            json_str = json.dumps(bundle_data, indent=2, sort_keys=True)

            if output_file == "-":
                console.print(json_str)
            else:
                with open(output_file, "w") as f:
                    f.write(json_str)
                console.print(f"[green]Bundle saved to {output_file}[/green]")
        else:
            console.print(f"[green]Packed {len(bundle.rules)} rules[/green]")
            console.print(f"[blue]Fingerprint: {bundle.pack_fingerprint}[/blue]")

            if bundle.rules:
                table = Table(title="Matched Rules")
                table.add_column("ID", style="cyan")
                table.add_column("Name", style="white")
                table.add_column("Severity", style="red")
                table.add_column("Triggered By", style="yellow")

                for match in bundle.rules:
                    triggered = ", ".join(
                        match.triggered_by[:2]
                    )  # Show first 2 triggers
                    if len(match.triggered_by) > 2:
                        triggered += "..."
                    table.add_row(
                        match.rule.id,
                        match.rule.name,
                        match.rule.severity.value,
                        triggered or "N/A",
                    )

                console.print(table)

    except typer.Exit:
        # Re-raise typer.Exit exceptions (preserve exit codes)
        raise
    except (OSError, PermissionError) as e:
        console.print(f"[red]Packing failed: {e}[/red]")
        raise typer.Exit(EXIT_IO_ERROR) from e
    except Exception as e:
        console.print(f"[red]Packing failed: {e}[/red]")
        raise typer.Exit(EXIT_PACKING_FAILURE) from e


@app.command()
def doctor(
    path: Path | None = typer.Option(None, "--path", help="Path to HermezOS project")
) -> None:
    """Check HermezOS installation and configuration."""
    try:
        project_path = path or Path.cwd()
        config_path = project_path / "hermez.toml"
        registry_path = project_path / "registry"

        checks = []

        # Check configuration file
        if config_path.exists():
            checks.append(("Configuration file", True, str(config_path)))
        else:
            checks.append(("Configuration file", False, "hermez.toml not found"))

        # Check registry directory
        if registry_path.exists():
            checks.append(("Registry directory", True, str(registry_path)))
        else:
            checks.append(("Registry directory", False, "registry/ not found"))

        # Check for rule files
        rule_count = 0
        if registry_path.exists():
            for _ in registry_path.rglob("*.yaml"):
                rule_count += 1

        checks.append(("Rule files", rule_count > 0, f"{rule_count} rules found"))

        # Display results
        table = Table(title="HermezOS Doctor")
        table.add_column("Check", style="white")
        table.add_column("Status", style="green")
        table.add_column("Details", style="blue")

        for check_name, status, details in checks:
            status_icon = "[green]✓[/green]" if status else "[red]✗[/red]"
            table.add_row(check_name, status_icon, details)

        console.print(table)

        # Overall status
        all_good = all(status for _, status, _ in checks)
        if all_good:
            console.print("\n[green]HermezOS is healthy![/green]")
        else:
            console.print(
                "\n[yellow]Some issues found. Run 'hermez init' to fix.[/yellow]"
            )

    except typer.Exit:
        # Re-raise typer.Exit exceptions (preserve exit codes)
        raise
    except (OSError, PermissionError) as e:
        console.print(f"[red]Doctor check failed: {e}[/red]")
        raise typer.Exit(EXIT_IO_ERROR) from e
    except Exception as e:
        console.print(f"[red]Doctor check failed: {e}[/red]")
        raise typer.Exit(EXIT_IO_ERROR) from e


@app.command()
def bootstrap(
    feature: str | None = typer.Argument(None, help="Feature to bootstrap (indexing, mcp, all)"),
    force: bool = typer.Option(False, "--force", help="Force reinstall even if already installed"),
) -> None:
    """Bootstrap optional dependencies for HermezOS features."""
    import subprocess
    import sys
    
    try:
        # Map features to extras
        feature_map = {
            "indexing": "indexing",
            "mcp": "mcp",
            "all": "all",
        }
        
        if feature is None:
            # Show available features
            console.print("[blue]Available features to bootstrap:[/blue]")
            console.print("  [cyan]indexing[/cyan] - Graph indexing with Graphiti and Kùzu")
            console.print("  [cyan]mcp[/cyan] - Model Context Protocol server support")
            console.print("  [cyan]all[/cyan] - All optional features")
            console.print("\n[yellow]Usage:[/yellow] hermez bootstrap <feature>")
            return
            
        if feature not in feature_map:
            console.print(f"[red]Unknown feature '{feature}'. Available: {', '.join(feature_map.keys())}[/red]")
            raise typer.Exit(EXIT_BAD_USAGE)
            
        extra = feature_map[feature]
        
        # Check if already installed (unless force)
        if not force:
            missing_deps = []
            
            if feature in ("indexing", "all"):
                try:
                    import requests
                except ImportError:
                    missing_deps.append("requests")
                    
                try:
                    import kuzu
                except ImportError:
                    missing_deps.append("kuzu")
                    
            if feature in ("mcp", "all"):
                try:
                    import mcp
                except ImportError:
                    missing_deps.append("mcp")
                    
            if not missing_deps:
                console.print(f"[green]Feature '{feature}' is already installed![/green]")
                console.print("[yellow]Use --force to reinstall[/yellow]")
                return
                
        # Install the feature
        console.print(f"[blue]Installing '{feature}' dependencies...[/blue]")
        
        # Use pip to install the extra
        cmd = [sys.executable, "-m", "pip", "install", f"hermezos[{extra}]"]
        if force:
            cmd.append("--force-reinstall")
            
        console.print(f"[dim]Running: {' '.join(cmd)}[/dim]")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            console.print(f"[green]✓ Successfully installed '{feature}' dependencies![/green]")
            
            # Show what was installed
            if feature in ("indexing", "all"):
                console.print("  [cyan]• requests[/cyan] - HTTP client for Graphiti live mode")
                console.print("  [cyan]• kuzu[/cyan] - Embedded graph database")
                
            if feature in ("mcp", "all"):
                console.print("  [cyan]• mcp[/cyan] - Model Context Protocol support")
                
            console.print(f"\n[blue]You can now use '{feature}' features![/blue]")
            
            # Show next steps
            if feature in ("indexing", "all"):
                console.print("\n[yellow]Next steps for indexing:[/yellow]")
                console.print("1. Enable indexing in hermez.toml:")
                console.print("   [graph]")
                console.print("   enabled = true")
                console.print("   driver = \"graphiti\"  # or \"kuzu\"")
                console.print("2. Run: hermez graph doctor")
                console.print("3. Export rules: hermez graph export")
                
        else:
            console.print(f"[red]✗ Installation failed![/red]")
            console.print(f"[red]Error: {result.stderr}[/red]")
            raise typer.Exit(EXIT_IO_ERROR)
            
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Bootstrap failed: {e}[/red]")
        raise typer.Exit(EXIT_IO_ERROR) from e


# Graph command group
graph_app = typer.Typer()
app.add_typer(graph_app, name="graph", help="Graph indexing operations")


@graph_app.command()
def export(
    path: Path | None = typer.Option(None, "--path", help="Path to HermezOS project"),
) -> None:
    """Export rules to Graphiti JSONL format."""
    try:
        config_path = path / "hermez.toml" if path else Path.cwd() / "hermez.toml"
        if not config_path.exists():
            console.print(
                f"[red]HermezOS project not found at {config_path.parent}[/red]"
            )
            raise typer.Exit(EXIT_BAD_USAGE)

        config = Config(config_path)
        
        if not config.graph_enabled:
            console.print("[yellow]Graph indexing is disabled. Enable it in hermez.toml:[/yellow]")
            console.print("[yellow][graph][/yellow]")
            console.print("[yellow]enabled = true[/yellow]")
            console.print("[yellow]driver = \"graphiti\"[/yellow]")
            raise typer.Exit(EXIT_OK)
            
        if config.graph_driver != "graphiti":
            console.print(f"[red]Export requires driver='graphiti', got '{config.graph_driver}'[/red]")
            raise typer.Exit(EXIT_BAD_USAGE)

        storage = get_storage(config)
        index = get_index(config)
        
        try:
            # Load all rules and upsert to index
            rules = storage.list_rules()
            console.print(f"[blue]Loading {len(rules)} rules...[/blue]")
            
            for rule in rules:
                index.upsert_card(rule)
            
            # Close index to trigger export
            index.close()
            
            # Report results
            export_path = Path(config.graph_export_path)
            nodes_file = export_path / "nodes.jsonl"
            edges_file = export_path / "edges.jsonl"
            
            if nodes_file.exists() and edges_file.exists():
                nodes_count = sum(1 for _ in open(nodes_file))
                edges_count = sum(1 for _ in open(edges_file))
                console.print(f"[green]Exported {nodes_count} nodes and {edges_count} edges[/green]")
                console.print(f"[blue]Files: {nodes_file}, {edges_file}[/blue]")
            else:
                console.print("[yellow]Export completed but files not found[/yellow]")
                
        finally:
            if index:
                index.close()

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Export failed: {e}[/red]")
        raise typer.Exit(EXIT_IO_ERROR) from e


@graph_app.command()
def sync(
    path: Path | None = typer.Option(None, "--path", help="Path to HermezOS project"),
) -> None:
    """Sync rules to live Graphiti server."""
    try:
        config_path = path / "hermez.toml" if path else Path.cwd() / "hermez.toml"
        if not config_path.exists():
            console.print(
                f"[red]HermezOS project not found at {config_path.parent}[/red]"
            )
            raise typer.Exit(EXIT_BAD_USAGE)

        config = Config(config_path)
        
        if not config.graph_enabled:
            console.print("[yellow]Graph indexing is disabled. Enable it in hermez.toml:[/yellow]")
            console.print("[yellow][graph][/yellow]")
            console.print("[yellow]enabled = true[/yellow]")
            console.print("[yellow]driver = \"graphiti\"[/yellow]")
            console.print("[yellow]mode = \"live\"[/yellow]")
            raise typer.Exit(EXIT_OK)
            
        if config.graph_driver != "graphiti":
            console.print(f"[red]Sync requires driver='graphiti', got '{config.graph_driver}'[/red]")
            raise typer.Exit(EXIT_BAD_USAGE)
            
        if config.graph_mode != "live":
            console.print(f"[red]Sync requires mode='live', got '{config.graph_mode}'[/red]")
            raise typer.Exit(EXIT_BAD_USAGE)

        storage = get_storage(config)
        index = get_index(config)
        
        try:
            # Load all rules and sync to server
            rules = storage.list_rules()
            console.print(f"[blue]Syncing {len(rules)} rules to {config.graph_url}...[/blue]")
            
            for rule in rules:
                index.upsert_card(rule)
            
            console.print("[green]Sync completed[/green]")
                
        finally:
            if index:
                index.close()

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Sync failed: {e}[/red]")
        raise typer.Exit(EXIT_IO_ERROR) from e


@graph_app.command("doctor")
def graph_doctor(
    path: Path | None = typer.Option(None, "--path", help="Path to HermezOS project"),
) -> None:
    """Check graph indexing configuration and health."""
    try:
        config_path = path / "hermez.toml" if path else Path.cwd() / "hermez.toml"
        if not config_path.exists():
            console.print(
                f"[red]HermezOS project not found at {config_path.parent}[/red]"
            )
            raise typer.Exit(EXIT_BAD_USAGE)

        config = Config(config_path)
        
        # Display configuration
        table = Table(title="Graph Indexing Configuration")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Enabled", str(config.graph_enabled))
        table.add_row("Driver", config.graph_driver)
        table.add_row("Mode", config.graph_mode)
        
        if config.graph_driver == "graphiti":
            table.add_row("URL", config.graph_url)
            table.add_row("Export Path", config.graph_export_path)
        elif config.graph_driver == "kuzu":
            table.add_row("DB Path", config.graph_db_path)
            
        console.print(table)
        
        # Health checks
        checks = []
        
        if not config.graph_enabled:
            checks.append(("Graph indexing", False, "Disabled in configuration"))
        else:
            checks.append(("Graph indexing", True, f"Enabled with driver '{config.graph_driver}'"))
            
            # Driver-specific checks
            if config.graph_driver == "graphiti":
                if config.graph_mode == "live":
                    # Test connection to Graphiti server
                    try:
                        import requests
                        response = requests.head(config.graph_url, timeout=5)
                        if response.status_code < 400:
                            checks.append(("Graphiti server", True, f"Reachable at {config.graph_url}"))
                        else:
                            checks.append(("Graphiti server", False, f"HTTP {response.status_code}"))
                    except Exception as e:
                        checks.append(("Graphiti server", False, f"Connection failed: {e}"))
                else:
                    # Check export directory
                    export_path = Path(config.graph_export_path)
                    if export_path.exists():
                        checks.append(("Export directory", True, f"Exists at {export_path}"))
                    else:
                        checks.append(("Export directory", False, f"Not found: {export_path}"))
                        
            elif config.graph_driver == "kuzu":
                # Test Kuzu availability and DB path
                try:
                    import kuzu
                    checks.append(("Kuzu library", True, "Available"))
                    
                    db_path = Path(config.graph_db_path)
                    if db_path.exists():
                        checks.append(("Database path", True, f"Exists at {db_path}"))
                    else:
                        checks.append(("Database path", False, f"Will be created at {db_path}"))
                        
                except ImportError:
                    checks.append(("Kuzu library", False, "Not installed (pip install kuzu)"))
        
        # Display health check results
        health_table = Table(title="Health Checks")
        health_table.add_column("Check", style="white")
        health_table.add_column("Status", style="green")
        health_table.add_column("Details", style="blue")
        
        for check_name, status, details in checks:
            status_icon = "[green]✓[/green]" if status else "[red]✗[/red]"
            health_table.add_row(check_name, status_icon, details)
        
        console.print(health_table)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Doctor check failed: {e}[/red]")
        raise typer.Exit(EXIT_IO_ERROR) from e


@app.command()
def mcp() -> None:
    """Start the MCP (Model Context Protocol) server."""
    try:
        mcp_main()
    except KeyboardInterrupt:
        # Handle graceful shutdown
        pass
    except Exception as e:
        console.print(f"[red]MCP server failed: {e}[/red]")
        raise typer.Exit(EXIT_IO_ERROR) from e


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
