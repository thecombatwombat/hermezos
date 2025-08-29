"""Tests for HermezOS CLI commands."""

import json
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from hermezos.cli import app, EXIT_VALIDATION_ERROR, EXIT_BAD_USAGE


class TestCLI:
    """Test CLI commands."""

    @pytest.fixture
    def runner(self):
        """CLI runner fixture."""
        return CliRunner()

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # Create hermez.toml
            config_content = """
[registry]
root_path = "registry"

[packer]
default_limit = 50
"""
            (project_path / "hermez.toml").write_text(config_content)

            # Create registry
            registry_path = project_path / "registry"
            registry_path.mkdir()

            yield project_path

    def test_init_command(self, runner, tmp_path):
        """Test hermez init command."""
        result = runner.invoke(app, ["init", "--path", str(tmp_path)])

        assert result.exit_code == 0
        assert "HermezOS initialized" in result.output

        # Check files were created
        assert (tmp_path / "hermez.toml").exists()
        assert (tmp_path / "registry").exists()

    def test_init_existing_force(self, runner, temp_project):
        """Test init with existing files and force flag."""
        # Should fail without force
        result = runner.invoke(app, ["init", "--path", str(temp_project)])
        assert result.exit_code == EXIT_BAD_USAGE
        assert "already initialized" in result.output

        # Should succeed with force
        result = runner.invoke(app, ["init", "--path", str(temp_project), "--force"])
        assert result.exit_code == 0

    def test_add_command(self, runner, temp_project):
        """Test hermez add command."""
        result = runner.invoke(
            app, ["add", "test", "Test Rule", "--path", str(temp_project)]
        )
    
        assert result.exit_code == 0
        assert "Rule 'RULE-test-test-rule' created" in result.output
    
        # Check rule file was created
        rule_file = temp_project / "registry" / "test" / "RULE-test-test-rule.yaml"
        assert rule_file.exists()

    def test_list_command(self, runner, temp_project):
        """Test hermez list command."""
        # First add a rule
        runner.invoke(app, ["add", "test", "List Test Rule", "--path", str(temp_project)])
    
        # List rules
        result = runner.invoke(app, ["list", "--path", str(temp_project)])
    
        assert result.exit_code == 0
        assert "List Test Rule" in result.output

    def test_list_json_command(self, runner, temp_project):
        """Test hermez list --json command."""
        # First add a rule
        runner.invoke(app, ["add", "test", "JSON Test Rule", "--path", str(temp_project)])
    
        # List rules as JSON
        result = runner.invoke(app, ["list", "--json", "--path", str(temp_project)])
    
        assert result.exit_code == 0
    
        # Should be valid JSON
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) > 0
        assert data[0]["name"] == "JSON Test Rule"

    def test_validate_command(self, runner, temp_project):
        """Test hermez validate command."""
        # First add a rule
        runner.invoke(app, ["add", "test", "Validate Test Rule", "--path", str(temp_project)])

        # Validate rules
        result = runner.invoke(app, ["validate", "--path", str(temp_project)])

        assert result.exit_code == 0
        assert "All rules valid" in result.output

    def test_pack_command(self, runner, temp_project):
        """Test hermez pack command."""
        # Create a test file to analyze
        test_file = temp_project / "test.gradle"
        test_file.write_text("apply plugin: 'com.android.application'")

        # Add a rule that should match
        runner.invoke(app, ["add", "android", "Gradle Plugin Rule", "--path", str(temp_project)])
    
        # Pack rules
        result = runner.invoke(
            app, ["pack", str(test_file), "--project-path", str(temp_project)]
        )
    
        assert result.exit_code == 0
        # Should show packing results
        assert "Packed" in result.output or "No rules" in result.output

    def test_pack_json_command(self, runner, temp_project):
        """Test hermez pack --json command."""
        # Create a test file
        test_file = temp_project / "test.gradle"
        test_file.write_text("test content")

        runner.invoke(app, ["add", "test", "JSON Pack Rule", "--path", str(temp_project)])
    
        # Pack with JSON output
        result = runner.invoke(
            app,
            ["pack", str(test_file), "--json", "--output", "-", "--project-path", str(temp_project)],
        )
    
        assert result.exit_code == 0

        # Should be valid JSON
        data = json.loads(result.output)
        assert "pack_request" in data
        assert "rules" in data
        assert "pack_fingerprint" in data

    def test_doctor_command(self, runner, temp_project):
        """Test hermez doctor command."""
        result = runner.invoke(app, ["doctor", "--path", str(temp_project)])

        assert result.exit_code == 0
        assert "HermezOS Doctor" in result.output
        assert "Configuration file" in result.output
        assert "Registry directory" in result.output

    def test_invalid_command(self, runner):
        """Test invalid command handling."""
        result = runner.invoke(app, ["invalid-command"])

        assert result.exit_code != 0
        assert "No such command" in result.output

    def test_bad_usage(self, runner):
        """Test bad usage handling."""
        result = runner.invoke(app, ["pack"])  # Missing required path argument

        assert result.exit_code == 2  # Bad usage exit code
        assert "Missing argument" in result.output


class TestCLIIntegration:
    """Integration tests for CLI functionality."""

    @pytest.fixture
    def runner(self):
        """CLI runner fixture."""
        return CliRunner()

    def test_full_workflow(self, runner, tmp_path):
        """Test complete CLI workflow."""
        project_path = tmp_path / "hermez_test"
        project_path.mkdir()

        # Initialize
        result = runner.invoke(app, ["init", "--path", str(project_path)])
        assert result.exit_code == 0

        # Add rule
        result = runner.invoke(
            app, ["add", "test", "Integration Test Rule", "--path", str(project_path)]
        )
        assert result.exit_code == 0, result.output

        # Validate
        result = runner.invoke(app, ["validate", "--path", str(project_path)])
        assert result.exit_code == 0

        # List
        result = runner.invoke(app, ["list", "--path", str(project_path)])
        assert result.exit_code == 0
        assert "Integration Test Rule" in result.output

        # Doctor
        result = runner.invoke(app, ["doctor", "--path", str(project_path)])
        assert result.exit_code == 0

    def test_rule_filtering(self, runner, tmp_path):
        """Test rule filtering in list command."""
        project_path = tmp_path / "filter_test"
        project_path.mkdir()

        # Initialize
        runner.invoke(app, ["init", "--path", str(project_path)])

        # Add rules with different domains
        runner.invoke(
            app, ["add", "android", "Android Rule", "--path", str(project_path)]
        )
        runner.invoke(
            app, ["add", "python", "Python Rule", "--path", str(project_path)]
        )

        # List all
        result = runner.invoke(app, ["list", "--path", str(project_path)])
        assert "Android Rule" in result.output
        assert "Python Rule" in result.output

        # List android only
        result = runner.invoke(
            app, ["list", "--domain", "android", "--path", str(project_path)]
        )
        assert "Android Rule" in result.output
        assert "Python Rule" not in result.output

    def test_pack_filters(self, runner, tmp_path):
        """Test pack command filters."""
        project_path = tmp_path / "pack_test"
        project_path.mkdir()

        # Initialize and add rule
        runner.invoke(app, ["init", "--path", str(project_path)])
        runner.invoke(
            app, ["add", "test", "Pack Filter Rule", "--path", str(project_path)]
        )

        # Create test file
        test_file = project_path / "test.txt"
        test_file.write_text("test content")

        # Pack with limit
        result = runner.invoke(
            app, ["pack", str(test_file), "--limit", "1", "--project-path", str(project_path)]
        )
        assert result.exit_code == 0

    def test_init_validate_list_commands(self, runner, tmp_path):
        """Test init, validate, and list commands with exit codes
        and expected strings."""
        project_path = tmp_path / "cli_test"
        project_path.mkdir()

        # Test init command
        result = runner.invoke(app, ["init", "--path", str(project_path)])
        assert result.exit_code == 0
        assert "HermezOS initialized" in result.output

        # Verify files were created
        assert (project_path / "hermez.toml").exists()
        assert (project_path / "registry").exists()

        # Add a test rule
        result = runner.invoke(
            app, ["add", "test", "CLI Test Rule", "--path", str(project_path)]
        )
        assert result.exit_code == 0, result.output
        assert "Rule 'RULE-test-cli-test-rule' created" in result.output

        # Test validate command
        result = runner.invoke(app, ["validate", "--path", str(project_path)])
        assert result.exit_code == 0
        assert "All rules valid" in result.output

        # Test list command
        result = runner.invoke(app, ["list", "--path", str(project_path)])
        assert result.exit_code == 0
        assert "CLI Test Rule" in result.output

    def test_pack_to_file_and_compare_golden(self, runner, tmp_path):
        """Test pack command output to file and compare with golden file."""
        project_path = tmp_path / "golden_test"
        project_path.mkdir()

        # Initialize project
        runner.invoke(app, ["init", "--path", str(project_path)])

        # Copy the existing rule to the test registry
        import shutil

        test_registry = project_path / "registry" / "android"
        test_registry.mkdir(parents=True)
        shutil.copy(
            "registry/android/prefer-plugins-dsl--RULE-android-plugins-dsl.yaml",
            test_registry / "prefer-plugins-dsl--RULE-android-plugins-dsl.yaml",
        )

        # Create a test gradle file that should match the rule
        test_file = project_path / "build.gradle"
        test_file.write_text("apply plugin: 'com.android.application'")

        # Pack to a JSON file
        pack_output = project_path / "pack.json"
        result = runner.invoke(
            app,
            [
                "pack",
                str(test_file),
                "--json",
                str(pack_output),
                "--project-path",
                str(project_path),
                ],
        )
        assert result.exit_code == 0

        # Verify the pack.json file was created
        assert pack_output.exists()

        # Load and compare with golden file (normalizing timestamps)
        with open(pack_output) as f:
            pack_data = json.load(f)

        with open("tests/data/golden_packbundle.json") as f:
            golden_data = json.load(f)

        # Normalize timestamps for comparison (ignore created_at field)
        pack_data_normalized = pack_data.copy()
        golden_data_normalized = golden_data.copy()

        # Remove timestamp fields for comparison
        if "created_at" in pack_data_normalized:
            del pack_data_normalized["created_at"]
        if "created_at" in golden_data_normalized:
            del golden_data_normalized["created_at"]

        # Compare the structure and key fields
        assert (
            pack_data_normalized["pack_request"]["path"]
            == golden_data_normalized["pack_request"]["path"]
        )
        assert (
            pack_data_normalized["pack_request"]["intent_tags"]
            == golden_data_normalized["pack_request"]["intent_tags"]
        )
        assert (
            pack_data_normalized["pack_request"]["languages"]
            == golden_data_normalized["pack_request"]["languages"]
        )

        # Check that rules are present
        assert len(pack_data_normalized["rules"]) > 0
        assert len(golden_data_normalized["rules"]) > 0

        # Check that the first rule has expected structure
        rule = pack_data_normalized["rules"][0]
        golden_rule = golden_data_normalized["rules"][0]

        assert rule["rule"]["id"] == golden_rule["rule"]["id"]
        assert rule["rule"]["name"] == golden_rule["rule"]["name"]
        assert rule["rule"]["domain"] == golden_rule["rule"]["domain"]

        # Check that fingerprints are present
        assert "fingerprint" in rule
        assert "pack_fingerprint" in pack_data_normalized
        assert len(pack_data_normalized["pack_fingerprint"]) > 0


class TestCLIErrorHandling:
    """Test CLI error handling."""

    @pytest.fixture
    def runner(self):
        """CLI runner fixture."""
        return CliRunner()

    def test_missing_config(self, runner, tmp_path):
        """Test behavior with missing config."""
        result = runner.invoke(app, ["list", "--path", str(tmp_path)])

        # Should handle missing config gracefully
        assert result.exit_code == EXIT_BAD_USAGE

    def test_corrupt_config(self, runner, tmp_path):
        """Test behavior with corrupt config."""
        config_file = tmp_path / "hermez.toml"
        config_file.write_text("invalid toml content {")

        result = runner.invoke(app, ["list", "--path", str(tmp_path)])

        # Should handle corrupt config
        assert result.exit_code == EXIT_BAD_USAGE

    def test_invalid_rule_file(self, runner, tmp_path):
        """Test behavior with invalid rule file."""
        # Initialize
        runner.invoke(app, ["init", "--path", str(tmp_path)])

        # Create invalid rule file
        registry_path = tmp_path / "registry" / "test"
        registry_path.mkdir(parents=True)
        rule_file = registry_path / "invalid.yaml"
        rule_file.write_text("invalid: yaml: content: [")

        result = runner.invoke(app, ["validate", "--path", str(tmp_path)])

        # Should handle invalid rule file
        assert result.exit_code == EXIT_VALIDATION_ERROR, result.output
