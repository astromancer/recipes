"""
Some common decorators.
"""

# std
import numbers
import warnings
from collections import abc
from textwrap import dedent

# third-party
from loguru import logger

# relative
from ..functionals import noop, raises
from ..decorators.base import Decorator


# ---------------------------------------------------------------------------- #
# pylint: disable=invalid-name


# ---------------------------------------------------------------------------- #
class Emit:
    """
    Helper class for emitting messages of variable severity.
    """

    _action_ints = dict(enumerate(('ignore', 'info', 'warn', 'raise'), -1))
    _equivalence = {'error': 'raise'}

    _actions = {
        'ignore':   noop,               # silently ignore
        'info':     logger.info,
        'warn':     warnings.warn,      # emit warning
        'raise':    raises(Exception)   # raise
    }

    def __init__(self, action='ignore', exception=Exception):

        if exception is not None:
            self._actions['raise'] = raises(exception)

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
            return self._equivalence.get(action, action)

        raise TypeError(f'Invalid type for `action`: {action}')


# ---------------------------------------------------------------------------- #
class catch(Decorator):
    """
    Catch an exception and log it, or raise an alternate exception.
    """

    _default_message_template = \
        'Caught the following {err.__class__.__name__}: {err}'

    def __init__(self, *, exceptions=Exception, action='warn',
                 alternate=None, message=None, raise_from=True, warn=None,
                 **kws):

        if isinstance(warn, str):
            action = 'warn'
            message = warn
        elif isinstance(warn, Warning):
            action = 'warn'
            message = warn.args[0]
        elif warn:
            raise TypeError(f'Invalid type {type(warn)} for parameter `warn`.')

        self.exceptions = exceptions
        self.emit = Emit(action, alternate)
        self.alternate = alternate
        self.template = str(message or self._default_message_template)
        self.raise_from = bool(raise_from)
        self.kws = dict(kws)

    def __wrapper__(self, func, *args, **kws):
        try:
            return func(*args, **kws)

        except self.exceptions as err:
            self.__exit__(type(err), err, ())

    def message(self, _func=None, args=(), kws=None, err=None):
        """format the message template"""
        return self.template.format(*(args or ()),
                                    **{**self.kws, **(kws or {})},
                                    err=err)

    def __enter__(self):
        pass

    def __exit__(self, exc_type, err, exc_tb):

        if not err:
            return

        if self.emit.action != 'raise':
            self.emit(self.message(None, None, None, err))
            return True  # this suppresses the exception

        if self.alternate is None:
            raise

        if not self.raise_from:
            err = None

        raise self.alternate from err


class catch_warnings(catch):

    def __init__(self, *, exceptions=Warning, action='error',
                 message='', raise_from=True, **kws):
        super().__init__(exceptions=exceptions, action=action,
                         message=message, raise_from=raise_from, **kws)

    def __wrapper__(self, func, *args, **kws):
        with warnings.catch_warnings():
            warnings.filterwarnings(self.emit.action, self.message, self.exceptions)
            return super().__wrapper__(func, *args, **kws)


# ---------------------------------------------------------------------------- #

class fallback(Decorator):
    """Return the fallback value in case of exception."""

    def __init__(self, value=None, exceptions=(Exception, ), warns=False):
        self.fallback = value
        if (not isinstance(exceptions, abc.Collection)
                and issubclass(exceptions, BaseException)):
            exceptions = (exceptions,)
        self.excepts = tuple(exceptions)
        self.emit = Emit(warns - 1)

    def __wrapper__(self, func, *args, **kws):
        try:
            return func(*args, **kws)
        except self.excepts as err:
            self.emit(err)
            return self.fallback


class post:
    """Run `func(*args, **kws) after running the wrapped function."""

    def __init__(self, func: abc.Callable, *args, **kws):
        assert callable(func)
        self.post = func
        self.post_args = args
        self.post_kws = kws

    def __wrapper__(self, func, *args, **kws):
        result = func(*args, **kws)
        try:
            self.post(*self.post_args, **self.post_kws)
        except Exception as err:
            from recipes import pprint as pp

            warnings.warn(dedent(f'''
                Exception during post function execution:
                {pp.caller(self.post, self.post_args, self.post_kws)}
                {err}''')
                          )
        return result


class pre:
    """Run `func(*args, **kws) after running the wrapped function."""

    def __init__(self, func, *args, **kws):
        assert callable(func)
        self.pre = func
        self.pre_args = args
        self.pre_kws = kws

    def __wrapper__(self, func, *args, **kws):
        try:
            self.pre(*self.pre_args, **self.pre_kws)
        except Exception as err:
            from recipes import pprint as pp

            warnings.warn(dedent(f'''
                Exception during pre function execution:
                {pp.caller(self.pre, self.pre_args, self.pre_kws)}
                {err}''')
                          )
        return func(*args, **kws)
