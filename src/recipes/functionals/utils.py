"""
Functional helpers.
"""

# ---------------------------------------------------------------------------- #
# Canonical do nothing function


def noop(*_, **__):
    """Do nothing."""


# ---------------------------------------------------------------------------- #
# Functions that simply return the input parameter(s) unmodified

def echo0(first, *_, **__):
    """simply return the 0th parameter."""
    return first


def echo(*_):
    """Return all parameters unchanged."""
    return _


# ---------------------------------------------------------------------------- #
# Decorators for restricting operations on selected function parameters only
# TODO: proper decorator FutureIndex(0)

def on_nth(func, n):  # apply.nth_positional(func, 1)(*args)

    def wrapped(obj):
        return func(obj[n])

    return wrapped


def on_zeroth(func):
    return on_nth(func, 0)


def on_first(func):
    return on_nth(func, 1)


#
on_1st = on_first
on_0th = on_zeroth

# ---------------------------------------------------------------------------- #
# Null conditionals


def is_none(x):
    return x is None


def not_none(x):
    return x is not None


# ---------------------------------------------------------------------------- #
# Negating truth tests

def negate(func=bool):
    """Negates a callable that returns boolean."""

    # TODO: double negate returns original
    def wrapped(obj):
        return not func(obj)

    return wrapped


# ---------------------------------------------------------------------------- #
# Raising future exceptions

def raises(exception):
    """Raises an exception of type `exception`."""

    assert issubclass(exception, BaseException)

    def _raises(msg, *args, **kws):
        raise exception(msg.format(*args, **kws))

    return _raises


# ---------------------------------------------------------------------------- #
# Callable that always return the same object, ignoring all parameters

class always:
    """A callable that always returns the same value."""

    def __init__(self, obj):
        self.obj = obj

    def __call__(self, func, *args, **kws):
        return self.obj

    def __str__(self):
        return f'{self.__class__.__name__}({self.obj})'

    __repr__ = __str__
