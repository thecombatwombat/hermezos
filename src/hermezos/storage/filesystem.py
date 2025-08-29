"""File system storage implementation for HermezOS."""

import os
import tempfile
from pathlib import Path
from typing import Union, Any

import ruamel.yaml
from pydantic import ValidationError

from ..models import RuleCard


class FileSystemStorage:
    """File system-based storage for rule cards."""

    def __init__(self, root: Path):
        """Initialize storage with root path."""
        self.root_path = Path(root)
        self.yaml = ruamel.yaml.YAML()
        self.yaml.preserve_quotes = True
        self.yaml.indent(mapping=2, sequence=4, offset=2)

    def load_all_cards(self) -> list[RuleCard]:
        """Load all rule cards from storage, parse YAML, and normalize."""
        cards: list[RuleCard] = []

        if not self.root_path.exists():
            return cards

        for yaml_file in self.root_path.rglob("*.yaml"):
            try:
                with open(yaml_file, encoding="utf-8") as f:
                    data = self.yaml.load(f)

                if data is None:
                    continue

                # Validate and create RuleCard
                rule = RuleCard(**data)

                # Call normalize() as required
                rule = rule.normalize()

                cards.append(rule)

            except (
                OSError,
                FileNotFoundError,
                ValidationError,
                ruamel.yaml.constructor.ConstructorError,
                ruamel.yaml.parser.ParserError,
                ruamel.yaml.scanner.ScannerError,
            ) as e:
                # Log error but continue processing other files
                print(f"Error loading {yaml_file}: {e}")
                continue

        return cards

    def save_card(self, card: RuleCard) -> None:
        """Save a rule card to storage with atomic write."""
        rule_path = self._get_rule_path(card.id)

        # Convert to dict and serialize to YAML
        card_dict = card.model_dump(exclude_unset=True)

        # Convert enum values to strings for YAML serialization
        def convert_enums(obj: Any) -> Any:
            if isinstance(obj, dict):
                return {k: convert_enums(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_enums(item) for item in obj]
            elif hasattr(obj, "value"):  # Enum
                return obj.value
            else:
                return obj

        serializable_dict = convert_enums(card_dict)

        # Create YAML string
        from io import StringIO

        stream = StringIO()
        self.yaml.dump(serializable_dict, stream)
        yaml_str = stream.getvalue()

        # Atomic write
        self._atomic_write(rule_path, yaml_str)

    def list_paths(self) -> list[Path]:
        """List all YAML file paths in storage."""
        if not self.root_path.exists():
            return []

        return list(self.root_path.rglob("*.yaml"))

    def _get_rule_path(self, rule_id: str) -> Path:
        """Get the file path for a rule ID."""
        # Parse domain from rule ID (RULE-<domain>-<slug>)
        parts = rule_id.split("-")
        if len(parts) < 3 or parts[0] != "RULE":
            raise ValueError(f"Invalid rule ID format: {rule_id}")

        domain = parts[1]
        domain_dir = self.root_path / domain
        domain_dir.mkdir(parents=True, exist_ok=True)

        return domain_dir / f"{rule_id}.yaml"

    def _atomic_write(self, path: Path, content: str) -> None:
        """Write content to file atomically."""
        # Create temporary file in same directory
        temp_fd = None
        temp_path = None

        try:
            # Create temporary file
            temp_fd, temp_path_str = tempfile.mkstemp(
                dir=path.parent, prefix=f"{path.name}.tmp.", suffix=".tmp"
            )
            temp_path = Path(temp_path_str)

            # Write content to temporary file
            with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())  # Force write to disk

            temp_fd = None  # Don't close again in finally

            # Atomic rename
            temp_path.replace(path)

        finally:
            if temp_fd is not None:
                os.close(temp_fd)
            if temp_path and temp_path.exists():
                temp_path.unlink(missing_ok=True)

    def _load_rule_from_file(self, path: Path) -> Union[RuleCard, None]:
        """Load a rule card from a YAML file."""
        try:
            with open(path, encoding="utf-8") as f:
                data = self.yaml.load(f)

            if data is None:
                return None

            # Validate and create RuleCard
            rule = RuleCard(**data)
            return rule

        except (
            FileNotFoundError,
            ValidationError,
            ruamel.yaml.constructor.ConstructorError,
            ruamel.yaml.parser.ParserError,
            ruamel.yaml.scanner.ScannerError,
        ):
            return None

    def list_rules(self, domain: Union[str, None] = None) -> list[RuleCard]:
        """List all rule cards, optionally filtered by domain."""
        rules = []

        if domain:
            # List rules from specific domain
            domain_dir = self.root_path / domain
            if not domain_dir.exists():
                return []

            for yaml_file in domain_dir.glob("*.yaml"):
                rule = self._load_rule_from_file(yaml_file)
                if rule:
                    rules.append(rule)
        else:
            # List all rules from all domains
            if not self.root_path.exists():
                return []

            for yaml_file in self.root_path.rglob("*.yaml"):
                rule = self._load_rule_from_file(yaml_file)
                if rule:
                    rules.append(rule)

        return rules

    def get_rule(self, rule_id: str) -> Union[RuleCard, None]:
        """Get a specific rule card by ID."""
        rule_path = self._get_rule_path(rule_id)
        return self._load_rule_from_file(rule_path)

    def delete_rule(self, rule_id: str) -> bool:
        """Delete a rule card by ID. Returns True if deleted."""
        rule_path = self._get_rule_path(rule_id)

        if rule_path.exists():
            rule_path.unlink()
            return True

        return False

    def validate_rule(self, rule: RuleCard) -> list[str]:
        """Validate a rule card. Returns list of validation errors."""
        errors = []

        # Check for duplicate IDs
        existing_rule = self.get_rule(rule.id)
        if existing_rule and existing_rule != rule:
            errors.append(f"Rule with ID '{rule.id}' already exists")

        # Validate references exist (if they point to local docs)
        for ref in rule.references:
            if ref.doc_url.startswith("./") or ref.doc_url.startswith("../"):
                doc_path = self.root_path.parent / ref.doc_url
                if not doc_path.exists():
                    errors.append(f"Referenced documentation not found: {ref.doc_url}")

        # Validate action consistency
        if rule.action.type == "script" and not rule.action.fix_command:
            errors.append("Script actions must have a fix_command")

        if rule.action.type == "manual" and not rule.action.steps:
            errors.append("Manual actions must have steps")

        # Enhanced script permission check
        if rule.action.type == "script" and rule.action.fix_command:
            self._validate_script_permissions(rule.action.fix_command, errors)

        return errors

    def _validate_script_permissions(self, fix_command: str, errors: list[str]) -> None:
        """Validate script permissions for fix_command."""
        try:
            # Extract the script path from command (first argument before any options)
            command_parts = fix_command.strip().split()
            if not command_parts:
                errors.append("Script fix_command cannot be empty")
                return

            script_path_str = command_parts[0]

            # Convert to Path and resolve
            if script_path_str.startswith("./") or script_path_str.startswith("../"):
                # Relative path - resolve relative to project root
                script_path = (self.root_path.parent / script_path_str).resolve()
            else:
                # Absolute path
                script_path = Path(script_path_str).resolve()

            # Check if script exists
            if not script_path.exists():
                errors.append(f"Script file not found: {script_path}")
                return

            # Check if script is executable
            if not os.access(script_path, os.X_OK):
                errors.append(f"Script is not executable: {script_path}")

            # Additional check: ensure it's a regular file (not a directory)
            if not script_path.is_file():
                errors.append(f"Script path is not a regular file: {script_path}")

        except (OSError, ValueError) as e:
            errors.append(f"Error validating script permissions: {e}")
