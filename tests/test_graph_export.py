"""Tests for Graphiti export functionality."""

import json
import tempfile
from pathlib import Path

import pytest
from hermezos.index.graphiti import GraphitiIndex
from hermezos.models import (
    Action,
    ActionType,
    PackRequest,
    Provenance,
    Reference,
    RuleCard,
    Severity,
    Status,
)


@pytest.fixture
def sample_rule():
    """Create a sample rule card for testing."""
    return RuleCard(
        schema_version=1,
        id="RULE-test-sample",
        name="Sample Test Rule",
        version=1,
        status=Status.ACTIVE,
        severity=Severity.WARNING,
        domain="test",
        intent_tags=["testing", "example"],
        action=Action(type=ActionType.MANUAL, steps=["Test step"]),
        references=[Reference(doc_url="./docs/test.md", note="Test documentation")],
        provenance=Provenance(
            author="Test Author",
            created="2024-01-01T00:00:00Z",
            last_updated="2024-01-01T00:00:00Z",
        ),
    )


def test_graphiti_export_creates_files(sample_rule):
    """Test that Graphiti export creates nodes.jsonl and edges.jsonl files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        export_path = Path(temp_dir) / "graph"

        # Create index in export_only mode
        index = GraphitiIndex(mode="export_only", export_path=export_path)

        # Upsert a rule
        index.upsert_card(sample_rule)

        # Close to trigger export
        index.close()

        # Check that files were created
        nodes_file = export_path / "nodes.jsonl"
        edges_file = export_path / "edges.jsonl"

        assert nodes_file.exists()
        assert edges_file.exists()


def test_graphiti_export_stable_output(sample_rule):
    """Test that Graphiti export produces stable, sorted output across runs."""
    with tempfile.TemporaryDirectory() as temp_dir:
        export_path = Path(temp_dir) / "graph"

        # First export
        index1 = GraphitiIndex(mode="export_only", export_path=export_path)
        index1.upsert_card(sample_rule)
        index1.close()

        # Read first export
        nodes_file = export_path / "nodes.jsonl"
        edges_file = export_path / "edges.jsonl"

        with open(nodes_file) as f:
            nodes1 = f.read()
        with open(edges_file) as f:
            edges1 = f.read()

        # Second export (clean directory)
        nodes_file.unlink()
        edges_file.unlink()

        index2 = GraphitiIndex(mode="export_only", export_path=export_path)
        index2.upsert_card(sample_rule)
        index2.close()

        # Read second export
        with open(nodes_file) as f:
            nodes2 = f.read()
        with open(edges_file) as f:
            edges2 = f.read()

        # Should be identical
        assert nodes1 == nodes2
        assert edges1 == edges2


def test_graphiti_export_content_structure(sample_rule):
    """Test that exported JSONL has correct structure and content."""
    with tempfile.TemporaryDirectory() as temp_dir:
        export_path = Path(temp_dir) / "graph"

        index = GraphitiIndex(mode="export_only", export_path=export_path)
        index.upsert_card(sample_rule)
        index.close()

        # Read and parse nodes
        nodes_file = export_path / "nodes.jsonl"
        nodes = []
        with open(nodes_file) as f:
            for line in f:
                nodes.append(json.loads(line.strip()))

        # Should have rule, domain, intent tags, and doc nodes
        node_types = {node["type"] for node in nodes}
        expected_types = {"RuleCard", "Domain", "IntentTag", "Doc"}
        assert expected_types.issubset(node_types)

        # Check rule card node
        rule_nodes = [n for n in nodes if n["type"] == "RuleCard"]
        assert len(rule_nodes) == 1
        rule_node = rule_nodes[0]
        assert rule_node["id"] == "RULE-test-sample"
        assert rule_node["domain"] == "test"
        assert rule_node["status"] == "active"
        assert rule_node["severity"] == "warning"

        # Read and parse edges
        edges_file = export_path / "edges.jsonl"
        edges = []
        with open(edges_file) as f:
            for line in f:
                edges.append(json.loads(line.strip()))

        # Should have edges for domain, tags, and docs
        edge_types = {edge["type"] for edge in edges}
        expected_edge_types = {"OF_DOMAIN", "HAS_TAG", "DOC"}
        assert expected_edge_types.issubset(edge_types)

        # Check that all edges originate from the rule
        rule_edges = [e for e in edges if e["source"] == "RULE-test-sample"]
        assert len(rule_edges) >= 4  # domain + 2 tags + doc


def test_graphiti_export_sorted_output(sample_rule):
    """Test that exported JSONL is sorted by ID for deterministic output."""
    with tempfile.TemporaryDirectory() as temp_dir:
        export_path = Path(temp_dir) / "graph"

        # Create multiple rules to test sorting
        rule2 = RuleCard(
            schema_version=1,
            id="RULE-alpha-first",
            name="Alpha Rule",
            version=1,
            status=Status.ACTIVE,
            severity=Severity.INFO,
            domain="alpha",
            intent_tags=["alpha"],
            action=Action(type=ActionType.MANUAL, steps=["Alpha step"]),
            provenance=Provenance(
                author="Test",
                created="2024-01-01T00:00:00Z",
                last_updated="2024-01-01T00:00:00Z",
            ),
        )

        index = GraphitiIndex(mode="export_only", export_path=export_path)

        # Add rules in reverse alphabetical order
        index.upsert_card(sample_rule)  # RULE-test-sample
        index.upsert_card(rule2)  # RULE-alpha-first

        index.close()

        # Read nodes and check sorting
        nodes_file = export_path / "nodes.jsonl"
        with open(nodes_file) as f:
            lines = f.readlines()

        # Parse first few nodes to check sorting
        nodes = [json.loads(line.strip()) for line in lines[:5]]
        node_ids = [node["id"] for node in nodes]

        # Should be sorted alphabetically
        assert node_ids == sorted(node_ids)


def test_graphiti_export_candidate_ids_returns_empty():
    """Test that Graphiti export mode returns empty candidate list."""
    with tempfile.TemporaryDirectory() as temp_dir:
        export_path = Path(temp_dir) / "graph"

        index = GraphitiIndex(mode="export_only", export_path=export_path)
        request = PackRequest(path=".", intent_tags=["testing"])

        result = index.candidate_ids(request)

        assert result == []

        index.close()
