"""
Script for tidying import statements in python source files.
"""

# std
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
@click.option('-s', '--style',
              default='aesthetic', show_default=True,
              type=click.Choice(STYLES))
@click.option('-r', '--recurse',
              default=True, show_default=True,
              type=click.BOOL)
def main(files_or_folders, style, recurse):
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

    file = None
    for file in get_workload(files_or_folders, recurse):
        worker(file, style)

    if file is None:
        logger.info('No files found! Exiting.')


def get_workload(files_or_folders, recurse):
    for item in files_or_folders:  # TODO parallel!
        for file in _iter_files(item, recurse):
            yield file


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
    logger.info('Tidying import statements in {}', repr(str(file)))
    refactor(file, style)
