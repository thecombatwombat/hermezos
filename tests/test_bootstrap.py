"""Tests for bootstrap functionality and dependency handling."""

from unittest.mock import patch

import pytest


def test_graphiti_lazy_import_error():
    """Test that GraphitiIndex raises helpful error when requests is missing."""
    from src.hermezos.index.graphiti import _get_requests

    # Mock requests import to fail
    with patch.dict("sys.modules", {"requests": None}):
        with patch(
            "builtins.__import__", side_effect=ImportError("No module named 'requests'")
        ):
            with pytest.raises(ImportError) as exc_info:
                _get_requests()

            assert "requests" in str(exc_info.value)
            assert "hermezos[indexing]" in str(exc_info.value)
            assert "hermez bootstrap" in str(exc_info.value)


def test_kuzu_lazy_import_error():
    """Test that KuzuIndex raises helpful error when kuzu is missing."""
    from src.hermezos.index.kuzu_index import _get_kuzu

    # Mock kuzu import to fail
    with patch.dict("sys.modules", {"kuzu": None}):
        with patch(
            "builtins.__import__", side_effect=ImportError("No module named 'kuzu'")
        ):
            with pytest.raises(ImportError) as exc_info:
                _get_kuzu()

            assert "kuzu" in str(exc_info.value)
            assert "hermezos[indexing]" in str(exc_info.value)
            assert "hermez bootstrap" in str(exc_info.value)


def test_index_factory_disabled_indexing():
    """Test that make_index returns NullIndex when indexing is disabled."""
    import tempfile
    from pathlib import Path

    from src.hermezos.config import Config
    from src.hermezos.index import make_index
    from src.hermezos.index.null_index import NullIndex

    # Create a temporary config file with indexing disabled
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(
            """
[graph]
enabled = false
driver = "null"
"""
        )
        config_path = Path(f.name)

    try:
        config = Config(config_path)
        index = make_index(config)

        # Should return NullIndex when disabled
        assert isinstance(index, NullIndex)

    finally:
        config_path.unlink(missing_ok=True)


def test_bootstrap_command_help():
    """Test that bootstrap command shows help when no feature is specified."""
    import typer
    from typer.testing import CliRunner

    from src.hermezos.cli import bootstrap

    app = typer.Typer()
    app.command()(bootstrap)

    runner = CliRunner()
    result = runner.invoke(app, [])

    assert result.exit_code == 0
    assert "Available features to bootstrap:" in result.stdout
    assert "indexing" in result.stdout
    assert "mcp" in result.stdout
    assert "all" in result.stdout


def test_bootstrap_unknown_feature():
    """Test that bootstrap command rejects unknown features."""
    import typer
    from typer.testing import CliRunner

    from src.hermezos.cli import bootstrap

    app = typer.Typer()
    app.command()(bootstrap)

    runner = CliRunner()
    result = runner.invoke(app, ["unknown_feature"])

    assert result.exit_code != 0
    assert "Unknown feature" in result.stdout
