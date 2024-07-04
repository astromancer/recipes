
# std
import fnmatch as fnm
import itertools as itt

# relative
from ..pprint.dispatch import pformat
from ..containers import dicts, ensure
from .utils import superclasses
from .represent import Represent

# ---------------------------------------------------------------------------- #


def sanitize(kws, *ignore):
    return dicts.remove(kws, {'self', 'kws', '__class__', *ignore})


# alias
sanitize_locals = sanitize


def get_slots(cls, ignore='_*', ancestors=all):
    attrs = _get_slots(cls, ancestors)

    if ignore:
        return [atr for atr in attrs if _include(atr, ignore)]

    return attrs


def _include(atr, patterns):
    for pattern in ensure.tuple(patterns):
        if fnm.fnmatch(atr, pattern):
            return False
    return True


def _get_slots(cls, ancestors=all, ):
    if not isinstance(cls, type) and hasattr(cls, '__slots__'):
        cls = type(cls)

    bases = itt.chain([cls], superclasses(cls))
    bases = (base for base in bases if hasattr(base, '__slots__'))
    ancestors = None if ancestors is all else int(ancestors)
    for base in itt.islice(bases, ancestors):
        yield from ensure.tuple(getattr(base, '__slots__', ()))


# ---------------------------------------------------------------------------- #

class Represent(Represent):

    def __set_name__(self, kls, name):
        # loop through the slots of all the bases and make a repr from that
        self.attrs = get_slots(kls, self.ignore)


# ---------------------------------------------------------------------------- #

class SlotHelper:
    """
    Helper class for objects with __slots__.
    """

    __slots__ = ()
    __repr__ = Represent()
    __non_init_params = {'self', 'args', 'kws'}

    @classmethod
    def from_dict(cls, kws):
        init_params = set(_get_slots(cls))
        init_params |= set(cls.__init__.__code__.co_varnames) - cls.__non_init_params
        return cls(**{s: kws.pop(s) for s in init_params if s in kws})

    def __init__(self, *args, **kws):
        # generic init that sets attributes for input keywords
        kws = sanitize(kws)

        used = set()
        for key, val in zip(self.__slots__, args):
            setattr(self, key, val)
            used.add(key)

        if overspecified := (used & set(kws)):
            raise ValueError(f'Multiple values for parameter(s) {overspecified}.')

        for key, val in kws.items():
            setattr(self, key, val)

    def __getstate__(self):
        return {at: getattr(self, at) for at in _get_slots(type(self))}

    def __setstate__(self, state):
        for at in _get_slots(type(self)):
            setattr(self, at, state[at])

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False

        for at in _get_slots(type(self)):
            eq = (getattr(self, at) == getattr(other, at))
            if not isinstance(eq, bool):
                eq = eq.all()  # numpy hack
            if not eq:
                return False

        return True
