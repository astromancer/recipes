"""
Ensure container type continuity, coerce objects to given container type and
wrap unsized objects.
"""

# std
import typing
from collections import abc

# relative
import builtins
from ..functionals import negate
from ..decorators import Decorator


# ---------------------------------------------------------------------------- #
# Null

def not_null(obj, except_=('',)):
    #      scalar                                                array-like
    return bool(((obj in except_) or obj) if is_scalar(obj) else len(obj))


# alias
notnull = not_null
isnull = is_null = negate(not_null)


# ---------------------------------------------------------------------------- #
# Scalars (unsized)
SCALARS = (str, bytes)


def is_scalar(obj, accept=SCALARS):
    return not isinstance(obj, abc.Sized) or isinstance(obj, accept)


def duplicate_if_scalar(obj, n=2, scalars=SCALARS, ensure=builtins.list,
                        emit=ValueError):
    """
    Ensure object size or duplicate if necessary.

    Parameters
    ----------
    obj : number or array-like

    Returns
    -------

    """

    if is_scalar(obj, scalars):
        return ensure([obj] * n)

    # Sized object
    size = len(obj)
    if size == 1:
        return list(obj) * n

    #
    from recipes.flow.emit import Emit

    emit = Emit(emit)
    if size == 0:
        emit(f'Cannot duplicate empty {type(obj)}.')
        return ensure([obj] * n)

    if (size != n):
        emit(f'Input object of type {type(obj)} has incorrect size: {size}. '
             'Expected either a scalar type object, or a Container with length '
             f'in {{1, {n} }}.')

    return ensure(obj)


# ---------------------------------------------------------------------------- #
_str_from_iter = ((str, ''.join), )


class TypeContinuity(Decorator):
    """
    Function decorator for ensuring type input output continuity and coercion.
    """

    def __init__(self, ensure=_str_from_iter, coerce=None, disallow=()):

        self.coerce = coerce
        self.ensure = dict(ensure)
        self.disallowed = tuple(disallow)  # NOTE! ensure.tuple NOT builtin

        if coerce:
            assert isinstance(coerce, type)

    def __wrapper__(self, func, items, *args, **kws):

        if isinstance(items, self.disallowed):
            raise TypeError(
                f'Objects of type {type(items).__name__} are not accepted by '
                f'the function {func.__name__}.'
            )

        # get output type
        if not (kls := self.ensure.get(all)):
            kls = self.ensure.get((kls := type(items)), kls)

        # call function
        answer = func(items, *args, **kws)

        if self.coerce:
            answer = map(self.coerce, answer)

        return kls(answer)


# ---------------------------------------------------------------------------- #

class Ensure:
    """
    Function decorator for ensuring type input output continuity and coercion.
    """

    def __init__(self, wrapper, coerce=None,
                 is_scalar=builtins.str, not_scalar=abc.Iterable):

        self.coerce = coerce
        self.scalars = is_scalar
        self.not_scalars = not_scalar

        if coerce:
            assert isinstance(coerce, type)

        if wrapper is None or isinstance(wrapper, type):
            # None => input object will determine output object
            self.wrapper = wrapper

        elif isinstance(wrapper, typing._GenericAlias):
            self.wrapper = getattr(builtins, wrapper._name.lower())
            self.coerce, = typing.get_args(wrapper)

        else:
            raise TypeError(f'Invalid wrapper type {wrapper}.')

    def __call__(self, obj, coerce=None):
        """
        Wrap unsized objects and coerce to a given container type and / or item
        type.
        """

        # item type
        coerce = coerce or self.coerce

        # container type
        wrapper = self.wrapper or type(obj)

        # ensure iterable
        itr = iterable(obj, self.scalars, self.not_scalars)

        # wrap
        return wrapper(map(coerce, itr) if coerce else itr)


# alias
EnsureWrapped = Ensure

# ---------------------------------------------------------------------------- #
# overwrite builtins :o

list = Ensure(builtins.list)  # noqa: F811
tuple = Ensure(builtins.tuple)
set = Ensure(builtins.set)


# ---------------------------------------------------------------------------- #

def ensure(wrapper, obj, coerce=None, scalars=SCALARS):
    return wrapped(obj, wrapper, coerce, scalars)


def wrapped(obj, to=builtins.list, coerce=None, scalars=SCALARS):
    itr = iterable(obj, scalars)
    return to(map(coerce, itr) if coerce else itr)


def iterable(obj, scalars=SCALARS, not_scalar=abc.Iterable):
    if obj is None:
        return

    if isinstance(obj, not_scalar) and not isinstance(obj, scalars):
        yield from obj
        return

    yield obj
