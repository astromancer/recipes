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
from ..decorators import Decorator
# from ..oo.slots import SlotHelper # Circilar!


def _resolve_object(obj, placeholder):

    while placeholder is not PlaceHolder:
        if isinstance(placeholder, _FutureSlice):
            obj = obj[placeholder.key]
        elif isinstance(placeholder, _FutureLookup):
            obj = getattr(obj, placeholder.key)
        placeholder = placeholder.parent

    return obj


class PlaceHolder:
    # Singleton representing any omitted parameter
    def __new__(cls):
        return PlaceHolder

    def __class_getitem__(cls, key):
        return _FutureSlice(key, cls)

    def __getattr__(cls, attr):
        return _FutureLookup(attr, cls)


class _FutureSlice(PlaceHolder):
    # object representing an indexed placeholder

    __slots__ = ('key', )

    def __init__(self, key, parent=None):
        self.key = key
        self.parent = parent

    def __new__(cls, *args, **kws):
        return object.__new__(cls)  # not a singleton!

    def __getattr__(self, attr):
        return _FutureLookup(attr, self)

    def __getitem__(self, key):
        return _FutureSlice(key, self)


class _FutureLookup(_FutureSlice):
    # object representing attribute lookup on a placeholder
    pass


class PartialAt(Decorator):

    def __init__(self, args, kws):
        self.args = list(args)
        self._positions = tuple(where(args, PlaceHolder))

        self.kws = kws = dict(kws)
        self._keywords = tuple(where(kws, PlaceHolder))

    def __call__(self, func):
        return super().__call__(func, emulate=False, kwsyntax=True)

    def __wrapper__(self, func, *args, **kws):
        return func(*self._get_args(args), **self._get_kws(kws))

    @property  # cache?
    def nfree(self):
        return len(self._positions)

    def _get_args(self, args=()):
        # fill placeholders in `self.args` with dynamic values from `args` here
        # to get final positional args tuple for the function call
        if (nargs := len(args)) != self.nfree:
            raise ValueError(
                f'{self} requires {self.nfree} parameters, received {nargs}.'
            )

        # shallow copy
        _args = self.args[:]

        # fill
        for i, a in zip(self._positions, args):
            _args[i] = _resolve_object(a, self.args[i])

        return tuple(_args)

    def _get_kws(self, kws):
        # fill placeholders in `self.kws` with dynamic values from `kws` here to
        # get final keyword parameters for the function call

        if undespecified := set(self._keywords) - set(kws.keys()):
            raise ValueError(f'Required keyword arguments {undespecified} not found.')

        # shallow copy
        out = self.kws.copy()

        # fill
        for key in self._keywords:
            out[key] = _resolve_object(kws[key], self.kws[key])

        return out


class Partial(Decorator):

    Task = PartialAt

    def __call__(self, func, emulate=False, kwsyntax=False):
        return super().__call__(func, emulate, kwsyntax)

    def __wrapper__(self, func, *args, **kws):
        return self.Task(args, kws)(func)


# aliases
partial = Partial
placeholder = PlaceHolder
