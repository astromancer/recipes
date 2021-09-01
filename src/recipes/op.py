"""
Some drop-in replacements for the cool builtin operator classes, but with added
support for default values 
"""

# pylint: disable=redefined-builtin
# pylint: disable=invalid-name

# std
from collections import abc
import builtins
import warnings
import functools as ftl
import operator as _op
from operator import *
from collections import abc

# local
import docsplice as doc

# relative
from .functionals import echo0, raises


class NULL:
    "Null singleton"


def any(itr, test=bool):
    """
    Return True if test(x) is True for any x in the iterable.
    If the iterable is empty, return False.

    This function performs exactly the same function as the builtin any, but 
    additionally allows the item evaluation test to be user-specified.

    Parameters
    ----------
    itr : iterable
        Items to be evaluated.
    test : callable, optional
        Test function for items in the iterable. Must return a bool. Default 
        is the builtin bool function.

    Returns
    -------
    bool

    Examples
    --------
    >>> any(('U', 'X'), str.isupper)
    True
    """
    return builtins.any(map(test, itr))


@doc.splice(any, replace={'any': 'all', 'False': 'True'})
def all(itr, test=bool):
    return builtins.all(map(test, itr))


def prepend(obj, prefix):
    return prefix + obj


def append(obj, suffix):
    return obj + suffix


class ItemGetter:
    """
    (Multi-)Item getter with optional default substitution
    """
    _worker = staticmethod(getitem)
    _excepts = (KeyError, IndexError)
    _raises = KeyError

    def __init__(self, *keys, default=NULL, defaults=None):
        self.keys = keys
        self.defaults = defaults or {}
        typo = set(self.defaults.keys()) - set(self.keys)
        if typo:
            warnings.warn(f'Invalid keys in `defaults` mapping: {typo}')

        self.default = default
        if default is NULL:
            # intentionally override the `get_default` method
            self.get_default = raises(self._raises)

    def __call__(self, target):  # -> List:
        unpack = tuple if len(self.keys) > 1 else next
        return unpack(self._iter(target))

    def get_default(self, key):
        """Retrieve the default value of the `key` attribute"""
        # pylint: disable=method-hidden
        return self.defaults.get(key, self.default)

    def _iter(self, target):
        for i in self.keys:
            try:
                yield self._worker(target, i)
            except self._excepts:
                # note. Next line will raise KeyError if no default provided at init
                yield self.get_default(i)


class AttrGetter(ItemGetter):
    """
    (Multi-)Attribute getter with optional default substitution and chained
    lookup support for nested objects.
    """
    _excepts = (AttributeError, )

    @staticmethod
    def _worker(target, key):
        return _op.attrgetter(key)(target)


class AttrSetter:
    """
    (Multi-)Attribute setter with chained lookup support for setting attributes
    on nested objects.
    """
    # this is valuable when vectorizing attribute lookup

    def __init__(self, *keys):
        self.keys = []
        self.getters = []
        for key in keys:
            *chained, attr = key.rsplit('.', 1)
            self.keys.append(attr)
            self.getters.append(AttrGetter(*chained) if chained else echo0)

    def __call__(self, target, values):
        assert len(values) == len(self.keys)
        for get_obj, attr, value in zip(self.getters, self.keys, values):
            # logger.debug(get_obj(target), attr, value)
            setattr(get_obj(target), attr, value)


class VectorizeMixin:
    def __call__(self, target):
        return list(self.map(target))

    def map(self, target):
        assert isinstance(target, abc.Collection)
        return map(super().__call__, target)

    def filter(self, *args):
        *test, target = args
        return filter(test or None, self.map(target))


class ItemVector(VectorizeMixin, ItemGetter):
    """Vectorized ItemGetter"""


class AttrVector(VectorizeMixin, AttrGetter):
    """Vectorized AttrGetter"""


class MethodCaller:
    """
    This is adapted from `operator.methodcaller`. The code below is copied
    verbatim from 'operator.py' (since you can't inherit from
    `operator.methodcaller!`) with only the `__call__` method altered to support
    chained attribute lookup like:
    >>> MethodCaller('foo.bar.func', *args, **kws)(object)

    Return a callable object that calls the given method on its operand.
    After f = methodcaller('name'), the call f(r) returns r.name().
    After g = methodcaller('name', 'date', foo=1), the call g(r) returns
    r.name('date', foo=1).
    """
    __slots__ = ('_name', '_args', '_kwargs')

    def __init__(*args, **kwargs):
        if len(args) < 2:
            msg = ("%s needs at least one argument, the method name"
                   % args[0].__class__.__name__)
            raise TypeError(msg)

        self = args[0]
        self._name = args[1]
        if not isinstance(self._name, str):
            raise TypeError('method name must be a string')
        self._args = args[2:]
        self._kwargs = kwargs

    def __call__(self, obj):
        return attrgetter(self._name)(obj)(*self._args, **self._kwargs)

    def __repr__(self):
        args = [repr(self._name),
                *map(repr, self._args)]
        args.extend('%s=%r' % (k, v) for k, v in self._kwargs.items())
        return '%s.%s(%s)' % (self.__class__.__module__,
                              self.__class__.__name__,
                              ', '.join(args))

    def __reduce__(self):
        if self._kwargs:
            return (ftl.partial(self.__class__, self._name, **self._kwargs),
                    self._args)

        return self.__class__, (self._name,) + self._args
# update c
# MethodCaller.__doc__ += op.methodcaller.__doc__.replace('methodcaller', 'MethodCaller')


def index(obj, item, start=0, test=eq, default=NULL):
    """
    Find the index position of `item` in list `l`, or if a test function is
    provided, the first index position for which the test evaluates as true. If
    the item is not found, or no items test positive, return the provided
    default value.

    Parameters
    ----------
    obj : list or str
        The items to be searched
    item : object
        item to be found
    start : int, optional
        optional starting index for the search, by default 0
    test : callable, optional
        Function used to identify the item. Calling sequence of this function is
        `test(x, item)`, where `x` is an item from the input list. The function
        should return boolean value to indicate whether the position of that
        item is to be returned in the index list. The default is `op.eq`, which
        tests each item for equality with input `item`.
    default : object, optional
        The default to return if `item` was not found in the input list, by
        default None

    Returns
    -------
    int
        The index position where the first occurance of `item` is found, or
        where `test` evaluates true
    """
    # if not isinstance(l, list):
    #     l = list(l)

    test = test or eq
    for i, x in enumerate(obj[start:], start):
        if test(x, item):
            return i

    # behave like standard indexing by default
    #  -> only if default parameter was explicitly given do we return that
    #   instead of raising a ValueError
    if default is NULL:
        raise ValueError(f'{item} is not in {type(obj)}')

    return default


class contained:  # pylint: disable=invalid-name
    """
    Helper class for condition testing presence of items in sequences

    Example
    >>> [*map(contained('*').within, ['', '**', '..'])]
    [False, True, False]
    """

    def __init__(self, item):
        self.item = item

    def within(self, container):
        return self.item in container


# aliases
itemgetter = ItemGetter
attrgetter = AttrGetter
