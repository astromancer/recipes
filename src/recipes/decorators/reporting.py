"""
Decorators for exposing function arguments / returns
"""

# std
import sys
import time
from io import StringIO

# third-party
from loguru import logger

# relative
from ..string import indent
from .base import Decorator


# ---------------------------------------------------------------------------- #

def format_print(string, *args, **kws):
    print(string.format(*args, **kws))


class trace(Decorator):
    """
    Decorator to print function call details - parameters names and effective 
    values optional arguments specify stuff to print before and after, as well 
    as specific pretty printing options to `formatter`.

    Examples
    --------

    >>> from recipes.decorators.trace import trace
    >>> @trace()
    ... def foo(a, b, c, **kw):
    ...     return a
    ...
    ... foo('aaa', 42, id, gr=8, bar=...)

    foo(a       = aaa,
        b       = 42,
        c       = <built-in function id>,
        kwargs  = {'bar': Ellipsis, 'gr': 8} )

    Out[43]: 'aaa'
    """

    def __init__(self,
                 pre='Tracing function call:\n >>> {signature}',
                 post='{func.__name__} returned result in {elapsed}:\n > {result}',
                 emit=logger.info,
                 formatter=None,
                 **options):

        from recipes import pprint as pp
        formatter = formatter or pp.caller  # avoid circular import

        self.pre = pre
        self.post = post
        self.options = options

        assert callable(emit)
        assert callable(formatter)
        self.emit = emit
        self.formatter = formatter

    # def _emit(self):

    def __wrapper__(self, func, *args, **kws):

        try:
            if '{signature}' in self.pre:
                signature = indent(self.formatter(func, args, kws,
                                                  **self.options))
            self.emit(self.pre, **locals())
        except Exception as err:
            logger.exception(
                '{} while printing the trace info for func call for {}:\n{}\n'
                'Continuing program execution: The function will now '
                'be called.', type(err).__name__, func, err
            )

        start = time.time()
        result = func(*args, **kws)
        elapsed = time.time() - start

        try:
            if self.post is not None:
                self.emit(self.post, **locals())
        except Exception as err:
            logger.exception(
                '{} while printing the trace info for call to {}:\n{}\n'
                'Continuing program execution: The result will now '
                'be returned.', type(err).__name__, func, err
            )

        # sys.stdout.flush()
        return result


# alias
args = params = Trace = trace


class suppress(Decorator):
    """Suppress all print statements during a function call"""

    def __wrapper__(self, func, *args, **kws):
        # shadow stdout temporarily
        actualstdout = sys.stdout
        sys.stdout = StringIO()

        # call the actual function
        result = func(*args, **kws)

        # restore stdout
        sys.stdout = actualstdout
        sys.stdout.flush()

        return result
