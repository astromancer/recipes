
"""
Pretty print object namespaces.
"""

from .. import op
from .mapping import pformat as _pformat


def pformat(target, attrs=..., maybe=(), ignore='*_', name=None, rename=(),
            enclose='<>', **kws):

    name = name or type(target).__name__
    state = op.get.attrs(target, attrs, maybe, ignore)

    if rename := dict(rename):
        state = {rename.get(key, key): val for key, val in state.items()}

    opn, *close = enclose
    newline = kws.get('newline', '')
    if '\n' in newline:
        space = len(opn) + len(kws.get('brackets', '()')[0])
        kws['newline'] = ' ' * space + newline

    return ''.join((opn,
                    _pformat(state, name, **kws),
                    *close))


# ---------------------------------------------------------------------------- #
class PrettyPrint:
    """Mixin class that pretty prints object state space from slots."""

    def __str__(self):
        return pformat(self)  # self.__class__.__name__

    def __repr__(self):
        return pformat(self)  # self.__class__.__name__

    def pformat(self, attrs=..., maybe=(), ignore='*_', name=None, enclose='<>', **kws):
        return pformat(self, attrs, maybe, ignore, name, enclose, **kws)

    def pprint(self, **kws):
        print(self.pformat(**kws))


# alias
PPrinter = Pprinter = PrettyPrint
