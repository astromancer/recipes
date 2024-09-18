"""
Cache / Memoization decorators and helpers.
"""


# std
import numbers
import warnings
from collections import abc
from inspect import _VAR_KEYWORD as _VKW, _empty, signature

# relative
from ..functionals import echo0
from ..string import named_items
from ..decorators import Decorator
from ..logging import LoggingMixin
from ..pprint.callers import describe
from ..oo.property import CachedProperty
from .manager import CacheManager
from .caches import DEFAULT_CAPACITY


# ---------------------------------------------------------------------------- #


def check_hashable_defaults(func):
    sig = signature(func)
    for name, p in sig.parameters.items():
        if p.default is _empty:
            continue

        if isinstance(p.default, abc.Hashable):
            continue

        raise TypeError(
            f'{describe(func)} has default value for {p.kind} parameter {name}'
            f' = {p.default} that is not hashable.'
        )
    return sig


def _check_hashers(mapping, ignore=()):
    typed = _ignore_params(dict(mapping), ignore)
    for f in typed.values():
        if isinstance(f, Ignore):
            continue

        if not callable(f):
            raise TypeError('Hashing functions should be callable, received '
                            f'{type(f).__name__}.')
    return typed


def _ignore_params(typed, ignore=()):
    if not ignore:
        return typed

    if isinstance(ignore, str):
        ignore = [ignore]

    for name in ignore:
        func = typed.pop(name, Ignore(name))
        if isinstance(func, Ignore):
            typed[name] = func
            continue

        raise ValueError(f'Ambiguity for parameter {name}: Asked to ignore, '
                         'but also appears in `typed` mapping.')

    return typed

# ---------------------------------------------------------------------------- #

# class HashableParameters():
#     def __hash__(self):


class Cached(Decorator, LoggingMixin):
    """
    Decorator for memoization on callable objects.

    Features:
        * Keyword parameters fully supported.
        * Works on any callable object that is picklable.
        * Optional type coercion of parameter values prior to caching (typing).
        * Conditionally ignore specific parameters, or entirely reject an entry,
          based on user specified conditionals.
        * Cache contents are referenced as the `__cache__` attribute on the
          decorated function.
        * Gracefully handle any exceptions that happen on attempted cache
          insertion, for example: When attempting to cache a call that has
          non-hashable parameter values, a informative warning is emitted and
          the caching is merely skipped instead of raising a TypeError.
        * Raises TypeError when attempting to decorate a function with
          non-hashable default arguments.

    TODO:
        thread safety.
        some stats like ftl.lru_cache
        limit capacity in MB
        more serialization formats
        more cache types
        telemetry to see if chache is amortising compute costs or not

    """

    @classmethod
    def to_file(cls, filename, capacity=DEFAULT_CAPACITY, policy='lru',
                ignore=(), typed=(), enabled=True):
        """
        Decorator for persistent function memoization that saves cache to file
        as a pickle / json / ...
        """

        # this here simply to make `filename` a required arg
        return cls(filename, capacity, policy, ignore, typed, enabled)

    @staticmethod
    def property(depends_on=(), read_only=False):
        return CachedProperty(depends_on, read_only)

    def __init__(self, filename=None, capacity=DEFAULT_CAPACITY, policy='lru',
                 ignore=(), typed=(), enabled=True):
        """
        A general purpose decorator for function return value caching
        (memoization).

        Parameters
        ----------
        filename : str or Path, optional
            Location on disc for persistent caching. If None, the default, the
            cache will be active for the duration of the main programme only.
        capacity : int, optional
            Size limit in number of items, by default 128.
        policy : str, optional
            Replacent policy, by default 'lru'. Currently only lru support.
        ignore : collection of str
            Parameter names that will be ignored when computing the hash key.
        typed : dict, optional
            Dictionary mapping parameters to callable, by default (). These are
            the hash functions for each parameter. ie. Each function will be
            called to get the cache key for that parameter. The final key for
            the cache entry is a tuple of the individual parameter keys,
            including any keywords passed to the function. Parameters can be
            given in the `typed` by their name (string), or position (int) for
            position-only or positional-or-keyword parameters. If a parameter is
            not found in the `typed` mapping, we default to the builtin hash
            mechanism.

        Examples
        --------
        Persistent caching:
        >>> @to_file('/tmp/foo_cache.pkl')
        ... def foo(a, b=0, *c, **kws):
        ...     '''this my compute heavy function'''
        ...     return a * 7 + b
        ...
        ... foo(6)
        ... foo.__cache__
        CacheManager[size: 1/128,
                     file: '/tmp/foo_cache.pkl']{
            (6, 0, (), ()): 42
        }

        The cache remains unchanged for function calls with unhashable
        parameters values.
        >>> foo([1], [0])
        CacheRejectionWarning: Function 'foo' received unhashable argument: 
        'a' = [1]
        Return value for call will not be cached.

        >>> foo.__cache__
        CacheManager[size: 1/128,
                     file: '/tmp/foo_cache.pkl']{
            (6, 0, (), ()): 42
        }

        Keywords are supported:
        >>> foo(6, hello='world')
        ... foo.__cache__
        CacheManager[size: 2/128,
                     file: '/tmp/foo_cache.pkl']{
            (6, 0, (), ()):                    42,
            (6, 0, (), (('hello', 'world'),)): 42
        }
        We see that a new cache entry was made for the invocation with keyword
        arguments.
        """

        self.sig = None
        self.typed = _check_hashers(typed, ignore)
        self.retyped = {}
        self.cache = CacheManager(capacity, filename, policy, enabled)

        # file rotation
        # filename = self.cache.filename
        # self.filename_template = None
        # if filename and '{' in filename:
        #     self.filename_template = filename

    def __call__(self, func):
        """
        Decorate the function
        """

        if not callable(func):
            # Emit a warning and return the original object
            warnings.warn(f'Cannot memoize {type(func)} {func} which is not '
                          f'callable. Results will not be cached.')
            return func

        if isinstance(func, type):
            # if self.cache.filename and self.cache.path.suffix == '.json':
            #     raise ValueError('Classes are not JSON serializable')

            # decorator is applied to a class - decorate the `__call__` method
            original = func.__call__

            # FIXME: CAN'T PICKLE THIS LOCAL FUNCTION
            def caller(x, *args, **kws):
                return original(x, *args, **kws)

            # decorate and override the __call__ method
            setattr(func, '__call__', self(caller))

            # additionally set the __cache__ on the object itself
            func.__cache__ = func.__call__.__cache__

            # return the patched object
            return func

        # create decorator
        decorated = super().__call__(func)

        # check for non-hashable defaults: it is generally impossible to
        #  correctly memoize something that depends on non-hashable arguments.
        self.sig = check_hashable_defaults(func)

        if not self.sig.parameters:
            warnings.warn(f'Cannot memoize {describe(func)} which takes no '
                          f'parameters.')
            return func

        # resolve typed keys to parameter names
        self.typed, self.retyped = self.resolve_types(self.typed)

        # since functools.wraps does not work on methods, explicitly decalare
        # decorated function here
        # ftl.update_wrapper(decorated, func)

        # make a reference to the cache on the decorated function for
        # convenience. this will allow us to more easily add cache items
        # manually etc.
        decorated.__cache__ = self.cache
        return decorated

    def resolve_types(self, mapping, strict=True):
        names = list(self.sig.parameters.keys())

        retyped = {}
        for key in tuple(mapping.keys()):
            if isinstance(key, numbers.Integral):
                mapping[names[key]] = mapping.pop(key)

            if isinstance(key, type):
                retyped[key] = mapping.pop(key)

        key_types = set(map(type, mapping.keys())) - {str, type}

        if key_types:
            raise ValueError(f'Hash map key has incorrect types {key_types}.')

        # all keys are now str
        if strict and (invalid := (set(mapping.keys()) - set(names))):
            raise ValueError(f'{describe(self.__wrapped__)} takes no '
                             f'{named_items(list(invalid), "parameter")}.')

        return mapping, retyped

    def _gen_hash_key(self, mapping):

        for name, val in mapping.items():
            convert = self.typed.get(name)

            # Filter ignored params
            if isinstance(convert, Ignore):
                if not convert.silent:
                    # emit warning on non-silent ignore
                    self.logger.opt(lazy=True).debug(
                        'Ignoring argument in {}',
                        lambda: f'{describe(self.__wrapped__)}: {name!r} = {val!r}'
                    )
                # go to next parameter
                continue

            # parameter not ignored
            if (par := self.sig.parameters.get(name)) and (par.kind is _VKW):
                # deal with variadic keyword args (**kws):
                yield tuple(zip(val.keys(), self._gen_hash_key(val)))

            else:
                convert = convert or self.retyped.get(type(val), echo0)
                yield convert(val)

            # remove the keys that have been bound to other position-or-keyword
            # parameters. variadic keyword args can come in any order. To ensure
            # we resolve calls like foo(a=1, b=2) and foo(b=2, a=1) to the same
            # cache item, we need to order the keywords. Finally convert to
            # tuple of 2-tuples (key value pairs) so we can hash

            # keys = sorted(set(val.keys()) - set(mapping.keys()))
            # kws = dict(zip(keys, map(val.get, keys)))
            # yield tuple(self._gen_hash_key(kws))

    def get_key(self, *args, **kws):
        """
        Compute cache key from function parameter values
        """
        bound = self.sig.bind(*args, **kws)
        bound.apply_defaults()
        return tuple(self._gen_hash_key(bound.arguments))

    def is_hashable(self, params):
        """
        Check if the set of parameter values of a call are hashable. 
        ie. can the return value from the function call with this set of 
        parameters be cached?

        Parameters
        ----------
        params : tuple
            Tuple of parameter values generated by the `get_key` method.
            (*pos, *pos_or_kw, (*var_pos), (kws.items()))


        Returns
        -------
        bool
        """
        for name, val in zip(self.sig.parameters, params):
            if isinstance(val, abc.Hashable):
                continue

            # emit warning and break out if we receive a rejection sentinel or
            # unhashable type
            what = ('unhashable argument',
                    'rejection sentinel')[isinstance(val, Reject)]
            warnings.warn(
                f'{describe(self.__wrapped__).capitalize()} received {what}:'
                f' {name!r} = {val!r}\n'
                'Return value for call will not be cached.',
                CacheRejectionWarning
            )
            return False
        return True

    # def rotate_file(self, **params):
    #     self.cache.filename = self.filename_template.format(**params)

    def __wrapper__(self, func, *args, **kws):
        """
        Caches the result of the function call
        """

        # self.rotate_file(**params)
        if not self.cache.enabled:
            self.logger.debug('Caching disabled for {}. Calling.',
                              describe(func))
            return func(*args, **kws)

        key = self.get_key(*args, **kws)
        if not self.is_hashable(key):
            return func(*args, **kws)

        # if we are here, we should be ok to lookup / cache the answer
        # pylint: disable=broad-except
        try:
            if key in self.cache:
                self.logger.debug('Intercepted {:s} call: Loading result from '
                                  'cache.', describe(func))
                return self.cache[key]
        except Exception as error:
            # since caching is not mission critical, just log the error and
            # then run the function
            self.logger.exception('Cache lookup for {:s} failed with\n{}.\n'
                                  'Function will now be called.',
                                  describe(func), error)
            return func(*args, **kws)

        # If we are here, it means there is no cache entry for this call
        # signature. Compute!
        answer = func(*args, **kws)

        # If function call succeeded, add result to cache
        try:
            self.cache[key] = answer
            self.logger.debug('Result has been cached.')
        except Exception:
            self.logger.exception('Caching result for {:s} call failed!',
                                  describe(func))

        return answer


# alias
cached = Cached


class Ignore:
    """
    Cache ignore directive for specific function parameters.

    Examples
    --------
    A constructor that caches object instances, but ignores the `verbose` 
    parameter:

    >>> @classmethod
    ... @caches.to_file('~/.cache/mycache.json',
    ...                 typed={'verbose': Ignore(silent=True)})
    ... def builder(cls, a, verbose=True, **kws):
    ...     if verbose:
    ...         print(f'Message from {cls}')
    ...     return cls(a, **kws)

    Notes
    -----
    This class will be used internally when initializing the `Cached` decorator
    with non-empty `ignore` parameter listing the function parameter name(s) to 
    ignore.
    """
    __hash__ = None  # signals python interpreter that this object is unhashable

    def __init__(self, silent=True):
        self.silent = bool(silent)


class Reject(Ignore):
    """
    Reject the cache entry entirely - ie do not cache.

    Examples
    --------
    The function below caches its return values only if the `file` parameter is
    given. If `file` is None or empty, the function will always run, returning None.

    >>> @caches.cached(typed={'file': lambda _: _ or Reject(silent=True)})
    ... def read(file, **kws):
    ...     if file:
    ...         return process_text(Path(file).read_text(), **kws)

    """


class CacheRejectionWarning(Warning):
    pass
