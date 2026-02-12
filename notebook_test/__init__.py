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
            r'open\s*\([^)]*["\'][rwa]'
        ]
        
        code_cells = [cell for cell in nb.cells if cell.cell_type == 'code']
        if not code_cells:
            issues.append("No code cells found in notebook")
            
        for i, cell in enumerate(code_cells):
            if not cell.source.strip():
                issues.append(f"Empty code cell at index {i}")
                continue
                
            # Security validation
            for pattern in dangerous_patterns:
                if re.search(pattern, cell.source, re.IGNORECASE):
                    issues.append(f"Potentially dangerous code in cell {i}: {pattern}")
                    
        return issues
    
    def execute_notebook(self, notebook_path: str, output_path: Optional[str] = None) -> Dict[str, Any]:
        """Execute a notebook and return execution results.
        
        Args:
            notebook_path: Path to the notebook file
            output_path: Optional path to save executed notebook
            
        Returns:
            Dictionary containing execution results and metadata
        """
        if not os.path.exists(notebook_path):
            raise NotebookExecutionError(f"Notebook file not found: {notebook_path}")
            
        try:
            # Load notebook
            with open(notebook_path, 'r', encoding='utf-8') as f:
                nb = nbformat.read(f, as_version=4)
                
            # Validate structure
            issues = self.validate_notebook_structure(nb)
            if issues and not self.allow_errors:
                raise NotebookExecutionError(f"Validation failed: {'; '.join(issues)}")
                
            # Execute notebook
            start_time = datetime.now()
            logger.info(f"Starting execution of {notebook_path}")
            
            try:
                nb_executed, resources = self.executor.preprocess(nb, {'metadata': {'path': os.path.dirname(notebook_path)}})
            except Exception as e:
                error_msg = f"Execution failed: {str(e)}"
                logger.error(error_msg)
                raise NotebookExecutionError(error_msg)
                
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            # Collect execution results
            results = {
                'success': True,
                'execution_time': execution_time,
                'cell_count': len(nb_executed.cells),
                'validation_issues': issues,
                'outputs': self._extract_outputs(nb_executed) if self.capture_output else [],
                'errors': self._extract_errors(nb_executed)
            }
            
            # Save executed notebook if requested
            if output_path:
                with open(output_path, 'w', encoding='utf-8') as f:
                    nbformat.write(nb_executed, f)
                results['output_saved'] = output_path
                
            logger.info(f"Successfully executed {notebook_path} in {execution_time:.2f}s")
            return results
            
        except Exception as e:
            logger.error(f"Failed to execute notebook {notebook_path}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    def _extract_outputs(self, nb: nbformat.NotebookNode) -> List[Dict[str, Any]]:
        """Extract outputs from executed notebook cells."""
        outputs = []
        for i, cell in enumerate(nb.cells):
            if cell.cell_type == 'code' and hasattr(cell, 'outputs'):
                cell_outputs = []
                for output in cell.outputs:
                    output_data = {
                        'output_type': output.output_type,
                        'execution_count': getattr(output, 'execution_count', None)
                    }
                    
                    if hasattr(output, 'text'):
                        output_data['text'] = output.text
                    if hasattr(output, 'data'):
                        output_data['data'] = output.data
                        
                    cell_outputs.append(output_data)
                    
                if cell_outputs:
                    outputs.append({
                        'cell_index': i,
                        'outputs': cell_outputs
                    })
        return outputs
    
    def _extract_errors(self, nb: nbformat.NotebookNode) -> List[Dict[str, Any]]:
        """Extract errors from executed notebook cells."""
        errors = []
        for i, cell in enumerate(nb.cells):
            if cell.cell_type == 'code' and hasattr(cell, 'outputs'):
                for output in cell.outputs:
                    if output.output_type == 'error':
                        errors.append({
                            'cell_index': i,
                            'ename': output.ename,
                            'evalue': output.evalue,
                            'traceback': output.traceback
                        })
        return errors
    
    def test_notebook(self, notebook_path: str, expected_outputs: Optional[Dict] = None) -> bool:
        """Test a notebook and validate against expected outputs.
        
        Args:
            notebook_path: Path to notebook file
            expected_outputs: Optional dictionary of expected outputs to validate
            
        Returns:
            True if test passes, False otherwise
        """
        try:
            results = self.execute_notebook(notebook_path)
            
            if not results['success']:
                logger.error(f"Notebook execution failed: {results.get('error', 'Unknown error')}")
                return False
                
            # Check for execution errors
            if results['errors'] and not self.allow_errors:
                logger.error(f"Notebook contains execution errors: {len(results['errors'])} errors found")
                return False
                
            # Validate expected outputs if provided
            if expected_outputs and self.capture_output:
                if not self._validate_expected_outputs(results['outputs'], expected_outputs):
                    logger.error("Output validation failed")
                    return False
                    
            logger.info(f"Notebook test passed: {notebook_path}")
            return True
            
        except Exception as e:
            logger.error(f"Test failed with exception: {str(e)}")
            return False
    
    def _validate_expected_outputs(self, actual_outputs: List[Dict], expected_outputs: Dict) -> bool:
        """Validate actual outputs against expected outputs."""
        # Simple validation - can be extended based on requirements
        for cell_index, expected in expected_outputs.items():
            cell_outputs = next((out for out in actual_outputs if out['cell_index'] == int(cell_index)), None)
            if not cell_outputs:
                logger.warning(f"No outputs found for cell {cell_index}")
                continue
                
            # Validate output types and basic content
            for expected_output in expected.get('outputs', []):
                found_match = False
                for actual_output in cell_outputs['outputs']:
                    if actual_output['output_type'] == expected_output.get('output_type'):
                        found_match = True
                        break
                        
                if not found_match:
                    logger.error(f"Expected output type {expected_output.get('output_type')} not found in cell {cell_index}")
                    return False
                    
        return True

def run_notebook_test(notebook_path: str, **kwargs) -> bool:
    """Convenience function to run a single notebook test.
    
    Args:
        notebook_path: Path to notebook file
        **kwargs: Additional arguments passed to NotebookTester
        
    Returns:
        True if test passes, False otherwise
    """
    tester = NotebookTester(**kwargs)
    return tester.test_notebook(notebook_path)

def run_notebook_tests(notebook_paths: List[str], **kwargs) -> Dict[str, bool]:
    """Run tests on multiple notebooks.
    
    Args:
        notebook_paths: List of notebook file paths
        **kwargs: Additional arguments passed to NotebookTester
        
    Returns:
        Dictionary mapping notebook paths to test results
    """
    tester = NotebookTester(**kwargs)
    results = {}
    
    for notebook_path in notebook_paths:
        try:
            results[notebook_path] = tester.test_notebook(notebook_path)
        except Exception as e:
            logger.error(f"Failed to test {notebook_path}: {str(e)}")
            results[notebook_path] = False
            
    return results