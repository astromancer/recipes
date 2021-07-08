"""
Host of useful miscellaneous classes and functions.
"""


# std libs
import sys
import shutil
import logging
from numbers import Number
from collections import abc, deque

# third-party libs
import numpy as np

# local libs
from recipes.logging import logging, get_module_logger

# relative libs
from .interactive import is_interactive



# module level logger
logger = get_module_logger()
logging.basicConfig()
logger.setLevel(logging.INFO)


ZERO_DEPTH_BASES = (str, bytes, Number, range, bytearray)


def duplicate_if_scalar(a, n=2, raises=True):
    """

    Parameters
    ----------
    a : number or array-like

    Returns
    -------

    """
    # if isinstance(a, numbers.Number):
    #     return [a] * n

    if np.size(a) == 1:
        # preserves duck type arrays
        return np.asanyarray([a] * n).squeeze()

    if (np.size(a) != n) and raises:
        raise ValueError(f'Input should be of size 1 or {n}')

    return a


def get_terminal_size(fallback=(80, 24)):
    """Returns the initial terminal size."""

    # NOTE: NOT DYNAMIC. ie. resizing a window voids this ?
    # FIXME:

    if not is_interactive():
        return shutil.get_terminal_size(fallback)

    # in notebook / qtconsole / ipython terminal
    # NOTE: AFAICT it's not possible to distinguish between qtconsole and
    # notebook here

    from jupyter_core.paths import jupyter_config_dir
    from pathlib import Path
    import re

    path = Path(jupyter_config_dir())
    config_file = path / 'jupyter_qtconsole_config.py'

    wh = []
    with config_file.open() as fp:
        raw = fp.read()
        for j, s in enumerate(('width', 'height')):
            mo = re.search(rf'c.ConsoleWidget.console_{s} = (\d+)', raw)
            if mo:
                w_h = int(mo.group(1))
            else:
                # fallback
                logger.warning('Cannot determine terminal size for this '
                               'interactive session')
                w_h = fallback[j]
            wh.append(w_h)

    w, h = wh
    return w, h


def getsize(obj_0):
    """Recursively iterate to sum size of object & members."""

    def inner(obj, _seen_ids=set()):
        obj_id = id(obj)
        if obj_id in _seen_ids:
            return 0

        _seen_ids.add(obj_id)
        size = sys.getsizeof(obj)
        if isinstance(obj, ZERO_DEPTH_BASES):
            pass  # bypass remaining control flow and return

        elif isinstance(obj, (tuple, list, abc.Set, deque)):
            size += sum(inner(i) for i in obj)

        elif isinstance(obj, abc.Mapping) or hasattr(obj, 'items'):
            size += sum(inner(k) + inner(v) for k, v in obj.items())

        # Check for custom object instances - may subclass above too
        if hasattr(obj, '__dict__'):
            size += inner(vars(obj))

        if hasattr(obj, '__slots__'):  # can have __slots__ with __dict__
            size += sum(inner(getattr(obj, s)) for s in obj.__slots__ if
                        hasattr(obj, s))

        return size

    return inner(obj_0)


class Unbuffered:
    """Class to make stdout unbuffered"""

    def __init__(self, stream):
        self.stream = stream

    def write(self, data):
        self.stream.write(data)
        self.stream.flush()

    def __getattr__(self, attr):
        return getattr(self.stream, attr)
