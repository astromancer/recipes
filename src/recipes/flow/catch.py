
# std
import warnings
from collections import abc

# relative
from ..decorators.base import Decorator
from .emit import Emit


# ---------------------------------------------------------------------------- #
class Catch(Decorator):
    """
    Catch an exception and log it, or raise an alternate exception.
    """

    _default_message_template = \
        'Caught the following {err.__class__.__name__}: {err}'

    def __init__(self, *,
                 exceptions=Exception, action='warn',
                 alternate=None, message=None,
                 raise_from=True, warn=None,
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


class CatchWarnings(Catch):

    def __init__(self, *, exceptions=Warning, action='error',
                 message='', raise_from=True, **kws):
        super().__init__(exceptions=exceptions, action=action,
                         message=message, raise_from=raise_from, **kws)

    def __wrapper__(self, func, *args, **kws):
        with warnings.catch_warnings():
            warnings.filterwarnings(
                self.emit.action, self.message, self.exceptions)
            return super().__wrapper__(func, *args, **kws)


class Fallback(Decorator):
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
