

# std libs
import json
from pathlib import Path
from collections import OrderedDict as odict

# local libs
from ..dicts import pformat
from ..logging import logging, get_module_logger

# relative libs
from ..logging import LoggingMixin
from ..io import serialize, deserialize, guess_format
from .caches import Cache

# TODO: serializing the Cache class is error prone and hard to maintain.
# Better to simply serialize the dict and init the cache from that??

# TODO: sqlite, yaml, dill


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

    # load existing cache
    logger.info('Loading cache at %r', filename)

    # dispatch loading on file extension
    fmt = guess_format(filename)
    cache = deserialize(filename, fmt, **{**kws,  **LOAD_KWS.get(fmt, {})})

    # print info
    logger.debug('Cache contains %d entries. Capacity is %d.',
                 len(cache), cache.capacity)
    return cache


class CacheManager(LoggingMixin):
    """
    Manages cache saving and loading etc.
    """

    def __init__(self, kind, capacity, filename=None):
        self.capacity = int(capacity)
        self.filename = str(filename) if filename else None
        # self.logger.debug(self.__name__, f'{capacity=}; {filename=}')

        # if caching to disc and file exists, flag that we need to load it
        self.data = Cache.oftype(kind)(capacity)  # the actual cache
        self.stale = bool(self.filename) and self.path.exists()

    def __str__(self):
        info = {'size': self.capacity}
        if self.filename:
            info['file'] = self.path.name
        return pformat(self,
                       f'{type(self).__name__}{pformat(info, brackets="[]")}',
                       hang=True)

    @property
    def filename(self):
        return self._filename

    @filename.setter
    def filename(self, filename):
        self._filename = str(filename) if filename else None

        if self.path and not self.path.parent.exists():
            raise ValueError(f'Parent folder does not exist: '
                             f'{self.path.parent}')

    @property
    def path(self):
        if self.filename:
            return Path(self.filename)

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
        if self.filename and self.stale:
            self.data.update(load(self.filename))

    # @classmethod
    # def load(cls, filename, **kws):
    #     """
    #     Load a picked cache from disc

    #     Parameters
    #     ----------
    #     filename : str
    #         File system path to the cache location.

    #     Returns
    #     -------
    #     Cache
    #         A cache with the desired replacement policy.

    #     Raises
    #     ------
    #     TypeError
    #         If the pickeled obect at the given location is not a of the correct
    #         type.
    #     """

    #     return cache

    def save(self, filename=None, **kws):
        """save the cache in chosen format"""
        # TODO: option to save only at exit??
        filename = filename or self.filename
        if filename is None:
            raise ValueError('Please provide a filename.')

        self.logger.debug('Saving cache: %r', filename)
        fmt = guess_format(filename)
        if fmt is json:
            self.to_json(filename)
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
            json.dumps(self.data, **{**kws, **SAVE_KWS[json]}).encode()
        )

    # classmethod??
    # def from_json(self, **kws):
    #     return deserialize(self.filename, json,
    #                        **{**kws, **LOAD_KWS[json]})
