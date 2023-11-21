"""
Script for tidying import statements in python source files.
"""

# std
import itertools as itt
import contextlib as ctx
from pathlib import Path

# third-party
import click
from loguru import logger

# relative
from ...io.gitignore import GitIgnore
from . import STYLES, refactor


# ---------------------------------------------------------------------------- #

@click.command()
@click.argument('files_or_folders', nargs=-1)
@click.option('-s', '--style', default='aesthetic', show_default=True, type=click.Choice(STYLES))
@click.option('-r', '--recurse', default=True, show_default=True, type=click.BOOL)
@click.option('-j', '--njobs', default=1, show_default=True, type=click.INT)
@click.option('-v', '--verbose', count=True)
def main(files_or_folders, style, recurse, njobs, verbose):
    #   filter_unused=None,
    #   split=0,
    #   merge=1,
    #   relativize=None,
    #   #  unscope=False,
    #   headers=True
    #   dry_run=debug
    """
    Refactor and sort python import statements. This script takes an arbitrary 
    number of input parameters: the file(s) to be refactored, and/or folder(s) 
    (packages/modules) to be traversed and refactored.
    """

    # turn on logging
    logger.configure(activation=[('recipes', 'INFO')])

    workload = get_workload(files_or_folders, recurse)
    ok, workload = check_workload(workload)
    if not ok:
        logger.info('No files found! Exiting.')
        return 0

    #
    _worker, context = setup_compute(worker, njobs, verbose=verbose * 20)
    with context as compute:
        compute(_worker(file, style) for file in workload)

    return 0


def setup_compute(worker, njobs, backend='multiprocessing', **kws):

    # NOTE: object serialization is about x100-150 times faster with
    # "multiprocessing" backend. ~0.1s vs 10s for "loky".
    if njobs == 1:
        return worker, ctx.nullcontext(list)

    context = ContextStack()
    worker = delayed(worker)
    executor = Parallel(njobs, backend, **kws)
    context.add(executor)
    return worker, context


def get_workload(files_or_folders, recurse):
    for item in files_or_folders:
        for file in _iter_files(item, recurse):
            yield file


def check_workload(itr):
    first = next(itr, None)
    if first is None:
        return False, ()

    return True, itt.chain([first], itr)


def _iter_files(file_or_folder, recurse):

    path = Path(file_or_folder).resolve()

    if not path.exists():
        logger.warning("File or directory does not exist: '{}'.", path)
        return

    if path.is_dir():
        if (gitignore := path / '.gitignore').exists():
            files = GitIgnore(gitignore).iter(depth=(1, any)[recurse])
            files = filter(_py_file, files)
        else:
            files = (path.glob, path.rglob)[recurse]('*.py')

        yield from files

    elif _py_file(path):
        yield path

    else:
        logger.warning("Not a valid python file: '{}'.", path)


def _py_file(path):
    return path.suffix == '.py'


def worker(file, style):
    logger.info('Tidying import statements in {}.', repr(str(file)))
    refactor(file, style)
