"""Command-line interface for HermezOS."""

import builtins
import json
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .config import Config
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
from .mcp.server import main as mcp_main

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
    intent_tags: builtins.list[str] | None = typer.Option(
        None, "--intent", help="Filter by intent tags"
    ),
    languages: builtins.list[str] | None = typer.Option(
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

        bundle = packer.pack(rules, request)

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
