"""CLI with performance optimizations and parallel execution."""
import click
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from notebook_test.runner import run_notebook, NotebookError
from notebook_test.strip import strip_outputs

@click.group()
def main(): pass

@main.command()
@click.argument('path')
@click.option('--timeout', default=120, type=int, help='Timeout per notebook in seconds')
@click.option('--parallel', '-p', default=4, type=int, help='Number of parallel workers')
@click.option('--benchmark', '-b', is_flag=True, help='Show timing benchmarks')
def run(path, timeout, parallel, benchmark):
    """Execute notebooks with parallel processing and performance metrics."""
    start_time = time.time()
    
    notebooks = _find_notebooks_optimized(path)
    if not notebooks:
        click.echo('No notebooks found')
        return
    
    if benchmark:
        click.echo(f'Found {len(notebooks)} notebooks in {time.time() - start_time:.3f}s')
    
    passed, failed = 0, 0
    exec_start = time.time()
    
    # Use parallel execution for better performance
    with ThreadPoolExecutor(max_workers=min(parallel, len(notebooks))) as executor:
        # Submit all notebook executions
        future_to_notebook = {
            executor.submit(_execute_notebook, nb_path, timeout): nb_path 
            for nb_path in notebooks
        }
        
        # Process results as they complete
        for future in as_completed(future_to_notebook):
            nb_path = future_to_notebook[future]
            try:
                success, error_msg, exec_time = future.result()
                if success:
                    status_msg = f'  PASS {nb_path}'
                    if benchmark:
                        status_msg += f' ({exec_time:.2f}s)'
                    click.echo(status_msg)
                    passed += 1
                else:
                    click.echo(f'  FAIL {nb_path}: {error_msg}')
                    failed += 1
            except Exception as e:
                click.echo(f'  FAIL {nb_path}: Execution error - {str(e)}')
                failed += 1
    
    total_time = time.time() - exec_start
    summary = f'\n{passed} passed, {failed} failed'
    if benchmark:
        summary += f' (total: {total_time:.2f}s, avg: {total_time/len(notebooks):.2f}s/notebook)'
    click.echo(summary)
    
    if failed: 
        raise SystemExit(1)

@main.command()
@click.argument('path')
@click.option('--parallel', '-p', default=4, type=int, help='Number of parallel workers')
def strip(path, parallel):
    """Strip outputs from notebooks with parallel processing."""
    notebooks = _find_notebooks_optimized(path)
    if not notebooks:
        click.echo('No notebooks found')
        return
    
    with ThreadPoolExecutor(max_workers=min(parallel, len(notebooks))) as executor:
        future_to_notebook = {
            executor.submit(_strip_notebook, nb_path): nb_path 
            for nb_path in notebooks
        }
        
        for future in as_completed(future_to_notebook):
            nb_path = future_to_notebook[future]
            try:
                future.result()
                click.echo(f'  Stripped {nb_path}')
            except Exception as e:
                click.echo(f'  ERROR stripping {nb_path}: {str(e)}')

def _execute_notebook(nb_path, timeout):
    """Execute a single notebook and return results with timing."""
    start_time = time.time()
    try:
        run_notebook(nb_path, timeout=timeout)
        exec_time = time.time() - start_time
        return True, None, exec_time
    except NotebookError as e:
        exec_time = time.time() - start_time
        return False, str(e), exec_time
    except Exception as e:
        exec_time = time.time() - start_time
        return False, f"Unexpected error: {str(e)}", exec_time

def _strip_notebook(nb_path):
    """Strip outputs from a single notebook."""
    strip_outputs(nb_path)
    return True

def _find_notebooks_optimized(path):
    """Optimized notebook discovery using pathlib for better performance."""
    path_obj = Path(path)
    
    if path_obj.is_file():
        return [str(path_obj)] if path_obj.suffix == '.ipynb' else []
    
    # Use pathlib's glob for faster directory traversal
    notebooks = []
    for nb_path in path_obj.rglob('*.ipynb'):
        # Skip checkpoint directories
        if '.ipynb_checkpoints' not in str(nb_path):
            notebooks.append(str(nb_path))
    
    return sorted(notebooks)

def _find_notebooks(path):
    """Legacy notebook finder for backward compatibility."""
    if os.path.isfile(path): 
        return [path]
    nbs = []
    for root, _, files in os.walk(path):
        for f in sorted(files):
            if f.endswith('.ipynb') and '.ipynb_checkpoints' not in root:
                nbs.append(os.path.join(root, f))
    return nbs