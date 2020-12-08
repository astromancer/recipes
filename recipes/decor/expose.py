"""
Decorators for exposing function arguments / returns
"""
import builtins
import inspect
from io import StringIO
import sys
import math
import functools as ftl  # , pprint

from .base import Decorator
from ..introspect.utils import get_module_name
import textwrap as txw
import types

POS, PKW, VAR, KWO, VKW = list(inspect._ParameterKind)


def get_inner(func, args=(), kws=None):
    """"""
    kws = kws or {}
    while isinstance(func, ftl.partial):
        kws.update(func.keywords)
        args += func.args
        func = func.func
    return func, args, kws


def show_func(func, args=None, kws=None, wrap=80, show_modules=None,
              params_per_line=None, hang=None, show_defaults=True):
    """Pretty format a function, and optionally, its paramater values"""
    # todo ppl
    # TODO: option to not print param names

    if not callable(func):
        raise TypeError(f'Object {func} is not a callable')

    # get object name string with module
    name = '.'.join(
        filter(None, (get_module_name(func, show_modules),
                      func.__qualname__))
    )

    #
    sig = inspect.signature(func)
    with_args = not (args is None and kws is None)
    if with_args:
        ba = sig.bind(*args, **kws)
        if show_defaults:
            ba.apply_defaults()

        fmt = '{:}={!r}'
        items = ba.arguments.items()
    else:
        fmt = '{1!s}'
        # inject special markers
        items = list(sig.parameters.items())
        kinds = [p.kind for _, p in items]

        if (POS in kinds) and (len(set(kinds)) > 1):
            items.insert(kinds.index(POS) + 1, ('/', '/'))

        if (KWO in kinds) and (VAR not in kinds):
            items.insert(kinds.index(KWO), ('*', '*'))

    # format!
    if not items:
        return name + '()'

    items = list(map(fmt.format, *zip(*items)))
    # item_widths = list(map(len, items))
    widest = max(map(len, items))

    # get default choices for repr
    ppl = params_per_line
    if ppl:
        ppl = int(params_per_line)
        wrap = False
    # elif wrap:
    #     ppl = max(wrap // widest, 1)
    # else:
    #     ppl = 100
    # ppl = ppl or 100

    #
    indent = len(name) + 1
    if hang is None:
        hang = ((not ppl and len(items) > 7)
                or
                (wrap and widest > wrap - indent))

    hang = bool(hang)
    if hang:
        indent = 4

    if wrap:
        wrap -= indent

    if widest > wrap:
        # truncate!!
        pass

    ppl = ppl or 100

    # make the signature rep
    s = ''
    line = ''
    for i, v in enumerate(items):
        if i > 0:
            line += ', '

        if ((i % ppl) == 0) or (wrap and (len(line) + len(v) > wrap)):
            s += f'{line}\n'
            line = v
        else:
            line += v

        # if len(s) > wrap:
        #     # FIXME: this will break in the middle of **kws or *args etc...
        #     s = '\n'.join(txw.wrap(s, wrap))
    s += line
    s = txw.indent(s, ' ' * indent).lstrip('\n')

    if hang:
        s = f'\n{s}\n'
    else:
        s = s.lstrip()

    return name + s.join('()')

    """Get func repr in pretty format"""
    # TODO: update docstring
    # TODO: interject str formatter for types eg. np.ndarray?
    # TODO: colourise elements  / defaults / non-defaults


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


class args(Decorator):
    """
    Decorator to print function call details - parameters names and effective 
    values optional arguments specify stuff to print before and after, as well 
    as specific pretty printing options to `show_func`.

    Example
    -------

    >>> from recipes.decor import expose
    >>> @expose.args()
    ... def foo(a, b, c, **kw):
    ...     return a
    ...
    ... foo('aaa', 42, id, gr=8, bar=...)

    prints:
    foo(a       = aaa,
        b       = 42,
        c       = <built-in function id>,
        kwargs  = {'bar': Ellipsis, 'gr': 8} )

    Out[43]: 'aaa'
    """

    def __init__(self, pre='expose.args\n', post='-' * 80, **options):
        self.pre = pre
        self.post = post
        self.options = options

    def wrapper(self, *args, **kws):
        print(self.pre)
        print(show_func(self.func, args, kws, **self.options))

        from IPython import embed
        embed(header="Embedded interpreter at 'expose.py':196")

        result = self.func(*args, **kws)



        print(self.post)
        sys.stdout.flush()
        return result


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
