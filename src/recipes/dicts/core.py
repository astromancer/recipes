"""
Recipes extending mutable mapping functionality.
"""


# std
import os
import numbers
import itertools as itt
from pathlib import Path
from collections import OrderedDict, UserDict, abc, defaultdict

# third-party
import more_itertools as mit

# relative
from ..flow import Emit
from ..string import indent
from ..utils import is_scalar


# TODO: a factory function which takes requested props, eg:
# indexable=True, attr='r', ordered=True)

# ---------------------------------------------------------------------------- #

def isdict(obj):
    return isinstance(obj, abc.MutableMapping)


is_dict = isdict


# ---------------------------------------------------------------------------- #
def pformat(mapping, name=None,
            lhs=repr, equal=': ', rhs=repr,
            sep=',', brackets='{}',
            align=None, hang=False,
            tabsize=4, newline=os.linesep,
            ignore=()):
    """
    Pretty format (nested) dicts.

    Parameters
    ----------
    mapping : MutableMapping
        Mapping to represent as string.
    name : str, optional
        Name given to the object, the object class name is used by default. In
        the case of `mapping` being a builtin `dict` type, the name is set to an
        empty string in order to render them in a similar style to what builtin
        produces.
    lhs : Callable or dict of callable, optional
        Function used to format dictionary keys, by default repr.
    equal  : str, optional
        Symbol used for equal sign, by default ': '.
    rhs : Callable or dict of callable, optional
        Function used to format dictionary values, by default repr.
    sep : str, optional
        String used to separate successive key-value pairs, by default ','.
    brackets : str or Sequence of length 2, optional
        Characters used for enclosing brackets, by default '{}'.
    align : bool, optional
        Whether to align values (right hand side) in a column, by default True
        if `newline` contains and actual newline character '\\n' else False.
    hang : bool, optional
        Whether to hang the first key-value pair on a new line, by default False.
    tabsize : int, optional
        Number of spaces to use for indentation, by default 4.
    newline : str, optional
        Newline character, by default os.linesep.
    ignore : tuple of str
        Keys that will be omitted in the representation of the mapping.

    Returns
    -------
    str
        Pretty representation of the dict.

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

    Raises
    ------
    TypeError
        If the input is not a MutableMapping.
    ValueError
        _description_
    """
    if not isinstance(mapping, abc.MutableMapping):
        raise TypeError(f'Object of type: {type(mapping)} is not a '
                        'MutableMapping')

    if name is None:
        name = ('' if (kls := type(mapping)) is dict else kls.__name__)

    brackets = brackets or ('', '')
    if len(brackets) != 2:
        raise ValueError(
            f'Brackets should be a pair of strings, not {brackets!r}.'
        )

    # set default align flag
    if align is None:
        align = os.linesep in newline

    # format
    string = _pformat(mapping,
                      # resolve formatting functions
                      _get_formatters(lhs), equal, _get_formatters(rhs),
                      sep, brackets,
                      align, hang,
                      tabsize, newline,
                      ignore)
    ispace = 0 if hang else len(name)
    string = indent(string, ispace)  # f'{" ": <{pre}}
    return f'{name}{string}' if name else string


def _get_formatters(fmt):
    # Check formatters are valid callables
    # Retruns
    # A defaultdict that returns `repr` as the default formatter

    if callable(fmt):
        return defaultdict(lambda: fmt)

    if not isinstance(fmt, abc.MutableMapping):
        raise TypeError(
            f'Invalid formatter type {type(fmt)}. Key/value formatters should '
            f'be callable, or a mapping of callables.'
        )

    for key, func in fmt.items():
        if callable(func):
            continue

        raise TypeError(
            f'Invalid formatter type {type(fmt)} for key {key!r}. Key/value '
            f'formatters should be callable.'
        )

    return defaultdict((lambda: repr), fmt)


def _pformat(mapping, lhs_func_dict, equal, rhs_func_dict, sep, brackets,
             align, hang, tabsize, newline, ignore):

    if len(mapping) == 0:
        # empty dict
        return brackets

    # remove ignored keys
    if remove_keys := set(mapping.keys()) & set(ignore):
        mapping = mapping.copy()
        for key in remove_keys:
            mapping.pop(key)

    # note that keys may not be str, so first convert
    keys = tuple(lhs_func_dict[key](key) for key in mapping.keys())
    keys_size = list(map(len, keys))

    string, close = brackets
    pos = len(string)
    if align:
        # make sure we line up the values
        leqs = len(equal)
        width = max(keys_size)
        wspace = [width - w + leqs for w in keys_size]
    else:
        wspace = itt.repeat(1)

    if hang:
        string += newline
        close = newline + close
    else:
        tabsize = pos

    indents = mit.padded([hang * tabsize], tabsize)
    separators = itt.chain(
        itt.repeat(sep + newline, len(mapping) - 1),
        [close]
    )
    for pre, key, (okey, val), wspace, end in \
            zip(indents, keys, mapping.items(), wspace, separators):
        # THIS places ':' directly before value
        # string += f'{"": <{pre}}{key: <{width}s}{equal }'
        # WHILE this places it directly after key
        # print(f'{pre=:} {key=:} {width=:}')
        # print(repr(f'{"": <{pre}}{key}{equal: <{width}s}'))
        # new = f'{"": <{pre}}{key}{equal: <{width}s}'
        string += f'{"": <{pre}}{key}{equal: <{wspace}s}'

        if isinstance(val, abc.MutableMapping):
            part = _pformat(val, lhs_func_dict, equal, rhs_func_dict, sep,
                            brackets, align, hang, tabsize, newline, ignore)
        else:
            part = rhs_func_dict[okey](val)

        # objects with multi-line representations need to be indented
        # `post` is item sep or closing bracket
        string += f'{indent(part, tabsize + len(key) + wspace)}{end}'

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


def invert(d, conversion=None):
    if conversion is None:
        conversion = {list: tuple}

    inverted = type(d)()
    for key, val in d.items():
        kls = type(val)
        if kls in conversion:
            val = conversion[kls](val)

        if not isinstance(val, abc.Hashable):
            raise ValueError(
                f'Cannot invert dictionary with non-hashable item: {val} of '
                f'type {type(val)}. You may wish to pass a conversion mapping '
                f'to this function to aid invertion of dicts containing non-'
                f'hashable items.'
            )

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
    ...        for case in (str.upper, str.lower) for letter in 'abc'),
    ...       z=100)
    {'A': 65, 'B': 66, 'C': 67, 'a': 97, 'b': 98, 'c': 99, 'z': 100}

    Returns
    -------
    dict
        Merged dictionary.
    """

    out = {}
    for mapping in mappings:
        out.update(mapping)
    out.update(kws)
    return out


# ---------------------------------------------------------------------------- #


def _split(mapping, keys):
    for key in keys:
        if key in mapping:
            yield key, mapping.pop(key)


def split(mapping, keys, *extra):
    if isinstance(keys, str):
        keys = keys,

    keys = (*keys, *extra)
    return mapping, dict(_split(mapping, keys))


def remove(mapping, keys, *extra):
    split(mapping, keys, *extra)
    return mapping

# ---------------------------------------------------------------------------- #


class Pprinter:
    """Mixin class that pretty prints dictionary content."""

    def __str__(self):
        return pformat(self)  # self.__class__.__name__

    def __repr__(self):
        return pformat(self)  # self.__class__.__name__

    def pformat(self, **kws):
        return pformat(self, **kws)

    def pprint(self, **kws):
        print(self.pformat(**kws))


# alias
PPrinter = Pprinter


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
    # default_factory = None
    factory_uses_key = False  # TODO: can detect this by inspection

    # def __init__(self, factory=None, *args, **kws):
    #     # have to do explicit init since class attribute alone doesn't seem to
    #     # work for specifying default_factory
    #     defaultdict.__init__(self, factory or self.default_factory, *args, **kws)

    def __missing__(self, key):
        if self.default_factory is None:
            # super handles / throws
            return defaultdict.__missing__(self, key)

        # construct default object
        new = self[key] = self.default_factory(*[key][:int(self.factory_uses_key)])
        return new


# ---------------------------------------------------------------------------- #


class vdict(dict):
    """
    Dictionary with vectorized item lookup.
    """
    _wrapper = list

    def __getitem__(self, key):
        # dispatch on list, np.ndarray for vectorized item getting with
        # arbitrary nesting
        try:
            return super().__getitem__(key)
        except (KeyError, TypeError) as err:
            # vectorization
            if not is_scalar(key):
                # Container and not str
                return self._wrapper(self[_] for _ in key)

            if key in (Ellipsis, None):
                return self._wrapper(self.values())

            raise err from None


# ---------------------------------------------------------------------------- #
class _AccessManager:
    """
    Mixin that toggles read/write access.
    """

    _readonly = False
    _message = '{self.__class__.__name__}: write access disabled.'

    @property
    def readonly(self):
        return self._readonly

    @readonly.setter
    def readonly(self, readonly):
        self._readonly = bool(readonly)

    def freeze(self):
        self.readonly = True

    def unfreeze(self):
        self.readonly = False

    def __missing__(self, key):
        if self.readonly:
            raise KeyError(self._message.format(self=self))

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
# TODO AttrItemWrite


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

    # def __reduce__(self):
    #     print('REDUCE! ' * 20)
    #     return dict, ()


class OrderedAttrDict(OrderedDict, AttrBase):
    """OrderedDict with key access through attribute lookup."""

    def __init__(self, *args, **kws):
        super().__init__(*args, **kws)
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
        Add many keys to the existing dict that all map to the same key

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

    many2one = many_to_one


class ManyToOneMap(TransDict):
    """
    Expands on TransDict by adding equivalence mapping functions for keywords.
    """

    emit = Emit('raise')

    def __init__(self, dic=None, **kws):
        super().__init__(dic, **kws)
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
            raise ValueError(f'{func} object is not callable.')
        self._mappings.append(func)

    def add_funcs(self, *funcs):
        for func in funcs:
            self.add_func(func)

    def _loop_translators(self, key):
        # try translate with equivalence maps
        for func in self._mappings:
            # yield catch(func, message=message)(key)
            try:
                translated = func(key)
                if translated is not None:
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

    def __deepcopy__(self, memo):
        import copy
        return type(self)(self.default_factory,
                          copy.deepcopy(self.items()))

    def __repr__(self):
        return (f'{self.__class__.__name__}({self.default_factory}, '
                f'{OrderedDict.__repr__(self)})')


# alias
OrderedDefaultDict = DefaultOrderedDict
