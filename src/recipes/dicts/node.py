
# std
import numbers
import itertools as itt
from typing import MutableMapping
from collections import defaultdict

# relative
from .. import op
from ..utils import is_scalar
from ..functionals import always
from ..iter import cofilter, first_true_index
from .core import AutoVivify, Pprinter, vdict


# ---------------------------------------------------------------------------- #
NULL = object()

# ---------------------------------------------------------------------------- #

# def __getattr__(self, attr):
#     if attr in self.__dict__:
#         return getattr(self, attr)
#     return getattr(self._val, attr)


# class NodeList(list):
#     def __getitem__(self, key):
#         return NodeList(
#             [child[key] for child in self if isinstance(child, vdict)]
#         )

def _get_val(item):
    return item._val if isinstance(item, LeafNode) else item
    # new = item._val if isinstance(item, LeafNode) else item
    # print(type(item), '--->', type(new))
    # return new


def _get_filter_func(keys):

    if keys is NULL:
        return always(True)

    if keys is None:
        keys = bool

    if callable(keys):
        return keys

    if is_scalar(keys):
        return op.contained(keys).within

    def test(inner):
        return any(key in inner for key in keys)

    return test


def _excise_key(keys, test):
    drop_index = first_true_index(keys, test=test)
    keys = list(keys)
    drop_key = keys[drop_index]
    keys.remove(keys[drop_index])
    return tuple(keys), (drop_key, drop_index)


def _crosscheck_keys(keys):
    bad = set()
    for a, b in itt.combinations(keys, 2):
        if a[:len(b)] == b:
            bad.add(b)
        if b[:len(a)] == a:
            bad.add(a)

    return bad


def _filter_keys(keys, test):
    new_keys, dropped = zip(*(_excise_key(keys, test) for keys in keys))
    bad = _crosscheck_keys(new_keys)
    new_keys = list(new_keys)
    for b in bad:
        i = new_keys.index(b)
        replace, index = dropped[i]
        new = list(new_keys[i])
        new.insert(index, replace)
        new_keys[i] = tuple(new)

    return new_keys


class _NodeIndexing:

    # support tuple indexing for accessing descendants
    _index_descendants_via = tuple

    def __check(self, key):
        return self._index_descendants_via and isinstance(key, self._index_descendants_via)

    def __resolve_node(self, key):
        node = self
        if self.__check(key):
            *keys, key = key
            if keys:
                node = node[tuple(keys)]
        return key, node

    def __getitem__(self, key):
        key, node = self.__resolve_node(key)
        return super(_NodeIndexing, node).__getitem__(key)

    def __setitem__(self, key, val):
        key, node = self.__resolve_node(key)
        return super(_NodeIndexing, node).__setitem__(key, val)

    def update(self, mapping=(), **kws):
        for key, val in dict(mapping, **kws).items():
            self[key] = val

    def pop(self, key, *default):
        key, node = self.__resolve_node(key)
        return super(_NodeIndexing, node).pop(key, *default)


class LeafNode:
    __slots__ = ('_val', 'parent')

    def __init__(self, val):
        self.parent = None
        self._val = val

    def __repr__(self):
        return str(self._val)


class DictNode(_NodeIndexing, AutoVivify, Pprinter, defaultdict, vdict):
    """
    A defaultdict that generates instances of itself. Used to create arbitrary 
    data trees without prior knowledge of final structure. 
    """

    def _attach(self, val):
        if isinstance(val, type(self)):
            node = val
        elif isinstance(val, MutableMapping):
            node = type(self)(**val)
            # node.update(val)
        else:
            node = LeafNode(val)

        node.parent = self
        return node

    def __init__(self, *args, **kws):
        factory = self._attach
        if args and callable(args[0]):  # and not isinstance(args[0], abc.Iterable):
            factory, *args = args

        # init
        defaultdict.__init__(self, factory)
        if args or kws:
            self.update(*args, **kws)

    def __iter__(self):
        # needed for ** unpacking to work. FNW
        return super().__iter__()

    def __getitem__(self, key):
        return _get_val(super().__getitem__(key))

    def __setitem__(self, key, val):
        return super().__setitem__(key, self._attach(val))

    # ------------------------------------------------------------------------ #
    def values(self):
        yield from map(_get_val, super().values())

    def items(self):
        yield from zip(self.keys(), self.values())

    def pop(self, key, *default):
        return _get_val(super().pop(key, *default))

    # def merge(self, other):
    #     self.update(other)
    # class _NodeMixin:

    # ------------------------------------------------------------------------ #

    def _root(self):
        node = self
        while hasattr(node, 'parent'):
            node = node.parent
        return node

    def leaves(self, levels=all):

        if isinstance(levels, numbers.Integral):
            levels = [levels]

        keys = []
        return dict(self._leaves(levels, 0, keys))

    def _leaves(self, levels, _level=0, _keys=None):
        for key, child in self.items():
            if isinstance(child, type(self)):
                yield from child._leaves(levels, _level + 1, (*_keys, key))
            elif (levels is all or _level in levels):
                yield (*_keys, key), child

    def flatten(self, levels=all):
        return self.leaves(levels)

    def filtered(self, keys=NULL, values=NULL, levels=all, *args, **kws):
        new = type(self)()

        new.update(self._filter(_get_filter_func(keys),
                                _get_filter_func(values),
                                levels))
        # new[keys] = val
        return new

    def _filter(self, key_test, val_test, levels):
        keys, values = cofilter(key_test, *zip(*self.leaves(levels).items()))
        values, keys = cofilter(val_test, values, keys)
        yield from zip(keys, values)

    def find(self, key, collapse=False, remapped_keys=None):
        # sourcery skip: assign-if-exp, reintroduce-else
        test = op.has(key).within
        found = self.filtered(test)

        if not collapse:
            return found

        found = found.flatten()
        new_keys = _filter_keys(found.keys(), test)

        if remapped_keys is not None:
            remapped_keys.update(zip(found.keys(), new_keys))

        return type(self)(dict(zip(new_keys, found.values())))

    def transform(self, key_transform, *args, **kws):
        new = type(self)()
        for keys, val in self.leaves().items():
            new[key_transform(keys, *args, **kws)] = val

        return new

    # alias
    reshape = transform

    def map(self, func, *args, **kws):
        # create new empty
        new = type(self)()
        for name, child in self.items():
            if isinstance(child, type(self)):
                new[name] = child.map(func, *args, **kws)
            else:
                new[name] = func(child, *args, **kws)
        return new

    def split(self, keys):
        return tuple(self.transform(_split_trans, keys).values())


def _split_trans(keys, accept):
    return (any(key in accept for key in keys), *keys)
