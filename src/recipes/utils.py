"""Commom utility functions."""

# std
import numbers
from collections import abc


def duplicate_if_scalar(a, n=2, raises=True):  # TODO: severity
    """
    Ensure object size or duplicate if necessary.

    Parameters
    ----------
    a : number or array-like

    Returns
    -------

    """
    # if isinstance(a, numbers.Number):
    #     return [a] * n

    if not isinstance(a, abc.Sized):
        return [a] * n

    size = len(a)
    if size == 0:
        return [a] * n

    if size == 1:
        return list(a) * n

    # if np.size(a) == 1:
    #     # preserves duck type arrays
    #     return np.asanyarray([a] * n).squeeze()

    if (size != n) and raises:
        raise ValueError(f'Input object of type {type(a)} has incorrect size. '
                         f'Expected either a scalar type object, or a Container'
                         f' with length in {{1, {n}}}.')

    return a


def _integers_from_slices(slices, n):
    integers = set()
    for s in slices:
        integers |= set(range(*s.indices(n)))
    return integers


def ensure_list(obj):
    if isinstance(obj, abc.Iterator):
        return list(obj)
    return duplicate_if_scalar(obj, 1, raises=False)


def _delete(container, indices):
    from recipes.dicts import groupby

    n = len(container)

    # ensure list
    indices = groupby(ensure_list(indices), type)
    integers = _integers_from_slices(indices.pop(slice, ()), n)
    for kls, idx in indices.items():
        if not issubclass(kls, numbers.Integral):
            raise TypeError(f'Invalid index type {kls}.')
        integers = integers.union(idx)

    # remove duplicate indices accounting for wrapping
    i = prev = -1
    for i in sorted({(i + n) % n for i in integers}):
        yield container[prev + 1:i]
        prev = i

    if i < n - 1:
        yield container[i + 1:]
