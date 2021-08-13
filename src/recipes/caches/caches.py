

# std libs
import json
from pathlib import Path
from collections import MutableMapping, OrderedDict as odict

# relative libs
from ..dicts import pformat
from ..io import deserialize, guess_format
from ..logging import logging, get_module_logger, LoggingMixin


# TODO: sqlite, yaml, dill, msgpack, srsly


# module level logger
logger = get_module_logger()
logging.basicConfig()
logger.setLevel(logging.INFO)

# ------------------------------- json helpers ------------------------------- #


def lists_to_tuples(item):
    if isinstance(item, list):
        # recurse
        return tuple(map(lists_to_tuples, item))
    return item


class JSONCacheEncoder(json.JSONEncoder):
    """
    A custom JSONEncoder class that knows how to encode Cache objects.
    """

    # def default(self, o):
    #     # print('DEFAULT', o)
    #     return super().default(o)

    def encode(self, obj):
        # print('TYPE', obj)
        if isinstance(obj, Cache):
            # print('SAVE!', obj)
            return super().encode(
                {obj.__class__.__name__: obj.__dict__,
                 'items': list(obj.items())})  # FIXME: dict!!
            # note json does not support tuples, so hashability is lost here
        return super().encode(obj)


def cache_decoder(mapping):
    # logger.debug('cache_decoder: %s', mapping)
    if len(mapping) == 2:
        name = next(iter(mapping.keys()))
        kls = Cache.types_by_name().get(name)
        if kls:
            # avoid infinite recursion by removing the filename parameter
            filename = mapping[name].pop('_filename')
            obj = Cache(**mapping[name])

            # since json convert all tuples to list, we have to remap
            # to tuples
            # obj.update(mapping['cached'])
            for key, val in mapping['items']:
                # json converts tuples to lists, so we have to back convert
                # so we can hash
                obj[lists_to_tuples(key)] = val

            obj.filename = filename
            return obj
    return mapping


class CacheDecoder(json.JSONDecoder):
    def __init__(self, **kws):
        super().__init__(**{**kws, **LOAD_KWS[json]})


LOAD_KWS = {json: {'object_hook': cache_decoder}}
SAVE_KWS = {json: {'cls': JSONCacheEncoder}}

# ---------------------------------------------------------------------------- #


def load(filename, **kws):
    """
    Load cache from disc

    Parameters
    ----------
    filename : str or Path
        File location on disc

    Returns
    -------
    Cache
        A `MutableMapping` which maps function parameter values to results.
    """
    # dispatch loading on file extension
    fmt = guess_format(filename)
    cache = deserialize(filename, fmt, **{**kws,  **LOAD_KWS.get(fmt, {})})
    cache.filename = filename
    return cache


class Cache(LoggingMixin, MutableMapping):
    """
    A cache that optionally persists on disk
    """
    types = {}

    @classmethod
    def oftype(cls, kind):
        """
        Get cache class from `kind` string.

        Parameters
        ----------
        kind : str
            Item replacement policy

        Examples
        --------
        >>> Cache.oftype('rlu')(capacity=128)

        Returns
        -------
        type
            `Cache` subclass

        Raises
        ------
        ValueError
            If `kind` could not be resolved to a supported cache type.
        """
        # choose the cache type
        kls = cls.types.get(kind.lower(), None)
        if kls is None:
            raise ValueError(
                f'Unknown cache type {kind!r}. Currently supported: '
                f'{tuple(cls.types.keys())}'
            )
        return kls

    def __init_subclass__(cls):
        # add the subclass to the types dict
        cls.types[cls.__name__.replace('Cache', '').lower()] = cls

    def __init__(self, capacity, *args, **kws):
        self.capacity = int(capacity)

    def __str__(self):
        name = self.__class__.__name__
        add_info = f'size={self.capacity}'
        if self.filename:
            add_info += f', file={Path(self.filename).stem}'
        return pformat(self, f'{name}[{add_info}]', hang=True)

    def clear(self):
        """Clear all items from the cache"""
        while self:
            self.popitem()


class LRUCache(Cache, odict):
    """
    An extensible Least Recently Used cache

    adapted from:
    https://www.geeksforgeeks.org/lru-cache-in-python-using-ordereddict/

    see also:
    https://en.wikipedia.org/wiki/Cache_replacement_policies#Least_recently_used_(LRU)

    """

    def __init__(self, capacity):
        # initialising capacity
        # print('LRU.__init__')
        Cache.__init__(self, capacity)
        self._move = True

    def __str__(self):
        return Cache.__str__(self)

    def get(self, key, default=None):
        if key in self:
            return self[key]
        return default

    def __getitem__(self, key):
        # we return the value of the key that is queried in O(1) and return -1
        # if we don't find the key in out dict / cache. Also move key to end to
        # show that it was recently used.
        item = super().__getitem__(key)
        if self._move:
            self.move_to_end(key)
        return item

    def __setitem__(self, key, value):
        # first, add / update the key by conventional methods. Also move the key
        # to the end to show that it was recently used. Check if length has
        # exceeded capacity, if so remove first key (least recently used)
        super().__setitem__(key, value)
        self.move_to_end(key)

        if len(self) > self.capacity:
            # `popitem` will call __getitem__, but fail on `move_to_end`
            # unless we set `_move` to False. bit hackish
            self._move = False
            self.popitem(last=False)
            self._move = True
