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
    results = []
    
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
                results.append((nb_path, success, exec_time if benchmark else 0))
            except Exception as e:
                click.echo(f'  ERROR {nb_path}: {e}')
                failed += 1
    
    total_time = time.time() - start_time
    click.echo(f'\n{passed} passed, {failed} failed')
    
    if benchmark:
        avg_time = sum(r[2] for r in results if r[1]) / max(passed, 1)
        click.echo(f'Total time: {total_time:.2f}s, Average per notebook: {avg_time:.2f}s')
        click.echo(f'Speedup: {len(notebooks) * avg_time / total_time:.1f}x with {parallel} workers')
    
    if failed:
        raise SystemExit(1)

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
        return False, f'Unexpected error: {e}', exec_time

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
            executor.submit(_strip_notebook, nb): nb 
            for nb in notebooks
        }
        
        for future in as_completed(future_to_notebook):
            nb_path = future_to_notebook[future]
            try:
                future.result()
                click.echo(f'  Stripped {nb_path}')
            except Exception as e:
                click.echo(f'  ERROR stripping {nb_path}: {e}')

def _strip_notebook(nb_path):
    """Strip outputs from a single notebook."""
    strip_outputs(nb_path)

def _find_notebooks_optimized(path):
    """Highly optimized notebook discovery with early filtering and Path objects."""
    path_obj = Path(path)
    
    if path_obj.is_file():
        return [str(path_obj)] if path_obj.suffix == '.ipynb' else []
    
    if not path_obj.is_dir():
        return []
    
    notebooks = []
    skip_dirs = {'.git', '__pycache__', 'node_modules', '.pytest_cache', '.tox', 'venv', '.venv'}
    
    try:
        # Use pathlib for better performance and cross-platform compatibility
        for notebook_path in path_obj.rglob('*.ipynb'):
            # Skip if any parent directory should be ignored
            if any(part.startswith('.') or part in skip_dirs for part in notebook_path.parts):
                continue
            notebooks.append(str(notebook_path))
        
        # Sort for consistent ordering
        notebooks.sort()
        return notebooks
        
    except (OSError, PermissionError) as e:
        click.echo(f'Warning: Could not access some directories: {e}')
        return []

def _find_notebooks(path):
    """Legacy notebook discovery function for backward compatibility."""
    if os.path.isfile(path): 
        return [path] if path.endswith('.ipynb') else []
    
    nbs = []
    for root, dirs, files in os.walk(path):
        # Skip hidden directories and common non-notebook dirs for performance
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {'__pycache__', 'node_modules', '.git'}]
        
        # Efficiently filter and sort notebook files
        notebook_files = sorted([f for f in files if f.endswith('.ipynb')])
        for f in notebook_files:
            nbs.append(os.path.join(root, f))
    
    return nbs