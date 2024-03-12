"""
Polymorphic container utilities.
"""

# std
import itertools as itt
import numbers as nrs
import functools as ftl

# relative
from .. import iter as itr
from . import ensure


# ---------------------------------------------------------------------------- #

def match_input_type(func):

    @ftl.wraps(func)
    def wrapper(items, *args, **kws):
        kls = type(items)
        answer = func(items, *args, **kws)
        return kls(answer)

    return wrapper


# ---------------------------------------------------------------------------- #

def prepend(obj, prefix):
    return prefix + obj


def append(obj, suffix):
    return obj + suffix


# ---------------------------------------------------------------------------- #
# Item deletion

def _delete(container, indices):
    # delete multiple elements in a mutable container.
    # Will destroy items by calling `del` on each item at the given indices
    for i in _resolve_indices(indices, len(container), reverse=True):
        del container[i]

    return container


def _delete_immutable(container, indices):
    # iterator that rebuilds an immutable container, excluding specific indices
    n = len(container)
    i = prev = -1
    for i in _resolve_indices(indices, n):
        yield container[prev + 1:i]
        prev = i

    if i < n - 1:
        yield container[i + 1:]


def delete_immutable(container, indices):
    return sum(_delete_immutable(container, indices), type(container)())


def _resolve_indices(indices, n, reverse=False):
    from recipes.containers.dicts import groupby

    # ensure list
    indices = groupby(type, ensure.list(indices))
    integers = _integers_from_slices(indices.pop(slice, ()), n)
    for kls, idx in indices.items():
        if not issubclass(kls, nrs.Integral):
            raise TypeError(f'Invalid index type {kls}.')
        integers = integers.union(idx)

    # remove duplicate indices accounting for wrapping
    return sorted({(i + n) % n for i in integers}, reverse=reverse)


def _integers_from_slices(slices, n):
    integers = set()
    for s in slices:
        integers |= set(range(*s.indices(n)))
    return integers


# ---------------------------------------------------------------------------- #
# dispatch for item deletion

@ftl.singledispatch
def delete(obj, indices):
    raise TypeError(f'Invalid object: {obj!r} for item deleton.')


#
delete.register(tuple)(delete_immutable)


@delete.register(list)
def _(items, indices=()):
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

    return _delete(items, indices)


@delete.register(str)
def _(string, indices=()):
    """
    Remove characters at position `indices` from string.

    Parameters
    ----------
    string : str
        The string from which to remove characters.
    indices : collection of int
        Character index positions to delete. Negative indices are supported. 
        Duplicated indices are filtered.

    Examples
    --------
    >>> delete('0123456789', [0, 9])
    '12345678'
    >>> delete('0123456789', [0, -1, 9])
    '12345678'
    >>> delete('0123456789', [0, -1])
    '12345678'

    Returns
    -------
    str
    """

    return ''.join(_delete_immutable(string, indices)) if indices else string


# ---------------------------------------------------------------------------- #
# remove / replace items

def _remove(items, value, start=0):
    return delete(items, itr.where(items, value, start=start))


def remove(items, *values, start=0):
    result = items[start:]
    for value in values:
        result = _remove(result, value)
        if not result:
            break

    return items[:start] + result


@match_input_type
def replace(items, old, new):

    items = list(items)
    for index in itr.where(items, old):
        items[index] = new

    return items


# ---------------------------------------------------------------------------- #
# where, where.unique, where.duplicate

select = match_input_type(itr.select)
split = match_input_type(itr.split)
split_where = match_input_type(itr.split_where)
split_non_consecutive = match_input_type(itr.split_non_consecutive)
duplicates = match_input_type(itr.duplicates)


# @ doc.splice(op.index, omit='Parameters[default]')
@match_input_type
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


def split_like(items, lists):
    """
    Split a list `items` into sublists, each with the same size as the sequence of
    (raggedly sized) lists in `lists`.
    """

    *indices, total = itt.accumulate(map(len, lists))
    assert len(items) == total
    return split(items, indices)
