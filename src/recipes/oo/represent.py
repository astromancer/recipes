"""
Object representaion helpers.
"""

from ..pprint.dispatch import pformat


# ---------------------------------------------------------------------------- #
DEFAULT_STYLE = dict(
    lhs=str,
    equal='=',
    rhs=repr,
    brackets='()',
    enclose='<>',
    align=False
)


# ---------------------------------------------------------------------------- #

def qualname(kls):
    return f'{kls.__module__}.{kls.__name__}'


def get_attrs(obj, keys, maybe=()):
    return {**{key: getattr(obj, key) for key in keys},
            **{key: val for key in maybe if (val := getattr(obj, key))}}


class Represent:

    DEFAULT_STYLE = dict(
        lhs=str,
        equal='=',
        rhs=repr,
        brackets='()',
        enclose='<>',
        align=False
    )

    def __init__(self, attrs=..., maybe=(), ignore='*_',
                 enclose=DEFAULT_STYLE['enclose'], style=(), **kws):

        # attributes
        self.attrs = attrs
        self.maybe = maybe
        self.ignore = ignore

        # style
        self.enclose = enclose or ('', '')
        self.style = kws

    def __get__(self, instance, kls):
        if instance:  # lookup from instance
            if self.attrs is ...:
                # use all attributes in `__dict__`
                attrs = tuple(getattr(instance, '__dict__', ()))
                self.attrs = get_attrs(instance, attrs, self.maybe)

        return self  # lookup from class

    def __call__(self, obj):
        opn, *close = self.enclose
        return ''.join((pformat(self.attrs, f'{opn}{type(obj).__name__}',
                                **self.style),
                        *close))
