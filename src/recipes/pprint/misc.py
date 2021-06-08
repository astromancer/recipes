"""
Miscellaneous functions for pretty printing
"""


# relative libs
from ..dicts import pformat


def dicts(dict_):
    print(pformat(dict_))


def seq_repr_trunc(seq, max_items=10, edge_items=1, sep=','):
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
