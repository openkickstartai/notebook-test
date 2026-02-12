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
            
        code_cells = [cell for cell in nb.cells if cell.cell_type == 'code']
        if not code_cells:
            issues.append("Notebook contains no code cells")
            
        # Check for potentially dangerous operations
        dangerous_patterns = ['os.system', 'subprocess.call', 'eval(', 'exec(']
        for i, cell in enumerate(code_cells):
            source = cell.get('source', '')
            for pattern in dangerous_patterns:
                if pattern in source:
                    issues.append(f"Cell {i+1} contains potentially unsafe operation: {pattern}")
                    
        return issues
    
    def extract_cell_errors(self, nb: nbformat.NotebookNode) -> List[Dict[str, Any]]:
        """Extract error information from executed notebook cells.
        
        Args:
            nb: Executed notebook object
            
        Returns:
            List of error dictionaries with cell index and error details
        """
        errors = []
        
        for i, cell in enumerate(nb.cells):
            if cell.cell_type == 'code' and hasattr(cell, 'outputs'):
                for output in cell.outputs:
                    if output.output_type == 'error':
                        errors.append({
                            'cell_index': i,
                            'error_name': output.ename,
                            'error_value': output.evalue,
                            'traceback': output.traceback,
                            'cell_source': cell.source[:200] + '...' if len(cell.source) > 200 else cell.source
                        })
                        
        return errors
    
    def analyze_outputs(self, nb: nbformat.NotebookNode) -> Dict[str, Any]:
        """Analyze notebook outputs for validation and reporting.
        
        Args:
            nb: Executed notebook object
            
        Returns:
            Dictionary containing output analysis results
        """
        output_stats = {
            'total_outputs': 0,
            'output_types': {},
            'cells_with_output': 0,
            'large_outputs': 0
        }
        
        for cell in nb.cells:
            if cell.cell_type == 'code' and hasattr(cell, 'outputs') and cell.outputs:
                output_stats['cells_with_output'] += 1
                
                for output in cell.outputs:
                    output_stats['total_outputs'] += 1
                    output_type = output.output_type
                    output_stats['output_types'][output_type] = output_stats['output_types'].get(output_type, 0) + 1
                    
                    # Check for large outputs (potential memory issues)
                    output_size = len(str(output))
                    if output_size > 100000:  # 100KB threshold
                        output_stats['large_outputs'] += 1
                        
        return output_stats
    
    def execute_notebook(self, notebook_path: str, working_dir: Optional[str] = None) -> Dict[str, Any]:
        """Execute a notebook and return comprehensive results with validation.
        
        Args:
            notebook_path: Path to the notebook file
            working_dir: Working directory for notebook execution
            
        Returns:
            Dictionary containing execution results, validation, and metadata
        """
        start_time = datetime.now()
        
        try:
            # Validate file existence and permissions
            if not os.path.exists(notebook_path):
                raise FileNotFoundError(f"Notebook not found: {notebook_path}")
                
            if not os.access(notebook_path, os.R_OK):
                raise PermissionError(f"Cannot read notebook: {notebook_path}")
            
            # Read and validate notebook
            with open(notebook_path, 'r', encoding='utf-8') as f:
                try:
                    nb = nbformat.read(f, as_version=4)
                except nbformat.ValidationError as e:
                    raise NotebookExecutionError(f"Invalid notebook format: {e}")
            
            # Pre-execution validation
            validation_issues = self.validate_notebook_structure(nb)
            if validation_issues and not self.allow_errors:
                logger.warning(f"Validation issues found: {validation_issues}")
            
            # Set working directory
            execution_path = working_dir or str(Path(notebook_path).parent)
            
            # Execute the notebook with error handling
            try:
                executed_nb, resources = self.executor.preprocess(
                    nb, 
                    {'metadata': {'path': execution_path}}
                )
            except Exception as exec_error:
                logger.error(f"Execution failed for {notebook_path}: {exec_error}")
                return {
                    'status': 'failed',
                    'error': str(exec_error),
                    'error_type': type(exec_error).__name__,
                    'traceback': traceback.format_exc(),
                    'path': notebook_path,
                    'execution_time': (datetime.now() - start_time).total_seconds(),
                    'validation_issues': validation_issues
                }
            
            # Analyze results
            cell_errors = self.extract_cell_errors(executed_nb)
            output_analysis = self.analyze_outputs(executed_nb) if self.capture_output else {}
            
            code_cells = [cell for cell in executed_nb.cells if cell.cell_type == 'code']
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Determine overall status
            status = 'success'
            if cell_errors:
                status = 'completed_with_errors' if self.allow_errors else 'failed'
            elif validation_issues:
                status = 'completed_with_warnings'
            
            return {
                'status': status,
                'cells_executed': len(code_cells),
                'total_cells': len(executed_nb.cells),
                'execution_time': execution_time,
                'errors': cell_errors,
                'validation_issues': validation_issues,
                'output_analysis': output_analysis,
                'notebook': executed_nb if self.capture_output else None,
                'path': notebook_path,
                'kernel_name': self.kernel_name,
                'timestamp': start_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Unexpected error executing notebook {notebook_path}: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'error_type': type(e).__name__,
                'traceback': traceback.format_exc(),
                'path': notebook_path,
                'execution_time': (datetime.now() - start_time).total_seconds()
            }
    
    def test_notebooks(self, notebook_paths: List[str], 
                      fail_fast: bool = False) -> Dict[str, Any]:
        """Test multiple notebooks and return aggregated results.
        
        Args:
            notebook_paths: List of notebook file paths to test
            fail_fast: Whether to stop on first failure
            
        Returns:
            Dictionary containing aggregated test results
        """
        results = []
        failed_count = 0
        
        for notebook_path in notebook_paths:
            logger.info(f"Testing notebook: {notebook_path}")
            result = self.execute_notebook(notebook_path)
            results.append(result)
            
            if result['status'] in ['failed', 'error']:
                failed_count += 1
                if fail_fast:
                    logger.error(f"Stopping due to failure in {notebook_path}")
                    break
        
        return {
            'total_notebooks': len(notebook_paths),
            'tested_notebooks': len(results),
            'passed': len([r for r in results if r['status'] == 'success']),
            'failed': failed_count,
            'results': results,
            'overall_status': 'passed' if failed_count == 0 else 'failed'
        }

# Convenience functions for common use cases
def test_notebook(notebook_path: str, **kwargs) -> Dict[str, Any]:
    """Test a single notebook with default settings."""
    tester = NotebookTester(**kwargs)
    return tester.execute_notebook(notebook_path)

def test_notebooks_in_directory(directory: str, pattern: str = "*.ipynb", **kwargs) -> Dict[str, Any]:
    """Test all notebooks matching pattern in directory."""
    notebook_paths = list(Path(directory).glob(pattern))
    notebook_paths = [str(p) for p in notebook_paths]
    
    tester = NotebookTester(**kwargs)
    return tester.test_notebooks(notebook_paths)

# Export main classes and functions
__all__ = ['NotebookTester', 'NotebookExecutionError', 'test_notebook', 'test_notebooks_in_directory']