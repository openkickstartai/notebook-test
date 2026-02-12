"""notebook-test: Run notebooks as CI tests."""
__version__ = "0.1.0"

import nbformat
from nbconvert.preprocessors import ExecutePreprocessor
import os
from pathlib import Path

class NotebookTester:
    """Core class for testing Jupyter notebooks."""
    
    def __init__(self, timeout=600, kernel_name='python3'):
        self.timeout = timeout
        self.kernel_name = kernel_name
        self.executor = ExecutePreprocessor(
            timeout=self.timeout,
            kernel_name=self.kernel_name
        )
    
    def run_notebook(self, notebook_path):
        """Execute a notebook and return success status."""
        try:
            with open(notebook_path, 'r') as f:
                nb = nbformat.read(f, as_version=4)
            
            self.executor.preprocess(nb, {'metadata': {'path': os.path.dirname(notebook_path)}})
            return True, None
        except Exception as e:
            return False, str(e)
    
    def validate_notebook(self, notebook_path):
        """Validate notebook format and structure."""
        try:
            with open(notebook_path, 'r') as f:
                nbformat.read(f, as_version=4)
            return True, None
        except Exception as e:
            return False, f"Invalid notebook format: {e}"

def run_notebook(notebook_path, timeout=600):
    """Convenience function to run a single notebook."""
    tester = NotebookTester(timeout=timeout)
    return tester.run_notebook(notebook_path)

def discover_notebooks(directory='.'):
    """Discover all notebook files in a directory."""
    path = Path(directory)
    return list(path.rglob('*.ipynb'))
