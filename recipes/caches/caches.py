# import functools as ftl
from collections import OrderedDict as odict

# from .caches import Cache
from ..io import serialize, deserialize, guess_format
# from pickle import PicklingError
# import warnings
from pathlib import Path
from ..logging import LoggingMixin
import json
# import re

# TOOD: serializing the Cache class is error prone and hard to maintain. 
# Better to simply serialize the dict and init the cache from that??

# TODO: sqlite, yaml, dill

# ------------------------------- json helpers ------------------------------- #

def lists_to_tuples(item):
    if isinstance(item, list):
        # recurse
        return tuple(map(lists_to_tuples, item))
    return item

class CacheEncoder(json.JSONEncoder):
    """
    A custom JSONEncoder class that knows how to encode Cache objects.
    """

    def default(self, o):
        # print('DEFAULT', o)
        return super().default(o)

    def encode(self, obj):
        # print('TYPE', obj)
        if isinstance(obj, Cache):
            # print('SAVE!', obj)
            return super().encode(
                {obj.__class__.__name__: obj.__dict__,
                 'items': list(obj.items())}) # FIXME: dict!!
            # note json does not support tuples, so hashability is lost here
        return super().encode(obj)


def cache_decoder(mapping):
    # print('DECODE:', mapping)
    if len(mapping) == 2:
        name = next(iter(mapping.keys()))
        kls = Cache.types_by_name().get(name)
        if kls:
            # avoid infinite recursion by removing the filename parameter
            filename = mapping[name].pop('filename')
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
SAVE_KWS = {json: {'cls': CacheEncoder}}


# ---------------------------------------------------------------------------- #
class CacheMeta(type):
    """
    Constructor for Cache types.  Allows the implementation details of various
    item replacement policies to be developed and handled independently and
    allocated at runtime based on user input.
    """
    def factory(cls, kind):
        # choose the cache type
        # print('inside factory', cls)
        kls = cls.types.get(kind.lower(), None)
        if kls is None:
            raise ValueError(
                f'Unknown cache type {kind!r}. Currently supported: '
                f'{tuple(cls.types.keys())}'
            )
        return kls

    def __call__(cls, capacity, filename=None, kind='lru', **kws):
        """
        Initialize the cache

        Parameters
        ----------
        capacity : int
            Maximal item size of the cache
        filename : str or Path
            File location of the cache
        kind : str, optional
            The cache item replacement policy, by default 'lru'
            (only LRU currently supported)

        Returns
        -------
        [type]
            [description]
        """

        # implement the class factory before `__new__` is called on the class
        # print('inside meta call', cls)
        kls = cls.factory(kind)
        # print('meta got', kls)
        # print('args', args)
        # logger.debug(__name__, f'{capacity=}; {filename=}')

        if filename:
            filepath = Path(filename).expanduser().resolve()
            if filepath.exists():
                # unpickle the cache and return it
                return kls.load(str(filepath))

        # if we get here, the cache is either in RAM, or requested on disk but
        # non-existent (new cache)
        cache = type.__call__(kls, capacity, filename)  # .
        return cache


class Cache(LoggingMixin, metaclass=CacheMeta):
    """
    A cache that optionally persists on disk
    """
    types = {}

    def __init__(self, capacity, filename=None):
        self.capacity = int(capacity)
        self.filename = str(filename) if filename else None
        # self.logger.debug(self.__name__, f'{capacity=}; {filename=}')
        # TODO: maybe check that it's a valid system path
        # super().__init__()

    @property
    def path(self):
        if self.filename:
            return Path(self.filename)

    # def from_dict(self, mapping):
    #     # the initializer obove overwrites the normal dict init, but we still
    #     # want to be able to init from mappings when deserializing
    #     super().__init__(**mapping)

    def __init_subclass__(cls):
        # add the subclass to the types dict
        cls.types[cls.__name__.replace('Cache', '').lower()] = cls

    def __reduce__(self):
        # custom unpickling
        attrs = dict(filename=self.filename)
        return self.__class__, (self.capacity,), attrs, None, iter(self.items())

    def __str__(self):
        name = self.__class__.__name__
        add_info = f'size={self.capacity}'
        if self.filename:
            add_info += f' file={Path(self.filename).stem}'
        return super().__str__().replace(name, f'{name}[{add_info}]')

    def __setitem__(self, key, val):
        super().__setitem__(key,  val)
        # TODO: save in a thread so we can return value immediately!
        if self.filename:
            self.save()
        return val

    @classmethod
    # @ftl.cached_property
    def types_by_name(cls):
        return {kls.__name__: kls for kind, kls in cls.types.items()}

    @classmethod
    def load(cls, filename, **kws):
        """
        Load a picked cache from disc

        Parameters
        ----------
        filename : str
            File system path to the cache location

        Returns
        -------
        Cache
            A cache of the desired type

        Raises
        ------
        TypeError
            If the pickeled obect at the given location is not a of the correct
            type.
        """

        # load existing cache
        cls.logger.info('Loading cache at %r', filename)

        # dispatch loading on file extension
        # path = Path(filename)
        fmt = guess_format(filename)
        cache = deserialize(filename, fmt, **{**kws,  **LOAD_KWS.get(fmt, {})})
        cache.filename = filename

        # Check if serialized object is correct type
        if not isinstance(cache, cls):
            raise TypeError(
                f'Expected {cls.__name__!r} type object at '
                f'location {filename!r}. Found {type(cache)!r} instead.')

        # print info
        cls.logger.debug('Cache contains %d entries. Capacity is %d.',
                         len(cache), cache.capacity)
        return cache

    def save(self, filename=None, **kws):
        """save the cache in chosen format"""
        # TODO: option to save only at exit??
        filename = filename or self.filename
        if filename is None:
            raise ValueError('Please provide a filename.')

        self.logger.debug('Saving cache: %r', filename)
        fmt = guess_format(filename)

        if fmt is json:
            self.to_json()
        else:
            # TODO: might be slow for large caches - do in thread?
            # more optimal save methods might also exist for specific policies!
            serialize(filename, self, fmt,
                      **{**kws, **SAVE_KWS.get(fmt, {})})
        #
        self.logger.debug('Saved: %r', filename)

        # except PicklingError as err:
        #     warnings.warn(
        #         'Could not save cache since some objects could not be '
        #         f'serialized: {err!s}')

    def to_json(self, filename=None, **kws):
        # NOTE: dump doesn't work unless you re-write a whole stack of
        # complicated code in JSONEncoder.iterencode. This is a hack which
        # avoids all that...
        filename = filename or self.filename
        if filename is None:
            raise ValueError('Please provide a filename.')

        Path(filename).write_bytes(
            json.dumps(self, **{**kws, **SAVE_KWS[json]}).encode()
        )

    # classmethod??
    # def from_json(self, **kws):
    #     return deserialize(self.filename, json,
    #                        **{**kws, **LOAD_KWS[json]})

# TODO
# class CallerCache:
#     connects the cache with the function so we can more easily add cache items
#     manually
#     def __init__(self, func):



class LRUCache(Cache, odict):
    """
    An extensible Least Recently Used cache

    adapted from:
    https://www.geeksforgeeks.org/lru-cache-in-python-using-ordereddict/

    see also:
    https://en.wikipedia.org/wiki/Cache_replacement_policies#Least_recently_used_(LRU)

    """

    def __init__(self, capacity, filename=None):
        # initialising capacity
        # print('LRU.__init__')
        Cache.__init__(self, capacity, filename)
        self._move = True

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
            # line below will call __getitem__, but fail on `move_to_end`
            # unless we set `_move` to False. bit hackish
            self._move = False
            self.popitem(last=False)
            self._move = True

    def clear(self):
        while self:
            self.popitem()


# TYPES = {'lru': LRUCache}
