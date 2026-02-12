"""Notebook testing framework for validating Jupyter notebook execution."""

__version__ = "0.1.0"

import nbformat
from nbconvert.preprocessors import ExecutePreprocessor
from typing import Dict, List, Optional, Any, Tuple
import logging
import os
import sys
import traceback
from pathlib import Path
from datetime import datetime
import json
import re

logger = logging.getLogger(__name__)

class NotebookExecutionError(Exception):
    """Custom exception for notebook execution failures."""
    pass

class NotebookTester:
    """Main class for testing Jupyter notebooks with comprehensive validation."""
    
    def __init__(self, timeout: int = 600, kernel_name: str = "python3", 
                 allow_errors: bool = False, capture_output: bool = True):
        """Initialize notebook tester with security and validation options.
        
        Args:
            timeout: Maximum time in seconds to wait for each cell
            kernel_name: Kernel to use for execution
            allow_errors: Whether to continue execution after cell errors
            capture_output: Whether to capture and validate cell outputs
        """
        self.timeout = timeout
        self.kernel_name = kernel_name
        self.allow_errors = allow_errors
        self.capture_output = capture_output
        
        # Configure executor with security settings
        self.executor = ExecutePreprocessor(
            timeout=timeout,
            kernel_name=kernel_name,
            allow_errors=allow_errors,
            store_widget_state=False,  # Security: disable widget state
            record_timing=True
        )
    
    def validate_notebook_structure(self, nb: nbformat.NotebookNode) -> List[str]:
        """Validate notebook structure and return any issues found.
        
        Args:
            nb: Notebook object to validate
            
        Returns:
            List of validation warnings/errors
        """
        issues = []
        
        if not nb.cells:
            issues.append("Notebook contains no cells")
            return issues
            
        # Check for dangerous imports or commands
        dangerous_patterns = [
            r'import\s+os\s*;.*system',
            r'subprocess\.',
            r'eval\s*\(',
            r'exec\s*\(',
            r'__import__\s*\(',
            r'open\s*\([^)]*["\']w["\']'
        ]
        
        for i, cell in enumerate(nb.cells):
            if cell.cell_type == 'code':
                source = cell.get('source', '')
                for pattern in dangerous_patterns:
                    if re.search(pattern, source, re.IGNORECASE):
                        issues.append(f"Cell {i}: Potentially dangerous code detected")
                        
                # Check for empty code cells
                if not source.strip():
                    issues.append(f"Cell {i}: Empty code cell")
                    
        return issues
    
    def execute_notebook(self, notebook_path: str) -> Tuple[bool, Dict[str, Any]]:
        """Execute a notebook and return success status with detailed results.
        
        Args:
            notebook_path: Path to the notebook file
            
        Returns:
            Tuple of (success, results_dict)
        """
        results = {
            'path': notebook_path,
            'start_time': datetime.now().isoformat(),
            'success': False,
            'errors': [],
            'warnings': [],
            'execution_time': 0,
            'cells_executed': 0,
            'cells_failed': 0
        }
        
        try:
            # Load notebook
            with open(notebook_path, 'r', encoding='utf-8') as f:
                nb = nbformat.read(f, as_version=4)
            
            # Validate structure
            validation_issues = self.validate_notebook_structure(nb)
            if validation_issues:
                results['warnings'].extend(validation_issues)
                
            # Execute notebook
            start_time = datetime.now()
            
            try:
                nb_executed, resources = self.executor.preprocess(nb, {'metadata': {'path': os.path.dirname(notebook_path)}})
                results['success'] = True
                results['cells_executed'] = len([cell for cell in nb_executed.cells if cell.cell_type == 'code'])
                
            except Exception as e:
                results['errors'].append(f"Execution failed: {str(e)}")
                results['cells_failed'] = 1
                
                # Try to get more details about which cell failed
                if hasattr(e, 'cell_index'):
                    results['errors'].append(f"Failed at cell {e.cell_index}")
                    
            execution_time = (datetime.now() - start_time).total_seconds()
            results['execution_time'] = execution_time
            results['end_time'] = datetime.now().isoformat()
            
        except FileNotFoundError:
            results['errors'].append(f"Notebook file not found: {notebook_path}")
        except nbformat.ValidationError as e:
            results['errors'].append(f"Invalid notebook format: {str(e)}")
        except Exception as e:
            results['errors'].append(f"Unexpected error: {str(e)}")
            logger.exception(f"Error executing notebook {notebook_path}")
            
        return results['success'], results
    
    def test_notebooks(self, notebook_paths: List[str]) -> Dict[str, Any]:
        """Test multiple notebooks and return comprehensive results.
        
        Args:
            notebook_paths: List of paths to notebook files
            
        Returns:
            Dictionary with test results for all notebooks
        """
        overall_results = {
            'total_notebooks': len(notebook_paths),
            'successful': 0,
            'failed': 0,
            'results': [],
            'start_time': datetime.now().isoformat()
        }
        
        for notebook_path in notebook_paths:
            logger.info(f"Testing notebook: {notebook_path}")
            success, results = self.execute_notebook(notebook_path)
            
            overall_results['results'].append(results)
            
            if success:
                overall_results['successful'] += 1
                logger.info(f"✓ {notebook_path} passed")
            else:
                overall_results['failed'] += 1
                logger.error(f"✗ {notebook_path} failed")
                for error in results['errors']:
                    logger.error(f"  Error: {error}")
                    
        overall_results['end_time'] = datetime.now().isoformat()
        overall_results['success_rate'] = overall_results['successful'] / overall_results['total_notebooks'] if overall_results['total_notebooks'] > 0 else 0
        
        return overall_results

def run_notebook_tests(notebook_paths: List[str], **kwargs) -> bool:
    """Convenience function to run notebook tests.
    
    Args:
        notebook_paths: List of notebook file paths
        **kwargs: Additional arguments for NotebookTester
        
    Returns:
        True if all notebooks pass, False otherwise
    """
    tester = NotebookTester(**kwargs)
    results = tester.test_notebooks(notebook_paths)
    
    # Print summary
    print(f"\nNotebook Test Results:")
    print(f"Total: {results['total_notebooks']}")
    print(f"Passed: {results['successful']}")
    print(f"Failed: {results['failed']}")
    print(f"Success Rate: {results['success_rate']:.1%}")
    
    return results['failed'] == 0

# Export main classes and functions
__all__ = ['NotebookTester', 'NotebookExecutionError', 'run_notebook_tests']