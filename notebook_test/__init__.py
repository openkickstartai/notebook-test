"""notebook-test: Run notebooks as CI tests."""
__version__ = "0.1.0"

import nbformat
from nbconvert.preprocessors import ExecutePreprocessor
import os
import logging
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
import json
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NotebookTestResult:
    """Container for notebook test results."""
    
    def __init__(self, notebook_path: str, success: bool, error: Optional[str] = None, 
                 execution_time: Optional[float] = None, cell_count: int = 0):
        self.notebook_path = notebook_path
        self.success = success
        self.error = error
        self.execution_time = execution_time
        self.cell_count = cell_count
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return {
            'notebook_path': self.notebook_path,
            'success': self.success,
            'error': self.error,
            'execution_time': self.execution_time,
            'cell_count': self.cell_count,
            'timestamp': self.timestamp
        }

class NotebookTester:
    """Core class for testing Jupyter notebooks with comprehensive error handling."""
    
    def __init__(self, timeout: int = 600, kernel_name: str = 'python3', 
                 allow_errors: bool = False, store_widget_state: bool = True):
        self.timeout = timeout
        self.kernel_name = kernel_name
        self.allow_errors = allow_errors
        self.store_widget_state = store_widget_state
        
        # Configure executor with proper error handling
        self.executor = ExecutePreprocessor(
            timeout=self.timeout,
            kernel_name=self.kernel_name,
            allow_errors=self.allow_errors,
            store_widget_state=self.store_widget_state
        )
        
        logger.info(f"NotebookTester initialized with timeout={timeout}s, kernel={kernel_name}")
    
    def run_notebook(self, notebook_path: str) -> NotebookTestResult:
        """Execute a notebook and return comprehensive test result."""
        start_time = datetime.now()
        notebook_path = str(Path(notebook_path).resolve())
        
        try:
            # Validate file exists
            if not os.path.exists(notebook_path):
                error_msg = f"Notebook file not found: {notebook_path}"
                logger.error(error_msg)
                return NotebookTestResult(notebook_path, False, error_msg)
            
            # Read and validate notebook
            logger.info(f"Reading notebook: {notebook_path}")
            with open(notebook_path, 'r', encoding='utf-8') as f:
                nb = nbformat.read(f, as_version=4)
            
            cell_count = len(nb.cells)
            logger.info(f"Executing {cell_count} cells in notebook")
            
            # Execute notebook
            resources = {
                'metadata': {
                    'path': os.path.dirname(notebook_path)
                }
            }
            
            self.executor.preprocess(nb, resources)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Notebook executed successfully in {execution_time:.2f}s")
            
            return NotebookTestResult(
                notebook_path=notebook_path,
                success=True,
                execution_time=execution_time,
                cell_count=cell_count
            )
            
        except nbformat.ValidationError as e:
            error_msg = f"Invalid notebook format: {str(e)}"
            logger.error(error_msg)
            return NotebookTestResult(notebook_path, False, error_msg)
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            error_msg = f"Execution failed: {str(e)}"
            logger.error(f"Notebook execution failed after {execution_time:.2f}s: {error_msg}")
            return NotebookTestResult(
                notebook_path=notebook_path,
                success=False,
                error=error_msg,
                execution_time=execution_time
            )
    
    def validate_notebook(self, notebook_path: str) -> NotebookTestResult:
        """Validate notebook format and structure without execution."""
        notebook_path = str(Path(notebook_path).resolve())
        
        try:
            if not os.path.exists(notebook_path):
                error_msg = f"Notebook file not found: {notebook_path}"
                return NotebookTestResult(notebook_path, False, error_msg)
            
            with open(notebook_path, 'r', encoding='utf-8') as f:
                nb = nbformat.read(f, as_version=4)
            
            # Additional validation checks
            if not hasattr(nb, 'cells'):
                error_msg = "Notebook missing cells attribute"
                return NotebookTestResult(notebook_path, False, error_msg)
            
            cell_count = len(nb.cells)
            logger.info(f"Notebook validation passed: {cell_count} cells found")
            
            return NotebookTestResult(
                notebook_path=notebook_path,
                success=True,
                cell_count=cell_count
            )
            
        except nbformat.ValidationError as e:
            error_msg = f"Invalid notebook format: {str(e)}"
            logger.error(error_msg)
            return NotebookTestResult(notebook_path, False, error_msg)
            
        except Exception as e:
            error_msg = f"Validation error: {str(e)}"
            logger.error(error_msg)
            return NotebookTestResult(notebook_path, False, error_msg)
    
    def run_multiple_notebooks(self, notebook_paths: List[str]) -> List[NotebookTestResult]:
        """Run multiple notebooks and return results."""
        results = []
        for path in notebook_paths:
            logger.info(f"Processing notebook {len(results) + 1}/{len(notebook_paths)}: {path}")
            result = self.run_notebook(path)
            results.append(result)
        return results

def run_notebook(notebook_path: str, timeout: int = 600, **kwargs) -> NotebookTestResult:
    """Convenience function to run a single notebook with enhanced result."""
    tester = NotebookTester(timeout=timeout, **kwargs)
    return tester.run_notebook(notebook_path)

def discover_notebooks(directory: str = '.', exclude_checkpoints: bool = True) -> List[str]:
    """Discover all notebook files in a directory with filtering options."""
    path = Path(directory)
    if not path.exists():
        logger.warning(f"Directory does not exist: {directory}")
        return []
    
    notebooks = list(path.rglob('*.ipynb'))
    
    if exclude_checkpoints:
        notebooks = [nb for nb in notebooks if '.ipynb_checkpoints' not in str(nb)]
    
    notebook_paths = [str(nb) for nb in notebooks]
    logger.info(f"Discovered {len(notebook_paths)} notebooks in {directory}")
    
    return notebook_paths

def generate_test_report(results: List[NotebookTestResult], output_file: Optional[str] = None) -> Dict[str, Any]:
    """Generate a comprehensive test report from results."""
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r.success)
    failed_tests = total_tests - passed_tests
    
    report = {
        'summary': {
            'total_tests': total_tests,
            'passed': passed_tests,
            'failed': failed_tests,
            'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0
        },
        'results': [result.to_dict() for result in results],
        'generated_at': datetime.now().isoformat()
    }
    
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info(f"Test report saved to {output_file}")
    
    return report

# Export main classes and functions
__all__ = [
    'NotebookTester',
    'NotebookTestResult', 
    'run_notebook',
    'discover_notebooks',
    'generate_test_report'
]