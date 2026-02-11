"""CLI."""
import click
import os
from notebook_test.runner import run_notebook, NotebookError
from notebook_test.strip import strip_outputs

@click.group()
def main(): pass

@main.command()
@click.argument('path')
@click.option('--timeout', default=120, type=int)
def run(path, timeout):
    """Execute notebooks and report errors."""
    notebooks = _find_notebooks(path)
    if not notebooks:
        click.echo('No notebooks found'); return
    passed, failed = 0, 0
    for nb_path in notebooks:
        try:
            run_notebook(nb_path, timeout=timeout)
            click.echo(f'  PASS {nb_path}')
            passed += 1
        except NotebookError as e:
            click.echo(f'  FAIL {nb_path}: {e}')
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
