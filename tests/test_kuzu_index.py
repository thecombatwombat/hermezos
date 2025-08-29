"""Tests for KuzuIndex implementation."""

import tempfile
from pathlib import Path

import pytest

from hermezos.models import (
    Action,
    ActionType,
    PackRequest,
    Provenance,
    RuleCard,
    Severity,
    Status,
)

# Skip tests if Kuzu is not available
kuzu = pytest.importorskip("kuzu")

# Import after pytest.importorskip to avoid import errors
from hermezos.index.kuzu_index import KuzuIndex  # noqa: E402


@pytest.fixture
def temp_db_path():
    """Create a temporary file path for Kuzu database."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir) / "test_kuzu.db"


@pytest.fixture
def sample_rules():
    """Create sample rule cards for testing."""
    return [
        RuleCard(
            schema_version=1,
            id="RULE-test-alpha",
            name="Alpha Test Rule",
            version=1,
            status=Status.ACTIVE,
            severity=Severity.WARNING,
            domain="test",
            intent_tags=["testing", "alpha"],
            action=Action(type=ActionType.MANUAL, steps=["Alpha step"]),
            provenance=Provenance(
                author="Test",
                created="2024-01-01T00:00:00Z",
                last_updated="2024-01-01T00:00:00Z",
            ),
        ),
        RuleCard(
            schema_version=1,
            id="RULE-test-beta",
            name="Beta Test Rule",
            version=2,
            status=Status.ACTIVE,
            severity=Severity.ERROR,
            domain="test",
            intent_tags=["testing", "beta"],
            action=Action(type=ActionType.MANUAL, steps=["Beta step"]),
            provenance=Provenance(
                author="Test",
                created="2024-01-01T00:00:00Z",
                last_updated="2024-01-01T00:00:00Z",
            ),
        ),
        RuleCard(
            schema_version=1,
            id="RULE-prod-gamma",
            name="Gamma Production Rule",
            version=1,
            status=Status.ACTIVE,
            severity=Severity.INFO,
            domain="prod",
            intent_tags=["production", "gamma"],
            action=Action(type=ActionType.MANUAL, steps=["Gamma step"]),
            provenance=Provenance(
                author="Test",
                created="2024-01-01T00:00:00Z",
                last_updated="2024-01-01T00:00:00Z",
            ),
        ),
    ]


def test_kuzu_index_initialization(temp_db_path):
    """Test that KuzuIndex initializes correctly."""
    index = KuzuIndex(temp_db_path)

    # Database directory should be created
    assert temp_db_path.exists()

    # Should be able to close without errors
    index.close()


def test_kuzu_index_upsert_and_query(temp_db_path, sample_rules):
    """Test upserting rules and querying by intent tags."""
    index = KuzuIndex(temp_db_path)

    try:
        # Upsert all sample rules
        for rule in sample_rules:
            index.upsert_card(rule)

        # Query by intent tag "testing"
        request = PackRequest(path=".", intent_tags=["testing"])
        candidates = index.candidate_ids(request)

        # Should return rules with "testing" tag
        expected_ids = {"RULE-test-alpha", "RULE-test-beta"}
        assert set(candidates) == expected_ids

        # Results should be sorted
        assert candidates == sorted(candidates)

    finally:
        index.close()


def test_kuzu_index_query_multiple_tags(temp_db_path, sample_rules):
    """Test querying with multiple intent tags (OR logic)."""
    index = KuzuIndex(temp_db_path)

    try:
        # Upsert all sample rules
        for rule in sample_rules:
            index.upsert_card(rule)

        # Query by multiple tags
        request = PackRequest(path=".", intent_tags=["alpha", "gamma"])
        candidates = index.candidate_ids(request)

        # Should return rules with either "alpha" or "gamma" tag
        expected_ids = {"RULE-test-alpha", "RULE-prod-gamma"}
        assert set(candidates) == expected_ids

    finally:
        index.close()


def test_kuzu_index_query_no_matches(temp_db_path, sample_rules):
    """Test querying with tags that don't match any rules."""
    index = KuzuIndex(temp_db_path)

    try:
        # Upsert all sample rules
        for rule in sample_rules:
            index.upsert_card(rule)

        # Query by non-existent tag
        request = PackRequest(path=".", intent_tags=["nonexistent"])
        candidates = index.candidate_ids(request)

        # Should return empty list
        assert candidates == []

    finally:
        index.close()


def test_kuzu_index_query_no_filters(temp_db_path, sample_rules):
    """Test querying without any filters returns all rules."""
    index = KuzuIndex(temp_db_path)

    try:
        # Upsert all sample rules
        for rule in sample_rules:
            index.upsert_card(rule)

        # Query without filters
        request = PackRequest(path=".")
        candidates = index.candidate_ids(request)

        # Should return all rule IDs
        expected_ids = {"RULE-test-alpha", "RULE-test-beta", "RULE-prod-gamma"}
        assert set(candidates) == expected_ids

    finally:
        index.close()


def test_kuzu_index_delete_card(temp_db_path, sample_rules):
    """Test deleting a rule card."""
    index = KuzuIndex(temp_db_path)

    try:
        # Upsert rules
        for rule in sample_rules:
            index.upsert_card(rule)

        # Delete one rule
        index.delete_card("RULE-test-alpha")

        # Query should not return deleted rule
        request = PackRequest(path=".", intent_tags=["testing"])
        candidates = index.candidate_ids(request)

        # Should only return beta rule
        assert candidates == ["RULE-test-beta"]

    finally:
        index.close()


def test_kuzu_index_upsert_overwrites(temp_db_path):
    """Test that upserting the same rule ID overwrites existing data."""
    index = KuzuIndex(temp_db_path)

    try:
        # Create initial rule
        rule1 = RuleCard(
            schema_version=1,
            id="RULE-test-update",
            name="Original Rule",
            version=1,
            status=Status.ACTIVE,
            severity=Severity.INFO,
            domain="test",
            intent_tags=["original"],
            action=Action(type=ActionType.MANUAL, steps=["Original step"]),
            provenance=Provenance(
                author="Test",
                created="2024-01-01T00:00:00Z",
                last_updated="2024-01-01T00:00:00Z",
            ),
        )

        # Upsert initial rule
        index.upsert_card(rule1)

        # Query by original tag
        request = PackRequest(path=".", intent_tags=["original"])
        candidates = index.candidate_ids(request)
        assert candidates == ["RULE-test-update"]

        # Create updated rule with same ID but different tags
        rule2 = RuleCard(
            schema_version=1,
            id="RULE-test-update",
            name="Updated Rule",
            version=2,
            status=Status.ACTIVE,
            severity=Severity.WARNING,
            domain="test",
            intent_tags=["updated"],
            action=Action(type=ActionType.MANUAL, steps=["Updated step"]),
            provenance=Provenance(
                author="Test",
                created="2024-01-01T00:00:00Z",
                last_updated="2024-01-02T00:00:00Z",
            ),
        )

        # Upsert updated rule
        index.upsert_card(rule2)

        # Query by original tag should return nothing
        request = PackRequest(path=".", intent_tags=["original"])
        candidates = index.candidate_ids(request)
        assert candidates == []

        # Query by updated tag should return the rule
        request = PackRequest(path=".", intent_tags=["updated"])
        candidates = index.candidate_ids(request)
        assert candidates == ["RULE-test-update"]

    finally:
        index.close()


def test_kuzu_index_error_handling(temp_db_path):
    """Test that KuzuIndex handles errors gracefully."""
    index = KuzuIndex(temp_db_path)

    try:
        # Test querying with invalid request (should not crash)
        request = PackRequest(path=".", intent_tags=["test"])
        candidates = index.candidate_ids(request)

        # Should return empty list when no data exists
        assert candidates == []

        # Test deleting non-existent rule (should not crash)
        index.delete_card("RULE-nonexistent")

    finally:
        index.close()
