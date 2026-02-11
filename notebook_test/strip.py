"""Strip outputs from notebooks."""
import nbformat

def strip_outputs(path: str):
    """Remove all cell outputs and execution counts."""
    nb = nbformat.read(path, as_version=4)
    for cell in nb.cells:
        if cell.cell_type == 'code':
            cell.outputs = []
            cell.execution_count = None
    nbformat.write(nb, path)
