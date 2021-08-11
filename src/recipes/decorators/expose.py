"""
Decorators for exposing function arguments / returns
"""

from io import StringIO
import sys
import functools as ftl  # , pprint
from .. import pprint as pp

from .base import Decorator


def get_inner(func, args=(), kws=None):
    """"""
    kws = kws or {}
    while isinstance(func, ftl.partial):
        kws.update(func.keywords)
        args += func.args
        func = func.func
    return func, args, kws


class show(Decorator):
    """
    Decorator to print function call details - parameters names and effective 
    values optional arguments specify stuff to print before and after, as well 
    as specific pretty printing options to `show_func`.

    Examples
    --------

    >>> from recipes.decorators import expose
    >>> @expose.show()
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

    def __init__(self, pre='', post='', **options):
        self.pre = pre
        self.post = post
        self.options = options

    def wrapper(self, *args, **kws):
        print(self.pre)
        print(pp.caller(self.func, args, kws, **self.options))

        result = self.func(*args, **kws)

        print(self.post)
        sys.stdout.flush()
        return result

args = show

def returns(func):
    """Decorator to print function return details"""
    @ftl.wraps(func)
    def wrapper(*args, **kw):
        r = func(*args, **kw)
        print('%s\nreturn %s' % (func.__name__, r))
        return r

    return wrapper


def suppress(func):
    """Suppress all print statements in a function call"""

    @ftl.wraps(func)
    def wrapper(*args, **kws):
        # shadow stdout temporarily
        actualstdout = sys.stdout
        sys.stdout = StringIO()

        # call the actual function
        r = func(*args, **kws)

        # restore stdout
        sys.stdout = actualstdout
        sys.stdout.flush()

        return r

    return wrapper


# class InfoPrintWrapper(DecoratorBase):
#     def setup(self, pre='', post=''):
#         self.pre = pre
#         self.post = post

#     def __call__(self)
#     # def make_wrapper(self, func):
#     #     @ftl.wraps(func)
#     #     def wrapper(*args, **kw):
#     #         print(self.pre)
#     #         r = func(*args, **kw)
#     #         print(self.post)
#     #         return r

#     #     return wrapper


# class SameLineDone(InfoPrintWrapper):
#     def setup(self, pre='', post='', **kws):
#         self.pre = pre
#         up = '\033[1A'
#         right = '\033[%iC' % (len(pre) + 3)
#         self.post = up + right + post
