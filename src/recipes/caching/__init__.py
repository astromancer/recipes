"""
A small API for persistent caching
"""

from . import hashers
from .caches import *
from .decor import Cached, Ignore, Reject

# import os
# os.environ['PYTHONHASHSEED'] = 789


# ---------------------------------------------------------------------------- #
# Aliases                                       # pylint: disable=invalid-name
to_file = Cached.to_file
memoize = cached = Cached
