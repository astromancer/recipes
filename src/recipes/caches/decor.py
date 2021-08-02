"""
Memoization decorators and helpers
"""




# std libs
import warnings
import functools as ftl
from collections import abc
from inspect import signature, _empty, _VAR_KEYWORD

# local libs
from recipes.functionals import negate, echo0

# relative libs
from .caches import Cache
from ..logging import LoggingMixin


# from ..interactive import exit_register


def fullname(func):
    return f'{func.__class__.__name__} {func.__name__!r}'


def check_hashable_defaults(func):
    sig = signature(func)
    for name, p in sig.parameters.items():
        if p.default is _empty:
            continue

        if isinstance(p.default, abc.Hashable):
            continue

        raise TypeError(
            f'{fullname(func)} has default value for {p.kind} parameter {name}'
            f' = {p.default} that is not hashable.'
        )
    return sig


def check_hash_map(mapping):
    hash_map = dict(mapping)
    bad = next(filter(negate(callable), hash_map.values()), None)
    if bad:
        raise TypeError(f'Hashing functions should be callable, received '
                        f'{type(bad).__name__}')
    return hash_map


class Cached(LoggingMixin):
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

    def __init__(self, filename=None, capacity=128, kind='lru', hash_map=()):
        """
        A general purpose function memoizer cache.

        Parameters
        ----------
        filename : str or Path, optional
            Location on disc for persistent caching. If None, the default, the
            cache will be active for the duration of the main programme only. 
        capacity : int, optional
            Size limit in number of items, by default 128.
        kind : str, optional
            Replacent policy, by default 'lru'. Currently only lru support.
        hash_map : dict, optional
            Dictionary mapping parameters to callable, by default (). These are
            the hash functions for each parameter. ie. Each function will be
            called to get the cache key for that parameter. The final key for
            the cache entry is a tuple of the individual parameter keys,
            including any keywords passed to the function. Parameters can be
            given in the `hash_map` by their name, or position (int) for
            position-only or positional-or-keyword parameters. If a parameter is
            not found in the `hash_map`, we default to the builtin hash
            mechanism.

        Examples
        --------
        >>> @to_file('/tmp/foo_cache.pkl')
        ... def foo(a, b=0, *c, **kws):
        ...     '''this my compute heavy function'''
        ...     return a * 7 + b
        ...
        ... foo(6)
        ... foo.__cache__
        LRUCache([((('a', 6), ('b', 0), ('c', ())), 42)])

        >>> foo([1], [0])
        UserWarning: Refusing memoization due to unhashable argument passed
        to function 'foo': 'a' = [1]

        >>> foo.__cache__
        LRUCache([((('a', 6), ('b', 0), ('c', ())), 42)])

        The cache remains unchanged for function calls with unhashable
        parameters values.

        >>> foo(6, hello='world')
        ... foo.__cache__
        LRUCache([((('a', 6), ('b', 0), ('c', ())), 42),
                    ((('a', 6), ('b', 0), ('c', ()), ('hello', 'world')), 42)])

        A new cache entry was made for the keyword arguments.
        """
        self.func = None
        self.sig = None
        self.hash_map = check_hash_map(hash_map)
        self.__init_args = (filename, capacity, kind)
        self.cache = Cache(capacity, filename, kind=kind)

    def __call__(self, func):
        """
        Decorator the function
        """

        # check func
        # if isinstance(func, type):
        #     # if the decorator is applied to a class
        #     if self.cache.filename and self.cache.path.suffix == '.json':
        #         raise ValueError('Classes are not serializable')

        #     return type(f'Cached{func.__name__}', (_Cached, func), {})

        # # hopefully we have a function or a method!
        # assert isinstance(func, (types.MethodType,
        #                          types.FunctionType,
        #                          types.BuiltinFunctionType,
        #                          types.BuiltinMethodType))

        # check for non-hashable defaults: it is generally impossible to
        #  correctly memoize something that depends on non-hashable arguments
        
        self.func = func
        self.sig = check_hashable_defaults(func)

        # since functools.wraps does not work on methods, explicitly decalare
        # decorated function here
        @ftl.wraps(func)
        def decorated(*args, **kws):
            return self.memoize(*args, **kws)

        # make a reference to the cache on the decorated function for
        # convenience. this will allow us to more easily add cache items
        # manually etc.
        decorated.__cache__ = self.cache  # OR decorated.__cache__??
        # hack so we can access the inners of this class from the decorated
        # function returned here
        # `decorated.__self__.attr`.
        decorated.__self__ = self
        return decorated

    def _gen_hash_key(self, args, kws):
        """
        Generate hash key from function arguments.
        """
        bound = self.sig.bind(*args, **kws)
        bound.apply_defaults()
        for name, val in bound.arguments.items():
            hasher = self.hash_map.get(name, echo0)
            if self.sig.parameters[name].kind is not _VAR_KEYWORD:
                yield hasher(val)
            else:
                # deal with variadic keyword args (**kws):
                # remove the keys that have been bound to other position-or-keyword
                # parameters. variadic keyword args can come in any order. To ensure
                # we resolve calls like foo(a=1, b=2) and foo(b=2, a=1) to the same
                # cache item, we need to order the keywords. Finally convert to
                # tuple of 2-tuples (key value pairs) so we can hash
                keys = sorted(set(kws.keys()) - set(bound.arguments.keys()))
                yield hasher(tuple(zip(keys, map(kws.get, keys))))

    def get_key(self, *args, **kws):
        """
        Compute cache key from function parameter values
        """
        return tuple(self._gen_hash_key(args, kws))

    def is_hashable(self, key):
        for name, val in zip(self.sig.parameters, key):
            if not isinstance(val, abc.Hashable):
                silent = isinstance(val, Ignore) and val.silent
                if not silent:
                    warnings.warn(
                        f'Refusing to cache return value due to unhashable '
                        f'argument in {fullname(self.func)}: {name!r} = {val!r}'
                    )
                #
                return False

            # even though we have hashable types for our function arguments, the
            # actual hashing might not still work, so we catch any potential
            # exceptions here
            try:
                hash(val)
            except TypeError as err:
                warnings.warn(
                    f'Hashing failed for {fullname(self.func)}: {name!r} = '
                    f'{val!r} due to:\n{err!s}'
                )
                #
                return False
        return True

    def memoize(self, *args, **kws):
        """
        Caches the result of the function call
        """
        func = self.func
        key = self.get_key(*args, **kws)
        if not self.is_hashable(key):
            return func(*args, **kws)

        # load the cached values from file
        # if self.cache is None:
        #     self.cache = Cache.load(self.__init_args[0])

        try:
            # if we are here, we should be ok to lookup / cache the answer
            if key in self.cache:
                self.logger.debug('Loading result from cache for call to %s.',
                                  fullname(self.func))
                return self.cache[key]
        except Exception as err:
            self.logger.exception('Cache lookup failed!')
            # since caching is not mission critical, re-run the function
            return self.func(*args, **kws)

        # add result to cache
        self.cache[key] = answer = self.func(*args, **kws)
        return answer


# class ConstructorCache:
#     def __new__(self, kls, *args, **kws):
#         self.kls = kls


# , monkey patch the
# constructor so the entire class gets cached!

# name = f'Cached{func.__name__}'
# eval(f'global {name}')

# class _Cached:   # FIXME: this local object cannot be pickled
#     @self.__class__(*self.__init_args)
#     def __new__(cls, *args, **kws):
#         # print('NEW!!!')
#         obj = super().__new__(cls)
#         obj.__init_args = args
#         return obj

#     # def __reduce__(self):
#     #     return func, self.__init_args


class to_file(Cached):
    """
    Decorator for persistent function memoization that saves cache to file as a
    pickle
    """

    def __init__(self, filename, capacity=128, kind='lru'):
        # this here simply to make `filename` a required arg
        Cached.__init__(self, filename, capacity, kind)


class Ignore:
    def __init__(self, silent=False):
        self.silent = bool(silent)

    def __hash__(self):
        pass


# aliases
memoize = cached = Cached
