"""
Some drop-in replacements for the very cool builtin operator classes, but with
added support for default values. Along with some additional related operational
workhorses.
"""

# pylint: disable=redefined-builtin
# pylint: disable=function-redefined
# pylint: disable=invalid-name
# pylint: disable=wildcard-import, unused-wildcard-import


# std
import fnmatch as fnm
import operator as _op
import functools as ftl
from operator import (getitem, ge, gt, le, lt, ne, add, sub, eq, mul, floordiv,
                      truediv)
from collections import abc

# relative
import builtins
from .functionals import echo0
from .containers import ensure


# ---------------------------------------------------------------------------- #

# Null singleton
_NULL = object()
_NOT_FOUND = object()


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
    >>> any(('U', 'x'), str.isupper)
    True
    """
    return builtins.any(map(test, itr))


# @ doc.splice(any, replace={'any': 'all', 'False': 'True'})
def all(itr, test=bool):
    return builtins.all(map(test, itr))


# ---------------------------------------------------------------------------- #
# Reversed binary operators

def reverse_operands(operator):
    """Decorator that reverses the order of input arguments."""

    def wrapper(a, b, /):
        return operator(b, a)

    # docstring
    wrapper.__doc__ = operator.__doc__.replace(' a ', ' b ').replace(' b.', ' a.')

    return wrapper


def _make_reverse_operators(*ops):
    for op in ops:
        yield reverse_operands(op)


#
radd, rsub, rmul, rtruediv, rfloordiv = _make_reverse_operators(
    add, sub, mul, truediv, floordiv)


# ---------------------------------------------------------------------------- #
# API helper

def _resolve_attr_names(obj, names=...):
    if names is ...:
        if hasattr(obj, '__slots__'):
            # local to avoid circular import
            from recipes.oo.slots import get_slots
            return get_slots(obj)

        return list(obj.__dict__)

    names = ensure.list(names)

    # additional properties can be given like (..., 'xx')
    if ... in names:
        i = names.index(...)
        return [*names[:i], *_resolve_attr_names(obj, ...), *names[i+1:]]

    return names


def resolve_attr_names(obj, names=..., ignore=(), check=False):
    names = _resolve_attr_names(obj, names)

    if ignore:
        names = exclude(names, ignore)

    if check:
        for name in names:
            assert hasattr(obj, name)

    return names


def exclude(attrs, ignore):
    return [atr for atr in attrs if _include(atr, ignore)]


def _include(atr, patterns):
    for pattern in ensure.tuple(patterns):
        if fnm.fnmatch(atr, pattern):
            return False
    return True


class Get:

    def items(self, indices):
        return ItemGetter(*indices)

    __call__ = item = items

    def attrs(self, obj, required=..., conditional=(), ignore='*_'):
        if required is not ... and (overlap := (set(required) & set(conditional))):
            raise ValueError(
                f'Attributes cannot be both required and conditional: {overlap}'
            )

        maybe = {}
        if conditional:
            maybe = AttrMap(*ensure.tuple(conditional), default=_NOT_FOUND)(obj)
            maybe = {key: val for key, val in maybe.items()
                     if val is not _NOT_FOUND}

        # resolve names
        required = resolve_attr_names(obj, required, ignore)

        # fetch
        return {**AttrMap(*required)(obj), **maybe}

    attr = attrs


# Singleton for item / attribute retrieval
get = Get()


# ---------------------------------------------------------------------------- #

class ItemGetter:
    """
    (Multi-)Item getter with optional default substitution.
    """
    _worker = staticmethod(getitem)
    _excepts = LookupError
    _raises = KeyError

    def __init__(self, *keys, default=_NULL, defaults=None):
        self.keys = keys
        self.default = default
        self.defaults = defaults or {}
        self.unpack = tuple if len(self.keys) > 1 else next

        # FIXME: FAILS for slices: TypeError: unhashable type: 'slice'
        # typo = set(self.defaults.keys()) - set(self.keys)
        # if typo:
        #     warnings.warn(f'Invalid keys in `defaults` mapping: {typo}')

        # if default is _NULL:
        #     # intentionally override the `get_default` method
        #     self.get_default = raises(self._raises)

    def __call__(self, target):
        return self.unpack(self._iter(target))

    def __repr__(self):
        return f'{self.__class__.__name__}({self.keys})'

    def get_default(self, key):
        """Retrieve the default value of the `key` attribute"""
        if self.default is _NULL:
            raise self._raises(key)

        return self.defaults.get(key, self.default)

    def _iter(self, target):
        for i in self.keys:
            try:
                yield self._worker(target, i)
            except self._excepts:
                # NOTE. Next line raises KeyError if no default provided at init
                yield self.get_default(i)


class AttrGetter(ItemGetter):
    """
    (Multi-)Attribute getter with optional default substitution and chained
    lookup support for sumultaneously retrieving many attributes from nested
    objects.
    """
    _excepts = (AttributeError, )

    @staticmethod
    def _worker(target, key):
        return _op.attrgetter(key)(target)

    def __call__(self, target, default=_NULL):  # -> Tuple or Any:
        if default is not _NULL:
            self.default = default
        return super().__call__(target)


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
        keys = self.keys
        if len(keys) == 1 and (ensure.is_scalar(values) or len(values) != 1):
            values = [values]

        if isinstance(values, dict):
            keys = values.keys()
            values = values.values()

        assert len(values) == len(keys)

        for get_obj, attr, value in zip(self.getters, keys, values):
            setattr(get_obj(target), attr, value)


# Get items / attributes as dict
class MapBase:
    """
    Mixin that returns a `dict` keyed on requested itmes / attributes.
    """

    def __init__(self, *keys, default=_NULL, defaults=None):
        super().__init__(*keys, default=default, defaults=defaults)
        self.unpack = tuple
        # always unpack to tuple since we will use that to create a dict

    def __call__(self, target):
        return dict(zip(self.keys, super().__call__(target)))


class ItemMap(MapBase, ItemGetter):
    """
    Like `ItemGetter`, but returns a `dict` keyed on requested items.
    """


class AttrMap(MapBase, AttrGetter):
    """
    Like `AttrGetter`, but returns a `dict` keyed on requested attributes. 
    """


# ---------------------------------------------------------------------------- #

class MethodCaller:
    """
    This is adapted from `operator.methodcaller`. The code below is taken from
    'operator.py' (since you can't inherit from `operator.methodcaller!`) with
    only the `__call__` method altered to support chained attribute lookup like:
    >>> MethodCaller('foo.bar.func', *args, **kws)(object)

    Return a callable object that calls the given method on its operand.
    After f = methodcaller('name'), the call f(r) returns r.name().
    After g = methodcaller('name', 'date', foo=1), the call g(r) returns
    r.name('date', foo=1).
    """
    __slots__ = ('_name', '_getter', '_args', '_kwargs')

    def __init__(*args, **kwargs):  # pylint: disable=no-method-argument
        if len(args) < 2:
            msg = (f'{args[0].__class__.__name__} needs at least one argument, '
                   f'the method name')

            raise TypeError(msg)

        self = args[0]
        self._name = args[1]
        self._getter = AttrGetter(self._name)
        if not isinstance(self._name, str):
            raise TypeError(
                f'Method name must be a string, not {type(self._name)}.'
            )
        self._args = args[2:]
        self._kwargs = kwargs

    def __call__(self, obj, *args, **kws):
        return self._getter(obj)(*self._args, *args, **self._kwargs, **kws)

    def __repr__(self):
        args = [repr(self._name),
                *map(repr, self._args)]
        args.extend(f'{k}={v!r}' for k, v in self._kwargs.items())
        kls = type(self)
        return f"{kls.__module__}.{kls.__name__}({', '.join(args)})"

    def __reduce__(self):
        if self._kwargs:
            return (ftl.partial(self.__class__, self._name, **self._kwargs),
                    self._args)

        return self.__class__, (self._name, *self._args)


# ---------------------------------------------------------------------------- #

class MapperBase:
    def __call__(self, target):
        return list(self.map(target))

    def map(self, target):
        assert isinstance(target, abc.Iterable)
        return map(super().__call__, target)

    def filter(self, *args):
        *test, target = args
        return filter((test or None), self.map(target))


class ItemVector(MapperBase, ItemGetter):
    """Vectorized ItemGetter"""


class AttrVector(MapperBase, AttrGetter):  # AttrTable!
    """Attribute getter that fetches across items in a container when called."""


class MethodVector(MethodCaller):
    def __call__(self, target):
        assert isinstance(target, abc.Iterable)
        return list(map(super().__call__, target))


# ---------------------------------------------------------------------------- #
def index(collection, item, start=0, test=eq, default=_NULL):
    """
    Find the index position of `item` in `collection`, or if a test function is
    provided, the first index position for which the test evaluates True. If
    the item is not found, or no items test positive, return the provided
    default value.

    Parameters
    ----------
    collection : list or str
        The items to be searched.
    item : object
        Item to be found.
    start : int, optional
        Optional starting index for the search, by default 0.
    test : callable, optional
        Function used to identify the item. Calling sequence of this function is
        `test(x, item)`, where `x` is an item from the input list. The function
        should return boolean value to indicate whether the position of that
        item is to be returned in the index list. The default is `op.eq`, which
        tests each item for equality with input `item`.
    default : object, optional
        The default to return if `item` was not found in the input list, by
        default None.

    Returns
    -------
    int
        The index position where the first occurance of `item` is found, or
        where `test` evaluates true
    """
    # if not isinstance(l, list):
    #     l = list(l)

    test = test or eq
    for i, x in enumerate(collection[start:], start):
        if test(x, item):
            return i

    # behave like standard indexing by default
    #  -> only if default parameter was explicitly given do we return that
    #   instead of raising a ValueError
    if default is _NULL:
        raise ValueError(f'{item!r} is not in {type(collection).__name__}')

    return default


class contained:  # pylint: disable=invalid-name
    """
    Helper class for condition testing presence of items in sequences.

    Example
    >>> [*map(contained('*').within, ['', '**', '..'])]
    [False, True, False]
    """
    def __new__(cls, *args):
        return (args[0] in args[1]) if len(args) == 2 else super().__new__(cls)

    def __init__(self, item):
        self.item = item

    def __call__(self, container):
        """ item in container"""
        return self.item in container

    def within(self, container):
        return self(container)


class startswith:

    __slots__ = 'item'

    def __new__(cls, *args):
        return (args[0].startswith(args[1])) if len(args) == 2 else super().__new__(cls)

    def __init__(self, item):
        self.item = item

    def __call__(self, container):
        return container.startswith(self.item)


# aliases
itemgetter = ItemGetter
attrgetter = AttrGetter
has = contained
