"""
Miscellaneous functions for pretty printing
"""


# std
import os

# relative
from ..string import overlay


# ---------------------------------------------------------------------------- #
STD_BRACKETS = object()
STD_BRACKET_TYPES = {set: '{}',
                     list: '[]',
                     tuple: '()'}

# ---------------------------------------------------------------------------- #


def collection(obj, max_items=10, edge_items=1, sep=',', dots='...',
               brackets=STD_BRACKETS, fmt=repr):
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

    assert callable(fmt)

    if brackets is STD_BRACKETS:
        brackets = STD_BRACKET_TYPES.get(type(obj), '[]')
    elif not brackets:
        brackets = ('', '')

    brackets = list(map(str, brackets)) 
    assert len(brackets) == 2
    
    if len(obj) <= max_items:
        return sep.join(map(fmt, obj)).join(brackets)

    return f'{sep} {dots} '.join(
        (sep.join(map(fmt, obj[:edge_items])),
         sep.join(map(fmt, obj[-edge_items:])))
    ).join(brackets)


def banner(text, swoosh='=', width=80, title=None, align='^'):
    # TODO move to string module
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
    pre = swoosh if title is None else overlay(title, swoosh, align)
    return os.linesep.join((pre, str(text), swoosh, ''))
