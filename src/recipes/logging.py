"""
Logging helpers.
"""


# std
import sys
import time
import atexit
import logging
import functools as ftl

# third-party
from loguru import logger

# relative
from . import pprint as pp
from .pprint.nrs import hms
from .decorators import Decorator
from .introspect.utils import (get_caller_frame, get_class_name,
                               get_class_that_defined_method, get_module_name)


# ---------------------------------------------------------------------------- #
def get_module_logger(depth=-1):
    """
    Create a logger for a module by calling this function from the module
    namespace.
    """
    return logging.getLogger(get_module_name(get_caller_frame(2), depth))


# ---------------------------------------------------------------------------- #


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


class LoggingMixin:
    class Logger:

        # use descriptor so we can access the logger via logger and cls().logger
        # Making this attribute a property also avoids pickling errors since
        # `logging.Logger` cannot be picked

        parent = None
        """This attribute allows you to optionally set the parent dynamically 
        which is sometimes useful"""

        # @staticmethod
        # def get_name(fname, parent):

        @staticmethod
        def add_parent(record, parent):
            """Prepend the class name to the function name in the log record."""
            # TODO: profile this function to see how much overhead you are adding
            fname = record['function']
            
            if fname.startswith('<cell line:'):
                # catch interactive use
                return 
                
            parent = get_class_that_defined_method(getattr(parent, fname))
            parent = '' if parent is None else parent.__name__
            record['function'] = f'{parent}.{fname}'

        def __get__(self, obj, kls=None):
            return logger.patch(
                ftl.partial(self.add_parent, parent=(kls or type(obj)))
            )

    logger = Logger()

# ---------------------------------------------------------------------------- #


class Catch(Decorator, LoggingMixin):
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


# alias
catch_and_log = catch = Catch


# ---------------------------------------------------------------------------- #
class TimeDeltaFormatter:
    """
    Helper for printing elapsed time in hms format eg: 00ʰ02ᵐ33.2ˢ
    """

    def __init__(self, timedelta, **kws):
        self.timedelta = timedelta
        self._kws = {**kws,
                     # defaults
                     **dict(precision=1,
                            unicode=True)}

    def __format__(self, spec):
        return hms(self.timedelta.total_seconds(), **self._kws)


class RepeatMessageHandler:
    """
    A loguru sink that filters repeat log messages and instead emits a 
    custom summary message.
    """

    _keys = (
        # 'file',
        'function', 'line',
        'message',
        'exception', 'extra'
    )
    #
    formatter = staticmethod(str.format)

    def __init__(self,
                 target=sys.stderr,
                 template=' ⤷ [Previous {n_messages} {n_repeats} in {t}]\n',
                 x='×',
                 xn=' {x}{n:d}',
                 buffer_size=12):

        self._target = target
        self._repeats = 0
        self._repeating = None
        self._template = str(template)
        self._x = str(x)
        self._xn = str(xn)
        self._memory = []
        self.buffer_size = int(buffer_size)
        self._timestamp = None

        atexit.register(self._write_repeats)

    def write(self, message):
        #
        args = (message.record['level'].no, message.record['file'].path,
                *(message.record[k] for k in self._keys))
        if args in self._memory:  # if self._previous_args == args:
            if self._repeats:  # multiple consecutive messages repeat
                idx = self._memory.index(args)
                if idx == 0:
                    self._repeats += 1
                    self._repeating = 0
                elif idx == (self._repeating + 1):
                    self._repeating = idx
                else:
                    # out of sequence, flush
                    self._flush()
            else:
                # drop all previous unique messages
                self._memory = self._memory[self._memory.index(args):]
                self._repeating = 0
                self._repeats += 1
                self._timestamp = time.time()

            return

        # add to buffered memory
        if self._repeats:
            # done repeating, write summary of repeats, flush memory
            self._flush()

        self._memory.append(args)
        if len(self._memory) > self.buffer_size:
            self._memory.pop(0)

        self._target.write(message)

    def _flush(self):
        self._write_repeats()

        self._memory = []
        self._repeats = 0
        self._repeating = None

    def _write_repeats(self):
        if self._repeats == 0:
            return

        # xn = #('' if self._repeats == 1 else
        xn = self._xn.format(x=self._x, n=self._repeats + 1)

        # {i} message{s|i} repeat{s|~i}{xn}
        i = len(self._memory) - 1
        n_messages = f'{f"{i + 1} " if (many := i > 1) else ""}message{"s" * many}'
        n_repeats = f'repeat{"s" * (not many)}{xn}'
        t = hms(time.time() - self._timestamp, precision=3, short=True, unicode=True)
        self._target.write(self.formatter(self._template, **locals()))
