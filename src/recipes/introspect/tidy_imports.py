#! /usr/bin/env python

if __name__ != '__main__':
    raise SystemExit()


import sys
from recipes.introspect.imports import refactor
import motley


# TODO: argparse options

filename = sys.argv[1]
debug = False

print('Tidying import statements in %s' % motley.blue(filename))
refactor(filename)#.sort_imports(dry_run=debug, report=debug)
