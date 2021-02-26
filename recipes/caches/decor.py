"""
Memoization classes
"""


import types
import functools as ftl
from pathlib import Path
import warnings

from .caches import Cache
# from .persistence import PersistantCache
from ..logging import LoggingMixin
# from ..interactive import exit_register

from collections import abc
from inspect import signature, _empty, _VAR_KEYWORD


def check_hashable_defaults(func):
    sig = signature(func)
    for name, p in sig.parameters.items():
        if p.default is _empty:
            continue

        if isinstance(p.default, abc.Hashable):
            continue

        raise TypeError(
            f'{func.__class__.__name__} {func.__name__!r} has default value '
            f'for {p.kind} parameter {name} = {p.default} that is not hashable.'
        )
    return sig


def generate_key(sig, args, kws):
    """
    Generate name, value pairs that will be used as a unique key 
    for caching the return values.
    """

    bound = sig.bind(*args, **kws)
    bound.apply_defaults()
    for name, val in bound.arguments.items():
        if sig.parameters[name].kind is not _VAR_KEYWORD:
            yield name, val
    yield from kws.items()


class Cached(LoggingMixin):  # Cached
    """
    Decorator for memoization on callable objects

    Features:
        : keyword support
        : cache contents can be viewed transparently as the `cache` attribute on
          the decorated function
        : Raises when attempting to decorate a function with non-hashable
          default arguments
        : When non-hashable arguments are passed to a decorated function, a
          warning is emitted and the caching is merely skipped instead of
          raising a TypeError
        : When used to decorate a class, the `__new__` constructor is
          automatically  decorated so that instances of the class get memoized.

    TODOs: 
        probably not thread safe. not yet tested
        some stats like ftl.lru_cache
        limit capacity in MB
        format json / pkl
        optional ignore keywords
        more cache types

    """

    def __init__(self, filename=None, capacity=128, kind='lru'):
        """
        Example:
        --------
        >>> @to_file('/tmp/foo_cache.pkl')
            def foo(a, b=0, *c, **kws):
                '''this my compute heavy function'''
                return a * 7 + b

        >>> foo(6)
        >>> print(foo.cache)
            LRUCache([((('a', 6), ('b', 0), ('c', ())), 42)])

        >>> foo([1], [0])
            UserWarning: Refusing memoization due to unhashable argument passed
            to function 'foo': 'a' = [1]

        >>> print(foo.cache)
            LRUCache([((('a', 6), ('b', 0), ('c', ())), 42)])
            # cache unchanged

        >>> foo(6, hello='world')
        >>> print(foo.cache)
            LRUCache([((('a', 6), ('b', 0), ('c', ())), 42),
                      ((('a', 6), ('b', 0), ('c', ()), ('hello', 'world')), 42)])
            # new cache entry for keyword arguments
        """
        self.func = None
        self.sig = None
        self._init_args = (filename, capacity, kind)
        self.cache = Cache(capacity, filename, kind=kind)


    def __call__(self, func):
        """
        Decorator the function
        """

        # check func
        if isinstance(func, type):
            # if the decorator is applied to a class, monkey patch the
            # constructor so the entire class gets cached!

            # name = f'Cached{func.__name__}'
            # eval(f'global {name}')

            class _Cached:   # FIXME: this local object cannot be pickled
                @self.__class__(*self._init_args)
                def __new__(cls, *args, **kws):
                    # print('NEW!!!')
                    obj = super().__new__(cls)
                    obj._init_args = args
                    return obj

                # def __reduce__(self):
                #     return func, self._init_args

            return type(f'Cached{func.__name__}', (_Cached, func), {})

        # hopefully we have a function or a method!
        assert isinstance(func, (types.MethodType,
                                 types.FunctionType,
                                 types.BuiltinFunctionType,
                                 types.BuiltinMethodType))

        # check for non-hashable defaults: it is generally impossible to
        #  correctly memoize something that depends on non-hashable arguments
        check_hashable_defaults(func)
        self.func = func
        self.sig = check_hashable_defaults(func)

        # since functools.wraps does not work on methods, explicitly decalare
        # decorated function here
        @ftl.wraps(func)
        def decorated(*args, **kws):
            return self.memoize(*args, **kws)

        # make a reference to the cache on the decorated function for
        # convenience
        decorated.cache = self.cache
        # hack so we can access the inners of this class from the decorated
        # function returned here
        # `decorated.__self__.attr`.
        decorated.__self__ = self
        return decorated

    def get_key(self, *args, **kws):
        """Create cache key from passed function parameters"""
        return tuple(generate_key(self.sig, args, kws))

    def memoize(self, *args, **kws):
        """caches the result of the function call"""

        key = self.get_key(*args, **kws)
        for name, val in key:
            if not isinstance(val, abc.Hashable):
                warnings.warn(
                    'Refusing to cache return value due to unhashable argument '
                    f'in {self.func.__class__.__name__} {self.func.__name__!r}:'
                    f' {name!r} = {val!r}')
                #
                return self.func(*args, **kws)

            # even though we have hashable types for our function arguments, the
            # actual hashing might not still work, so we catch any potential
            # exceptions here
            try:
                hash(val)
            except TypeError as err:
                warnings.warn(
                    f'Hashing failed for '
                    f'{self.func.__class__.__name__} {self.func.__name__!r}: '
                    f'{name!r} = {val!r} due to:\n{err!s}')
                #
                return self.func(*args, **kws)

        # if we are here, we should be ok to lookup / cache the answer
        if key in self.cache:
            self.logger.debug('Loading result from cache for call to %s %r.',
                              self.func.__class__.__name__, self.func.__name__)
            return self.cache[key]

        # add result to cache
        self.cache[key] = answer = self.func(*args, **kws)
        return answer


class to_file(Cached):
    """
    Decorator for persistent function memoization that saves cache to file as a
    pickle
    """

    def __init__(self, filename, capacity=128, kind='lru'):
        # this here simply to make `filename` a required arg
        Cached.__init__(self, filename, capacity, kind)


# aliases
memoize = cached = Cached