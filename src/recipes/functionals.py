"""
Common decorators and simple helpers for functional code patterns.
"""

# pylint: disable=invalid-name

import warnings


def noop(*_, **__):
    """Do nothing."""


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
    """Negates a callable that return boolean."""
    def wrapped(obj):
        return not func(obj)
    return wrapped


def raises(kind):
    """raises an exception of type `kind`."""
    def _raises(msg):
        raise kind(msg)
    return _raises


class Emit:
    """
    Helper class for emitting messages of variable severity.
    """

    def __init__(self, severity=-1, exception=Exception):
        self._actions = {-1: noop,              # silently ignore invalid types
                         0: warnings.warn,      # emit warning
                         1: raises(exception)}  # raise
        self.severity = severity

    @property
    def severity(self):
        """set message severity"""
        return self._severity

    @severity.setter
    def severity(self, val):
        self._severity = int(val)
        self.emit = self._actions[self._severity]

    def __call__(self, message):
        self.emit(message)
