"""
Some common decorators.
"""

# std

# relative
from .emit import Emit
from .trace import Trace
from .catch import Catch, CatchWarnings, Fallback
from .inject import Prior, Post


# aliases
# ---------------------------------------------------------------------------- #
pre = prior = Prior
post = Post
trace = Trace
catch = Catch
fallback = Fallback
catch_warnings = CatchWarnings
