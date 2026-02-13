"""Tests for notebook runner.

These tests require ipykernel to be installed so a Python kernel is available.
Run with: pytest tests/test_runner.py -v
"""
import json
import os
import tempfile

import pytest

from notebook_test.runner import run_notebook, NotebookError


def _mk_notebook(cells):
    """Create a temporary .ipynb file with the given cells."""
    nb = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "name": "python3",
                "display_name": "Python 3",
                "language": "python",
            },
            "language_info": {"name": "python"},
        },
        "cells": cells,
    }
    f = tempfile.NamedTemporaryFile(suffix=".ipynb", mode="w", delete=False)
    json.dump(nb, f)
    f.flush()
    f.close()
    return f.name


def _code_cell(source):
    return {
        "cell_type": "code",
        "source": source,
        "metadata": {},
        "outputs": [],
        "execution_count": None,
    }


@pytest.mark.skipif(
    os.environ.get("SKIP_KERNEL_TESTS") == "1",
    reason="Skipping kernel-dependent tests",
)
class TestRunner:
    def test_run_passing_notebook(self):
        nb = _mk_notebook([_code_cell("x = 1 + 1\nassert x == 2")])
        try:
            run_notebook(nb, timeout=30)
        finally:
            os.unlink(nb)

    def test_run_failing_notebook_raises(self):
        nb = _mk_notebook([_code_cell('raise ValueError("boom")')])
        try:
            with pytest.raises(NotebookError):
                run_notebook(nb, timeout=30)
        finally:
            os.unlink(nb)

    def test_run_multi_cell_notebook(self):
        cells = [
            _code_cell("a = 10"),
            _code_cell("b = a * 2"),
            _code_cell("assert b == 20"),
        ]
        nb = _mk_notebook(cells)
        try:
            run_notebook(nb, timeout=30)
        finally:
            os.unlink(nb)

    def test_run_empty_notebook(self):
        nb = _mk_notebook([])
        try:
            run_notebook(nb, timeout=30)
        finally:
            os.unlink(nb)
