"""Tests for NullIndex implementation."""

import pytest

from hermezos.index.null_index import NullIndex
from hermezos.models import PackRequest, RuleCard, Status, Severity, Action, ActionType, Provenance


def test_null_index_candidate_ids():
    """Test that NullIndex returns empty list for candidate_ids."""
    index = NullIndex()
    request = PackRequest(path=".", intent_tags=["test"])
    
    result = index.candidate_ids(request)
    
    assert result == []


def test_null_index_upsert_card():
    """Test that NullIndex upsert_card is a no-op."""
    index = NullIndex()
    card = RuleCard(
        schema_version=1,
        id="RULE-test-example",
        name="Test Rule",
        version=1,
        status=Status.ACTIVE,
        severity=Severity.INFO,
        domain="test",
        action=Action(type=ActionType.MANUAL, steps=["Test step"]),
        provenance=Provenance(
            author="Test",
            created="2024-01-01T00:00:00Z",
            last_updated="2024-01-01T00:00:00Z"
        )
    )
    
    # Should not raise any exceptions
    index.upsert_card(card)


def test_null_index_delete_card():
    """Test that NullIndex delete_card is a no-op."""
    index = NullIndex()
    
    # Should not raise any exceptions
    index.delete_card("RULE-test-example")


def test_null_index_close():
    """Test that NullIndex close is a no-op."""
    index = NullIndex()
    
    # Should not raise any exceptions
    index.close()


def test_null_index_stability():
    """Test that NullIndex behavior is stable across multiple calls."""
    index = NullIndex()
    request = PackRequest(path=".", intent_tags=["test"])
    
    # Multiple calls should return the same result
    result1 = index.candidate_ids(request)
    result2 = index.candidate_ids(request)
    
    assert result1 == result2 == []