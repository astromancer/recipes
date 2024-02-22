"""
Some miscellaneous utility functions.
"""

# std
import numbers as nrs
import functools as ftl
from collections import abc

# relative
from ..iter import where
from ..functionals import negate
from . import ensure


# ---------------------------------------------------------------------------- #
# Null

def not_null(obj, except_=('',)):
    #      scalar                                                array-like
    return bool((obj or (obj in except_)) if is_scalar(obj) else len(obj))


# alias
notnull = not_null
isnull = is_null = negate(not_null)


# ---------------------------------------------------------------------------- #
# Scalars (unsized)

def is_scalar(obj, accept=(str, )):
    return not isinstance(obj, abc.Sized) or isinstance(obj, accept)


def duplicate_if_scalar(obj, n=2, accept=(str, ), emit=ValueError):
    """
    Ensure object size or duplicate if necessary.

    Parameters
    ----------
    obj : number or array-like

    Returns
    -------

    """

    if is_scalar(obj, accept):
        return [obj] * n

    # Sized object
    size = len(obj)
    if size == 1:
        return list(obj) * n

    #
    from recipes.flow.emit import Emit

    emit = Emit(emit)
    if size == 0:
        emit(f'Cannot duplicate empty {type(obj)}.')
        return [obj] * n

    if (size != n):
        emit(f'Input object of type {type(obj)} has incorrect size: {size}. '
             'Expected either a scalar type object, or a Container with length '
             f'in {{1, {n}}}.')

    return obj


# ---------------------------------------------------------------------------- #
# item deletion workers

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
    return type(container)(_delete_immutable(container, indices))


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
# remove items

def _remove(items, value, start=0):
    return delete(items, where(items, value, start=start))


def remove(items, *values, start=0):
    result = items[start:]
    for value in values:
        result = _remove(result, value)
        if not result:
            break

    return items[:start] + result
