"""
Recipes involving lists.
"""

# std libs
from collections import defaultdict
import re
import itertools as itt

# third-party libs
import more_itertools as mit

# relative libs
from .dicts import DefaultOrderedDict
from .iter import nth_zip
import docsplice as doc
from . import op


def _echo(_):
    return _


def _zero(*_):
    return 0


def _make_key(master_key, funcs):
    def sort_key(x):
        values = ((f or _zero)(z) for f, z in zip(funcs, x))
        return (master_key(*x),) + tuple(values)
    return sort_key


def cosort(*lists, **kws):
    """
    Extended co-sorting of lists. Sort any number of lists simultaneously
    according to:
        * optional sorting function(s)
        * and/or a global sorting function.

    Parameters
    ----------
    One or more lists

    Keywords
    --------
    master_key: callable
        Sort by evaluated value of some combination of all items in the lists
        (call signature of this function needs to be such that it accepts an
        argument tuple of items from each list.
        eg.: master_key = lambda *l: sum(l) will order all the lists by the
        sum of the items from each list.
        If not provided, revert to sorting by `key` function
    key: callable or tuple of callables
        If callble sorting done by value of key(item) for items in first
        iterable If tuple sorting done by value of
        (key[0](item_0), ..., key[n](item_n)) for items in the first n iterables
        (where n is the length of the key tuple) i.e. the first callable is the
        primary sorting criterion, and the rest act as tie-breakers.
        If not provided sorting done by value of first input list. 

    Returns
    -------
    tuple of sorted lists

    Raises
    ------
    ValueError, KeyError

    Examples
    --------
    Sorting multiple lists in sympathy:
    >>> cosort('32145', range(5))

    Capture sorting indices:
    >>> l = list('CharacterS')
    >>> cosort(l, range(len(l)))
    (['C', 'S', 'a', 'a', 'c', 'e', 'h', 'r', 'r', 't'],
     [0, 9, 2, 4, 5, 7, 1, 3, 8, 6])
    >>> cosort(l, range(len(l)), key=str.lower)
    (['a', 'a', 'C', 'c', 'e', 'h', 'r', 'r', 'S', 't'],
     [2, 4, 0, 5, 7, 1, 3, 8, 9, 6])
    """
    # TODO: extend examples doc

    # convert to lists
    lists = list(map(list, lists))

    # check that all lists have the same length
    if len(set(map(len, lists))) != 1:
        raise ValueError('Cannot co-sort raggedly shaped lists')

    list0 = list(lists[0])
    if not list0:  # all lists are zero length
        return lists

    master_key = kws.pop('master_key', None)
    key = kws.pop('key', None)
    order = kws.pop('order', 1)
    if kws:
        raise ValueError(f'Unrecognised keyword(s): {tuple(kws.keys())}')

    # enable default behaviour
    if key is None:
        # if global sort function given and no local (secondary) key given
        #   ==> no tiebreakers
        # if no global sort and no local sort keys given, sort by values
        key = _zero if master_key else _echo

    # if no master key, use null func
    master_key = master_key or _zero

    # validity checks for sorting functions
    if not callable(master_key):
        raise ValueError('master_key needs to be callable')

    if callable(key):
        key = (key, )
    if not isinstance(key, (tuple, list)):
        raise KeyError("Keyword arg 'key' should be 'None', callable, or a"
                       f"sequence of callables, not {type(key)}")

    res = sorted(zip(*lists), key=_make_key(master_key, key))
    if order == -1:
        res = reversed(res)

    return tuple(map(list, zip(*res)))


def lists(mapping):
    """create a sequence of lists from a mapping / iterator /generator"""
    return list(map(list, mapping))


# def sort_by_index(*its, indices=None):
#     """Use index array to sort items in multiple sequences"""
#     if indices is None:
#         return its
#     return tuple(list(map(it.__getitem__, ix))
#                  for it, ix in zip(its, itt.repeat(indices)))


@doc.splice(op.index, omit='Parameters[default]')
def where(l, item, start=0, test=op.eq):
    """
    A multi-indexer for lists. Return index positions of all occurances of
    `item` in a list `l`.  If a test function is given, return all indices at
    which the test evaluates true.

    {Parameters}

    Examples
    --------
    >>> l = ['ab', 'Ba', 'cb', 'dD']
    >>> where(l, 'a', str.__contains__)
    [0, 1]
    >>> where(l, 'a', indexer=str.startswith)
    [0]


    Returns
    -------
    list of int or `default`
        The index positions where test evaluates true
    """
    test = test or op.eq
    return list(_where(l, item, start, test))


def _where(l, item, start=0, test=op.eq):
    i = start
    n = len(l)
    while i < n:
        try:
            i = op.index(l, item, i, test=test)
            yield i
        except ValueError:
            # done
            return
        else:
            i += 1  # start next search one on


def flatten(l):
    """
    Flatten arbitrarily nested sequences

    Parameters
    ----------
    l : list
        [description]

    Returns
    -------
    list
        [description]
    """
    return list(mit.collapse(l))


def split(l, idx):
    """Split a list into sublists at the given indices"""
    if len(idx) == 0:
        return [l]

    if idx[0] != 0:
        idx = [0] + idx

    if idx[-1] != len(l):
        idx += [len(l)]

    return [l[sec] for sec in map(slice, idx, idx[1:])]


def split_where(l, item, start=0, test=None):
    """
    Split a list into sublists at the positions of positive test evaluation.
    """
    # idx = where(l, item, indexer)

    # withfirst=False, withlast=False,
    # if withfirst:
    #     idx = [0] + idx
    # if withlast:
    #     idx += [len(l) - 1]

    return split(l, where(l, item, start, test))


def missing_integers(l):
    """Find the gaps in a sequence of integers"""
    return sorted(set(range(min(l), max(l) + 1)) - set(l))


# alias
missing_ints = missing_integers


# def increment_excedes(nrs, threshold):
#     enum = iter(nrs)
#     return where(nrs, '', 1, lambda x, _: x - next(enum) > threshold)

def partition(l, predicate):
    parts = defaultdict(list)
    indices = defaultdict(list)
    for i, item in enumerate(l):
        box = predicate(item)
        parts[box].append(item)
        indices[box].append(i)
    return parts, indices


def tally(l):
    """Return dict of item, count pairs for sequence."""
    t = DefaultOrderedDict(int)
    for item in l:
        t[item] += 1
    return t


def unique(l):
    """Return dict of unique (item, indices) pairs for sequence."""
    t = DefaultOrderedDict(list)
    for i, item in enumerate(l):
        t[item].append(i)
    return t


def iter_duplicates(l):
    """Yield tuples of item, indices pairs for duplicate values."""
    for key, idx in unique(l).items():
        if len(idx) > 1:
            yield key, idx


def duplicates(l):
    """Return tuples of item, indices pairs for duplicate values."""
    return list(iter_duplicates(l))


def where_duplicate(l):
    """Return lists of indices of duplicate entries"""
    return nth_zip(1, *iter_duplicates(l))
