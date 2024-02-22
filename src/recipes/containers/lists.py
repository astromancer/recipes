"""
Recipes involving lists.
"""


# std
import itertools as itt
from collections import defaultdict

# third-party
import more_itertools as mit

# relative
from .. import iter as _iter
from ..functionals import always, echo
from .utils import _delete


# function that always returns 0
_zero = always(0)


def lists(iters):
    """Create a sequence of lists from a mapping / iterator / generator."""
    return list(map(list, iters))


def cosort(*lists, key=None, master_key=None, order=1):
    """
    Extended co-sorting of lists. Sort any number of lists simultaneously
    according to:
        * optional sorting function(s)
        * and/or a global sorting function.

    Parameters
    ----------
    lists:
        One or more lists.
    key: None or callable or tuple of callables
        * If None (the default): Sorting done by value of first input list.
        * If callable: Sorting is done by value of
            >>> key(item)
          for successive items from the first iterable.
        * If tuple of callables: Sorting done by value of
              >>> key[0](item_0), ..., key[n](item_n)
          for items in the first n iterables (where n is the length of the `key`
          tuple) i.e. the first callable is the primary sorting criterion, and the
          rest act as tie-breakers.
    master_key: callable
        Sort by evaluated value of some combination of all items in the lists
        (call signature of this function needs to be such that it accepts an
        argument tuple of items - one from each list.
        For example:
        >>> master_key = lambda *items: sum(items)
        will order all the lists by the sum of the items from each list. If not
        provided, revert to sorting by `key` function.

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
    >>> items = list('CharacterS')
    >>> cosort(items, range(len(items)))
    (['C', 'S', 'a', 'a', 'c', 'e', 'h', 'r', 'r', 't'],
     [0, 9, 2, 4, 5, 7, 1, 3, 8, 6])
    >>> cosort(items, range(len(items)), key=str.lower)
    (['a', 'a', 'C', 'c', 'e', 'h', 'r', 'r', 'S', 't'],
     [2, 4, 0, 5, 7, 1, 3, 8, 9, 6])
    """
    # TODO: extend examples doc

    # convert to lists
    lists = list(map(list, lists))

    if not lists:
        return []

    # check that all lists have the same length
    unique_sizes = set(map(len, lists))
    if len(unique_sizes) != 1:
        raise ValueError(f'Cannot co-sort lists with varying sizes: '
                         f'{unique_sizes}')

    list0 = list(lists[0])
    if not list0:  # all lists are zero length
        return lists

    # enable default behaviour
    if key is None:
        # if global sort function given and no local (secondary) key given
        #   ==> no tiebreakers
        # if no global sort and no local sort keys given, sort by values
        key = _zero if master_key else echo

    # if no master key, use null func
    master_key = master_key or _zero

    # validity checks for sorting functions
    if not callable(master_key):
        raise ValueError('Parameter `master_key` needs to be callable')

    if callable(key):
        key = (key, )
    if not isinstance(key, (tuple, list)):
        raise KeyError(
            'Keyword-only parameter `key` should be `None`, callable, or a'
            f'sequence of callables, not {type(key)}.')

    res = sorted(zip(*lists), key=_make_cosort_key(master_key, key))
    if order == -1:
        res = reversed(res)

    return tuple(map(list, zip(*res)))


def _make_cosort_key(master_key, funcs):
    def sort_key(x):
        values = ((f or _zero)(z) for f, z in zip(funcs, x))
        return (master_key(*x),) + tuple(values)
    return sort_key


# @ doc.splice(op.index, omit='Parameters[default]')
def where(items, *args, start=0):
    """
    A multi-indexer for lists. Return index positions of all occurances of
    `item` in a list `items`. If a test function is given, return all indices at
    which the test evaluates true.

    {Parameters}

    Examples
    --------
    >>> items = ['ab', 'Ba', 'cb', 'dD']
    >>> where(items, op.contains, 'a')
    [0, 1]
    >>> where(items, str.startswith, 'a')
    [0]


    Returns
    -------
    list of int or `default`
        The index positions where test evaluates true.
    """
    return list(_iter.where(items, *args, start=start))


def select(items, test=bool):
    return list(_iter.select(items, test))


def flatten(items):
    """
    Flatten arbitrarily nested sequences

    Parameters
    ----------
    items : list
        [description]

    Returns
    -------
    list
        [description]
    """
    return list(mit.collapse(items))


def split(items, indices, offset=0):
    """Split a list `items` into sublists at the given indices."""
    return list(_iter.split(items, indices, offset))


def split_like(items, lists):
    """
    Split a list `items` into sublists, each with the same size as the sequence of
    (raggedly sized) lists in `lists`.
    """
    *indices, total = itt.accumulate(map(len, lists))
    assert len(items) == total
    return split(items, indices)


def sort_like(items, order):
    return cosort(order, items)[1]


def split_where(items, item, start=0, test=None):
    """
    Split a list into sublists at the positions of positive test evaluation.
    """
    # indices = where(items, item, indexer)

    # withfirst=False, withlast=False,
    # if withfirst:
    #     indices = [0] + indices
    # if withlast:
    #     indices += [len(items) - 1]

    return split(items, where(items, test, item, start=start))


def missing_integers(items):
    """Find the gaps in a sequence of integers"""
    return sorted(set(range(min(items), max(items) + 1)) - set(items))


# alias
missing_ints = missing_integers


def partition(items, predicate):
    parts = defaultdict(list)
    indices = defaultdict(list)
    for i, item in enumerate(items):
        box = predicate(item)
        parts[box].append(item)
        indices[box].append(i)
    return parts, indices


def tally(items):
    """Return dict of item, count pairs for sequence."""
    from ..containers.dicts import DefaultOrderedDict

    t = DefaultOrderedDict(int)
    for item in items:
        t[item] += 1
    return t


def unique(items):
    """Return dict of unique (item, indices) pairs for sequence."""
    from ..containers.dicts import DefaultOrderedDict

    t = DefaultOrderedDict(list)
    for i, item in enumerate(items):
        t[item].append(i)
    return t


def duplicates(items):
    """Return tuples of item, indices pairs for duplicate values."""
    return list(_iter.duplicates(items))


def where_duplicate(items):
    """Return lists of indices of duplicate entries"""
    return _iter.nth_zip(1, *_iter.duplicates(items))


def replace(items, value, new):
    if value not in items:
        return items

    items[items.index(value)] = new
    return items


def _remove(items, value, start=0):
    return delete(items, where(items, value, start=start))


def remove(items, *values, start=0):
    result = items[start:]
    for value in values:
        result = _remove(result, value)
        if not result:
            break

    return items[:start] + result


def delete(items, indices=()):
    """
    Remove characters at position `indices` from list. Items are deleted
    in-place, and the function returns the original list.

    Parameters
    ----------
    items : list
        The list from which to remove characters.
    indices : collection of int
        Character index positions to delete. Duplicated indices are filtered.
        Negative indices as well as slices, or a combination of both, are
        supported.

    Examples
    --------
    >>> delete(list('0123456789'), [0, 9])
    ['1', '2', '3', '4', '5', '6', '7', '8']
    >>> delete(list('0123456789'), [0, -1, 9])
    ['1', '2', '3', '4', '5', '6', '7', '8']
    >>> delete(list('0123456789'), [0, -1])
    ['1', '2', '3', '4', '5', '6', '7', '8']
    >>> delete(list('0123456789'), [0, -1, slice(0, 3)])
    ['3', '4', '5', '6', '7', '8']

    Returns
    -------
    list
    """

    _delete(items, indices)
    return items
