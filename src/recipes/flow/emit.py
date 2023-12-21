"""
Emit messages or warnings, or raise exceptions. Suppress output from overly
talkative functions.
"""

# std
import sys
import numbers
import warnings
from io import StringIO

# third-party
from loguru import logger

# relative
from ..decorators import Decorator
from ..functionals import noop, raises


# ---------------------------------------------------------------------------- #
class Emit:
    """
    Emit messages or warnings, or raise exceptions depending on requested action.
    Custom actions are also supported.
    """

    __slots__ = ('_action', 'emit')

    _action_ints = dict(enumerate(('ignore', 'info', 'warn', 'raise'), -1))
    _actions = {
        'ignore':   noop,               # silently ignore
        'info':     logger.info,
        'debug':    logger.debug,
        'warn':     warnings.warn,      # emit warning
        'raise':    raises(Exception)   # raise
    }
    _action_synonyms = {
        'error':  'raise',
        'silent': 'ignore'
    }

    def __init__(self, action='ignore', exception=Exception):

        action = action or 'ignore'

        if isinstance(action, Exception):
            exception = action
            action = 'raises'

        if exception is not None:
            self._actions['raise'] = raises(exception)

        # resolve action
        self.action = action

    def __call__(self, message, *args, **kws):
        self.emit(message, *args, **kws)

    def __enter__(self):
        return self

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

    def _resolve_action(self, action):
        if action is None:
            return 'ignore'

        if isinstance(action, numbers.Integral):
            return self._action_ints[action]

        if isinstance(action, str):
            action = action.rstrip('s')
            return self._action_synonyms.get(action, action)

        raise TypeError(f'Invalid type for `action`: {action}')


class Suppress(Decorator):
    """Suppress all print statements during a function call"""

    def __wrapper__(self, func, *args, **kws):
        # shadow stdout temporarily
        actualstdout = sys.stdout
        sys.stdout = StringIO()

        # call the actual function
        result = func(*args, **kws)

        # restore stdout
        sys.stdout = actualstdout
        sys.stdout.flush()

        return result


# alias
suppress = Suppress
