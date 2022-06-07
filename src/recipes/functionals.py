"""
Common decorators and simple helpers for functional code patterns.
"""

# pylint: disable=invalid-name

import numbers
import warnings


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
    _action_ints = dict(enumerate(('ignore', 'warn', 'raise'), -1))

    def __init__(self, action='ignore', exception=Exception):
        self._actions = {
            'ignore':   noop,  # silently ignore
            'warn':     warnings.warn,  # emit warning
            'raise':    raises(exception)  # raise
        }
        self.action = self._resolve_action(action)

    def _resolve_action(self, action):
        if isinstance(action, numbers.Integral):
            return self._action_ints[action]

        if isinstance(action, str):
            return action.rstrip('s')

        raise TypeError(f'Invalid type for `action`: {action}')

    @property
    def action(self):
        """set message action"""
        return self._action

    @action.setter
    def action(self, val):
        self._action = self._resolve_action(val)
        self.emit = self._actions[self._action]

    def __call__(self, message):
        self.emit(message)
