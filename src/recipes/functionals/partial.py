"""
Partial functions via placeholder syntax.


>>> def func(a, b, c, q=0, **kws):
...     return (a, b, c, q)
... 
... # special placeholder
... o = placeholder
... 
... # New partial function with one free parameter (originally position)
... func_partial_at_2_only = partial(func)('a', 'b', o, q=1, **kws)
... # later
... result = func_partial_at_2_only(2) # >>> func('a', 'b', 2)
... 
... 
... func_partial_at_1_and_2 = partial(func)('a', o, o, q=1, **kws)
... # later
... result = func_partial_at_2_only(1, 2)   # >>> func('a', 1, 2)
"""


from ..iter import where
from ..oo.slots import SlotHelper
from ..decorators import Decorator


# TODO map(partial(sub)(vector(subs.values()), subs))
# Can probably help do this with type annotations


class PlaceHolder:
    # Singleton representing any omitted parmeter
    def __new__(cls):
        return PlaceHolder

    def __class_getitem__(cls, key):
        return _IndexedPlaceHolder(key)


class _IndexedPlaceHolder(PlaceHolder, SlotHelper):
    __slots__ = ('key', )
    
    def __new__(cls, *args, **kws):
        return object.__new__(cls)


class PartialAt(Decorator):

    def __init__(self, args, kws):
        self.args = list(args)
        self._positions = tuple(where(args, PlaceHolder))
        self._positions_indexed = tuple(where(args, isinstance, _IndexedPlaceHolder))

        self.kws = kws = dict(kws)
        self._keywords = tuple(where(kws, PlaceHolder))
        self._keywords_indexed = tuple(where(kws, isinstance, _IndexedPlaceHolder))

    def __call__(self, func, kwsyntax=True):
        return super().__call__(func, kwsyntax)

    def __wrapper__(self, func, *args, **kws):
        return super().__wrapper__(
            func, *self._get_args(args), **self._get_kws(kws)
        )

    @property  # cache?
    def nfree(self):
        return len(self._positions) + len(self._positions_indexed)

    def _get_args(self, args):
        if (nargs := len(args)) != self.nfree:
            raise ValueError(
                f'{self} requires {self.nfree} parameters, received {nargs}.'
            )

        # shallow copy
        _args = self.args[:]
        
        # fill
        for i, a in zip(self._positions, args):
            _args[i] = a

        for i, a in zip(self._positions_indexed, args):
            _args[i] = a[_args[i].key]

        return tuple(_args)

    def _get_kws(self, kws):
        if undespecified := set(self._keywords + self._keywords_indexed) - set(kws.keys()):
            raise ValueError(f'Required Keyword arguments: {undespecified}.')

        # shallow copy 
        out = self.kws.copy()
        
        # fill
        for key in self._keywords:
            out[key] = kws[key]
            
        for key in self._keywords_indexed:
            out[key] = kws[key][out[key].key]

        return out


class Partial(Decorator):

    factory = PartialAt

    def __wrapper__(self, func, *args, **kws):
        return self.factory(args, kws)(func)


# aliases
partial = Partial
placeholder = PlaceHolder
