
# std
import os
import io
import ast
import sys
import math
import inspect
import pkgutil
import warnings as wrn
import functools as ftl
import itertools as itt
from pathlib import Path
from collections import defaultdict

# third-party
import more_itertools as mit
from stdlib_list import stdlib_list

# local
from recipes import cosort, op
from recipes.io import open_any
from recipes import pprint as pp
from recipes.functionals import negate
from recipes.string import replace_prefix, truncate
from recipes.logging import logging, get_module_logger

# relative
from ..io import safe_write

