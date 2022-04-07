"""
Miscellaneous functions for pretty printing
"""


# std
import os

# relative
from ..dicts import pformat
from ..string import overlay


STD_BRACKET_TYPES = {set: '{}',
                     list: '[]',
                     tuple: '()'}


def qualname(kls):
    return f'{kls.__module__}.{kls.__name__}'


def mapping(dict_, name=None, **kws):
    """
    Pretty print a dict-like mapping

    Parameters
    ----------
    dict_ : [type]
        [description]
    name : [type], optional
        [description], by default None

    Examples
    --------
    >>> 
    """
    print(pformat(dict_, name, **kws))


def collection(obj, max_items=10, edge_items=1, sep=',', dots='...'):
    """
    Print a pretty representation of a collection of items, trunctated
    at `max_items`.

    Parameters
    ----------
    obj
    max_items
    edge_items
    sep

    Returns
    -------

    """

    # if len(obj) <= max_items:
    #     return repr(obj)

    brackets = STD_BRACKET_TYPES.get(type(obj), '[]')
    if len(obj) <= max_items:
        return sep.join(map(repr, obj)).join(brackets)

    return f'{sep} {dots} '.join(
        (sep.join(map(repr, obj[:edge_items])),
         sep.join(map(repr, obj[-edge_items:])))
         ).join(brackets)


def banner(text, swoosh='=', width=80, title=None, align='^'):
    """

    Parameters
    ----------
    text
    swoosh
    width
    title
    align

    Returns
    -------

    """

    swoosh = swoosh * width
    pre = swoosh if title is None else overlay(' ', swoosh, align)
    return os.linesep.join((pre, text, swoosh, ''))
