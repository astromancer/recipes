"""
Common decorators and simple helpers for functional code patterns.
"""

# pylint: disable=invalid-name

# std
import numbers
import warnings

# third-party
from loguru import logger


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
    _action_ints = dict(enumerate(('ignore', 'info', 'warn', 'raise'), -1))
    _equivalence = {'error': 'raise'}

    _actions = {
        'ignore':   noop,  # silently ignore
        'info':     logger.info,
        'warn':     warnings.warn,  # emit warning
        'raise':    raises(Exception)  # raise
    }

    def __init__(self, action='ignore', exception=Exception):
        
        if exception is not Exception:
            self._actions['raise'] = raises(exception)
            
        self.action = action

    def _resolve_action(self, action):
        if action is None:
            return 'ignore'
        
        if isinstance(action, numbers.Integral):
            return self._action_ints[action]

        if isinstance(action, str):
            action = action.rstrip('s')
            return self._equivalence.get(action, action)

        raise TypeError(f'Invalid type for `action`: {action}')

    @property
    def action(self):
        """set message action"""
        return self._action

    @action.setter
    def action(self, val):
        if callable(val):
            # custom action (emit function)
            self._action = 'custom'
            self.emit = val
        else:
            self._action = self._resolve_action(val)
            self.emit = self._actions[self._action]

    def __call__(self, message, *args, **kws):
        self.emit(message, *args, **kws)
