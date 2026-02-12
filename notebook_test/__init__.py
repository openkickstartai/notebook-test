"""Notebook testing framework for validating Jupyter notebook execution."""

__version__ = "0.1.0"

import nbformat
from nbconvert.preprocessors import ExecutePreprocessor
from typing import Dict, List, Optional, Any
import logging
import os
from pathlib import Path

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
            if not os.path.exists(notebook_path):
                raise FileNotFoundError(f"Notebook not found: {notebook_path}")
                
            with open(notebook_path, 'r', encoding='utf-8') as f:
                nb = nbformat.read(f, as_version=4)
            
            # Execute the notebook
            self.executor.preprocess(nb, {'metadata': {'path': str(Path(notebook_path).parent)}})
            
            return {
                'status': 'success',
                'cells_executed': len([cell for cell in nb.cells if cell.cell_type == 'code']),
                'errors': [],
                'notebook': nb,
                'path': notebook_path
            }
            
        except Exception as e:
            logger.error(f"Failed to execute notebook {notebook_path}: {e}")
            return {
                'status': 'error',
                'cells_executed': 0,
                'errors': [str(e)],
                'notebook': None,
                'path': notebook_path
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
                if cell.cell_type != 'code':
                    continue
                    
                cell_result = {
                    'cell_index': i,
                    'cell_type': cell.cell_type,
                    'source': cell.source,
                    'status': 'pending',
                    'outputs': [],
                    'errors': []
                }
                
                try:
                    # Create a temporary notebook with just this cell
                    temp_nb = nbformat.v4.new_notebook()
                    temp_nb.cells = [cell]
                    
                    # Execute the single cell
                    self.executor.preprocess(temp_nb, {'metadata': {'path': str(Path(notebook_path).parent)}})
                    
                    cell_result['status'] = 'success'
                    cell_result['outputs'] = temp_nb.cells[0].get('outputs', [])
                    
                except Exception as e:
                    cell_result['status'] = 'error'
                    cell_result['errors'].append(str(e))
                    logger.warning(f"Cell {i} failed in {notebook_path}: {e}")
                
                results.append(cell_result)
                
        except Exception as e:
            logger.error(f"Failed to validate cells in {notebook_path}: {e}")
            results.append({
                'cell_index': -1,
                'status': 'error',
                'errors': [f"Failed to read notebook: {e}"]
            })
        
        return results
    
    def run_tests(self, notebook_paths: List[str]) -> Dict[str, Any]:
        """Run tests on multiple notebooks.
        
        Args:
            notebook_paths: List of paths to notebook files
            
        Returns:
            Summary of all test results
        """
        results = {
            'total_notebooks': len(notebook_paths),
            'passed': 0,
            'failed': 0,
            'details': []
        }
        
        for notebook_path in notebook_paths:
            result = self.execute_notebook(notebook_path)
            results['details'].append(result)
            
            if result['status'] == 'success':
                results['passed'] += 1
            else:
                results['failed'] += 1
        
        results['success_rate'] = results['passed'] / results['total_notebooks'] if results['total_notebooks'] > 0 else 0
        
        return results

def test_notebook(notebook_path: str, timeout: int = 600, kernel_name: str = "python3") -> Dict[str, Any]:
    """Convenience function to test a single notebook.
    
    Args:
        notebook_path: Path to the notebook file
        timeout: Maximum time in seconds to wait for each cell
        kernel_name: Kernel to use for execution
        
    Returns:
        Dictionary containing execution results
    """
    tester = NotebookTester(timeout=timeout, kernel_name=kernel_name)
    return tester.execute_notebook(notebook_path)

def discover_notebooks(directory: str, pattern: str = "*.ipynb") -> List[str]:
    """Discover notebook files in a directory.
    
    Args:
        directory: Directory to search in
        pattern: File pattern to match
        
    Returns:
        List of notebook file paths
    """
    path = Path(directory)
    return [str(p) for p in path.rglob(pattern) if p.is_file()]

__all__ = ['NotebookTester', 'test_notebook', 'discover_notebooks']