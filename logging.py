import functools
import inspect

from recipes.decor.base import DecoratorBase
from recipes.pprint import func2str
from recipes.oo import ClassProperty
from recipes.decor.memoize import memoize

import logging
from .pprint.progressbar import ProgressBarBase


from contextlib import contextmanager


@contextmanager
def all_logging_disabled(highest_level=logging.CRITICAL):
    # source: https://gist.github.com/simon-weber/7853144
    """
    A context manager that will prevent any logging messages
    triggered during the body from being processed.
    :param highest_level: the maximum logging level in use.
      This would only need to be changed if a custom level greater than CRITICAL
      is defined.
    """
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


# class LoggingMixin():
#     """
#     Mixin class that exposes the `logger` attribute for the class.
#     `logger` is an instance of logging.Logger
#     """
#
#     show_module_depth = 1  # eg:. foo.sub.Klass #for depth of 2
#
#     def get_name(self):
#         cls = type(self)
#         parents = cls.__module__.split('.')
#         parts = parents[:-self.show_module_depth - 1:-1] + [cls.__name__]
#         name = '.'.join(filter(None, parts))
#         return name
#
#     @property  # NOTE: making this a property avoids pickling error for the logger
#     def logger(self):
#         logger = logging.getLogger(self.name)
#         return logger

class LoggingMixin(object):
    """
    Mixin class that exposes the `logger` attribute for the class.
    `logger` is an instance of logging.Logger
    """
    _show_module_depth = 1  # eg:. foo.sub.Klass #for depth of 2

    # use `ClassProperty` decorator so we can access via cls.name and cls().name
    @ClassProperty
    @classmethod
    @memoize
    def log_name(cls):
        parts = cls.__module__.split('.') + [cls.__name__]
        parts = parts[-cls._show_module_depth - 1:]
        name = '.'.join(filter(None, parts))
        return name

    # making the logger a property avoids pickling error for inherited classes
    @ClassProperty
    @classmethod
    @memoize
    def logger(cls):
        return logging.getLogger(cls.log_name)


# ====================================================================================================
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


class ProgressLogger(ProgressBarBase):
    def __init__(self, precision=2, width=None, symbol='=', align='^',
                 sides='|', every='2.5%', logname='progress'):
        ProgressBarBase.__init__(self, precision, width, symbol, align, sides,
                                 every)
        self.name = logname

    def update(self, i=None):
        if i is None:
            i = self.inc()

        # don't update when unnecessary
        if not self.needs_update(i):
            return

        # always update when state given
        if i >= self.end:  # unless state beyond end
            return

        bar = self.get_bar(i)
        logger = logging.getLogger(self.name)
        logger.info('Progress: \n%s' % bar)

# class SyncedProgressLogger(ProgressLogger):
#     """can be used from multiple processes"""
#      def __init__(self, counter, precision=2, width=None, symbol='=', align='^', sides='|',
#                  logname='progress'):
#          ProgressLogger.__init__(self, precision, width, symbol, align, sides, logname)
#          self.counter = counter


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
