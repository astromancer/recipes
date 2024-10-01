"""
Script for tidying import statements in python source files.
"""

# std
from pathlib import Path

# third-party
import click
import numpy as np
from loguru import logger

# relative
from ...config import ConfigNode
from ...containers import ensure
from ...concurrency import Executor
from ...io.gitignore import GitIgnore
from . import STYLES, refactor


# ---------------------------------------------------------------------------- #
CONFIG = ConfigNode.load_module(__file__)

# ---------------------------------------------------------------------------- #


def _py_file(path):
    return path.suffix == '.py'


def _iter_files(file_or_folder, recurse, ignore):

    path = Path(file_or_folder).resolve()

    if not path.exists():
        logger.warning("File or directory does not exist: '{}'.", path)
        return

    if (gitignore := path / '.gitignore').exists():
        gitignore = GitIgnore(gitignore)
        gitignore.add(ignore)

    if path.is_dir():
        if gitignore:
            files = gitignore.iterdir(depth=(1, any)[recurse])
            files = filter(_py_file, files)
        else:
            files = (path.glob, path.rglob)[recurse]('*.py')

        yield from files

    elif _py_file(path):
        if gitignore.match(s := str(path)):
            logger.debug('Ignoring: {!r}.', s)
        else:
            yield path

    else:
        logger.warning("Not a valid python file: '{}'.", path)


# ---------------------------------------------------------------------------- #

class Tidy(Executor):

    __slots__ = ('style', 'recurse', 'ignore')

    def __init__(self, style='aesthetic', recurse=True, **config):

        super().__init__(**config)
        self.results = []           # this means the super call will not raise
        self.style = str(style)
        self.recurse = bool(recurse)
        self.ignore = set(CONFIG.get('ignore', ()))

    def __call__(self, *args, ignore=(), **kws):
        if ignore:
            self.ignore |= ensure.set(ignore)

        return super().__call__(*args, **kws)

    def compute(self, file, index, **kws):
        logger.info('Tidying import statements in {}.', repr(str(file)))
        refactor(file, self.style)

    def get_workload(self, files_or_folders, *args, **kws):

        files = list(self._resolve_files(files_or_folders))
        if not files:
            return []

        self.results = np.full(len(files), np.nan)
        return super().get_workload(files, *args, **kws)

    def _resolve_files(self, files_or_folders):
        self.logger.info('Resolving workload.')
        for item in files_or_folders:
            for file in _iter_files(item, self.recurse, self.ignore):
                yield file

    def collect(self, index, result):
        # No results returned from worker
        return


# ---------------------------------------------------------------------------- #

@click.command()
@click.argument('files_or_folders', nargs=-1)
@click.option('-s', '--style', default='aesthetic', show_default=True,
              type=click.Choice(STYLES),
              help='Sorting style.')
@click.option('-r', '--recurse', default=True, show_default=True, type=click.BOOL,
              help='Whether to step down the folder tree into sub-directories.')
@click.option('-i', '--ignore', default=(),
              help='List of files to ignore.')
@click.option('-j', '--njobs', default=-1, show_default=True, type=click.INT,
              help='Number of cuncurrent processes to run. This can speed up '
                   'operations significantly.')
# @click.option('-v', '--verbose', count=True)
def main(files_or_folders, style, recurse, ignore, njobs):
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

    tidy = Tidy(style, recurse)
    tidy(files_or_folders, ignore=ignore, njobs=njobs)

    return 0
