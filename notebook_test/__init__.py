"""Notebook testing framework for validating Jupyter notebook execution."""

__version__ = "0.1.0"

import nbformat
from nbconvert.preprocessors import ExecutePreprocessor
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class NotebookTester:
    """Main class for testing Jupyter notebooks."""
    
    def __init__(self, timeout: int = 600, kernel_name: str = "python3"):
        """Initialize notebook tester.
        
        Args:
            timeout: Maximum time in seconds to wait for each cell
            kernel_name: Kernel to use for execution
        """
        self.timeout = timeout
        self.kernel_name = kernel_name
        self.executor = ExecutePreprocessor(
            timeout=timeout,
            kernel_name=kernel_name
        )
    
    def execute_notebook(self, notebook_path: str) -> Dict[str, Any]:
        """Execute a notebook and return results.
        
        Args:
            notebook_path: Path to the notebook file
            
        Returns:
            Dictionary containing execution results and metadata
        """
        try:
            with open(notebook_path, 'r', encoding='utf-8') as f:
                nb = nbformat.read(f, as_version=4)
            
            # Execute the notebook
            self.executor.preprocess(nb, {'metadata': {'path': '.'}})
            
            return {
                'status': 'success',
                'cells_executed': len(nb.cells),
                'errors': [],
                'notebook': nb
            }
            
        except Exception as e:
            logger.error(f"Failed to execute notebook {notebook_path}: {e}")
            return {
                'status': 'error',
                'cells_executed': 0,
                'errors': [str(e)],
                'notebook': None
            }
    
    def validate_cells(self, notebook_path: str) -> List[Dict[str, Any]]:
        """Validate individual cells in a notebook.
        
        Args:
            notebook_path: Path to the notebook file
            
        Returns:
            List of validation results for each cell
        """
        results = []
        
        try:
            with open(notebook_path, 'r', encoding='utf-8') as f:
                nb = nbformat.read(f, as_version=4)
            
            for i, cell in enumerate(nb.cells):
                if cell.cell_type == 'code':
                    try:
                        # Basic syntax validation
                        compile(cell.source, f'<cell_{i}>', 'exec')
                        results.append({
                            'cell_index': i,
                            'status': 'valid',
                            'error': None
                        })
                    except SyntaxError as e:
                        results.append({
                            'cell_index': i,
                            'status': 'invalid',
                            'error': str(e)
                        })
                        
        except Exception as e:
            logger.error(f"Failed to validate cells in {notebook_path}: {e}")
            
        return results

def test_notebook(notebook_path: str, **kwargs) -> Dict[str, Any]:
    """Convenience function to test a notebook.
    
    Args:
        notebook_path: Path to the notebook file
        **kwargs: Additional arguments for NotebookTester
        
    Returns:
        Execution results
    """
    tester = NotebookTester(**kwargs)
    return tester.execute_notebook(notebook_path)

__all__ = ['NotebookTester', 'test_notebook']