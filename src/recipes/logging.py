"""
Logging helpers.
"""


# std
import sys
import functools as ftl
import logging
from logging import StreamHandler
from logging.handlers import MemoryHandler
from contextlib import contextmanager

# third-party
from loguru import logger

# relative
from . import op, pprint as pp
from .decorators import Decorator
from .introspect.utils import get_caller_frame, get_module_name, get_class_name


def get_module_logger(depth=-1):
    """
    Create a logger for a module by calling this function from the module
    namespace.
    """
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


# @contextmanager
# def _at_level(logger, level):
#     olevel = logger.getEffectiveLevel()
#     logger.setLevel(level)
#     yield
#     logger.setLevel(olevel)


# class BraceString(str):
#     def __mod__(self, other):
#         return self.format(*other)

#     def __str__(self):
#         return self


# class StyleAdapter(logging.LoggerAdapter):

#     def __init__(self, logger, extra=None):
#         super().__init__(logger, extra)

#     def process(self, msg, kwargs):
#         if kwargs.pop('style', '%') == '{':  # optional
#             msg = BraceString(msg)
#         return msg, kwargs


class LoggingDescriptor:
    # use descriptor so we can access the logger via logger and cls().logger
    # Making this attribute a property also avoids pickling errors since
    # `logging.Logger` cannot be picked

    def __init__(self, namespace_depth=-1):
        self.namespace_depth = int(namespace_depth)

    def __get__(self, obj, kls=None):
        return logging.getLogger(self.get_log_name(kls or type(obj)))

    @ftl.lru_cache
    def get_log_name(self, kls):
        return get_class_name(kls, self.namespace_depth)


# class LoggingMixin:
#     """
#     Mixin class that exposes the `logger` attribute for the class which is an
#     instance of python's build in `logging.Logger`.  Allows for easy
#     customization of loggers on a class by class level.

#     Examples
#     --------
#     # in sample.py
#     >>> class Sample(LoggingMixin):
#             def __init__(self):
#                 logger.debug('Initializing')

#     >>> from sample import Sample
#     >>> logger.setLevel(logging.debug)
#     """
#     logger = LoggingDescriptor()


class LoggingMixin:
    class Logger:

        # use descriptor so we can access the logger via logger and cls().logger
        # Making this attribute a property also avoids pickling errors since
        # `logging.Logger` cannot be picked
        # parent = None

        @staticmethod
        def add_parent(record, parent):
            record['function'] = f'{parent}.{record["function"]}'

        def __get__(self, obj, kls=None):
            return logger.patch(
                ftl.partial(self.add_parent, parent=(kls or type(obj)).__name__)
            )

    logger = Logger()


class catch_and_log(Decorator, LoggingMixin):
    """
    Decorator that catches and logs errors instead of actively raising
    exceptions.
    """

    def __wrapper__(self, func, *args, **kws):
        try:
            return func(*args, **kws)
        except Exception:
            logger.exception('Caught exception in %s: ',
                             pp.caller(func, args, kws))


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


class RepeatMessageHandler(MemoryHandler):
    """
    Filter duplicate log messages.
    """
    # These attributres will be compared to determine equality between Record objects
    _attrs = ('msg', 'args', 'levelname')
    _get_record_atr = op.AttrGetter(*_attrs)

    def __init__(self, capacity=2,
                 flushLevel=logging.ERROR,
                 target=StreamHandler(sys.stdout),
                 flushOnClose=True):
        super().__init__(capacity, flushLevel, target, flushOnClose)

    def emit(self, record):
        record.repeats = 1
        if not self.buffer:
            return super().emit(record)

        duplicate = self.is_repeat(record)
        if not duplicate:
            self.flush()
            return super().emit(record)

        previous = self.buffer[-1]
        previous.repeats += 1

    def is_repeat(self, record):
        if not self.buffer:
            return False

        return (self._get_record_atr(record) == self._get_record_atr(self.buffer[-1]))

    def flush(self):
        if not self.buffer:
            return

        previous = self.buffer[-1]
        if previous.repeats > 1:
            previous.msg += ' [Message repeats ×{}]'.format(previous.repeats)

        super().flush()
