"""
Memoization classes
"""

# TODO: rename caches - make package?

import types
from collections import OrderedDict as odict  # , UserDict as udict
import functools as ftl
from pathlib import Path
from pickle import PicklingError
import warnings

from .io import load_pickle, save_pickle
from .logging import LoggingMixin
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


def get_key(sig, args, kws):
    """Create cache key from passed function parameters"""
    return tuple(generate_key(sig, args, kws))


class LRUCache(odict):
    """
    An extensible Least Recently Used cache

    adapted from:
    https://www.geeksforgeeks.org/lru-cache-in-python-using-ordereddict/

    see also:
    https://en.wikipedia.org/wiki/Cache_replacement_policies#Least_recently_used_(LRU)

    """
    kind = 'lru'

    def __init__(self, capacity):
        # initialising capacity
        self.capacity = int(capacity)
        self._move = True

    def __reduce__(self):
        # ensure capacity gets set on unpickling
        return self.__class__, (self.capacity, )

    def get(self, key, default=None):
        if key in self:
            return self[key]
        return default

    def __getitem__(self, key):
        # we return the value of the key that is queried in O(1) and return -1
        # if we don't find the key in out dict / cache. Also move key to end to
        # show that it was recently used.
        item = super().__getitem__(key)
        if self._move:
            self.move_to_end(key)
        return item

    def __setitem__(self, key, value):
        # first, add / update the key by conventional methods. Also move the key
        # to the end to show that it was recently used. Check if length has
        # exceeded capacity, if so remove first key (least recently used)
        super().__setitem__(key, value)
        self.move_to_end(key)
        if len(self) > self.capacity:
            # line below will call __getitem__, but fail on `move_to_end`
            # unless we set `_move` to False. bit hackish
            self._move = False
            self.popitem(last=False)
            self._move = True

    def clear(self):
        while self:
            self.popitem()


class PersistantCache(LoggingMixin):
    """
    An LRU cache that persists in memory on file
    """

    # TODO: as a mixin

    #     # exit_register(self.save, filename, self._cache)
    #     return super().__new__(filename, capacity)

    def __init__(self, filename, capacity, kind='lru'):
        """
        A cache that persists on disk

        Parameters
        ----------
        filename : str or Path
            File location of the cache
        capacity : int
            Maximal item size of the cache
        kind : str, optional
            The cache item replacement policy, by default 'lru'
            (only LRU currently supported)

        Raises
        ------
        TypeError
            If the pickeled obect at the given location is not a
            `PersistantCache` type object.
                or
            If the cache exists at the given location, but it is not of the
            requested kind. ie. The item replacement policy differs from that
            which has been requested.
        """
        filepath = Path(filename).expanduser().resolve()
        self.filename = filename = str(filepath)

        kls = get_cache_type(kind)
        if filepath.exists():
            # load existing cache
            self.logger.info('Loading cache at %r', filename)
            cache = load_pickle(filename)

            # Check pickled object is correct type
            if not isinstance(cache, self.__class__):
                raise TypeError(
                    f'Expected {self.__class__.__name__!r} type object at '
                    f'location {filepath!r}. Found {type(cache)!r} instead.')

            # Check cache type is correct
            cache = cache.cache
            if not isinstance(cache, kls):
                raise TypeError(
                    f'Expected cache at location {filepath!r} to be of type '
                    f'{kls!r}. Found {type(cache)!r} instead.')

            # print info
            self.logger.debug('Cache contains %d entries. Capacity is %d.',
                              len(cache), cache.capacity)

        else:
            # no existing cache. create. this will only happen the first time
            # the function executes
            self.logger.info('Creating cache at %r', filename)
            cache = kls(capacity)

        #
        self.cache = cache

    def __repr__(self):
        return 'Persistent' + repr(self.cache)

    def __getitem__(self, key):
        return self.cache[key]

    def __setitem__(self, key, val):
        self.cache[key] = val
        # TODO: save in a thread so we can return value immediately!
        self.save()
        return val

    def __contains__(self, key):
        return key in self.cache

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.cache == other.cache
        if isinstance(other, dict):
            return self.cache == other
        return False

    def get(self, key, default=None):
        return self.cache.get(key, default)

    def save(self):
        """save the cache as a pickle"""
        self.logger.debug('Saving cache at %r', self.filename)
        try:
            save_pickle(self.filename, self)
        except PicklingError:
            warnings.warn('Could not save cache since some objects'
                          'could not be pickled')


CACHE_TYPES = {'lru': LRUCache}


def get_cache_type(kind):
    kind = kind.lower()
    if kind not in CACHE_TYPES:
        raise ValueError(f'Unknown cache type {kind!r}')
    return CACHE_TYPES[kind]


class Memoizer(LoggingMixin):
    """
    Decorator for memoization on callable objects

    Pros: Function keyword support
        : cache contents can be viewed transparently as the `cache` attribute on
          the decorated function
        : Raises when attempting to decorate a function with non-hashable
          default arguments
        : When non-hashable arguments are passed to a decorated function, a
          warning is emitted and the caching is merely skipped instead of
          raising a TypeError
        : When used to decorate a class, the `__new__` constructor is
          automatically  decorated so that instances of the class get memoized. 

    Cons: probably not thread safe. not yet tested

    """

    # TODO: some stats like ftl.lru_cache
    # TODO: limit capacity in MB
    # TODO: format json / pkl
    # TODO: optional ignore keywords
    # TODO: more cache types

    def __init__(self, capacity=128, kind='lru'):
        self.func = None
        self.sig = None
        self.cache = get_cache_type(kind)(capacity)
        self._cache_args = capacity, kind

    def __call__(self, func):
        """
        Decorator the function
        """

        # check func
        if isinstance(func, type):
            # if the decorator is applied to a class, memoize the constructor so
           # the entire class gets cached!

            class _Cached:
                @self.__class__(*self._cache_args)
                def __new__(cls, *args, **kws):
                    return super().__new__(cls)

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

    def memoize(self, *args, **kws):
        """caches the result of the function call"""

        answer = self.func(*args, **kws)
        key = get_key(self.sig, args, kws)
        for name, val in key:
            if not isinstance(val, abc.Hashable):
                warnings.warn(
                    'Refusing memoization due to unhashable argument in '
                    f'{self.func.__class__.__name__} {self.func.__name__!r}: '
                    f'{name!r} = {val!r}')
                #
                return answer

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
                return answer

        # if we are here, we should be ok to lookup / cache the answer
        if key in self.cache:
            self.logger.debug('Loading result from cache for call to %s %r.',
                              self.func.__class__.__name__, self.func.__name__)
            return self.cache[key]

        # add result to cache
        self.cache[key] = answer
        return answer


class to_file(Memoizer):
    """
    Decorator for persistent function memoization that saves cache to file as a
    pickle
    """

    # TODO: option to save only at exit??

    def __init__(self, filename, capacity=128, kind='lru'):
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
        self.cache = PersistantCache(filename, capacity, kind)
        self._cache_args = (filename, capacity, kind)


# alias
memoize = Memoizer
