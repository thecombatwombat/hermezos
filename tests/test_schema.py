"""Tests for HermezOS schema validation and rule card models."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from hermezos.models import (
    Action,
    ActionType,
    Detector,
    DetectorType,
    PackBundle,
    PackRequest,
    Provenance,
    Reference,
    RuleCard,
    RuleMatch,
    Scope,
    Severity,
    Status,
    Trigger,
    TriggerType,
    export_json_schemas,
)


class TestRuleCard:
    """Test RuleCard model validation and functionality."""

    def test_valid_rule_card_creation(self):
        """Test creating a valid rule card."""
        rule = RuleCard(
            schema_version=1,
            id="RULE-test-example",
            name="Test Rule",
            version=1,
            status=Status.ACTIVE,
            severity=Severity.INFO,
            domain="test",
            intent_tags=["test", "example"],
            scope=Scope(file_globs=["*.txt"], languages=["text"]),
            triggers=[Trigger(type=TriggerType.PATH_CONTAINS, value="test")],
            detectors=[Detector(type=DetectorType.REGEX, pattern=r"test.*")],
            action=Action(type=ActionType.MANUAL, steps=["Do something"]),
            hint="Test hint",
            references=[
                Reference(doc_url="https://example.com", note="Test reference")
            ],
            provenance=Provenance(
                author="Test Author",
                created="2024-01-15T10:00:00Z",
                last_updated="2024-01-15T10:00:00Z",
            ),
        )

        assert rule.id == "RULE-test-example"
        assert rule.status == Status.ACTIVE
        assert rule.severity == Severity.INFO
        assert rule.domain == "test"

    def test_rule_id_validation(self):
        """Test rule ID format validation."""
        # Valid ID
        RuleCard(
            schema_version=1,
            id="RULE-test-example",
            name="Test",
            version=1,
            status=Status.ACTIVE,
            severity=Severity.INFO,
            domain="test",
            action=Action(type=ActionType.MANUAL, steps=["test"]),
            provenance=Provenance(
                author="test",
                created="2024-01-01T00:00:00Z",
                last_updated="2024-01-01T00:00:00Z",
            ),
        )

        # Invalid IDs should raise ValidationError
        with pytest.raises(ValueError, match="Rule ID must start with 'RULE-'"):
            RuleCard(
                schema_version=1,
                id="invalid-id",
                name="Test",
                version=1,
                status=Status.ACTIVE,
                severity=Severity.INFO,
                domain="test",
                action=Action(type=ActionType.MANUAL, steps=["test"]),
                provenance=Provenance(
                    author="test",
                    created="2024-01-01T00:00:00Z",
                    last_updated="2024-01-01T00:00:00Z",
                ),
            ).normalize()

    def test_default_retriable(self):
        """Test default retriable value based on action type."""
        # Manual action should not be retriable by default
        rule = RuleCard(
            schema_version=1,
            id="RULE-test-manual",
            name="Manual Rule",
            version=1,
            status=Status.ACTIVE,
            severity=Severity.INFO,
            domain="test",
            action=Action(type=ActionType.MANUAL, steps=["Do something"]),
            provenance=Provenance(
                author="test",
                created="2024-01-01T00:00:00Z",
                last_updated="2024-01-01T00:00:00Z",
            ),
        ).normalize()
        assert rule.retriable is False

        # Script action should be retriable by default
        rule = RuleCard(
            schema_version=1,
            id="RULE-test-script",
            name="Script Rule",
            version=1,
            status=Status.ACTIVE,
            severity=Severity.INFO,
            domain="test",
            action=Action(type=ActionType.SCRIPT, fix_command="echo test"),
            provenance=Provenance(
                author="test",
                created="2024-01-01T00:00:00Z",
                last_updated="2024-01-01T00:00:00Z",
            ),
        ).normalize()
        assert rule.retriable is True

    def test_default_hint_generation(self):
        """Test automatic hint generation from action steps."""
        rule = RuleCard(
            schema_version=1,
            id="RULE-test-hint",
            name="Hint Test",
            version=1,
            status=Status.ACTIVE,
            severity=Severity.INFO,
            domain="test",
            action=Action(
                type=ActionType.MANUAL, steps=["First step to take", "Second step"]
            ),
            provenance=Provenance(
                author="test",
                created="2024-01-01T00:00:00Z",
                last_updated="2024-01-01T00:00:00Z",
            ),
        ).normalize()

        # Should use first step as hint if not provided
        assert rule.hint == "First step to take"

    def test_fingerprint_computation(self):
        """Test rule fingerprint computation."""
        rule1 = RuleCard(
            schema_version=1,
            id="RULE-test-fp",
            name="Fingerprint Test",
            version=1,
            status=Status.ACTIVE,
            severity=Severity.INFO,
            domain="test",
            action=Action(type=ActionType.MANUAL, steps=["test"]),
            provenance=Provenance(
                author="test",
                created="2024-01-01T00:00:00Z",
                last_updated="2024-01-01T00:00:00Z",
            ),
        )

        rule2 = RuleCard(
            schema_version=1,
            id="RULE-test-fp",
            name="Fingerprint Test",
            version=1,
            status=Status.ACTIVE,
            severity=Severity.INFO,
            domain="test",
            action=Action(type=ActionType.MANUAL, steps=["test"]),
            provenance=Provenance(
                author="test",
                created="2024-01-01T00:00:00Z",
                last_updated="2024-01-01T00:00:00Z",
            ),
        )

        # Same content should produce same fingerprint
        assert rule1.compute_fingerprint() == rule2.compute_fingerprint()

        # Different content should produce different fingerprint
        rule3 = rule1.model_copy(update={"version": 2})
        assert rule1.compute_fingerprint() != rule3.compute_fingerprint()

    def test_yaml_loading_and_derived_defaults(self):
        """Test loading YAML rule and asserting derived defaults."""
        # Sample YAML content based on the existing rule
        yaml_content = """
schema_version: 1
id: "RULE-android-plugins-dsl"
name: "Prefer Gradle plugins DSL"
version: 1
status: "active"
severity: "warning"
domain: "android"
intent_tags: ["build", "gradle"]
scope:
  repo_patterns: ["app/", "lib/"]
  file_globs: ["**/*.gradle.kts", "**/build.gradle"]
  languages: ["kotlin"]
triggers:
  - type: "path_contains"
    value: "app/src/main"
detectors:
  - type: "regex"
    file_glob: "**/build.gradle"
    pattern: "(?m)^apply plugin: 'kotlin-android'$"
action:
  type: "script"
  fix_command: "scripts/fix_kotlin_plugin.sh"
  steps:
    - "Open the module's Gradle file and use the plugins DSL."
hint: "Prefer plugins {} DSL over 'apply plugin'"
references:
  - doc_url: "docs/android/gradle_plugins.md#kotlin"
    note: "Rationale and example"
provenance:
  author: "HermezOS Team"
  created: "2024-01-15T10:00:00Z"
  last_updated: "2024-01-15T10:00:00Z"
"""

        # Parse YAML
        yaml_data = yaml.safe_load(yaml_content)

        # Create RuleCard from YAML data
        rule = RuleCard(**yaml_data).normalize()

        # Test derived defaults
        assert rule.retriable is True  # Script action should be retriable
        assert (
            rule.hint == "Prefer plugins {} DSL over 'apply plugin'"
        )  # Hint should be present

    def test_yaml_loading_script_action_defaults(self):
        """Test YAML loading with script action sets retriable=True."""
        yaml_content = """
schema_version: 1
id: "RULE-test-script-action"
name: "Test Script Action"
version: 1
status: "active"
severity: "info"
domain: "test"
action:
  type: "script"
  fix_command: "echo test"
  steps:
    - "Run the fix command"
provenance:
  author: "Test"
  created: "2024-01-15T10:00:00Z"
  last_updated: "2024-01-15T10:00:00Z"
"""

        yaml_data = yaml.safe_load(yaml_content)
        rule = RuleCard(**yaml_data).normalize()

        # Script action should default to retriable=True
        assert rule.retriable is True
        # Hint should be derived from first step
        assert rule.hint == "Run the fix command"

    def test_yaml_loading_manual_action_defaults(self):
        """Test YAML loading with manual action sets retriable=False."""
        yaml_content = """
schema_version: 1
id: "RULE-test-manual-action"
name: "Test Manual Action"
version: 1
status: "active"
severity: "info"
domain: "test"
action:
  type: "manual"
  steps:
    - "Do something manually"
    - "Then do something else"
provenance:
  author: "Test"
  created: "2024-01-15T10:00:00Z"
  last_updated: "2024-01-15T10:00:00Z"
"""

        yaml_data = yaml.safe_load(yaml_content)
        rule = RuleCard(**yaml_data).normalize()

        # Manual action should default to retriable=False
        assert rule.retriable is False
        # Hint should be derived from first step
        assert rule.hint == "Do something manually"


class TestPackRequest:
    """Test PackRequest model."""

    def test_pack_request_creation(self):
        """Test creating a pack request."""
        request = PackRequest(
            path="/test/path",
            intent_tags=["test", "example"],
            languages=["python"],
            limit=10,
        )

        assert request.path == "/test/path"
        assert request.intent_tags == ["test", "example"]
        assert request.languages == ["python"]
        assert request.limit == 10
        assert request.include_deprecated is False


class TestPackBundle:
    """Test PackBundle model."""

    def test_pack_bundle_creation(self):
        """Test creating a pack bundle."""
        request = PackRequest(path="/test")
        rule = RuleCard(
            schema_version=1,
            id="RULE-test-bundle",
            name="Bundle Test",
            version=1,
            status=Status.ACTIVE,
            severity=Severity.INFO,
            domain="test",
            action=Action(type=ActionType.MANUAL, steps=["test"]),
            provenance=Provenance(
                author="test",
                created="2024-01-01T00:00:00Z",
                last_updated="2024-01-01T00:00:00Z",
            ),
        )

        bundle = PackBundle(
            pack_request=request,
            rules=[
                RuleMatch(
                    rule=rule,
                    fingerprint=rule.compute_fingerprint(),
                    triggered_by=["test trigger"],
                    detected_in=["test.txt"],
                )
            ],
        )

        assert bundle.pack_request == request
        assert len(bundle.rules) == 1
        assert bundle.total_rules == 1
        assert bundle.pack_fingerprint is not None

    def test_bundle_fingerprint_stability(self):
        """Test that bundle fingerprints are stable."""
        request = PackRequest(path="/test")
        rule = RuleCard(
            schema_version=1,
            id="RULE-test-fp",
            name="Fingerprint Test",
            version=1,
            status=Status.ACTIVE,
            severity=Severity.INFO,
            domain="test",
            action=Action(type=ActionType.MANUAL, steps=["test"]),
            provenance=Provenance(
                author="test",
                created="2024-01-01T00:00:00Z",
                last_updated="2024-01-01T00:00:00Z",
            ),
        )

        bundle1 = PackBundle(
            pack_request=request,
            rules=[
                RuleMatch(
                    rule=rule,
                    fingerprint=rule.compute_fingerprint(),
                    triggered_by=["trigger"],
                    detected_in=["file.txt"],
                )
            ],
        )

        bundle2 = PackBundle(
            pack_request=request,
            rules=[
                RuleMatch(
                    rule=rule,
                    fingerprint=rule.compute_fingerprint(),
                    triggered_by=["trigger"],
                    detected_in=["file.txt"],
                )
            ],
        )

        # Same content should produce same fingerprint
        assert bundle1.pack_fingerprint == bundle2.pack_fingerprint


class TestEnums:
    """Test enum values and ordering."""

    def test_status_values(self):
        """Test Status enum values."""
        assert Status.DRAFT.value == "draft"
        assert Status.ACTIVE.value == "active"
        assert Status.DEPRECATED.value == "deprecated"

    def test_severity_values(self):
        """Test Severity enum values."""
        assert Severity.INFO.value == "info"
        assert Severity.WARNING.value == "warning"
        assert Severity.ERROR.value == "error"

    def test_action_type_values(self):
        """Test ActionType enum values."""
        assert ActionType.MANUAL.value == "manual"
        assert ActionType.SCRIPT.value == "script"
        assert ActionType.DOC.value == "doc"

    def test_detector_type_values(self):
        """Test DetectorType enum values."""
        assert DetectorType.REGEX.value == "regex"
        assert DetectorType.FILE_EXISTS.value == "file_exists"
        assert DetectorType.PATH_CONTAINS.value == "path_contains"

    def test_trigger_type_values(self):
        """Test TriggerType enum values."""
        assert TriggerType.PATH_CONTAINS.value == "path_contains"
        assert TriggerType.FILE_EXISTS.value == "file_exists"


class TestModelSerialization:
    """Test model JSON serialization."""

    def test_rule_card_serialization(self):
        """Test RuleCard JSON serialization."""
        rule = RuleCard(
            schema_version=1,
            id="RULE-test-serialize",
            name="Serialize Test",
            version=1,
            status=Status.ACTIVE,
            severity=Severity.INFO,
            domain="test",
            action=Action(type=ActionType.MANUAL, steps=["test"]),
            provenance=Provenance(
                author="test",
                created="2024-01-01T00:00:00Z",
                last_updated="2024-01-01T00:00:00Z",
            ),
        )

        # Should serialize to JSON
        json_str = rule.model_dump_json()
        assert json_str is not None

        # Should deserialize back
        rule_dict = json.loads(json_str)
        rule_copy = RuleCard(**rule_dict)
        assert rule_copy.id == rule.id

    def test_pack_bundle_serialization(self):
        """Test PackBundle JSON serialization."""
        request = PackRequest(path="/test")
        bundle = PackBundle(pack_request=request, rules=[])

        # Should serialize to JSON
        json_str = bundle.model_dump_json()
        assert json_str is not None

        # Should deserialize back
        bundle_dict = json.loads(json_str)
        bundle_copy = PackBundle(**bundle_dict)
        assert bundle_copy.pack_request.path == bundle.pack_request.path


class TestSchemaExport:
    """Test JSON schema export functionality."""

    def test_json_schema_export_exists(self):
        """Test that JSON schema export function exists and works."""
        with (
            patch("pathlib.Path.mkdir") as mock_mkdir,
            patch("builtins.open", create=True) as mock_open,
            patch("json.dump") as mock_dump,
            patch("builtins.print") as mock_print,
        ):
            # Create a temporary directory path
            output_dir = Path("/tmp/test_schemas")

            # Call the export function
            export_json_schemas(output_dir)

            # Verify mkdir was called
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

            # Verify open was called for each schema (4 schemas)
            assert mock_open.call_count == 4

            # Verify json.dump was called for each schema
            assert mock_dump.call_count == 4

            # Verify print was called for each schema
            assert mock_print.call_count == 4

    def test_json_schema_export_creates_files(self, tmp_path):
        """Test that JSON schema export creates the expected files."""
        output_dir = tmp_path / "schemas"
        export_json_schemas(output_dir)

        # Check that all expected schema files were created
        expected_files = [
            "rulecard.json",
            "packrequest.json",
            "packbundle.json",
            "rulematch.json",
        ]

        for filename in expected_files:
            schema_file = output_dir / filename
            assert schema_file.exists(), f"Schema file {filename} was not created"

            # Verify it's valid JSON
            with open(schema_file) as f:
                schema_data = json.load(f)
                assert isinstance(schema_data, dict)
                assert "$schema" in schema_data or "type" in schema_data
