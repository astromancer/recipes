#! /usr/bin/env python
"""
Script for tidying import statements in python source files.
"""

# pylint: disable=wrong-import-position

if __name__ != '__main__':
    raise SystemExit()


# std
import sys

# third-party
from loguru import logger

# local
import motley

# relative
from recipes.introspect.imports import refactor

# TODO: argparse options

filename = sys.argv[1]
debug = False

logger.info('Tidying import statements in {}', motley.blue(filename))
refactor(filename)#.sort_imports(dry_run=debug, report=debug)
