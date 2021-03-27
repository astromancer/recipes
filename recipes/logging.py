# std libs
import logging
import functools
from contextlib import contextmanager

# local libs
from .oo import ClassProperty
from .decor.base import DecoratorBase
from .introspect.utils import get_caller_frame, get_module_name
# from recipes.caches import cached

# relative libs

def get_module_logger(depth=-1):
    return logging.getLogger(get_module_name(get_caller_frame(2), depth))


@contextmanager
def all_logging_disabled(highest_level=logging.CRITICAL):
    """
    A context manager that will prevent any logging messages triggered during
    the body from being processed.
    
    Parameters
    ----------
    highest_level: int
        The maximum logging level in use. This would only need to be changed if
        a custom level greater than CRITICAL is defined.
    """
    # source: https://gist.github.com/simon-weber/7853144
    # two kind-of hacks here:
    #    * can't get the highest logging level in effect => delegate to the user
    #    * can't get the current module-level override => use an undocumented
    #       (but non-private!) interface

    previous_level = logging.root.manager.disable
    logging.disable(highest_level)

    try:
        yield
    finally:
        logging.disable(previous_level)


# FIXME: doesn't work! EG: 
# from graphing.sliders import TripleSliders
# TripleSliders.logger.setLevel(logging.DEBUG)
# TripleSliders.logger.debug('nothing')  # no message :'(

class LoggingMixin(object):
    """
    Mixin class that exposes the `logger` attribute for the class which is an
    instance of python's build in `logging.Logger`.  Allows for easy
    customization of loggers on a class by class level.

    Examples
    --------
    # in sample.py
    >>> class Sample(LoggingMixin):
            def __init__(self):
                self.logger.debug('Initializing')
    
    >>> from sample import Sample
    >>> Sample.logger.setLevel(logging.debug)
    """
    _show_module_depth = 1  # eg:. foo.sub.Klass #for depth of 2

    # use `ClassProperty` decorator so we can access via cls.name and cls().name
    # Making this attribute a property also avoids pickling errors since
    # `logging.Logger` cannot be picked
    @ClassProperty
    @classmethod
    # @memoize
    def log_name(cls):
        parts = cls.__module__.split('.') + [cls.__name__]
        parts = parts[-cls._show_module_depth - 1:]
        name = '.'.join(filter(None, parts))
        return name

    # making the logger a property avoids pickling error for inherited classes
    @ClassProperty
    @classmethod
    # @memoize
    def logger(cls):
        return logging.getLogger(cls.log_name)


class catch_and_log(DecoratorBase, LoggingMixin):
    """
    Decorator that catches and logs errors instead of actively raising.
    """

    # basename = 'log'        #base name of the log - to be set at module level

    def __init__(self, func):
        super().__init__(func)

        # NOTE: partial functions don't have the __name__, __module__ attributes!
        # retrieve the deepest func attribute -- the original func
        while isinstance(func, functools.partial):
            func = func.func
        self.__module__ = func.__module__
        self.__name__ = 'partial(%s)' % func.__name__

    def __call__(self, *args, **kws):
        try:
            result = self.func(*args, **kws)
            return result
        except Exception as err:
            self.logger.exception(
                '%s' % str(args))  # logs full trace by default


# class MultilineIndenter(logging.LoggerAdapter):
# """
# This example adapter expects the passed in dict-like object to have a
# 'connid' key, whose value in brackets is prepended to the log message.
# """
# def process(self, msg, kwargs):
# msg = msg.replace('\n', indent + '\n')
# return msg, kwargs

# logger = MultilineIndenter(logger, {})

# to get logging level:
# debug = logging.getLogger().isEnabledFor(logging.DEBUG)
