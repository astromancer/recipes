"""
A small API for persistent caching
"""

from .caches import *
from .decor import Cached, Ignore, Reject


# ---------------------------------------------------------------------------- #
# Aliases                                       # pylint: disable=invalid-name
to_file = Cached.to_file
memoize = cached = Cached
