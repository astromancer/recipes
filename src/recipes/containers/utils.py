"""
Polymorphic container utilities.
"""

# std
import itertools as itt
from collections import defaultdict

# third-party
import more_itertools as mit

# relative
from .. import iter as itr
from ..functionals import always, echo
from .ensure import is_scalar, TypeContinuity
from .delete import delete


# ---------------------------------------------------------------------------- #
# function that always returns 0
_zero = always(0)


# ---------------------------------------------------------------------------- #

def lists(iters):
    """Create a sequence of lists from a mapping / iterator / generator."""
    return list(map(list, iters))


def prepend(obj, prefix):
    return prefix + obj


def append(obj, suffix):
    return obj + suffix


@TypeContinuity
def flatten(items):
    """
    Flatten arbitrarily nested sequences.

    Parameters
    ----------
    items : list
        [description]

    Returns
    -------
    list
        [description]
    """
    return mit.collapse(items)


# ---------------------------------------------------------------------------- #
# remove / replace items

def delete_value(items, value, start=0, n=None):
    """Delete all occurences of a value."""
    return delete(items, itt.islice(itr.where(items, value, start=start), n))


def remove(items, *values, start=0):
    result = items[start:]
    for value in values:
        result = delete_value(result, value)
        if not result:
            break

    return items[:start] + result


@TypeContinuity()
def replace(items, old, new):

    items = list(items)
    for index in itr.where(items, old):
        items[index] = new

    return items


# ---------------------------------------------------------------------------- #
# Misc

def tally(items):
    """Return dict of item, count pairs for sequence."""
    tally = defaultdict(int)
    for item in items:
        tally[item] += 1
    return tally


def missing_integers(items):
    """Find the gaps in a sequence of integers"""
    return sorted(set(range(min(items), max(items) + 1)) - set(items))


# alias
missing_ints = missing_integers


def partition(items, predicate):
    parts = defaultdict(list)
    indices = defaultdict(list)
    for i, item in enumerate(items):
        id_ = predicate(item)
        parts[id_].append(item)
        indices[id_].append(i)
    return parts, indices


# @ doc.splice(op.index, omit='Parameters[default]')
@TypeContinuity(ensure={str: list})
def where(items, *args, start=0):
    """
    A container multi-indexer. Return index positions of all occurances of
    `item` in a list `items`. If a test function is given, return all indices at
    which the test evaluates true.

    Three distinct call signatures are supported:
        >>> where(items)                # indices where items are truthy
        >>> where(items, value)         # indices where items equal value
        >>> where(items, func, value)   # conditionally on func(item, value)

    Parameters
    ----------
    items : Iterable
        Any iterable. Note that this function will consume the iterable.
    args : ([test], rhs)
        test : callable, optional
            Function for testing, should return bool, by default op.eq.
        rhs : object
            Right hand side item for equality test.
    start : int, optional
        Starting index for search, by default 0.

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
    return itr.where(items, *args, start=start)


# ---------------------------------------------------------------------------- #

def sort_like(items, order):
    return cosort(order, items)[1]


# @TypeContinuity(ensure={all: tuple}, coerce=list)
def cosort(*items, key=None, master_key=None, order=1):
    """
    Extended co-sorting of multiple lists. Sort any number of lists
    simultaneously according to:
        * Sorting function(s) for each list and / or
        * A global sorting function.

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
    tuple[list]
        The sorted lists.

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
    items = lists(items)

    if not items:
        return []

    # check that all lists have the same length
    unique_sizes = set(map(len, items))
    if len(unique_sizes) != 1:
        raise ValueError(f'Cannot co-sort lists with varying sizes: {unique_sizes}')

    # catch for all lists zero length
    if unique_sizes == {0}:
        return items

    # sort
    result = sorted(zip(*items), key=_CosortHelper(key, master_key))

    if order == -1:
        result = reversed(result)

    return tuple(map(list, zip(*result)))


class _CosortHelper:

    __slots__ = ('key', 'master_key')

    def __init__(self, key, master_key):
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
            raise ValueError('Parameter `master_key` needs to be callable.')

        if callable(key):
            key = (key, )

        if is_scalar(key):
            raise KeyError(
                'Keyword-only parameter `key` should be `None`, callable, or a '
                f'sequence of callables, not {type(key)}.')

        self.key = key
        self.master_key = master_key

    def __call__(self, items):
        values = ((f or _zero)(z) for f, z in zip(self.key, items))
        return (self.master_key(*items), *values)


# ---------------------------------------------------------------------------- #
# where, where.unique, where.duplicate
select = TypeContinuity()(itr.select)
duplicates = TypeContinuity(ensure={all: list})(itr.duplicates)

# split iterators conserve container types, we only need to unpack the iterables
split = TypeContinuity(ensure={all: tuple})(itr.split)
split_like = TypeContinuity(ensure={all: tuple})(itr.split_like)
split_where = TypeContinuity(ensure={all: tuple})(itr.split_where)
split_non_consecutive = TypeContinuity(disallow=str)(itr.split_non_consecutive)

# Duplicate detection
unique = TypeContinuity(ensure={all: list})(itr.unique)
where_duplicate = TypeContinuity(ensure={all: list})(itr.where_duplicate)
where_duplicates = where_duplicate  # alias
