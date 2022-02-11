"""
Some common decorators.
"""

# std
import warnings
from collections import abc
from textwrap import dedent

# relative
from .. import pprint as pp
from ..functionals import Emit
from . import Decorator

# # pylint: disable=invalid-name

# def raises(exception):
#     """raises an exception of type `exception`."""
#     def _raises(msg):
#         raise exception(msg)
#     return _raises


class catch(Decorator):
    """
    Catch an exception and log it, or raise an alternate exception.
    """
    def __init__(self, exceptions=Exception, action=-1, alternate=Exception,
                 message='Caught the following {err.__class__.__name__}: {err}'
                 ):
        self.exceptions = exceptions
        self.emit = Emit(action, alternate)
        self.template = str(message)

    def __wrapper__(self, func, *args, **kws):
        try:
            return func(*args, **kws)
        except self.exceptions as err:
            self.emit(self.message(func, args, kws, err))

    def message(self, _func, args, kws,  err):
        """format the message template"""
        return self.template.format(*args, **kws, err=err)


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


class post(Decorator):
    """Run `func(*args, **kws) after running the wrapped function."""

    def __init__(self, func, *args, **kws):
        assert callable(func)
        self.post = func
        self.post_args = args
        self.post_kws = kws

    def __wrapper__(self, func, *args, **kws):
        result = func(*args, **kws)
        try:
            self.post(*self.post_args, **self.post_kws)
        except Exception as err:
            warnings.warn(dedent(f'''
                Exception during post function execution:
                {pp.caller(self.post, self.post_args, self.post_kws)}
                {err}''')
                          )
        return result


class pre(Decorator):
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
            warnings.warn(dedent(f'''
                Exception during pre function execution:
                {pp.caller(self.pre, self.pre_args, self.pre_kws)}
                {err}''')
                          )
        return func(*args, **kws)
