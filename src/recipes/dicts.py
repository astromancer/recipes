"""
Recipes involving dictionaries
"""

# std libs
import itertools as itt
import warnings
import types
import re
import numbers
from collections import abc, UserDict, OrderedDict, defaultdict
from .string import indent, brackets as bkt
from pathlib import Path
from collections.abc import Hashable


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


class AttrDict(dict):
    """dict with key access through attribute lookup"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self
        # pros: IDE autocomplete works on keys
        # cons: inheritance: have to init this superclass before all others

    def copy(self):
        """Ensure instance of same class is returned"""
        cls = self.__class__
        return cls(super(cls, self).copy())


class OrderedAttrDict(OrderedDict):
    """dict with key access through attribute lookup"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self

    def copy(self):
        """Ensure instance of same class is returned"""
        cls = self.__class__
        return cls(super(cls, self).copy())


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
    _auto_name_fmt = 'item%i'

    def __init__(self, items=None, **kws):
        if items is None:
            # construct from keywords
            super().__init__(**kws)
        elif isinstance(items, (list, tuple)):
            # construct from sequence: make keys using `_auto_name_fmt`
            super().__init__()
            for i, item in enumerate(items):
                if self._allow_item(item):
                    self[self._auto_name()] = self._convert_item(item)
        else:
            # construct from mapping
            super().__init__(items, **kws)

    def __setitem__(self, key, item):
        item = self._convert_item(item)
        OrderedDict.__setitem__(self, key, item)

    def _allow_item(self, item):
        return True

    def _convert_item(self, item):
        return item

    def _auto_name(self):
        return self._auto_name_fmt % len(self)

    def append(self, item):
        self[self._auto_name()] = self._convert_item(item)


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


class AttrReadItem(dict):
    """
    Dictionary with item access through attribute lookup.

    Note: Items keyed on names that are identical to the `dict` builtin
     methods, eg. 'keys', will not be accessible through attribute lookup.

    >>> x = AttrReadItem(hello=0, world=2)
    >>> x.hello, x.world
    (0, 2)
    >>> x['keys'] = None
    >>> x.keys
    <function AttrReadItem.keys>
    """

    # TODO: raise when trying to set attributes??

    def __getattr__(self, attr):
        """
        Try to get the value in the dict associated with `attr`. If attr is
        not a key, try get the attribute.
        """
        if attr in self:
            return self[attr]
            # return super().__getitem__(attr)
        #
        # try:
        return super().__getattribute__(attr)
        # except Exception:
        #     raise AttributeError('%r object has no attribute %r' %
        #                          (self.__class__.__name__, attr))


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
#                 self[self._auto_name()] = self._convert_item(item)
#         else:
#             super().__init__(groups, **kws)
#
#     def __setitem__(self, key, item):
#         item = self._convert_item(item)
#         OrderedDict.__setitem__(self, key, item)
#
#     def _convert_item(self, item):
#         return np.array(item, int)
#
#     def _auto_name(self):
#         return 'group%i' % len(self)
#
#     def append(self, item):
#         self[self._auto_name()] = self._convert_item(item)
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


def SENTINEL():
    pass


class TerseKws:
    """
    Class to assist many-to-one keard mappings
    """

    def __init__(self, pattern, answer=None):
        """

        Parameters
        ----------
        pattern
        answer
        """
        regex = ''
        self.answer = ''
        self.pattern = pattern
        sub = pattern
        while 1:
            s, (i0, i1) = bkt.square.match(sub, return_index=True,
                                           must_close=True)
            # print(s, i0, i1)
            if s is None:
                regex += sub
                break

            regex += f'{sub[:i0]}[{s}]{{0,{len(s)}}}'
            self.answer += sub[:i0]
            sub = sub[i1 + 1:]

            # print(sub, regex)
            # i += 1
        self.regex = re.compile(regex)

        if answer:
            self.answer = answer  # str(answer)

    def __call__(self, s):
        if self.regex.fullmatch(s):
            return self.answer
        # return SENTINEL singleton here instead of None since None
        # could be a valid dict entry
        return SENTINEL

    def __repr__(self):
        return f'{self.__class__.__name__}({self.pattern} --> {self.answer})'


class KeywordResolver:
    """Helper class for resolving terse keywords"""

    # TODO: as a decorator!!
    # TODO: detect ambiguous mappings
    # TODO: expand to handle arbitrary (non-keyword) mappings

    def __init__(self, mappings):
        self.mappings = []
        for k, v in mappings.items():
            # if isinstance(k, str)

            self.mappings.append(TerseKws(k, v))

    def __repr__(self):
        return repr(self.mappings)

    # def __call__(self,func):
    #     self.func = func

    def resolve(self, func, kws, namespace=None):
        """
        map terse keywords in `kws` to their full form. 
        If given, values from the `namespace` dict replace those in kws
        if their corresponging keywords are valid parameter names for `func` 
        and they are non-default values
        """
        # get arg names and defaults
        # TODO: use inspect.signature here ?
        code = func.__code__
        defaults = func.__defaults__
        arg_names = code.co_varnames[1:code.co_argcount]

        # load the defaults / passed args
        n_req_args = len(arg_names) - len(defaults)
        # opt_arg_names = arg_names[n_req_args:]

        args_dict = {}
        # now get non-default arguments (those passed by user)
        if namespace is not None:
            for i, o in enumerate(arg_names[n_req_args:]):
                v = namespace[o]
                if v is not defaults[i]:
                    args_dict[o] = v

        # resolve terse kws and add to dict
        for k, v in kws.items():
            if k not in arg_names:
                for m in self.mappings:
                    if m(k) in arg_names:
                        args_dict[m(k)] = v
                        break
                else:
                    # get name
                    name = func.__name__
                    if isinstance(func, types.MethodType):
                        name = f'{func.__self__.__class__.__name__}.{name}'
                    raise KeyError(
                        f'{k!r} is not a valid keyword for {name!r}')

        return args_dict
