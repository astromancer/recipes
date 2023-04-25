"""
Some miscellaneous utility functions.
"""

# std
import typing
import numbers
import builtins
from collections import abc

# relative
from .functionals import negate


def is_null(obj):
    if (obj is None) or (obj is False):
        return True

    try:
        return not bool(obj)
    except ValueError as err:
        if str(err).startswith('The truth value of an array with more than one '
                               'element is ambiguous.'):
            return obj.size

        raise err from None


not_null = notnull = negate(is_null)


# alias
isnull = is_null


def is_scalar(obj, exceptions=(str, )):
    return not isinstance(obj, abc.Sized) or isinstance(obj, exceptions)


def duplicate_if_scalar(obj, n=2, raises=True, exceptions=(str,)):  # TODO: action
    """
    Ensure object size or duplicate if necessary.

    Parameters
    ----------
    a : number or array-like

    Returns
    -------

    """

    if is_scalar(obj, exceptions):
        return [obj] * n

    size = len(obj)
    if size == 0:
        if raises:
            raise ValueError(f'Cannot duplicate empty {type(obj)}.')
        return [obj] * n

    if size == 1:
        return list(obj) * n

    if (size != n) and raises:
        raise ValueError(
            f'Input object of type {type(obj)} has incorrect size. Expected '
            f'either a scalar type object, or a Container with length in {{1, '
            f'{n}}}.'
        )

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
    from recipes.dicts import groupby

    # ensure list
    indices = groupby(ensure_list(indices), type)
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

# ---------------------------------------------------------------------------- #


class EnsureWrapped:
    def __init__(self, wrapper, is_scalar=str, not_scalar=abc.Iterable):

        if isinstance(wrapper, type):
            self.wrapper = wrapper
            self.coerce = None
        elif isinstance(wrapper, typing._GenericAlias):
            self.wrapper = getattr(builtins, wrapper._name.lower())
            self.coerce, = typing.get_args(wrapper)
        else:
            raise TypeError(f'Invalid wrapper type {wrapper}.')

        self.scalars = is_scalar
        self.not_scalars = not_scalar

    def __call__(self, obj, coerce=None):
        coerce = coerce or self.coerce
        itr = _ensure_wrapped(obj)
        return self.wrapper(map(coerce, itr) if coerce else itr)


def _ensure_wrapped(obj, scalars=str, not_scalar=abc.Iterable):
    if obj is None:
        return

    if isinstance(obj, not_scalar) and not isinstance(obj, scalars):
        yield from obj
        return

    yield obj


def ensure_wrapped(obj, to=list, coerce=None, scalars=str):
    itr = _ensure_wrapped(obj, scalars)
    return to(map(coerce, itr) if coerce else itr)


def ensure_list(obj, coerce=None):
    return ensure_wrapped(obj, list, coerce)
