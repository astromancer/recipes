#! /usr/bin/env python

"""
Script for tidying import statements in python source files.
"""


# pylint: disable=wrong-import-position

if __name__ != '__main__':
    raise SystemExit()


# std
from pathlib import Path

# third-party
import click
from loguru import logger

# local
import motley
from recipes.introspect.imports import STYLES, refactor


#
logger.configure(activation=[('recipes', 'INFO')])


@click.command()
@click.argument('files_or_folders', nargs=-1)
@click.option('-s', '--style', default='aesthetic', show_default=True,
              type=click.Choice(STYLES))
def main(files_or_folders, style,):
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
    file = None
    for item in files_or_folders:
        for file in _iter_files(item):
            worker(file, style)

    if file is None:
        logger.info('No files found! Exiting.')


def _iter_files(file_or_folder):

    path = Path(file_or_folder).resolve()

    if path.exists():
        if path.is_dir():
            yield from path.rglob('*.py')
        elif path.suffix == '.py':
            yield path
        else:
            logger.warning('Not a valid python file: \'{}\'.', path)
    else:
        logger.warning('File or directory does not exist: \'{}\'.', path)


def worker(file, style):
    logger.info('Tidying import statements in {}', motley.blue(repr(str(file))))
    refactor(file, style)


if __name__ == '__main__':
    main()
