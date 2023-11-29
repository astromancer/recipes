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


# ---------------------------------------------------------------------------- #

class _ParameterPlaceHolder:

    __slots__ = ()

    def __getitem__(self, key):
        return _FutureSlice(key, self)

    def __getattr__(self, attr):
        if attr.startswith('__') or attr in self.__slots__:
            return super().__getattribute__(attr)

        return _FutureLookup(attr, self)

    def _resolve(self, obj):

        if self is PlaceHolder:
            return obj

        node = self
        chain = []
        while node is not PlaceHolder:
            chain.append(node)
            node = node._parent

        for action in reversed(chain):
            if isinstance(action, _FutureLookup):
                obj = getattr(obj, action._key)

            elif isinstance(action, _FutureSlice):
                obj = obj[action._key]

            logger.debug('{} resolved {}', action, obj)

        return obj


class _FutureSlice(_ParameterPlaceHolder):
    # object representing an indexed placeholder

    __slots__ = ('_key', '_parent')

    def __init__(self, key, parent=None):
        self._key = key
        self._parent = parent


class _FutureLookup(_FutureSlice):
    # object representing attribute lookup on a placeholder
    pass


# ---------------------------------------------------------------------------- #

class PartialAt(Decorator):

    def __init__(self, args, kws):
        self.args = list(args)
        self._positions = tuple(where(args, isinstance, _ParameterPlaceHolder))

        self.kws = kws = dict(kws)
        self._keywords = tuple(where(kws, isinstance, _ParameterPlaceHolder))

    def __call__(self, func):
        return super().__call__(func, emulate=False, kwsyntax=True)

    def __wrapper__(self, func, *args, **kws):
        return func(*self._get_args(args), **self._get_kws(kws))

    @property
    def nfree(self):
        return len(self._positions)

    def _get_args(self, args=()):
        # fill placeholders in `self.args` with dynamic values from `args` here
        # to get final positional args tuple for the function call
        if (nargs := len(args)) != self.nfree:
            raise ValueError(
                f'{self} requires {self.nfree} parameters, but received {nargs}.'
            )

        # shallow copy
        _args = self.args[:]

        # fill
        for i, a in zip(self._positions, args):
            _args[i] = self.args[i]._resolve(a)

        return tuple(_args)

    def _get_kws(self, kws):
        # fill placeholders in `self.kws` with dynamic values from `kws` here to
        # get final keyword parameters for the function call

        if undespecified := set(self._keywords) - set(kws.keys()):
            raise ValueError(f'Required keyword arguments {undespecified} not found.')

        # fill static
        out = {**self.kws, **kws}

        # fill dynamic
        for key in self._keywords:
            out[key] = self.kws[key]._resolve(kws[key])

        return out


class Partial(Decorator):

    Task = PartialAt

    def __call__(self, func, emulate=False, kwsyntax=False):
        return super().__call__(func, emulate, kwsyntax)

    def __wrapper__(self, func, *args, **kws):
        return self.Task(args, kws)(func)


# ---------------------------------------------------------------------------- #
# aliases
partial = Partial
# singleton
placeholder = PlaceHolder = _ParameterPlaceHolder()
