"""
Emit messages or warnings, or raise exceptions. Suppress output from overly
talkative functions.
"""

# std
import sys
import warnings
from io import StringIO
from enum import IntEnum

# third-party
from loguru import logger

# relative
from ..decorators import Decorator
from ..functionals import noop, raises


# ---------------------------------------------------------------------------- #

def is_exception(obj):
    return isinstance(obj, Exception) \
        or (type(obj) is type and issubclass(obj, Exception))


class Action(IntEnum):

    NONE = IGNORE = SILENT = 0   # silently ignore
    INFO = NOTE = 1
    DEBUG = 2
    WARN = WARNING = 3
    ERROR = RAISE = 4
    CUSTOM = 5

    @classmethod
    def _missing_(cls, action):

        if action is None:
            return cls.NONE

        if isinstance(action, str):
            action = action.upper().rstrip('S')
            return getattr(cls, action, None)

        # handle case: >>> Emit(ValueError('Bad dog!'))()
        if issubclass(action, Exception):
            # cls._emitters[]
            return cls.ERROR


class Emit:
    """
    Emit messages or warnings, or raise exceptions depending on requested action.
    Custom actions are also supported.
    """

    __slots__ = ('_action', 'emit')

    _emitters = {
        0: noop,             # silently ignore
        1: logger.info,
        2: logger.debug,
        3: warnings.warn,
        4: raises(Exception)
    }

    def __init__(self, action='ignore', exception=Exception):

        action = action or 'ignore'
        if action == 'raises':
            action = raises(exception)

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
    def action(self, obj):
        self._action, self.emit = self._resolve_action_emitter(obj)

    def _resolve_action_emitter(self, action):
        if is_exception(action):
            # handle case: >>> ValueError('Bad dog!') and ValueError
            return Action.ERROR, raises(action)

        if callable(action):
            # custom action (emit function)
            return (Action.CUSTOM, action)

        action = Action(action)
        return action, self._emitters[action]


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
