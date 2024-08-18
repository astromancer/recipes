"""
Object representaion helpers.
"""

# std
import warnings

# relative
from .. import op
from ..pprint.dispatch import pformat


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

    def __init__(self, attrs=..., maybe=(), ignore='*_', remap=(),
                 enclose='<>', style=(), **kws):

        # attributes
        self.attrs = attrs
        self.maybe = maybe
        self.ignore = ignore
        self.remap = dict(remap)

        # The target instance to represent: set in `__get__` method below
        self.target = kws.pop('target', None)

        # style
        self.enclose = enclose or ('', '')
        self.style = {**DEFAULT_STYLE, **(style or {}), **kws}

    def __get__(self, instance, kls):
        if instance:  # lookup from instance
            self.target = instance

            if self.attrs is ...:
                # use all attributes in `__dict__`
                self.attrs = tuple(getattr(instance, '__dict__', ()))

        return self  # lookup from class

    def __call__(self):

        try:
            items = op.get.attrs(self.target, self.attrs, self.maybe)

            if self.remap:
                items = {self.remap.get(key, key): val for key, val in items.items()}

            opn, *close = self.enclose
            return ''.join((pformat(items,
                                    f'{opn}{type(self.target).__name__}',
                                    **self.style),
                            *close))

        except Exception as err:
            warnings.warn(f'Could not represent object due to {err!s}.')
            return type(self.target).__name__
