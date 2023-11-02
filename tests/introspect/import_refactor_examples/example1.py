
# std
import more_itertools as mit
from recipes import cosort
from recipes import op
from recipes.functionals import negate
from recipes.dicts import AutoVivify
from recipes import pprint as pp
import os
from recipes.string import replace_prefix
from recipes.io import open_any
import functools as ftl
from recipes.io import iter_lines
from recipes.string import truncate
from recipes.dicts import DefaultDict
from recipes.io import read_lines
from ..regex import split_iter
import io
import ast
import sys
import math
import inspect
import warnings as wrn
import itertools as itt
from pathlib import Path
from functools import partial
from collections import defaultdict

# third-party
import anytree
from stdlib_list import stdlib_list

# relative
from ..io import write_lines, safe_write, count_lines
from ..functionals import always, echo0 as echo


# FIXME: unscoped imports do not get added to top!!!
# FIXME: too many blank lines after module docstring


# TODO: split_modules
# TODO: style preference: "import uncertainties.unumpy as unp" over
#                         "from uncertainties import unumpy as unp"
# TODO: keep multiline imports as multiline
# TODO: local import that are already in global namespace

from recipes.logging import logging, get_module_logger
