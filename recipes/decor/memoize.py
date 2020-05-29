"""
Memoization classes
"""

from collections import OrderedDict
import functools as ftl
from pathlib import Path
from pickle import PicklingError
import warnings

from ..io import load_pickle, save_pickle
from ..logging import LoggingMixin
# from ..interactive import exit_register

from collections import Hashable
from inspect import signature, _empty, _VAR_KEYWORD


def check_hashable_defaults(func):
    sig = signature(func)
    for name, p in sig.parameters.items():
        if p.default is _empty:
            continue

        if isinstance(p.default, Hashable):
            continue

        raise TypeError(
            f'{func.__class__.__name__} {func.__name__!r} has default value '
            f'for {p.kind} parameter {name} = {p.default} that is not hashable.'
        )
    return sig


class LRUCache(OrderedDict):
    # adapted from:
    # https://www.geeksforgeeks.org/lru-cache-in-python-using-ordereddict/

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


class PersistentRLUCache(LRUCache):
    # TODO
    pass


class to_file(LoggingMixin):
    """
    Decorator for persistent function memoization that saves cache to file as a
    pickle

    Pros: cache can be viewed transparently as the `cache` attribute on the 
          decorated function
        : Function keyword support
        : Raises when attempting to decorate a function with non-hashable 
          default arguments
        : When non-hashable arguments are passed to a decorated function, a
          warning is emitted and the caching is merely skipped instead of 
          raising a TypeError  
    Cons: thread safety not tested ??

    """

    # TODO: some stats like ftl.lru_cache
    # TODO: limit capacity in MB
    # TODO: format json / pkl
    # TODO: option to save only at exit??
    # TODO: move this stuff to the PersistantRLUCache class
    # TODO: default file location?
    # TODO: optional ignore keywords

    def __init__(self, filename, capacity=128):
        """
        Example:
        --------
        >>> @to_file('/tmp/test_cache5.pkl')
            def foo(a, b=0, *c, **kws):
                '''this my compute heavy function'''
                return a * 7 + b
                
            foo(6)
            print(foo.cache) # LRUCache([((('a', 6), ('b', 0), ('c', ())), 42)])
            foo([1], [0])    # UserWarning: Refusing memoization due to
                             # unhashable argument passed to function 
                             # 'foo': 'a' = [1]
            print(foo.cache) # LRUCache([((('a', 6), ('b', 0), ('c', ())), 42)])
                             # cache unchanged
            foo(6, hello='world')
            print(foo.cache)  
            # new cache item for keyword arguments
            # LRUCache([((('a', 6), ('b', 0), ('c', ())), 42),
                        ((('a', 6), ('b', 0), ('c', ()), ('hello', 'world')), 42)])
            
        """

        filepath = Path(filename).expanduser().resolve()
        self.filename = filename = str(filepath)
        self.func = None

        if filepath.exists():
            # load existing cache
            self.logger.info('Loading cache at %r', filename)
            self.cache = load_pickle(filename)
            self.logger.debug('Cache contains %d entries. Capacity is %d',
                              len(self.cache), self.cache.capacity)
        else:
            # no existing cache. create.  this will only happen the first time
            # the function executes
            self.logger.info('Creating cache at %r', filename)
            self.cache = LRUCache(capacity)

        # exit_register(self.save, filename, self._cache)

    def __call__(self, func):
        """
        Decorator the function
        """
        # check for non-hashable defaults: it is generally impossible to
        #  correctly memoize something that depends on non-hashable arguments
        check_hashable_defaults(func)
        self.func = func
        self.sig = check_hashable_defaults(func)

        # since functools.wraps does not work on methods, explicitly decalare
        # decorated function here
        @ftl.wraps(func)
        def decorated(*args, **kws):
            return self.memoizer(*args, **kws)

        # make a reference to the cache on the decorated function for convenience
        decorated.cache = self.cache
        # hack so we can access the inners of this class from the decorated
        # function returned here
        # `decorated.__self__.attr`.
        decorated.__self__ = self
        return decorated

    def memoizer(self, *args, **kws):
        """does the caching"""

        key = self.get_key(args, kws)
        for name, val in key:
            if not isinstance(val, Hashable):
                warnings.warn(
                    'Refusing memoization due to unhashable argument passed to '
                    f'{self.func.__class__.__name__} {self.func.__name__!r}: '
                    f'{name!r} = {val!r}')

                return self.func(*args, **kws)

        if key in self.cache:
            self.logger.debug('Loading result from cache for call to %s %r.',
                              self.func.__class__.__name__, self.func.__name__)
            answer = self.cache[key]
        else:
            answer = self.cache[key] = self.func(*args, **kws)
            # TODO: save in a thread so we can return value immediately!
            self.save()
        return answer

    def gen_key(self, args, kws):
        """
        Generate name, value pairs that will be used as a unique key 
        for caching the return values.
        """

        bound = self.sig.bind(*args, **kws)
        bound.apply_defaults()
        for name, val in bound.arguments.items():
            if self.sig.parameters[name].kind is not _VAR_KEYWORD:
                yield name, val
        yield from kws.items()

    def get_key(self, args, kws):
        """Create cache key from passed function parameters"""
        return tuple(self.gen_key(args, kws))

    def save(self):
        # if self._save:
        self.logger.debug('Saving cache at %r', self.filename)
        try:
            save_pickle(self.filename, self.cache)
        except PicklingError:
            warnings.warn('Could not save cache since some objects'
                          'could not be pickled')


def memoize(f):
    """ Memoization decorator for functions taking one or more arguments. """

    class memodict(dict):
        def __init__(self, f):
            self.f = f

        def __call__(self, *args):
            return self[args]

        def __missing__(self, key):
            ret = self[key] = self.f(*key)
            return ret

    return memodict(f)

