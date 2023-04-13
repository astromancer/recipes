"""
Common decorators and simple helpers for functional code patterns.
"""

# pylint: disable=invalid-name

import functools as ftl


def noop(*_, **__):
    """Do nothing."""


def is_none(x):
    return x is None


def not_none(x):
    return x is not None


def echo0(_, *ignored_):
    """simply return the 0th parameter."""
    return _


def echo(*_):
    """Return all parameters unchanged."""
    return _


class always:
    """The object `obj` is returned on each call."""

    def __init__(self, obj):
        self.obj = obj

    def __call__(self, func, *args, **kws):
        return self.obj

    def __str__(self):
        return f'{self.__class__.__name__}({self.obj})'

    __repr__ = __str__


def negate(func=bool):
    """Negates a callable that returns boolean."""
    # TODO: double negate retrns original
    def wrapped(obj):
        return not func(obj)
    return wrapped


def raises(kind):
    """Raises an exception of type `kind`."""
    def _raises(msg):
        raise kind(msg)
    return _raises


def ignore_params(func):

    @ftl.wraps(func)
    def wrapper(*_, **__):
        return func()

    return wrapper


def ignore_returned(func):

    @ftl.wraps(func)
    def wrapper(*args, **kws):
        func(*args, **kws)

    return wrapper


ignore_returns = ignore_returned

