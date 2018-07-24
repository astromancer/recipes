"""
Recipes involving dictionaries
"""

from collections import Callable, UserDict, OrderedDict

from .iter import flatiter


# TODO: a factory function which takes requested props, eg: indexable=True,
# attr=True, ordered=True)


def pformat(dict_):
    """
    pformat (nested) dict types

    Parameters
    ----------
    dict_: dict
        Mapping to convert to str

    Returns
    -------
    str

    Examples
    --------
        >>> pprint(dict(x='hello',
                        longkey='w',
                        foo=dict(nested=1,
                                 what='lkdskldlkdlklkdlkd',
                                 x=dict(triple='nestnestnestnestyyy'))))

        {x      : hello,
         longkey: w,
         foo    : {nested: 1,
                   what  : lkdskldlkdlklkdlkd,
                   x     : {triple: nestnestnestnestyyy}}}

    """
    s = '{'
    last = len(dict_) - 1
    # make sure we line up the values
    w = max(map(len, dict_.keys()))
    for i, (k, v) in enumerate(dict_.items()):
        if i == 0:
            indent = 0
        else:
            indent = 1

        space = indent * ' '
        s += '{}{: <{}s}: '.format(space, k, w)

        if isinstance(v, dict):
            ds = pformat(v)
            ws = ' ' * (w + 3)
            s += ds.replace('\n', '\n' + ws)
        else:
            s += '%s' % str(v)

        s += [',\n', '}'][i == last]

    return s


def pprint(dict_):
    print(pformat(dict_))


class Pprinter(object):
    """Mixin class that pretty prints dictionary content"""

    def __str__(self):
        s = pformat(self)
        cls_name = self.__class__.__name__
        indent = ' ' * (len(cls_name) + 1)
        s = s.replace('\n', '\n' + indent)
        return '%s(%s)' % (cls_name, s)

    def __repr__(self):
        return str(self)


class Invertible(object):
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


class InvertibleDict(Invertible, dict):
    pass


class AutoVivification(dict):
    """Implement autovivification feature for dict."""

    def __missing__(self, key):
        value = self[key] = type(self)()
        return value


AutoViv = AutoVivify = AutoVivification


# TODO: factory methods to get class based on what you want: attribute
# lookup, indexability,

class AttrDict(dict):
    """dict with key access through attribute lookup"""

    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self
        # pros: IDE autocomplete works on keys
        # caveats: inheritance: have to init this superclass first??

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


class Indexable(object):
    """
    Mixin class that enables dict item access through integer keys like list

    >>> class X(Indexable, dict):
    >>>     pass

    >>> x = X(zip(('hello', 'world'), (1,2)))
    >>> x[1], x[:1]  # (2, [1])


    """

    def __getitem__(self, key):
        if isinstance(key, int):
            # note, this dissallows integer keys for parent object
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
        # if we get a list / tuple try interpret as list of arrays (group
        # labels)
        if items is None:
            super().__init__(**kws)
        elif isinstance(items, (list, tuple)):
            super().__init__()
            for i, item in enumerate(items):
                if self._allow_item(item):
                    self[self._auto_name()] = self._convert_item(item)
        else:
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


# class Indexable(object):
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
    def __getattr__(self, attr):
        """
        Try to get the value in the dict associated with `attr`. If attr is
        not a key, try get the attribute.
        Note: Items keyed on names that are identical to the `dict` builtin
        methods, eg. 'keys', will not be accessible through attribute lookup.

        >>> x = AttrReadItem(hello=0, world=2)
        >>> x.hello, x.world # (0, 1)
        >>> x['keys'] = None
        >>> x.keys  # <function AttrReadItem.keys>

        """
        if attr in self:
            return super().__getitem__(attr)
        #
        try:
            return super().__getattr__(attr)
        except Exception:
            raise AttributeError('%r object has no attribute %r' %
                                 (self.__class__.__name__, attr))


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


# ****************************************************************************************************
class TransDict(UserDict):
    """
    A many to one mapping.

    Provides a generic way of, for example, translating keywords to their
    intended meaning in a call signature.
    """

    def __init__(self, dic=None, **kwargs):
        super().__init__(dic, **kwargs)
        self._map = {}

    def add_translations(self, dic=None, **kwargs):
        """enable on-the-fly shorthand translation"""
        dic = dic or {}
        self._map.update(dic, **kwargs)

    # alias
    add_vocab = add_translations

    def __contains__(self, key):
        return super().__contains__(self._map.get(key, key))

    def __missing__(self, key):
        """if key not in keywords, try translate"""
        return self[self._map[key]]

    def allkeys(self):
        # TODO: Keysview**
        return flatiter((self.keys(), self._map.keys()))

    def many2one(self, many2one):
        # self[one]       #error check
        for many, one in many2one.items():
            for key in many:
                self._map[key] = one


# ****************************************************************************************************
class Many2OneMap(TransDict):
    """
    Expands on TransDict by adding equivalence mapping functions for keywords
    """

    def __init__(self, dic=None, **kwargs):
        super().__init__(dic, **kwargs)
        self._eqmap = []  # equivalence mappings

    def add_map(self, func):
        self._eqmap.append(func)

    def __missing__(self, key):
        try:
            # try translate with vocab
            return super().__missing__(key)
        except KeyError as err:
            # try translate with equivalence maps
            for emap in self._eqmap:
                if super().__contains__(emap(key)):
                    return self[emap(key)]
            raise err

    def __contains__(self, key):
        if super().__contains__(key):
            return True  # no translation needed

        for emap in self._eqmap:
            try:
                return super().__contains__(emap(key))
            except:
                pass

        return False


# SuperDict = Many2OneMap

class IndexableOrderedDict(OrderedDict):
    def __missing__(self, key):
        if isinstance(key, int):
            return self[list(self.keys())[key]]
        else:
            return OrderedDict.__missing__(self, key)


# ****************************************************************************************************
class DefaultOrderedDict(OrderedDict):
    # Source: http://stackoverflow.com/a/6190500/562769
    def __init__(self, default_factory=None, *a, **kw):
        if (default_factory is not None and
                not isinstance(default_factory, Callable)):
            raise TypeError('first argument must be callable')

        OrderedDict.__init__(self, *a, **kw)
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
        if self.default_factory is None:
            args = tuple()
        else:
            args = self.default_factory,
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
        return 'OrderedDefaultDict(%s, %s)' % (self.default_factory,
                                               OrderedDict.__repr__(self))


# DefaultOrderedDict


# ====================================================================================================
def invertdict(d):
    return dict(zip(d.values(), d.keys()))

# ====================================================================================================
