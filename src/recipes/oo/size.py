"""
Get the in-memory size of object.
"""

import sys
from numbers import Number
from collections import abc, deque


# ---------------------------------------------------------------------------- #
ZERO_DEPTH_BASES = (str, bytes, Number, range, bytearray)


# ---------------------------------------------------------------------------- #

def get_object_size(obj_0):
    """
    Recursively iterate to sum size of object & members.
    """

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
