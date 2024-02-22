# std
import typing
from collections import abc

# relative
import builtins


# ---------------------------------------------------------------------------- #

class Ensure:
    """
    Coerce objects to given container type
    """
    def __init__(self, wrapper, is_scalar=builtins.str, not_scalar=abc.Iterable):

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
        itr = iterable(obj)
        return self.wrapper(map(coerce, itr) if coerce else itr)


# alias
EnsureWrapped = Ensure


# ---------------------------------------------------------------------------- #

def wrapped(obj, to=builtins.list, coerce=None, scalars=builtins.str):
    itr = iterable(obj, scalars)
    return to(map(coerce, itr) if coerce else itr)


def iterable(obj, scalars=builtins.str, not_scalar=abc.Iterable):
    if obj is None:
        return

    if isinstance(obj, not_scalar) and not isinstance(obj, scalars):
        yield from obj
        return

    yield obj


# ---------------------------------------------------------------------------- #

def list(obj, coerce=None):
    return wrapped(obj, builtins.list, coerce)


def ensure(wrapper, obj, coerce=None, scalars=builtins.str):
    return wrapped(obj, wrapper, coerce, scalars)


# ---------------------------------------------------------------------------- #
# overwrite builtins :o

list = Ensure(builtins.list)  # noqa: F811
tuple = Ensure(builtins.tuple)
set = Ensure(builtins.set)
