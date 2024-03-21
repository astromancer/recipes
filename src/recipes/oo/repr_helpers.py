"""
Object representaion helpers.
"""

from ..pprint import pformat


# ---------------------------------------------------------------------------- #
DEFAULT_STYLE = dict(lhs=str,
                     equal='=',
                     rhs=repr,
                     brackets='()',
                     enclose='<>',
                     align=False)


# ---------------------------------------------------------------------------- #

def qualname(kls):
    return f'{kls.__module__}.{kls.__name__}'


def get_attrs(obj, keys, maybe=()):
    return {**{key: getattr(obj, key) for key in keys},
            **{key: val for key in maybe if (val := getattr(obj, key))}}


def _repr(obj, attrs, maybe=(), enclose=DEFAULT_STYLE['enclose'], **kws):
    opn, *close = enclose
    return ''.join((pformat(get_attrs(obj, attrs, maybe),
                            f'{opn}{type(obj).__name__}',
                            **kws),
                    *close))


class ReprHelper:

    # style keywords for repr
    _repr_style = DEFAULT_STYLE

    def __repr__(self, **kws):
        kws = {**self._repr_style, **kws}
        return _repr(self, kws.pop('attrs', ()), **kws)

    __str__ = __repr__

    # attrs = ()
    # if self._repr_style.get('attrs') is None:
    #     if hasattr(type(self), '__slots__'):
    #         attrs = self.__slots__

    #     if hasattr(type(self), '__dict__'):
    #         attrs = self.__dict__.keys()
