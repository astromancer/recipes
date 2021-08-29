"""
Recipes involving dictionaries
"""


# std
from collections import abc
from .functionals import Emit
import numbers
import warnings
import itertools as itt
from pathlib import Path
from collections.abc import Hashable
from collections import UserDict, OrderedDict, defaultdict

# third-party
import more_itertools as mit

# relative
from .string import indent


# TODO: a factory function which takes requested props, eg: indexable=True,
# attr=True, ordered=True)
# TODO: factory methods to get class based on what you want: attribute
# lookup, indexability,


def pformat(mapping, name=None, lhs=str, equals=': ', rhs=str, sep=',',
            brackets='{}', hang=False, tabsize=4):
    """
    pformat (nested) dict types

    Parameters
    ----------
    mapping: dict
        Mapping to convert to str
    name
    brackets
    equals

    sep
    converter

    Returns
    -------
    str

    Examples
    --------
    >>> pformat(dict(x='hello',
                        longkey='w',
                        foo=dict(nested=1,
                                what='?',
                                x=dict(triple='nested'))))
    {x      : hello,
     longkey: w,
     foo    : {nested: 1,
               what  : '?',
               x     : {triple: nested}}}

    """
    if name is None:
        kls = type(mapping)
        name = '' if kls is dict else kls.__name__

    brackets = brackets or ('', '')
    if len(brackets) != 2:
        raise ValueError(
            f'Brackets should be a pair of strings, not {brackets!r}'
        )

    string = _pformat(mapping, lhs, equals, rhs, sep, brackets, hang, tabsize)
    ispace = 0 if hang else len(name)
    string = indent(string, ispace)  # f'{" ": <{pre}}
    if name:
        return f'{name}{string}'
    return string


def _pformat(mapping, lhs=str, equals=': ', rhs=str, sep=',', brackets='{}',
             hang=False, tabsize=4):

    # if isinstance(mapping, dict): # abc.MutableMapping
    #     raise TypeError(f'Object of type: {type(mapping)} is not a '
    #                     f'MutableMapping')

    if len(mapping) == 0:
        # empty dict
        return brackets

    string, close = brackets
    if hang:
        string += '\n'
        close = '\n' + close
    else:
        tabsize = len(string)

    # make sure we line up the values
    # note that keys may not be str, so first convert
    keys = tuple(map(lhs, mapping.keys()))
    width = max(map(len, keys))  # + post_sep_space
    indents = itt.chain([hang * tabsize], itt.repeat(tabsize))
    separators = itt.chain(
        itt.repeat(sep + '\n', len(mapping) - 1),
        [close]
    )
    for pre, key, val, post in zip(indents, keys, mapping.values(), separators):
        string += f'{"": <{pre}}{key: <{width}s}{equals}'
        if isinstance(val, dict):  # abc.MutableMapping
            part = _pformat(val, lhs, equals, rhs, sep, brackets)
        else:
            part = rhs(val)

        # objects with multi-line representations need to be indented
        string += indent(part, width + tabsize + 1)
        # item sep / closing bracket
        string += post

    return string


def dump(mapping, filename, **kws):
    """
    Write dict to file in human readable form

    Parameters
    ----------
    mapping : [type]
        [description]
    filename : [type]
        [description]
    """
    Path(filename).write_text(pformat(mapping, **kws))


def invert(d, convertion={list: tuple}):
    inverted = type(d)()
    for key, val in d.items():
        kls = type(val)
        if kls in convertion:
            val = convertion[kls](val)

        if not isinstance(val, Hashable):
            raise ValueError(
                f'Cannot invert dictionary with non-hashable item: {val} of type {type(val)}. You may wish to pass a convertion mapping to this function to aid invertion of dicts containing non-hashable items.')

        inverted[val] = key
    return inverted


# ---------------------------------------------------------------------------- #
class Pprinter:
    """Mixin class that pretty prints dictionary content"""

    def __str__(self):
        return pformat(self, self.__class__.__name__)

    def __repr__(self):
        return pformat(self, self.__class__.__name__)


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

    factory_takes_key = False
    default_factory = None

    def __init__(self, factory=None, *args, **kws):
        # have to do explicit init since class attribute alone doesn't seem to
        # work for specifying default_factory
        super().__init__(factory or self.default_factory, *args, **kws)

    def __missing__(self, key):
        if self.default_factory is None:
            return super().__missing__(key)

        new = self[key] = self.default_factory(
            *[key][:int(self.factory_takes_key)]
        )
        return new


class AutoVivify:
    """Mixin that implements auto-vivification for dictionary types."""
    _av = True
    # _factory = ()

    @classmethod
    def autovivify(cls, b):
        """Turn auto-vivification on / off"""
        cls._av = bool(b)

    def __missing__(self, key):
        if self._av:
            value = self[key] = type(self)()  # *self._factory
            return value
        return super().__missing__(key)


class AVDict(dict, AutoVivify):
    pass


# class Node(defaultdict):
#     def __init__(self, factory, *args, **kws):


# class Tree(defaultdict, AutoVivify):
#     _factory = (defaultdict.default_factory, )

# TODO AttrItemWrite

class AttrBase(dict):
    def copy(self):
        """Ensure instance of same class is returned"""
        return self.__class__(super().copy())


class AttrReadItem(AttrBase):
    """
    Dictionary with item read access through attribute lookup.

    Note: Items keyed on names that are identical to method names of the `dict`
    builtin, eg. 'keys', will not be accessible through attribute lookup.

    Setting attributes on instances of this class is prohibited since it can
    lead to ambiguity. If you want item write access through attributes, use 
    `AttrDict`.

    >>> x = AttrReadItem(hello=0, world=2)
    >>> x.hello, x.world
    (0, 2)
    >>> x['keys'] = None
    >>> x.keys
    <function AttrReadItem.keys>

    """

    def __getattr__(self, attr):
        """
        Try to get the value in the dict associated with key `attr`. If `attr`
        is not a key, try get the attribute from the parent class.
        """
        if attr in self:
            return self[attr]

        return super().__getattribute__(attr)

    # def __setattr__(self, name: str, value):
    # TODO maybe warn once instead
    #     raise AttributeError(
    #         'Setting attributes on {} instances is not allowed. Use `recipes.dicts.AttrDict` if you need item write access through attributes.')


class AttrDict(AttrBase):
    """dict with key access through attribute lookup"""

    # pros: IDE autocomplete works on keys
    # cons: clobbers build in methods like `keys`, `items` etc...
    #     : inheritance: have to init this superclass before all others
    # FIXME: clobbers build in methods like `keys`, `items` etc...
    # check: dict.__dict__

    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self

    def __setstate__(self, state):
        self.__dict__ = self
        return state
    
    # def __reduce__(self):
    #     print('REDUCE! ' * 20)
    #     return dict, ()
    

class OrderedAttrDict(OrderedDict, AttrBase):
    """dict with key access through attribute lookup"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self



class Indexable:
    """
    Mixin class that enables dict item access through integer keys like list

    >>> class X(Indexable, dict):
    >>>     pass

    >>> x = X(zip(('hello', 'world'), (1,2)))
    >>> x[1], x[:1]  # (2, [1])


    """

    def __getitem__(self, key):
        if isinstance(key, numbers.Integral):
            # note, this disallows integer keys for parent object
            l = len(self)
            assert -l <= key < l, 'Invalid index: %r' % key
            return self[list(self.keys())[key]]

        if isinstance(key, slice):
            keys = list(self.keys())
            getter = super().__getitem__
            return [getter(keys[i]) for i in range(len(self))[key]]

        return super().__getitem__(key)


class ListLike(Indexable, OrderedDict, Pprinter):
    """
    Ordered dict with key access via attribute lookup. Also has some
    list-like functionality: indexing by int and appending new data.
    Best of both worlds.
    """
    auto_key_template = 'item%i'

    def __init__(self, items=(), **kws):
        if isinstance(items, (list, tuple, set)):
            # construct from sequence: make keys using `auto_key_template`
            super().__init__()
            for item in items:
                self.append(item)
        else:
            # construct from mapping
            super().__init__(items or (), **kws)

    def __setitem__(self, key, item):
        item = self.convert_item(item)
        OrderedDict.__setitem__(self, key, item)

    def check_item(self, item):
        return True

    def convert_item(self, item):
        return item

    def auto_key(self):
        # auto-generate key
        return self.auto_key_template % len(self)

    def append(self, item):
        self.check_item(item)
        self[self.auto_key()] = self.convert_item(item)


# class Indexable:
#     """Item access through integer keys like list"""
#
#     def __missing__(self, key):
#         if isinstance(key, int):
#             l = len(self)
#             assert -l <= key < l, 'Invalid index: %r' % key
#             return self[list(self.keys())[key]]
#         # if isinstance(key, slice)
#         # cannot do slices here since the are not hashable
#         return super().__missing__(key)


# class ListLike(AttrReadItem, OrderedDict, Indexable):
#     """
#     Ordered dict with key access via attribute lookup. Also has some
#     list-like functionality: indexing by int and appending new data.
#     Best of both worlds.  Also make sure labels are always arrays.
#     """
#      = 'item'
#
#     def __init__(self, groups=None, **kws):
#         # if we get a list / tuple try interpret as list of arrays (group
#         # labels)
#         if groups is None:
#             super().__init__()
#         elif isinstance(groups, (list, tuple)):
#             super().__init__()
#             for i, item in enumerate(groups):
#                 self[self.auto_key()] = self.convert_item(item)
#         else:
#             super().__init__(groups, **kws)
#
#     def __setitem__(self, key, item):
#         item = self.convert_item(item)
#         OrderedDict.__setitem__(self, key, item)
#
#     def convert_item(self, item):
#         return np.array(item, int)
#
#     def auto_key(self):
#         return 'group%i' % len(self)
#
#     def append(self, item):
#         self[self.auto_key()] = self.convert_item(item)
#
#     # def rename(self, group_index, name):
#     #     self[name] = self.pop(group_index)
#
#     @property
#     def sizes(self):
#         return [len(labels) for labels in self.values()]
#
#     def inverse(self):
#         return {lbl: gid for gid, labels in self.items() for lbl in labels}


class Record(Indexable, OrderedAttrDict):
    pass


class TransDict(UserDict):
    """
    A many to one mapping. Provides a generic way of translating keywords to
    their intended meaning. Good for human coders with flaky memory. May be
    confusing to the uninitiated, so use with discretion.

    Examples
    --------
    # TODO

    """

    def __init__(self, dic=None, **kwargs):
        super().__init__(dic, **kwargs)
        self._translated = {}

    def add_translations(self, dic=None, **kwargs):
        """enable on-the-fly shorthand translation"""
        dic = dic or {}
        self._translated.update(dic, **kwargs)

    # alias
    add_trans = add_vocab = add_translations

    def __contains__(self, key):
        return super().__contains__(self._translated.get(key, key))

    def __missing__(self, key):
        """if key not in keywords, try translate"""
        return self[self._translated[key]]

    # def allkeys(self):
    #     # TODO: Keysview**
    #     return flatiter((self.keys(), self._translated.keys()))

    def many2one(self, many2one):
        # self[one]       # error check
        for many, one in many2one.items():
            for key in many:
                self._translated[key] = one


class ManyToOneMap(TransDict):
    """
    Expands on TransDict by adding equivalence mapping functions for keywords
    """

    warn = True

    def __init__(self, dic=None, **kwargs):
        super().__init__(dic, **kwargs)
        # equivalence mappings - callables that return the desired item
        self._mappings = []

    def __missing__(self, key):
        try:
            # try translate with vocab
            return super().__missing__(key)
        except KeyError as err:
            for resolved in self._loop_mappings(key):
                if super().__contains__(resolved):
                    return self[resolved]
            raise err from None

    def add_mapping(self, func):
        if not callable(func):
            raise ValueError(f'{func} object is not callable')
        self._mappings.append(func)

    def add_mappings(self, *funcs):
        for func in funcs:
            self.add_mapping(func)

    def _loop_mappings(self, key):
        # try translate with equivalence maps
        for func in self._mappings:
            try:
                yield func(key)
            except Exception as err:
                if self.warn:
                    warnings.warn(
                        f'Equivalence mapping function failed with:\n{err!s}')

    def resolve(self, key):
        # try translate with vocab
        resolved = self._translated.get(key, key)
        if resolved in self:
            return resolved

        # resolve by looping through mappings
        for resolved in self._loop_mappings(key):
            if resolved in self:
                return resolved

    def __contains__(self, key):
        if super().__contains__(key):
            return True  # no translation needed

        for resolved in self._loop_mappings(key):
            return super().__contains__(resolved)

        return False


class IndexableOrderedDict(OrderedDict):
    def __missing__(self, key):
        if isinstance(key, int):
            return self[list(self.keys())[key]]

        # noinspection PyUnresolvedReferences
        return OrderedDict.__missing__(self, key)


class DefaultOrderedDict(OrderedDict):
    # Source: http://stackoverflow.com/a/6190500/562769
    # Note: dict order is gauranteed since pyhton 3.7
    def __init__(self, default_factory=None, mapping=(), **kws):
        if not (default_factory is None or callable(default_factory)):
            raise TypeError('first argument must be callable')

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

    def __deepcopy__(self, memo):
        import copy
        return type(self)(self.default_factory,
                          copy.deepcopy(self.items()))

    def __repr__(self):
        return '%s(%s, %s)' % (self.__class__.__name__,
                               self.default_factory,
                               OrderedDict.__repr__(self))

