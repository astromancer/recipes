

# std
import json
from pathlib import Path

# third-party
from loguru import logger

# relative
from ..dicts import pformat
from ..logging import LoggingMixin
from ..io import serialize, deserialize, guess_format
from . import Cache, DEFAULT_CAPACITY


# TODO: serializing the Cache class is error prone and hard to maintain.
# Better to simply serialize the dict and init the cache from that??

# TODO: sqlite, yaml, dill, jsons, msgpack


# ------------------------------- json helpers ------------------------------- #


def lists_to_tuples(item):
    # recurse
    return tuple(map(lists_to_tuples, item)) if isinstance(item, list) else item


class JSONCacheEncoder(json.JSONEncoder):
    """
    A custom JSONEncoder class that knows how to encode Cache objects.
    """

    # def default(self, o):
    #     # print('DEFAULT', o)
    #     return super().default(o)

    def default(self, obj):
        # print('TYPE', obj)
        # if isinstance(obj, Cache):
        #     return tuple(obj.items())

        if isinstance(obj, CacheManager):
            # Have to convert to tuple since json does not allow non-string keys
            # in dict which is lame...
            # note json does not support tuples, so hashability is lost here
            return {
                obj.__class__.__name__: {
                    **{at: getattr(obj, at) for at in obj.__slots__},
                    **{'data': tuple(obj.data.items())}
                }
            }

        return super().default(obj)


def cache_decoder(mapping):
    # logger.debug('cache_decoder: {:s}', mapping)
    if not mapping:
        return mapping

    name = next(iter(mapping.keys()))
    if name != 'CacheManager':
        return mapping

    # CacheManager
    kws = mapping[name]
    # since json convert all tuples to list, we have to remap
    # to tuples to preserve hashability
    cache = Cache.oftype(kws['policy'])(kws['capacity'])
    cache.update({lists_to_tuples(key): val
                  for key, val in kws.pop('data')})
    kws['data'] = cache

    logger.debug('Loading cache of type {!r} with state {}.',
                 type(cache), mapping[name])

    # load Manager
    obj = object.__new__(CacheManager)
    for at in CacheManager.__slots__:
        setattr(obj, at, kws[at])

    # kls = Cache.types_by_name().get(name)
    # if not kls:
    #     return mapping

    # avoid infinite recursion by removing the filename parameter
    # filename = mapping[name].pop('_filename')

    # obj.filename = filename
    return obj


class CacheDecoder(json.JSONDecoder):
    def __init__(self, **kws):
        super().__init__(**{**kws, **LOAD_KWS[json]})


LOAD_KWS = {json: {'object_hook': cache_decoder}}
SAVE_KWS = {json: {'cls': JSONCacheEncoder}}

# ---------------------------------------------------------------------------- #

null = object()


# def load(filename, **kws):


class CacheManager(LoggingMixin):
    """
    Manages cache saving and loading etc.
    """

    __slots__ = ('capacity', 'policy', 'data', 'enabled', 'stale', '_filename')

    def __init__(self, capacity=DEFAULT_CAPACITY, filename=None, policy='lru',
                 enabled=True):

        self.capacity = int(capacity)
        self.policy = str(policy).lower()
        self.filename = str(filename) if filename else None
        # self.logger.debug(self.__name__, f'{capacity=}; {filename=}')

        # if caching to disc and file exists, flag that we need to load it
        self.data = Cache.oftype(policy)(capacity)  # the actual cache
        self.stale = bool(self.filename) and self.path.exists()
        self.enabled = bool(enabled)

    def __str__(self):
        info = {'size': f'{len(self.data)}/{self.capacity}'}
        if self.filename:
            info['file'] = repr(str(self.path))
        info = pformat(info, type(self).__name__, lhs=str, rhs=str, brackets='[]')
        return pformat(self.data,
                       f'{info}',
                       hang=True)

    __repr__ = __str__

    @property
    def filename(self):
        return self._filename

    @filename.setter
    def filename(self, filename):
        self._filename = str(filename) if filename else None
        path = self.path
        if not path:
            return

        self.stale = True
        if path.parent.exists():
            return

        raise ValueError(f'Parent folder does not exist: {path.parent}')

    @property
    def path(self):
        if self.filename:
            return Path(self.filename)

    def __eq__(self, other):
        return (isinstance(other, type(self)) and
                (self.data == other.data) and
                (self.__dict__ == other.__dict__))

    def __contains__(self, key):
        self._update_from_file()
        return key in self.data

    def __getitem__(self, key):
        self._update_from_file()
        return self.data[key]

    def __setitem__(self, key, val):
        self.data[key] = val

        # TODO: save in a thread so we can return value immediately!
        if self.filename:
            self.save()
            self.stale = False
        return val

    def _update_from_file(self):
        if self.stale and self.filename and self.path.exists():
            clone = self.load(self.filename)
            # self.data.update(clone.data)
            # # RuntimeError: OrderedDict mutated during iteration
            self.data = clone.data
            self.stale = False

    def get(self, key, default=None):
        return self.data.get(key, default)

    def enable(self, filename=None):
        """
        (Re-)enable a cache, optionally at a new file location.

        Parameters
        ----------
        filename : str or Path, optional
            File system path for saving cache, by default None.

        Note, the filename parameter is here for convenience. Assigning a new
        location to the filename attribute also works.
        """
        self.enabled = True
        if filename:
            self.filename = filename

    def disable(self):
        self.enabled = False

    @classmethod
    def load(cls, filename, **kws):
        """
        Load a pickled cache from disc.

        Parameters
        ----------
        filename : str
            File system path to the cache location.

        Returns
        -------
        Cache
            A cache with the desired replacement policy.

        Raises
        ------
        TypeError
            If the pickled obect at the given location is not of the correct
            type.
        """

        # load existing cache
        cls.logger.info('Loading cache at {!r}.', filename)

        # dispatch loading on file extension
        fmt = guess_format(filename)
        cache = deserialize(filename, fmt, **{**kws, **LOAD_KWS.get(fmt, {})})

        # print info
        logger.debug('Loaded {!r} containing {:d}/{:d} entries.',
                     type(cache.data).__name__, len(cache.data),
                     cache.capacity)

        return cache

    def check_filename(self, filename):
        filename = filename or self.filename
        if filename is None:
            raise ValueError('Please provide a filename.')
        return filename

    def save(self, filename=None, **kws):
        """save the cache in chosen format."""
        filename = self.check_filename(filename)

        self.logger.debug('Saving cache: {!r}.', filename)
        fmt = guess_format(filename)

        if fmt is json:
            self.to_json()
        else:
            # TODO: might be slow for large caches - do in thread?
            # more optimal save methods might also exist for specific policies!
            serialize(filename, self, fmt,
                      **{**kws, **SAVE_KWS.get(fmt, {})})
        #
        self.logger.debug('Saved: {!r}', filename)

        # except PicklingError as err:
        #     warnings.warn(
        #         'Could not save cache since some objects could not be '
        #         f'serialized: {err!s}')

    def to_json(self, filename=None, **kws):
        # NOTE: dump doesn't work unless you re-write a whole stack of
        # complicated code in JSONEncoder.iterencode. This is a hack which
        # avoids all that...
        filename = self.check_filename(filename)
        with Path(filename).open('w') as fp:
            json.dump(self, fp, **{**kws, **SAVE_KWS[json]})  # .encode()

    # classmethod??
    # def from_json(self, **kws):
    #     return deserialize(self.filename, json,
    #                        **{**kws, **LOAD_KWS[json]})
