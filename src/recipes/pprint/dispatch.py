"""
Pretty printing type dispatch
"""


# std
import functools as ftl
from collections import abc

# relative
from .pformat import collection
from .mapping import pformat as mapping


# ---------------------------------------------------------------------------- #
STD_BRACKETS = object()
STD_BRACKET_TYPES = {set: '{}',
                     list: '[]',
                     tuple: '()'}

# ---------------------------------------------------------------------------- #


@ftl.singledispatch  # generic type implementation
def pformat(obj, **kws):
    return repr(obj)
    # raise TypeError(f'No dispatch method for pprinting objects of type {type(obj)}.')


@pformat.register(str)
def _(obj, _=None, **__):
    return repr(obj)


@pformat.register(abc.MutableMapping)
def _(obj, name=None, **kws):
    return mapping(obj, name, **kws)


@pformat.register(abc.Collection)
def _(obj, **kws):
    return collection(obj, **kws)


def pprint(obj, **kws):
    print(pformat(obj, **kws))
