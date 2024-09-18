
# std
import math
import numbers
import itertools as itt
import functools as ftl
from typing import MutableMapping
from collections import defaultdict

# relative
from ... import op
from ...oo import Alias
from ...logging import LoggingMixin
from ...functionals import always, negate
from ...pprint.mapping import PrettyPrint
from ...iter import cofilter, first_true_index
from ...functionals.partial import partial, placeholder as o
from .. import cosort
from ..ensure import is_scalar
from .core import AutoVivify


# ---------------------------------------------------------------------------- #
NULL = object()

# ---------------------------------------------------------------------------- #


def _get_filter_func(keys):

    if keys is NULL:
        return always(True)

    if keys is None:
        return bool

    return negate(_get_select_func(keys))


def _get_select_func(keys):

    if keys is NULL:
        return always(True)

    if callable(keys):
        return keys

    if isinstance(keys, str):
        return op.contained(keys).within

    if is_scalar(keys):
        return ftl.partial(op.eq, keys)

    def test(inner):
        # FIXME: this logical operation should be made explicit
        return any(key in inner for key in keys)

    return test


# ---------------------------------------------------------------------------- #
# Editing paths

def _excise_key(path, test):
    drop_index = first_true_index(path, test=test)
    path = list(path)
    drop_key = path[drop_index]
    path.remove(path[drop_index])
    return tuple(path), (drop_key, drop_index)


def _crosscheck_path(path):
    bad = set()
    for a, b in itt.combinations(path, 2):
        if a[:len(b)] == b:
            bad.add(b)
        if b[:len(a)] == a:
            bad.add(a)

    return bad


def _filter_path(path, test):
    new_path, dropped = zip(*(_excise_key(path, test) for path in path))
    bad = _crosscheck_path(new_path)
    new_path = list(new_path)
    for b in bad:
        i = new_path.index(b)
        replace, index = dropped[i]
        new = list(new_path[i])
        new.insert(index, replace)
        new_path[i] = tuple(new)

    return new_path


def balance_depth(key, depth, insert='', position=-1):
    # balance depth of the branches for table
    key = list(key)
    while len(key) < depth:
        key.insert(position, insert)

    return tuple(key)


# ---------------------------------------------------------------------------- #

def is_leaf(node):
    return isinstance(node, LeafNode)


def _get_val(item):
    return item._val if is_leaf(item) else item


def _unwrap(node, unwrap=True):
    if unwrap:
        return _get_val(node)
    return node


class _NodeIndexing:

    # support tuple indexing for accessing descendants
    _index_descendants_via = tuple

    def __check(self, key):
        return (idv := self._index_descendants_via) and isinstance(key, idv) and key

    def __resolve_node(self, key):
        node = self
        if self.__check(key):
            *keys, key = key
            if keys:
                # get / create node
                node = node[tuple(keys)]
        return key, node

    def __getitem__(self, key):
        if key == ():
            return self
        key, node = self.__resolve_node(key)
        return super(_NodeIndexing, node).__getitem__(key)

    def __setitem__(self, okey, val):
        key, node = self.__resolve_node(okey)
        if isinstance(node, _NodeIndexing):
            return super(_NodeIndexing, node).__setitem__(key, val)

        return super().__setitem__(okey, val)

    def __contains__(self, keys):

        if not isinstance(keys, tuple):
            return super().__contains__(keys)

        obj = self
        while len(keys):
            key, *keys = keys
            if isinstance(obj, type(self)) and key in obj:
                obj = obj[key]
            else:
                return False

        return True

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


class DictNode(_NodeIndexing, AutoVivify, PrettyPrint, defaultdict, LoggingMixin):
    """
    A defaultdict that generates instances of itself. Used to create arbitrary 
    data trees without prior knowledge of final structure. 
    """

    def _attach(self, val):
        if isinstance(val, type(self)):
            node = val
        elif isinstance(val, MutableMapping):
            node = type(self)()
            node.update(val)
            # NOTE: use update here in case there may be a key named 'self'
        else:
            node = LeafNode(val)

        node.parent = self
        return node

    def __init__(self, *args, **kws):
        self.parent = None
        factory = self._attach
        if args and callable(args[0]):
            factory, *args = args

        # init
        defaultdict.__init__(self, factory)
        if args or kws:
            self.update(*args, **kws)

    def __iter__(self):
        # needed for ** unpacking to work
        return super().__iter__()

    def __getitem__(self, key):
        return _get_val(super().__getitem__(key))

    def __setitem__(self, key, val):
        return super().__setitem__(key, self._attach(val))

    def __reduce__(self):
        return type(self), (), {}, None, self.items()

    # ------------------------------------------------------------------------ #

    def values(self):
        yield from map(_get_val, super().values())

    def items(self):
        yield from zip(self.keys(), self.values())

    def pop(self, key, *default, unwrap=True):
        return _unwrap(super().pop(key, *default), unwrap)

    def get(self, key, *default, unwrap=True):
        if key in self:
            return self[key]

        return super().get(key, *default)

    def update(self, mapping=(), **kws):

        if isinstance(mapping, DictNode):
            mapping = mapping.flatten()  # so we don't overwrite nested dicts

        super().update(mapping, **kws)

    def setdefault(self, key, value):
        if key in self:
            return self[key]

        self[key] = value
        return value

    # ------------------------------------------------------------------------ #
    def _root(self):
        node = self
        while hasattr(node, 'parent'):
            node = node.parent
        return node

    def depth(self):
        return max(len(key) for key, _ in self._flatten(all))

    def _size(self):
        return sum(1 if is_leaf(node) else node._size()
                   for node in super().values())

    def flatten(self, levels=all, keep_tuples=True):

        if isinstance(levels, numbers.Integral):
            levels = range(levels)

        flat = dict(self._flatten(levels, 0))

        if keep_tuples:
            return flat

        # flatten 1-tuples
        return dict(zip(next(zip(*flat.keys())), flat.values()))

    def _flatten(self, levels, _level=0, _keys=()):
        for key, child in self.items():
            if (levels is all or _level in levels) and isinstance(child, type(self)):
                yield from child._flatten(levels, _level + 1, (*_keys, key))
            else:
                yield (*_keys, key), child

    def prune(self, keys):
        return self.filter(keys)

    def filter(self, keys=NULL, values=NULL, levels=all):
        new = type(self)()
        new.update(self._filter(_get_filter_func(keys),
                                _get_filter_func(values),
                                levels))
        return new

    # alias
    filtered = Alias('filter')

    def select(self, keys=NULL, values=NULL, levels=0):
        new = type(self)()
        new.update(self._filter(_get_select_func(keys),
                                _get_select_func(values),
                                levels))
        return new

    def _filter(self, key_test, val_test, levels):
        if not self:
            return

        keys, values = cofilter(key_test, *zip(*self.flatten(levels).items()))
        values, keys = cofilter(val_test, values, keys)
        yield from zip(keys, values)

    def find(self, key, collapse=False, remapped_keys=None, default=NULL):
        # sourcery skip: assign-if-exp, reintroduce-else
        test = op.has(key).within
        found = self.select(test)

        if not found and default is not NULL:
            found = type(self)({key: default})

        if not collapse:
            return found

        found = found.flatten()
        new_keys = _filter_path(found.keys(), test)

        if remapped_keys is not None:
            remapped_keys.update(zip(found.keys(), new_keys))

        return type(self)(dict(zip(new_keys, found.values())))

    def reshape(self, key_transform, *args, **kws):

        new = type(self)()
        for keys, val in self.flatten().items():
            new_key = key_transform(keys, *args, **kws)
            if new_key in new:
                self.logger.warning('Overwriting existing value at key: {!r}.',
                                    new_key)
            #
            new[new_key] = val

        return new

    # alias
    transform = Alias('reshape')

    def rename(self, old, new):
        if old in self:
            self[new] = self.pop(old)
        return self

    def map(self, func, *args, **kws):
        # create new empty
        new = type(self)()
        for name, child in self.items():
            if isinstance(child, type(self)):
                new[name] = child.map(func, *args, **kws)
            else:
                new[name] = func(child, *args, **kws)
        return new

    def attrs(self, *attrs):
        return self.map(op.AttrGetter(*attrs))

    def split(self, keys):
        new = self.transform(_split_trans, keys)
        return (new[False], new[True])

    def sorted(self, keys):

        if callable(keys):
            raise NotImplementedError()

        if is_scalar(keys):
            raise ValueError(f'Expected callable or list of keys, not {type(keys)}.')

        new = type(self)()
        new.update(
            zip(*cosort(
                *zip(*self.items()),
                key=partial(op.index)(keys, o, default=math.inf),
            ))
        )
        return new

    def stack(self, level):

        # keys = []
        out = type(self)()
        for key, item in self.flatten().items():
            # keys.append()
            (key := list(key)).pop(level)
            out.setdefault((key := tuple(key)), [])
            target = out[key]
            target.append(item)

        return out

    def merge(self, other=(), **kws):
        kls = type(self)
        out = self.flatten()
        for mapping in (other, kws):
            out.update(kls(mapping).flatten())
        return kls(out)

    def balance(self, depth=None, insert=''):

        new = type(self)()
        depth = depth or self.depth()
        for path, val in self.flatten().items():
            new[balance_depth(path, depth, insert)] = val

        return new

    def coerce(self, unpack=False, **kws):
        for key, kls in kws.items():
            if key not in self:
                raise KeyError(key)

            # coerce
            self[key] = kls(*self[key]) if unpack else kls(self[key])

        return self


def _split_trans(keys, accept):
    return (any(key in accept for key in keys), *keys)
