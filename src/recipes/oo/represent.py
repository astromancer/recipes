"""
Object representaion helpers.
"""

# std
import warnings

# relative
from .. import op
from ..pprint.namespace import pformat


# ---------------------------------------------------------------------------- #
DEFAULT_STYLE = dict(
    lhs=str,
    equal='=',
    rhs=repr,
    brackets='()',
    align=False,
    newline='',
)


# ---------------------------------------------------------------------------- #

def qualname(kls):
    return f'{kls.__module__}.{kls.__name__}'


class Represent:

    __slots__ = ('_owner', 'attrs', 'maybe', 'ignore', 'remap',
                 'name', 'target', 'enclose', 'style')

    @classmethod
    def like(cls, other, attrs=..., **kws):
        if isinstance(other.__repr__, cls):
            init = op.get.attrs(other.__repr__, cls.__slots__)
            return cls(**{**init, **kws, 'attrs': attrs})

        raise TypeError(
            'Cannot inherit representation config from {other.__repr__!r}.'
        )

    def __init__(self, attrs=..., maybe=(), ignore='_*', remap=(), name=None,
                 enclose='<>', style=(), **kws):

        # attributes
        self.attrs = attrs
        self.maybe = maybe
        self.ignore = ignore
        self.remap = dict(remap)
        self.name = name

        # The target instance to represent: set in `__get__` method below
        # owner class set in `__set_name__```
        kws.pop('target', None)
        kws.pop('_owner', None)
        self.target = None
        self._owner = None

        # style
        self.enclose = enclose or ('', '')
        self.style = {**DEFAULT_STYLE, **(style or {}), **kws}

    def __set_name__(self, owner, name):
        self._owner = owner

    def __get__(self, instance, kls):
        if instance:
            # lookup from instance
            self.target = instance

        return self  # lookup from class

    def __repr__(self):
        # turtles all the way down
        return f'<{type(self).__name__}(owner={self._owner}, attrs={self.attrs})>'

    def __call__(self):
        try:
            _, params = self.__getstate__()
            params.pop('_owner')
            target = params.pop('target')
            kws = params.pop('style')
            return pformat(target, **params, **kws)

        except Exception as err:
            warnings.warn(f'Could not represent object namespace due to {err!r}.')
            return type(self.target).__name__
