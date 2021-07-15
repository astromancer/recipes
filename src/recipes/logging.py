
# std libs
import logging
import functools as ftl
from contextlib import contextmanager

# relative libs
from .decor.base import DecoratorBase
from .introspect.utils import get_caller_frame, get_module_name, get_class_name


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


# @contextmanager
# def _at_level(logger, level):
#     olevel = logger.getEffectiveLevel()
#     logger.setLevel(level)
#     yield
#     logger.setLevel(olevel)


class LoggingDescriptor:
    # use descriptor so we can access the logger via cls.logger and cls().logger
    # Making this attribute a property also avoids pickling errors since
    # `logging.Logger` cannot be picked

    def __init__(self, namespace_depth=1):
        self.namespace_depth = int(namespace_depth)

    def __get__(self, obj, kls=None):
        return logging.getLogger(self.get_log_name(kls or type(obj)))

    @ftl.lru_cache
    def get_log_name(self, kls):
        return get_class_name(kls, self.namespace_depth)


class LoggingMixin:
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
    logger = LoggingDescriptor()


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
            return self.func(*args, **kws)
        except Exception as err:
            self.logger.exception('%s' % str(args))


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
