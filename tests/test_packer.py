"""Tests for HermezOS packer logic."""

import tempfile
from pathlib import Path

import pytest

from hermezos.models import (
    Action,
    ActionType,
    Detector,
    DetectorType,
    PackRequest,
    Provenance,
    RuleCard,
    Scope,
    Severity,
    Status,
    Trigger,
    TriggerType,
)
from hermezos.packer import RulePacker
from hermezos.storage.filesystem import FileSystemStorage


class TestRulePacker:
    """Test RulePacker functionality."""

    @pytest.fixture
    def temp_registry(self):
        """Create a temporary registry for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "registry"
            registry_path.mkdir()

            # Create test rules
            android_domain = registry_path / "android"
            android_domain.mkdir()

            # Create a test rule
            rule = RuleCard(
                schema_version=1,
                id="RULE-android-test",
                name="Test Android Rule",
                version=1,
                status=Status.ACTIVE,
                severity=Severity.WARNING,
                domain="android",
                intent_tags=["test"],
                scope=Scope(file_globs=["*.gradle"], languages=["groovy"]),
                triggers=[Trigger(type=TriggerType.PATH_CONTAINS, value=".gradle")],
                detectors=[Detector(type=DetectorType.REGEX, pattern=r"test.*")],
                action=Action(type=ActionType.MANUAL, steps=["Fix the test issue"]),
                provenance=Provenance(
                    author="Test",
                    created="2024-01-15T10:00:00Z",
                    last_updated="2024-01-15T10:00:00Z",
                ),
            )

            # Save rule to file
            storage = FileSystemStorage(registry_path)
            storage.save_card(rule)

            yield registry_path

    @pytest.fixture
    def packer(self, temp_registry):
        """Create a RulePacker instance."""
        storage = FileSystemStorage(temp_registry)
        rules = storage.list_rules()
        return RulePacker(), rules

    def test_scope_matching(self, packer):
        """Test scope-based rule filtering."""
        packer_instance, rules = packer

        # Create test files
        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir)

            # Create files that should match
            gradle_file = test_dir / "build.gradle"
            gradle_file.write_text("test content")

            # Create files that shouldn't match
            txt_file = test_dir / "test.txt"
            txt_file.write_text("test content")

            # Should match gradle file
            assert packer_instance._matches_scope(rules[0], gradle_file)

            # Should not match txt file
            assert not packer_instance._matches_scope(rules[0], txt_file)

    def test_trigger_evaluation(self, packer):
        """Test trigger evaluation."""
        packer_instance, rules = packer

        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir)
            gradle_file = test_dir / "build.gradle"
            gradle_file.write_text("content")

            rule = rules[0]

            # Should trigger on path containing .gradle
            triggers = packer_instance._evaluate_triggers(rule, gradle_file)
            assert len(triggers) == 1
            assert "path contains '.gradle'" in triggers[0]

    def test_detector_evaluation(self, packer):
        """Test detector evaluation."""
        packer_instance, rules = packer

        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir)

            # File with matching content
            gradle_file = test_dir / "build.gradle"
            gradle_file.write_text("test pattern here")

            # File without matching content
            gradle_file2 = test_dir / "build.gradle.kts"
            gradle_file2.write_text("no match here")

            rule = rules[0]

            # Should detect in first file
            detected, detections = packer_instance._evaluate_detectors(
                rule, gradle_file
            )
            assert detected
            assert len(detections) == 1

            # Should not detect in second file
            detected2, detections2 = packer_instance._evaluate_detectors(
                rule, gradle_file2
            )
            assert not detected2

    def test_rule_sorting(self, packer):
        """Test deterministic rule sorting."""
        packer_instance, _ = packer

        # Create rules with different priorities
        rules = [
            RuleCard(
                schema_version=1,
                id="RULE-test-high",
                name="High Priority",
                version=1,
                status=Status.ACTIVE,
                severity=Severity.ERROR,
                domain="test",
                action=Action(type=ActionType.MANUAL, steps=["test"]),
                provenance=Provenance(
                    author="test",
                    created="2024-01-01T00:00:00Z",
                    last_updated="2024-01-01T00:00:00Z",
                ),
            ),
            RuleCard(
                schema_version=1,
                id="RULE-test-low",
                name="Low Priority",
                version=1,
                status=Status.DRAFT,
                severity=Severity.INFO,
                domain="test",
                action=Action(type=ActionType.MANUAL, steps=["test"]),
                provenance=Provenance(
                    author="test",
                    created="2024-01-01T00:00:00Z",
                    last_updated="2024-01-01T00:00:00Z",
                ),
            ),
        ]

        sorted_rules = packer_instance._sort_rules(rules)

        # Error severity should come before Info
        assert sorted_rules[0].severity == Severity.ERROR
        assert sorted_rules[1].severity == Severity.INFO

    def test_pack_request_filtering(self):
        """Test pack request filtering."""
        packer_instance = RulePacker()

        # Create additional test rules
        rule1 = RuleCard(
            schema_version=1,
            id="RULE-android-filter1",
            name="Android Rule 1",
            version=1,
            status=Status.ACTIVE,
            severity=Severity.WARNING,
            domain="android",
            intent_tags=["gradle"],
            scope=Scope(file_globs=["*.gradle"]),
            action=Action(type=ActionType.MANUAL, steps=["test"]),
            provenance=Provenance(
                author="test",
                created="2024-01-01T00:00:00Z",
                last_updated="2024-01-01T00:00:00Z",
            ),
        )

        rule2 = RuleCard(
            schema_version=1,
            id="RULE-python-filter2",
            name="Python Rule",
            version=1,
            status=Status.ACTIVE,
            severity=Severity.INFO,
            domain="python",
            intent_tags=["code"],
            scope=Scope(file_globs=["*.py"]),
            action=Action(type=ActionType.MANUAL, steps=["test"]),
            provenance=Provenance(
                author="test",
                created="2024-01-01T00:00:00Z",
                last_updated="2024-01-01T00:00:00Z",
            ),
        )

        # Test intent filtering
        intent_tags = ["gradle"]
        filtered = packer_instance._filter_by_intent([rule1, rule2], intent_tags)
        assert len(filtered) == 1
        assert filtered[0].domain == "android"

        # Test language filtering
        languages = ["python"]
        # The scope for rule2 has `languages=["python"]` but the
        # _filter_by_languages was failing.
        # It seems the `scope.languages` is not being set correctly
        # in the test object.
        # Let's fix the test to check the filtering correctly.
        rule2.scope.languages = ["python"]
        filtered = packer_instance._filter_by_languages([rule1, rule2], languages)
        assert len(filtered) == 1
        assert filtered[0].domain == "python"

    def test_pack_integration(self, packer):
        """Test full pack operation."""
        packer_instance, rules = packer

        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir)

            # Create a gradle file with test content
            gradle_file = test_dir / "build.gradle"
            gradle_file.write_text("test pattern here")

            # Create pack request
            request = PackRequest(path=str(test_dir))

            # Pack rules
            bundle = packer_instance.pack(rules, request)

            # Should find the test rule
            assert len(bundle.rules) == 1
            assert bundle.rules[0].rule.id == "RULE-android-test"
            assert bundle.total_rules == 1
            assert bundle.pack_fingerprint is not None
            assert bundle.hermez_version == "1.0.0"
            assert bundle.actions_summary is not None

    def test_pack_request_with_filters(self):
        """Test PackRequest with specific filters: intent_tags=["build"],
        languages=["kotlin"], file_globs=["**/*"], limit=5."""
        packer_instance = RulePacker()

        # Create test rules with different properties
        rules = [
            RuleCard(
                schema_version=1,
                id="RULE-android-build-kotlin",
                name="Android Build Kotlin Rule",
                version=1,
                status=Status.ACTIVE,
                severity=Severity.WARNING,
                domain="android",
                intent_tags=["build"],
                scope=Scope(file_globs=["**/*.gradle.kts"], languages=["kotlin"]),
                action=Action(type=ActionType.MANUAL, steps=["test"]),
                provenance=Provenance(
                    author="test",
                    created="2024-01-01T00:00:00Z",
                    last_updated="2024-01-01T00:00:00Z",
                ),
            ),
            RuleCard(
                schema_version=1,
                id="RULE-android-build-groovy",
                name="Android Build Groovy Rule",
                version=1,
                status=Status.ACTIVE,
                severity=Severity.INFO,
                domain="android",
                intent_tags=["build"],
                scope=Scope(file_globs=["**/*.gradle"], languages=["groovy"]),
                action=Action(type=ActionType.MANUAL, steps=["test"]),
                provenance=Provenance(
                    author="test",
                    created="2024-01-01T00:00:00Z",
                    last_updated="2024-01-01T00:00:00Z",
                ),
            ),
            RuleCard(
                schema_version=1,
                id="RULE-python-code",
                name="Python Code Rule",
                version=1,
                status=Status.ACTIVE,
                severity=Severity.ERROR,
                domain="python",
                intent_tags=["code"],
                scope=Scope(file_globs=["**/*.py"], languages=["python"]),
                action=Action(type=ActionType.MANUAL, steps=["test"]),
                provenance=Provenance(
                    author="test",
                    created="2024-01-01T00:00:00Z",
                    last_updated="2024-01-01T00:00:00Z",
                ),
            ),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir)

            # Create test files
            kotlin_file = test_dir / "build.gradle.kts"
            kotlin_file.write_text("kotlin content")

            groovy_file = test_dir / "build.gradle"
            groovy_file.write_text("groovy content")

            python_file = test_dir / "script.py"
            python_file.write_text("python content")

            # Create pack request with specific filters
            request = PackRequest(
                path=str(test_dir),
                intent_tags=["build"],
                languages=["kotlin"],
                file_globs=["**/*"],
                limit=5,
            )

            # Pack rules
            bundle = packer_instance.pack(rules, request)

            # Should find at least 1 rule (the kotlin one)
            assert len(bundle.rules) >= 1

            # Check that the rule matches our filters
            kotlin_rule_found = any(
                r.rule.id == "RULE-android-build-kotlin" for r in bundle.rules
            )
            assert kotlin_rule_found, "Kotlin build rule should be found"

            # Check fingerprints are present
            for rule_match in bundle.rules:
                assert rule_match.fingerprint is not None
                assert len(rule_match.fingerprint) > 0

    def test_deterministic_ordering_and_fingerprints(self, packer):
        """Test that packing produces deterministic order and fingerprints."""
        packer_instance, rules = packer

        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir)

            # Create test file
            gradle_file = test_dir / "build.gradle"
            gradle_file.write_text("test pattern")

            request = PackRequest(path=str(test_dir))

            # Run pack multiple times
            bundle1 = packer_instance.pack(rules, request)
            bundle2 = packer_instance.pack(rules, request)

            # Results should be identical
            assert bundle1.pack_fingerprint == bundle2.pack_fingerprint
            assert len(bundle1.rules) == len(bundle2.rules)
            assert bundle1.total_rules == bundle2.total_rules

            # Rule fingerprints should be identical
            for i, rule_match in enumerate(bundle1.rules):
                assert rule_match.fingerprint == bundle2.rules[i].fingerprint
                assert rule_match.rule.id == bundle2.rules[i].rule.id

            # Check that fingerprints are deterministic across different pack runs
            # by verifying they're not empty and have expected format (hex)
            for rule_match in bundle1.rules:
                assert rule_match.fingerprint is not None
                assert len(rule_match.fingerprint) == 64  # SHA256 hex length
                assert all(c in "0123456789abcdef" for c in rule_match.fingerprint)

    def test_deterministic_packing(self, packer):
        """Test that packing is deterministic."""
        packer_instance, rules = packer

        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir)

            # Create test file
            gradle_file = test_dir / "build.gradle"
            gradle_file.write_text("test pattern")

            request = PackRequest(path=str(test_dir))

            # Pack multiple times
            bundle1 = packer_instance.pack(rules, request)
            bundle2 = packer_instance.pack(rules, request)

            # Should be identical
            assert bundle1.pack_fingerprint == bundle2.pack_fingerprint
            assert len(bundle1.rules) == len(bundle2.rules)
            assert bundle1.rules[0].fingerprint == bundle2.rules[0].fingerprint

    def test_limit_application(self, packer):
        """Test rule limit application."""
        packer_instance, original_rules = packer

        # Create multiple rules
        additional_rules = []
        for i in range(5):
            rule = RuleCard(
                schema_version=1,
                id=f"RULE-test-limit{i}",
                name=f"Limit Test {i}",
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
            additional_rules.append(rule)

        all_rules = original_rules + additional_rules

        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir)
            gradle_file = test_dir / "build.gradle"
            gradle_file.write_text("test")

            # Pack with limit
            request = PackRequest(path=str(test_dir), limit=3)
            bundle = packer_instance.pack(all_rules, request)

            assert len(bundle.rules) == 3
            assert bundle.total_rules == 3

    def test_deprecated_filtering(self, packer):
        """Test deprecated rule filtering."""
        packer_instance, original_rules = packer

        # Create deprecated rule
        deprecated_rule = RuleCard(
            schema_version=1,
            id="RULE-test-deprecated",
            name="Deprecated Rule",
            version=1,
            status=Status.DEPRECATED,
            severity=Severity.INFO,
            domain="test",
            action=Action(type=ActionType.MANUAL, steps=["test"]),
            provenance=Provenance(
                author="test",
                created="2024-01-01T00:00:00Z",
                last_updated="2024-01-01T00:00:00Z",
            ),
        )

        # Create active rule
        active_rule = RuleCard(
            schema_version=1,
            id="RULE-test-active",
            name="Active Rule",
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

        all_rules = original_rules + [deprecated_rule, active_rule]

        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir)
            gradle_file = test_dir / "build.gradle"
            gradle_file.write_text("test")

            # Pack without deprecated
            request = PackRequest(path=str(test_dir), include_deprecated=False)
            bundle = packer_instance.pack(all_rules, request)

            # Should only include active rule
            rule_ids = [r.rule.id for r in bundle.rules]
            assert "RULE-test-active" in rule_ids
            assert "RULE-test-deprecated" not in rule_ids


class TestPackerEdgeCases:
    """Test edge cases in packer logic."""

    def test_empty_registry(self):
        """Test packing with empty registry."""
        packer = RulePacker()

        with tempfile.TemporaryDirectory() as test_dir:
            request = PackRequest(path=test_dir)
            bundle = packer.pack([], request)

            assert len(bundle.rules) == 0
            assert bundle.total_rules == 0
            assert bundle.pack_fingerprint is not None

    def test_nonexistent_path(self):
        """Test packing with nonexistent path."""
        packer_instance = RulePacker()
        rules = []

        request = PackRequest(path="/nonexistent/path")
        bundle = packer_instance.pack(rules, request)

        # Should handle gracefully
        assert isinstance(bundle, object)
        assert bundle.total_rules == 0

    def test_mixed_file_types(self):
        """Test packing with mixed file types."""
        # Create a simple test rule for gradle files
        rule = RuleCard(
            schema_version=1,
            id="RULE-test-gradle",
            name="Test Gradle Rule",
            version=1,
            status=Status.ACTIVE,
            severity=Severity.WARNING,
            domain="test",
            intent_tags=["test"],
            scope=Scope(
                file_globs=["*.gradle", "*.gradle.kts"], languages=["groovy", "kotlin"]
            ),
            detectors=[Detector(type=DetectorType.REGEX, pattern=r"test.*")],
            action=Action(type=ActionType.MANUAL, steps=["Fix the test issue"]),
            provenance=Provenance(
                author="Test",
                created="2024-01-15T10:00:00Z",
                last_updated="2024-01-15T10:00:00Z",
            ),
        )

        packer_instance = RulePacker()

        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir)

            # Create various file types
            files = [
                ("build.gradle", "test content"),
                ("build.gradle.kts", "kotlin test"),
                ("readme.txt", "no match"),
                ("script.py", "python code"),
            ]

            for filename, content in files:
                (test_dir / filename).write_text(content)

            request = PackRequest(path=str(test_dir))
            bundle = packer_instance.pack([rule], request)

            # Should find rules for gradle files
            assert len(bundle.rules) >= 1
