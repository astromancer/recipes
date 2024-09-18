"""
Recipes extending mutable mapping functionality.
"""


# std
import numbers
import warnings as wrn
import itertools as itt
from collections import OrderedDict, UserDict, abc, defaultdict

# third-party
import more_itertools as mit

# relative
from ...flow import Emit
from ...string import named_items
from ...functionals import echo0, raises
from ...pprint.mapping import PrettyPrint
from .. import ensure


# ---------------------------------------------------------------------------- #
NULL = object()


def factory(name, attrs='read', ordered=False, lookup='vectors', default=NULL,
            invertible=False, aliases=(), pprint=False):

    # TODO: a factory function which takes requested props, eg:
    bases = tuple(_get_bases(attrs, ordered, lookup, default, invertible, pprint))

    namespace = {}
    if default is not NULL:
        namespace['default_factory'] = lambda: default

    return type(name, bases, namespace)


def _get_bases(attrs='read', ordered=False, lookup='vectors', default=NULL,
               invertible=False, pprint=True):

    if attrs:
        yield _AccessManager

    if ordered:
        yield OrderedDict

    if default is not NULL:
        if default == 'autovivify':
            yield AutoViviify
        else:
            yield DefaultDict

    if lookup:
        yield _lookup_bases[lookup]

    if invertible:
        yield Invertible

    if pprint:
        yield PrettyPrint


# ---------------------------------------------------------------------------- #

class Invertible:
    """
    Mixin class for invertible mappings
    """

    def is_invertible(self):
        """check whether dict can be inverted"""
        # TODO
        return True

    def inverse(self):
        if self.is_invertible():
            return self.__class__.__bases__[1](zip(self.values(), self.keys()))


# class InvertibleDict(Invertible, dict):
#     pass

class DefaultDict(defaultdict):
    """
    Default dict that allows default factories which take the key as an
    argument.
    """

    _factory_uses_key = False      # TODO: can detect this by inspection

    # @property
    # def default_factory(self, func):

    # def __init__(self, factory=None, *args, **kws):
    #     # have to do explicit init since class attribute alone doesn't seem to
    #     # work for specifying default_factory
    #     defaultdict.__init__(self, factory or self.default_factory, *args, **kws)

    def __missing__(self, key):
        if self.default_factory is None:
            # super handles / throws
            return defaultdict.__missing__(self, key)

        # construct default object
        new = self[key] = self.default_factory(*[key][:int(self._factory_uses_key)])
        return new


# ---------------------------------------------------------------------------- #


class SpecialLookup:
    """
    Mixin for dispatching item lookup on arbitrary key types.
    """

    _handles = ()
    _ignores = ()
    _wrapper = tuple

    @classmethod
    def __handles(cls, key):
        return (isinstance(key, cls._handles) and not
                (cls._ignores and isinstance(key, cls._ignores)))

    def __setitem__(self, key, val):
        if self.__handles(key):
            raise TypeError(
                f'Object of type {type(key)!r} are not allowed as keys, '
                f'since they are used for dispatching special lookup.'
            )

        super().__setitem__(key, val)

    def __getitem__(self, key):
        if self.__handles(key):
            return self.__missing__(key)

        return super().__getitem__(key)

    def __missing__(self, key):
        if hasattr(super(), '__missing__'):
            return super().__missing__(key)
        raise KeyError(key)


def _int_lookup(mapping, index):
    if isinstance(index, numbers.Integral):
        size = len(mapping)
        if -size <= index < size:
            raise ValueError(f'Invalid index: {index!r} for size {size} '
                             f'mapping {type(mapping).__name__}.')
        if index < 0:
            index += size
        return mapping[mit.nth(mapping.keys(), index)]

    raise TypeError(f'Invalid type object {index} for indexing.')


class LookupAt:
    """
    Mixin that provides the `at` function for indexing ordered dicts with integers
    """

    def at(self, index):
        return _int_lookup(self, index)


class IntegerLookup(SpecialLookup):
    """
    Mixin class that enables dict item lookup with integer keys like list
    indexing. This class will prevent you from using integers as keys in the
    dict since that would be ambiguous. If you need both int keys and sequence
    position lookup, this can be done with the `at` method of the `LookupAt`
    mixin.

    >>> class X(IntegerLookup, dict):
    >>>     pass

    >>> x = X(zip(('hello', 'world'), (1,2)))
    >>> x[1]  # [1]

    """
    _handles = (numbers.Integral, )

    def __missing__(self, index):
        return _int_lookup(self, index)


class VectorLookup(SpecialLookup):
    """
    Mixin for vectorized item lookup.
    """
    _handles = (type(...), slice, abc.Sized)
    _ignores = (str, bytes)

    def __missing__(self, key):
        # dispatch on array-like objects for vectorized item lookup with
        # arbitrary nesting
        if key is ...:
            return self._wrapper(self.values())

        if isinstance(key, slice):
            getter = super().__getitem__
            return self._wrapper(getter(key) for key in
                                 itt.islice(self.keys(), key.start, key.stop))

        # here we have some `Sized` object that is not `str` or `bytes`
        # => vectorize
        return self._wrapper(self[_] for _ in key)


_lookup_bases = {'vectors': VectorLookup,
                 'int': IntegerLookup,
                 int: IntegerLookup}


class vdict(VectorLookup, dict):
    """
    Dictionary with vectorized item lookup.
    """
    _wrapper = list


# ---------------------------------------------------------------------------- #

class IndexableOrderedDict(IntegerLookup, OrderedDict):
    pass


class ListLike(IndexableOrderedDict):
    """
    Ordered dict with key access via attribute lookup. Also has some
    list-like functionality: indexing by int and appending new data.
    Best of both worlds.
    """
    _auto_key_template = 'item{}'
    _auto_key_counter = itt.count()

    def __init__(self, items=(), **kws):
        if ensure.is_scalar(items):
            # construct from mapping
            return super().__init__(items or (), **kws)

        # construct from sequence: make keys using `_auto_key_template`
        super().__init__(**kws)
        for item in items:
            self.append(item)

    def _auto_key(self):
        # auto-generate key
        return self._auto_key_template.format(next(self._auto_key_counter))

    def append(self, item):
        super().__setitem__(self._auto_key(), item)


class Record(OrderedDict, LookupAt, PrettyPrint):
    """
    Ordered dict with key access via attribute lookup. Also has some
    list-like functionality: indexing by int.
    """
    pass


class DefaultOrderedDict(OrderedDict):
    # Source: http://stackoverflow.com/a/6190500/562769
    # Note: dict order is gauranteed since pyhton 3.7

    def __init__(self, default_factory=None, mapping=(), **kws):
        if not (default_factory is None or callable(default_factory)):
            raise TypeError(
                f'First argument to {self.__class__.__name__} must be callable.'
            )

        OrderedDict.__init__(self, mapping, **kws)
        self.default_factory = default_factory

    def __getitem__(self, key):
        try:
            return OrderedDict.__getitem__(self, key)
        except KeyError:
            return self.__missing__(key)

    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError(key)

        self[key] = value = self.default_factory()
        return value

    def __reduce__(self):
        args = (self.default_factory, ) if self.default_factory else ()
        return type(self), args, None, None, self.items()

    def copy(self):
        return self.__copy__()

    def __copy__(self):
        return type(self)(self.default_factory, self)

    def __deepcopy__(self):
        import copy
        return type(self)(self.default_factory,
                          copy.deepcopy(self.items()))

    # def __repr__(self):
    #     return (f'{self.__class__.__name__}({self.default_factory}, '
    #             f'{OrderedDict.__repr__(self)})')


# alias
OrderedDefaultDict = DefaultOrderedDict


# ---------------------------------------------------------------------------- #

class _AccessManager:
    """
    Mixin that toggles read/write access.
    """

    _readonly = False
    _message = ('Key {key!r} not found in {self.__class__.__name__}. Available '
                'keys: {available}. Write access is disabled.')

    @property
    def readonly(self):
        return self._readonly

    @readonly.setter
    def readonly(self, readonly):
        self._readonly = bool(readonly)

    def freeze(self):
        self.readonly = True
        return self

    def unfreeze(self):
        self.readonly = False
        return self

    def __missing__(self, key):
        if self.readonly:
            raise KeyError(self._message.format(self=self, key=key,
                                                available=tuple(self.keys())))

        super().__missing__(key)


class AutoVivify(_AccessManager):
    """
    Mixin that implements auto-vivification for dictionary types.
    """

    @classmethod
    def autovivify(cls, b):
        """Turn auto-vivify on / off *for all instances of this class*."""
        cls._readonly = not bool(b)

    def __missing__(self, key):
        """
        Lookup for missing keys in the dict creates a new empty object if not
        readonly and returns it.
        """
        if self.readonly:
            return super().__missing__(key)

        value = self[key] = type(self)()
        return value


# ---------------------------------------------------------------------------- #

class AttrBase(dict):
    def copy(self):
        """Ensure instance of same class is returned."""
        return self.__class__(super().copy())


class _AttrReadItem:

    def __getattr__(self, key):
        """
        Try to get the value in the dict associated with key `key`. If `key`
        is not a key in the dict, try get the attribute from the parent class.
        """
        return self[key] if key in self else super().__getattribute__(key)


class AttrReadItem(AttrBase, _AttrReadItem):
    """
    Dictionary with item read access through attribute lookup.

    >>> x = AttrReadItem(hello=0, world=2)
    >>> x.hello, x.world
    (0, 2)

    Note: Items keyed on names that are identical to method names of `dict`
    eg. 'keys', will not be accessible through attribute lookup.

    >>> x['keys'] = None
    >>> x.keys
    <function AttrReadItem.keys>
    >>> print(x)
    {'hello': 0, 'world': 2, 'keys': None}

    Setting attributes on instances of this class is prohibited since it can
    lead to ambiguity. If you want item write access through attributes, use the
    `AttrDict` object.
    """

    # def __setattr__(self, name: str, value):
    # # TODO maybe warn once instead
    #     raise AttributeError(
    #         'Setting attributes on {} instances is not allowed. Use '
    #         '`recipes.dicts.AttrDict` if you need item write access through '
    #         'attributes.')


# TODO AttrReadWrite


class AttrDict(AttrBase):
    """dict with key access through attribute lookup"""

    # pros: IDE autocomplete works on keys
    # cons: clobbers build in methods like `keys`, `items` etc...
    #     : inheritance: have to init this superclass before all others

    # FIXME: clobbers build in methods like `keys`, `items` etc...
    # disallowed = tuple(dict.__dict__.keys())

    def __init__(self, *args, **kws):
        super().__init__(*args, **kws)
        self.__dict__ = self

    def __setstate__(self, state):
        self.__dict__ = self
        return state


class OrderedAttrDict(OrderedDict, AttrReadItem):
    """OrderedDict with key access through attribute lookup."""

    def __init__(self, *args, **kws):
        super().__init__(*args, **kws)
        self.__dict__ = self


# ---------------------------------------------------------------------------- #

# TODO: check TypeEnforcer Mixin form pyxides ??

class ItemConverter:
    def __init__(self, *args, **kws):
        super().__init__(*args, **kws)
        self.update(zip(self.keys(), self.values()))

    def __setitem__(self, key, item):
        super().__setitem__(key,  self._convert_item(item))

    def _convert_item(self, val):
        return val

    def update(self, items, **kws):
        for k, v in dict(items, **kws).items():
            self[k] = v

    # def _check_item(self, item):
    #     return True


# ---------------------------------------------------------------------------- #

class ManyToOne(UserDict):  # TranslationLayer
    """
    A many to one mapping via layered dictionaries. Provides a generic way of
    translating keywords to their intended meaning. Good for human coders with
    flaky memory. May be confusing to the uninitiated, so use with discretion.

    Examples
    --------
    # TODO

    """

    def __init__(self, dic=None, **kws):
        super().__init__(dic, **kws)
        self.dictionary = {}

    def add_mapping(self, dic=None, **kws):
        """Add translation dictionary"""
        dic = dic or {}
        self.dictionary.update(dic, **kws)

    # aliases
    add_trans = add_vocab = add_translations = add_mapping

    def __contains__(self, key):
        return super().__contains__(self.dictionary.get(key, key))

    def __missing__(self, key):
        """if key not in keywords, try translate"""
        return self[self.dictionary[key]]

    # def allkeys(self):
    #     # TODO: Keysview**
    #     return flatiter((self.keys(), self.dictionary.keys()))

    def many_to_one(self, mapping):
        """
        Add many keys to the existing dict that all map to the same key.

        Parameters
        ----------
        mapping : dict or collection of 2-tuples
            Keys are tuples of objects mapping to a single object.


        Examples
        --------
        >>> d.many_to_one({('all', 'these', 'keys', 'will', 'map to'):
                           'THIS VALUE')
        ... d['all'] == d['these'] == 'THIS VALUE'
        True
        """
        # self[one]       # error check
        for many, one in dict(mapping).items():
            for key in many:
                self.dictionary[key] = one

    # alias
    many2one = many_to_one


class TranslatorMap(ManyToOne):
    """
    Expands on ManyToOne by adding equivalence mapping functions for keywords.
    """

    emit = Emit('raise')

    def __init__(self, dic=None, **kws):
        super().__init__(dic, **kws)
        # equivalence mappings - callables that return the desired item.
        self.translators = []

    def __missing__(self, key):
        try:
            # try translate via `dictionary`
            return super().__missing__(key)
        except KeyError as err:
            # FIXME: does what `resolve` does??
            for resolved in self._loop_translators(key):
                if super().__contains__(resolved):
                    return self[resolved]
            raise err from None

    def add(self, translator):
        """Add translation function / dictionary dispatching on type"""
        if isinstance(translator, abc.MutableMapping):
            return self.add_mapping(translator)

        if callable(translator):
            return self.add_func(translator)

        raise TypeError(f'Invalid translator object {translator!r} of '
                        f'type {type(translator)!r}.')

    def add_func(self, func):
        if callable(func):
            return self.translators.append(func)

        raise ValueError(f'{func} object is not callable.')

    def add_funcs(self, *funcs):
        for func in funcs:
            self.add_func(func)

    def _loop_translators(self, key):
        # try translate with equivalence maps
        for func in self.translators:
            # yield catch(func, message=message)(key)
            try:
                if (translated := func(key)) is not None:
                    yield translated
            except Exception as err:
                self.emit(
                    f'{type(self).__name__}: Keyword translation function '
                    f'failed with:\n{err!s}.'
                )

    def resolve(self, key):
        # FIXME: return sentinel as `None` can be a valid mapping value
        # try translate with vocab
        resolved = self.dictionary.get(key, key)
        if resolved in self:
            return resolved

        # resolve by looping through mappings
        for resolved in self._loop_translators(key):
            if resolved in self:
                return resolved

    def __contains__(self, key):
        if super().__contains__(key):
            return True  # no translation needed

        for resolved in self._loop_translators(key):
            return super().__contains__(resolved)

        return False

# ---------------------------------------------------------------------------- #
