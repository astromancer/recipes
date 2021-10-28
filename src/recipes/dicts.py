"""
Recipes involving dictionaries
"""


# std
import numbers
import itertools as itt
from pathlib import Path
from collections.abc import Hashable
from collections import OrderedDict, UserDict, abc, defaultdict

# third-party
import more_itertools as mit

# relative
from .string import indent
from .functionals import Emit


# TODO: a factory function which takes requested props, eg: indexable=True,
# attr=True, ordered=True)
# TODO: factory methods to get class based on what you want: attribute
# lookup, indexability,


def pformat(mapping, name=None, lhs=repr, equals=': ', rhs=repr, sep=',',
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
    indents = mit.padded([hang * tabsize], tabsize)
    separators = itt.chain(
        itt.repeat(sep + '\n', len(mapping) - 1),
        [close]
    )
    for pre, key, val, post in zip(indents, keys, mapping.values(), separators):
        # THIS places ':' directly before value
        # string += f'{"": <{pre}}{key: <{width}s}{equals}'
        # WHILE this places it directly after key
        string += f'{"": <{pre}}{key}{equals: <{width - len(key) + len(equals)}s}'
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


def groupby(items, func):
    """Convert itt.groupby to a dict"""
    return {group: list(itr) for group, itr in itt.groupby(items, func)}


def merge(*mappings, **kws):
    """
    Merge an arbitrary number of dictionaries together by repeated update.

    Examples
    --------
    >>> merge(*({f'{(l := case(letter))}': ord(l)} 
    ...        for case in (str.upper, str.lower) for letter in 'abc'))
    {'A': 65, 'B': 66, 'C': 67, 'a': 97, 'b': 98, 'c': 99}

    Returns
    -------
    dict
        Merged dict

    """
    out = {}
    for mapping in mappings:
        out.update(mapping)
    out.update(kws)
    return out

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

    factory_takes_key = False  # TODO: can detect this by inspection
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


class TreeLike(AttrDict, AutoVivify):
    def __init__(self, mapping=(), **kws):
        super().__init__()
        kws.update(mapping)
        for a, v in kws.items():
            self[a] = v

    def __setitem__(self, key, val):
        if '.' in key:
            key, tail = key.split('.', 1)
            self[key][tail] = val
        else:
            super().__setitem__(key, val)


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
    A many to one mapping via layered dictionaries. Provides a generic way of
    translating keywords to their intended meaning. Good for human coders with
    flaky memory. May be confusing to the uninitiated, so use with discretion.

    Examples
    --------
    # TODO

    """

    def __init__(self, dic=None, **kwargs):
        super().__init__(dic, **kwargs)
        self.dictionary = {}

    def add_mapping(self, dic=None, **kwargs):
        """Add translation dictionary"""
        dic = dic or {}
        self.dictionary.update(dic, **kwargs)

    # alias
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
        Add many keys to the existing dict that all map to the same key

        Parameters
        ----------
        mapping : dict or collection of 2-tuples
            Keys are tuples of objects mapping to a single object.


        Examples
        --------
        >>> d.many_to_one({'all', 'these', 'keys', 'will', 'map to':
                           'THIS VALUE')
        ... d['all'] == d['these'] == 'THIS VALUE'
        True
        """
        # self[one]       # error check
        for many, one in dict(mapping).items():
            for key in many:
                self.dictionary[key] = one

    many2one = many_to_one


class ManyToOneMap(TransDict):
    """
    Expands on TransDict by adding equivalence mapping functions for keywords.
    """

    emit = Emit(1)

    def __init__(self, dic=None, **kwargs):
        super().__init__(dic, **kwargs)
        # equivalence mappings - callables that return the desired item.
        self._mappings = []

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

    def add(self, obj):
        """Add translation function / dictionary dispatching on type"""
        if isinstance(obj, abc.MutableMapping):
            self.add_mapping(obj)
        elif callable(obj):
            self.add_func(obj)
        else:
            raise TypeError(
                f'Invalid translation object {obj!r} of type {type(obj)!r}.'
            )

    def add_func(self, func):
        if not callable(func):
            raise ValueError(f'{func} object is not callable')
        self._mappings.append(func)

    def add_funcs(self, *funcs):
        for func in funcs:
            self.add_func(func)

    def _loop_translators(self, key):
        # try translate with equivalence maps
        for func in self._mappings:
            # yield catch(func, message=message)(key)
            try:
                yield func(key)
            except Exception as err:
                self.emit(
                    f'{type(self).__name__}: Equivalence mapping function'
                    f' failed with:\n{err!s}'
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
