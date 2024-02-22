"""
Some miscellaneous utility functions.
"""

# std
import numbers
from collections import abc

# relative
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

def _delete(container, indices):
    # delete multiple elements in a mutable container.
    # Will destroy items by calling `del` on each item at the given indices
    for i in _resolve_indices(indices, len(container), reverse=True):
        del container[i]


def _delete_immutable(container, indices):
    # iterator that rebuilds an immutable container, excluding specific indices
    n = len(container)
    i = prev = -1
    for i in _resolve_indices(indices, n):
        yield container[prev + 1:i]
        prev = i

    if i < n - 1:
        yield container[i + 1:]


def _resolve_indices(indices, n, reverse=False):
    from recipes.containers.dicts import groupby

    # ensure list
    indices = groupby(type, ensure.list(indices))
    integers = _integers_from_slices(indices.pop(slice, ()), n)
    for kls, idx in indices.items():
        if not issubclass(kls, numbers.Integral):
            raise TypeError(f'Invalid index type {kls}.')
        integers = integers.union(idx)

    # remove duplicate indices accounting for wrapping
    return sorted({(i + n) % n for i in integers}, reverse=reverse)


def _integers_from_slices(slices, n):
    integers = set()
    for s in slices:
        integers |= set(range(*s.indices(n)))
    return integers

