"""pytest plugin for collecting and running Jupyter notebooks as test items."""
import pytest
from notebook_test.runner import run_notebook, NotebookError


class NotebookItem(pytest.Item):
    """A pytest test item that executes a single Jupyter notebook."""

    def __init__(self, name, parent, notebook_path, timeout=120):
        super().__init__(name, parent)
        self.notebook_path = str(notebook_path)
        self.timeout = timeout

    def runtest(self):
        run_notebook(self.notebook_path, timeout=self.timeout)

    def repr_failure(self, excinfo):
        if isinstance(excinfo.value, NotebookError):
            return f"Notebook execution failed: {excinfo.value}"
        return super().repr_failure(excinfo)

    def reportinfo(self):
        return self.notebook_path, 0, f"notebook: {self.name}"


class NotebookFile(pytest.File):
    """Collector that yields a NotebookItem for each .ipynb file."""

    def collect(self):
        timeout = int(self.config.getoption("--nb-timeout", default=120))
        yield NotebookItem.from_parent(
            self, name=self.path.name, notebook_path=self.path, timeout=timeout
        )


def collect_notebooks(parent, file_path):
    """Collect .ipynb files as pytest test items.

    Usage in conftest.py::

        from notebook_test.pytest_plugin import collect_notebooks

        def pytest_collect_file(parent, file_path):
            return collect_notebooks(parent, file_path)
    """
    if file_path.suffix == ".ipynb" and ".ipynb_checkpoints" not in str(file_path):
        return NotebookFile.from_parent(parent, path=file_path)
    return None
