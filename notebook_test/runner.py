"""Notebook execution."""
import nbformat
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError

class NotebookError(Exception): pass

def run_notebook(path: str, timeout: int = 120, kernel: str = 'python3'):
    """Execute a notebook and raise on error."""
    nb = nbformat.read(path, as_version=4)
    client = NotebookClient(nb, timeout=timeout, kernel_name=kernel)
    try:
        client.execute()
    except CellExecutionError as e:
        raise NotebookError(f'Cell execution failed: {e}') from e
    except Exception as e:
        raise NotebookError(f'Execution error: {e}') from e
    return nb
