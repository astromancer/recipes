"""
Logging helpers.
"""


# std
import logging
import functools as ftl
from contextlib import contextmanager

# third-party
from loguru import logger

# relative
from . import pprint as pp
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
        
        parent = None
        """This attribute allows you to optionally set the parent dynamically 
        which is sometimes useful"""
        
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
            logger.exception('Caught exception in {:s}: ',
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
