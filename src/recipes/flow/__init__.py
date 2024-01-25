"""
Some common decorators.
"""

from .emit import Emit
from .trace import Trace
from .inject import Post, Prior
from .catch import Catch, CatchWarnings, Fallback


# aliases
# ---------------------------------------------------------------------------- #
pre = prior = Prior
post = Post
trace = Trace
catch = Catch
fallback = Fallback
catch_warnings = CatchWarnings
