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
import time
import sys
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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
    
    def validate_notebook_security(self, notebook_path: Path) -> bool:
        """Validate notebook for potential security issues before execution."""
        try:
            with open(notebook_path, 'r', encoding='utf-8') as f:
                nb = nbformat.read(f, as_version=4)
            
            # Check for potentially dangerous operations
            dangerous_patterns = [
                'os.system(',
                'subprocess.',
                'eval(',
                'exec(',
                '__import__',
                'open(',
                'file(',
                'input(',
                'raw_input('
            ]
            
            for cell in nb.cells:
                if cell.cell_type == 'code':
                    source = cell.source.lower()
                    for pattern in dangerous_patterns:
                        if pattern in source:
                            logger.warning(f"Potentially dangerous pattern '{pattern}' found in {notebook_path}")
                            return False
            
            return True
        except Exception as e:
            logger.error(f"Security validation failed for {notebook_path}: {e}")
            return False
    
    def execute_notebook(self, notebook_path: Path) -> NotebookTestResult:
        """Execute a single notebook and return test result."""
        start_time = time.time()
        
        try:
            # Security validation
            if not self.validate_notebook_security(notebook_path):
                return NotebookTestResult(
                    str(notebook_path), 
                    False, 
                    "Security validation failed - potentially dangerous operations detected"
                )
            
            # Read notebook
            with open(notebook_path, 'r', encoding='utf-8') as f:
                nb = nbformat.read(f, as_version=4)
            
            cell_count = len([cell for cell in nb.cells if cell.cell_type == 'code'])
            logger.info(f"Executing notebook {notebook_path} with {cell_count} code cells")
            
            # Execute notebook
            self.executor.preprocess(nb, {'metadata': {'path': str(notebook_path.parent)}})
            
            execution_time = time.time() - start_time
            logger.info(f"Successfully executed {notebook_path} in {execution_time:.2f}s")
            
            return NotebookTestResult(
                str(notebook_path), 
                True, 
                None, 
                execution_time, 
                cell_count
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(f"Failed to execute {notebook_path}: {error_msg}")
            logger.debug(f"Full traceback: {traceback.format_exc()}")
            
            return NotebookTestResult(
                str(notebook_path), 
                False, 
                error_msg, 
                execution_time
            )
    
    def test_notebooks(self, notebook_paths: List[Path]) -> List[NotebookTestResult]:
        """Test multiple notebooks and return results."""
        results = []
        
        for notebook_path in notebook_paths:
            if not notebook_path.exists():
                logger.error(f"Notebook not found: {notebook_path}")
                results.append(NotebookTestResult(
                    str(notebook_path), 
                    False, 
                    "File not found"
                ))
                continue
            
            result = self.execute_notebook(notebook_path)
            results.append(result)
        
        return results
    
    def discover_notebooks(self, directory: Path, pattern: str = "*.ipynb") -> List[Path]:
        """Discover notebook files in directory."""
        if not directory.exists():
            logger.error(f"Directory not found: {directory}")
            return []
        
        notebooks = list(directory.rglob(pattern))
        # Filter out checkpoint files
        notebooks = [nb for nb in notebooks if '.ipynb_checkpoints' not in str(nb)]
        
        logger.info(f"Discovered {len(notebooks)} notebooks in {directory}")
        return notebooks

def run_notebook_tests(directory: str = ".", pattern: str = "*.ipynb", 
                      timeout: int = 600, output_file: Optional[str] = None) -> bool:
    """Main function to run notebook tests."""
    directory_path = Path(directory)
    tester = NotebookTester(timeout=timeout)
    
    # Discover notebooks
    notebooks = tester.discover_notebooks(directory_path, pattern)
    
    if not notebooks:
        logger.warning("No notebooks found to test")
        return True
    
    # Execute tests
    results = tester.test_notebooks(notebooks)
    
    # Generate summary
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r.success)
    failed_tests = total_tests - passed_tests
    
    logger.info(f"Test Summary: {passed_tests}/{total_tests} passed, {failed_tests} failed")
    
    # Output results
    if output_file:
        output_path = Path(output_file)
        with open(output_path, 'w') as f:
            json.dump([r.to_dict() for r in results], f, indent=2)
        logger.info(f"Results written to {output_path}")
    
    # Print failed tests
    for result in results:
        if not result.success:
            logger.error(f"FAILED: {result.notebook_path} - {result.error}")
    
    return failed_tests == 0

# Export main components
__all__ = ['NotebookTester', 'NotebookTestResult', 'run_notebook_tests']