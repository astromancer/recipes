
# std
from collections import OrderedDict as odict

# relative
from ..logging import LoggingMixin
from ..string import remove_suffix


DEFAULT_CAPACITY = 2 ** 7

# TODO: sqlite, yaml, dill, msgpack, srsly

# # ------------------------------- json helpers ------------------------------- #


# def lists_to_tuples(item):
#     if isinstance(item, list):
#         # recurse
#         return tuple(map(lists_to_tuples, item))
#     return item


# # ---------------------------------------------------------------------------- #


# def load(filename, **kws):
#     """
#     Load cache from disc

#     Parameters
#     ----------
#     filename : str or Path
#         File location on disc

#     Returns
#     -------
#     Cache
#         A `MutableMapping` which maps function parameter values to results.
#     """
#     # dispatch loading on file extension
#     fmt = guess_format(filename)
#     cache = deserialize(filename, fmt, **{**kws,  **LOAD_KWS.get(fmt, {})})
#     cache.filename = filename
#     return cache


class Cache(LoggingMixin):  # abc.MutableMapping
    """
    A cache that optionally persists on disk
    """
    types = {}

    @classmethod
    def oftype(cls, policy):
        """
        Get cache class from `policy` string.

        Parameters
        ----------
        policy : str
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
            If `policy` could not be resolved to a supported cache replacement
            policy.
        """
        # choose the cache type
        kls = cls.types.get(policy.lower(), None)
        if kls is None:
            raise ValueError(
                f'Unknown cache type {policy!r}. Currently supported: '
                f'{tuple(cls.types.keys())}'
            )
        return kls

    def __init_subclass__(cls):
        # add the subclass to the types dict
        cls.types[cls.__name__.replace('Cache', '').lower()] = cls

    def __init__(self, capacity=DEFAULT_CAPACITY, *args, **kws):
        self.capacity = int(capacity)
        super().__init__(*args, **kws)

    # def __reduce__(self):
    #     print('YAYY!')
    #     return self.__class__, (self.capacity, )

    # @property
    def policy(self):
        return remove_suffix(type(self).__name__, 'Cache').lower()

    # def __contains__(self, key):
    #     self._update_from_file()
    #     return super().__contains__(key)

    # def __getitem__(self, key):
    #     self._update_from_file()
    #     return super().__getitem__(key)

    # def __setitem__(self, key, val):
    #     super().__setitem__(key,  val)
    #     # TODO: save in a thread so we can return value immediately!
    #     if self.filename:
    #         self.save()
    #         self.stale = False
    #     return val

    # def _update_from_file(self):
    #     if self.filename and self.stale:
    #         self.stale = False
    #         new = load(self.filename)
    #         # NOTE: line above unnecessarily deserializes the cache type when a
    #         # plain dict will do. might be able to speed things up with a better
    #         # save / load implementation
    #         new.stale = False
    #         self.update(new)

    @classmethod
    def types_by_name(cls):
        return {kls.__name__: kls for policy, kls in cls.types.items()}

    # classmethod??
    # def from_json(self, **kws):
    #     return deserialize(self.filename, json,
    #                        **{**kws, **LOAD_KWS[json]})

    def clear(self):
        """Clear all items from the cache"""
        while self:
            self.popitem()


class LRUCache(odict, Cache):
    """
    An extensible Least Recently Used cache.

    Adapted from:
    https://www.geeksforgeeks.org/lru-cache-in-python-using-ordereddict/

    See also:
    https://en.wikipedia.org/wiki/Cache_replacement_policies#Least_recently_used_(LRU)

    """

    def __init__(self, capacity=DEFAULT_CAPACITY):
        # initialising capacity
        # print('LRU.__init__')
        Cache.__init__(self, capacity)
        self._move = True

    def __str__(self):
        return Cache.__str__(self)

    def get(self, key, default=None):
        return self[key] if key in self else default

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
