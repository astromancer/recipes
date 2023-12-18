"""
Logging helpers.
"""


# std
import sys
import time
import atexit
import numbers
import functools as ftl
import contextlib as ctx

# third-party
from loguru import logger

# relative
from .pprint.nrs import hms
from .introspect.utils import get_defining_class


# ---------------------------------------------------------------------------- #
@ctx.contextmanager
def disabled(*libraries):
    """
    Temporarily disable logging for `libraries`.
    """

    for lib in libraries:
        logger.disable(lib)

    try:
        yield

    finally:
        # re-enable
        for lib in libraries:
            logger.enable(lib)


# ---------------------------------------------------------------------------- #
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

            if fname.startswith(('<cell line:', '<module>')):
                # catch interactive use
                return

            if method := getattr(parent, fname, None):
                parent = get_defining_class(method)
                parent = '' if parent is None else parent.__name__

            record['function'] = f'{parent}.{fname}'

        def __get__(self, obj, kls=None):
            return logger.patch(
                ftl.partial(self.add_parent, parent=(kls or type(obj)))
            )

    logger = Logger()


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


# ---------------------------------------------------------------------------- #

def _resolve_indent(indent, extra=''):

    if indent in (False, None):
        return ''

    if isinstance(indent, str):
        return indent

    if isinstance(indent, numbers.Integral):
        return ' ' * indent

    raise TypeError(
        f'Invalid object of type {type(indent).__name__!r} for `indent`: {indent!r}.'
    )


def resolve_indent(indent, extra=''):
    return _resolve_indent(indent) + _resolve_indent(extra)


class ParagraphWrapper:

    def __init__(self, target=sys.stderr, width=100, indent=4):
        self.target = target
        self.width = int(width)
        self.indent = resolve_indent(indent)
        # self.newline = f'\n{self.indent}'

    def resolve_indent(self, indent, extra=''):

        if indent is True:
            return self.indent

        return resolve_indent(indent)

    def write(self, message):

        # resolve indent
        indent = False
        if (record := getattr(message, 'record', None)):
            kws = record['extra']
            if indent := kws.pop('indent', False):
                indent = self.resolve_indent(indent, **kws)
                message = message[:-1].replace('\n', f'\n{indent}') + '\n'

        # send to target stream
        self.target.write(message)


class RepeatMessageHandler:
    """
    A loguru sink that filters repeat log messages and instead emits a 
    custom summary message.
    """

    # Message attributes to use as cache key
    _keys = ('function', 'line', 'message', 'exception', 'extra')  # 'file'

    #
    formatter = staticmethod(str.format)

    def __init__(self, target=sys.stderr, buffer_size=12,
                 template=' ⤷ [Previous {n_messages} {n_repeats} in {t}]\n',
                 x='×', xn=' {x}{n:d}'):

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
