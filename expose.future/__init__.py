"""
Decorators for exposing function arguments / returns
"""

import functools

from .utils import get_func_repr
from .. import DecoratorBase

# ====================================================================================================
class printWrap(DecoratorBase):
    """
    Decorator that pre- and post prints info
    """
    def setup(self, pre='', post='', **kws):
        self.pre = pre
        self.post = post

    def make_wrapper(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            print(self.pre)
            r = func(*args, **kw)
            print(self.post)
            return r
        return wrapper


# ====================================================================================================
class args(printWrap):
    """
    Decorator to print function call details - parameters names and effective values
    optional arguments specify stuff to print before and after, as well as verbosity level.

    Example
    -------
    In [43]: @expose.args()
        ...: def foo(a, b, c, **kw):
        ...:     return a
        ...:
        ...: foo('aaa', 42, id, gr=8, bar=...)

    prints:
    foo( a       = aaa,
         b       = 42,
         c       = <built-in function id>,
         kwargs  = {'bar': Ellipsis, 'gr': 8} )

    Out[43]: 'aaa'
    """
    def setup(self, pre='', post='\n', verbosity=1):
        super().setup(pre, post)
        self.verbosity = verbosity

    def make_wrapper(self, func):
        @functools.wraps(func)
        def wrapper(*fargs, **fkw):
            pre = '\n'.join((self.pre,
                             get_func_repr(func, fargs, fkw, self.verbosity)))
            return printWrap(pre, self.post)(func)(*fargs, **fkw)
        return wrapper


class returns(DecoratorBase):
    '''Decorator to print function return details'''
    def make_wrapper(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            r = func(*args, **kw)
            print('%s\nreturn %s' % (func.__name__, r))
            return r
        return wrapper
