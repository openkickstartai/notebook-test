"""Tests for CLI helpers."""
import json, os, tempfile
from notebook_test.cli import _find_notebooks


def _make_nb_tree(tmp, rel_paths):
    paths = []
    for rel in rel_paths:
        full = os.path.join(tmp, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        nb = {'nbformat': 4, 'nbformat_minor': 5, 'metadata': {}, 'cells': []}
        with open(full, 'w') as f:
            json.dump(nb, f)
        paths.append(full)
    return paths


def test_find_skips_checkpoints():
    with tempfile.TemporaryDirectory() as tmp:
        _make_nb_tree(tmp, [
            'a.ipynb',
            'sub/b.ipynb',
            '.ipynb_checkpoints/a-checkpoint.ipynb',
        ])
        found = _find_notebooks(tmp)
        names = [os.path.basename(p) for p in found]
        assert 'a.ipynb' in names
        assert 'b.ipynb' in names
        assert 'a-checkpoint.ipynb' not in names


def test_find_single_file():
    with tempfile.TemporaryDirectory() as tmp:
        paths = _make_nb_tree(tmp, ['only.ipynb'])
        found = _find_notebooks(paths[0])
        assert len(found) == 1


def test_find_empty_dir():
    with tempfile.TemporaryDirectory() as tmp:
        assert _find_notebooks(tmp) == []
