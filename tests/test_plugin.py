"""Tests for pytest_plugin module — unit-level checks only."""
from pathlib import Path
from unittest.mock import MagicMock

from notebook_test.pytest_plugin import collect_notebooks


def test_collect_ignores_non_ipynb():
    result = collect_notebooks(MagicMock(), Path("test.py"))
    assert result is None


def test_collect_ignores_checkpoints():
    result = collect_notebooks(
        MagicMock(), Path("/project/.ipynb_checkpoints/Untitled.ipynb")
    )
    assert result is None
