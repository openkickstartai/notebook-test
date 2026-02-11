"""Tests for strip."""
import json, os, tempfile
from notebook_test.strip import strip_outputs

def _mk_notebook(cells):
    nb = {'nbformat': 4, 'nbformat_minor': 5, 'metadata': {'kernelspec': {'name': 'python3'}}, 'cells': cells}
    f = tempfile.NamedTemporaryFile(suffix='.ipynb', mode='w', delete=False)
    json.dump(nb, f)
    f.flush()
    return f.name

def test_strip_removes_outputs():
    nb = _mk_notebook([{'cell_type': 'code', 'source': 'print(1)', 'metadata': {},
        'outputs': [{'output_type': 'stream', 'text': '1\n'}], 'execution_count': 1}])
    strip_outputs(nb)
    with open(nb) as f:
        data = json.load(f)
    assert data['cells'][0]['outputs'] == []
    assert data['cells'][0]['execution_count'] is None
    os.unlink(nb)

def test_strip_preserves_markdown():
    nb = _mk_notebook([{'cell_type': 'markdown', 'source': '# Title', 'metadata': {}}])
    strip_outputs(nb)
    with open(nb) as f:
        data = json.load(f)
    assert data['cells'][0]['source'] == '# Title'
    os.unlink(nb)
