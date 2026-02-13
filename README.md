# notebook-test

Run Jupyter notebooks as CI tests.

## Install

```bash
git clone https://github.com/openkickstartai/notebook-test.git
cd notebook-test && pip install -e .
```

## Usage

```bash
# Test all notebooks in a directory
notebook-test run notebooks/

# Test with timeout per cell
notebook-test run notebooks/ --timeout 60

# Run notebooks in parallel (4 workers)
notebook-test run notebooks/ -j 4

# Compare outputs (regression testing)
notebook-test diff notebook.ipynb --baseline expected/

# Strip outputs before git commit
notebook-test strip notebooks/
```

## pytest integration

```python
# conftest.py
from notebook_test.pytest_plugin import collect_notebooks

def pytest_collect_file(parent, file_path):
    return collect_notebooks(parent, file_path)
```

## Testing

```bash
pytest -v
```
