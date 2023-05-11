
# third-party
import more_itertools as mit

# relative
from ..iter import superclasses
from .repr_helpers import ReprHelper


# ---------------------------------------------------------------------------- #

def _sanitize(kws):
    kws = dict(kws)
    for _ in {'self', 'kws', '__class__'}:
        kws.pop(_, None)
    return kws


def _get_slots(cls):
    if not isinstance(cls, type) and hasattr(cls, '__slots__'):
        cls = type(cls)

    for base in (*superclasses(cls), cls):
        yield from getattr(base, '__slots__', ())


class SlotRepr(ReprHelper):
    """
    Represent objects with slots.
    """

    __slots__ = ()

    def __repr__(self, extra=(), **kws):
        kws = {**self._repr_style, **kws}
        if not (attrs := kws.pop('attrs', ())):
            # loop through the slots of all the bases and make a repr from that
            attrs = _get_slots(type(self))

        return super().__repr__(attrs=mit.collapse(attrs, extra), **kws)


__non_init_params = {'self', 'args', 'kws'}


class SlotHelper(SlotRepr):
    """
    Helper class for objects with __slots__.
    """

    __slots__ = ()

    @classmethod
    def from_dict(cls, kws):
        init_params = set(_get_slots(cls))
        init_params |= set(cls.__init__.__code__.co_varnames) - __non_init_params
        return cls(**{s: kws.pop(s) for s in init_params if s in kws})

    def __init__(self, *args, **kws):
        # generic init that sets attributes for input keywords
        kws = _sanitize(kws)

        used = set()
        for key, val in zip(self.__slots__, args):
            setattr(self, key, val)
            used.add(key)

        if overspecified := (used & set(kws)):
            raise ValueError(f'Multiple values for parameter {overspecified.pop()}.')

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
