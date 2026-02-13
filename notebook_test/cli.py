"""CLI."""
import click
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from notebook_test.runner import run_notebook, NotebookError
from notebook_test.strip import strip_outputs


def _run_one(nb_path, timeout):
    """Run single notebook, return (path, elapsed_sec, error_or_None)."""
    t0 = time.monotonic()
    try:
        run_notebook(nb_path, timeout=timeout)
        return nb_path, time.monotonic() - t0, None
    except NotebookError as e:
        return nb_path, time.monotonic() - t0, str(e)

@main.command()
@click.argument('path')
@click.option('--timeout', default=120, type=int)
@click.option('--workers', '-j', default=1, type=int, help='Parallel workers')
def run(path, timeout, workers):
    """Execute notebooks and report errors."""
    notebooks = _find_notebooks(path)
    if not notebooks:
        click.echo('No notebooks found'); return
    t_start = time.monotonic()
    passed, failed = 0, 0
    workers = min(max(workers, 1), len(notebooks))
    if workers > 1:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futs = {pool.submit(_run_one, nb, timeout): nb for nb in notebooks}
            for fut in as_completed(futs):
                nb_path, elapsed, err = fut.result()
                if err is None:
                    click.echo(f'  PASS {nb_path} ({elapsed:.1f}s)')
                    passed += 1
                else:
                    click.echo(f'  FAIL {nb_path}: {err} ({elapsed:.1f}s)')
                    failed += 1
    else:
            if f.endswith('.ipynb') and '.ipynb_checkpoints' not in os.path.normpath(root).split(os.sep):

            nb_path, elapsed, err = _run_one(nb_path, timeout)
            if err is None:
                click.echo(f'  PASS {nb_path} ({elapsed:.1f}s)')
                passed += 1
            else:
                click.echo(f'  FAIL {nb_path}: {err} ({elapsed:.1f}s)')
                failed += 1
    wall = time.monotonic() - t_start
    click.echo(f'\n{passed} passed, {failed} failed in {wall:.1f}s')
    if failed: raise SystemExit(1)

            failed += 1
    click.echo(f'\n{passed} passed, {failed} failed')
    if failed: raise SystemExit(1)

@main.command()
@click.argument('path')
def strip(path):
    """Strip outputs from notebooks."""
    for nb in _find_notebooks(path):
        strip_outputs(nb)
        click.echo(f'  Stripped {nb}')

def _find_notebooks(path):
    if os.path.isfile(path): return [path]
    nbs = []
    for root, _, files in os.walk(path):
        for f in sorted(files):
            if f.endswith('.ipynb') and '.ipynb_checkpoints' not in root:
                nbs.append(os.path.join(root, f))
    return nbs
