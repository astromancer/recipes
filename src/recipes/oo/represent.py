"""
Object representaion helpers.
"""

# std
import warnings

# relative
from .. import op
from ..containers import ensure
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

    __slots__ = ('attrs', 'maybe', 'ignore', 'rename',
                 'name', 'target', 'enclose', 'style', '_owner')

    @classmethod
    def like(cls, other, attrs=..., maybe=..., ignore=..., **kws):

        if not isinstance(other.__repr__, cls):
            raise TypeError(
                'Cannot inherit representation config from {other.__repr__!r}.'
            )

        # get attributes from other repr
        init = op.get.attrs(other.__repr__, cls.__slots__)

        # sub ellipsis ... with attrs from other repr
        for key, items in {'attrs': attrs, 'maybe': maybe, 'ignore': ignore}.items():
            items = ensure.tuple(items)
            if ... in items:
                i = items.index(...)
                items = (*items[:i], *ensure.tuple(init[key]), *items[i+1:])
            kws[key] = items

        return cls(**{**init, **kws})

    def __init__(self, attrs=..., maybe=(), ignore='_*', rename=(), name=None,
                 enclose='<>', style=(), **kws):

        # attributes
        self.attrs = attrs
        self.maybe = maybe
        self.ignore = ignore
        self.rename = dict(rename)
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
            attrs = list(Represent.__slots__[:-1])
            attrs.remove('target')
            params = op.AttrMap(*attrs)(self)
            kws = params.pop('style')
            return pformat(self.target, **params, **kws)

        except Exception as err:
            name = type(self.target).__name__
            warnings.warn(
                f'Could not represent {name!r} object namespace due to {err!r}.'
            )
            return name
