# std
import numbers as nrs
import functools as ftl

# relative
from .. import iter
from . import ensure


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
    raise TypeError(f'Invalid object: {obj!r} for item deletion.')


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


