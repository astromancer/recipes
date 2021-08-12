"""
Miscellaneous functions for pretty printing
"""


# relative libs
from ..dicts import pformat


def mapping(dict_, name=None, **kws):
    print(pformat(dict_, name, **kws))


def truncated(seq, max_items=10, edge_items=1, sep=','):
    """

    Parameters
    ----------
    seq
    max_items
    edge_items
    sep

    Returns
    -------

    """

    # if len(seq) <= max_items:
    #     return repr(seq)

    brackets = {set: '{}',
                list: '[]',
                tuple: '()'}.get(type(seq), '[]')
    if len(seq) <= max_items:
        return sep.join(map(repr, seq)).join(brackets)

    return ', ... '.join((sep.join(map(repr, seq[:edge_items])),
                          sep.join(map(repr, seq[-edge_items:]))
                          )).join(brackets)


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
