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


# TODO map(partial(sub)(vector(subs.values()), subs))
# Can probably help do this with type annotations


class PlaceHolder:
    # Singleton representing any omitted parmeter
    def __new__(self):
        return PlaceHolder


class PartialAt(Decorator):

    def __init__(self, positions, args, kws):
        self.positions = tuple(positions)
        self.nfree = len(self.positions)
        self.args = list(args)
        self.kws = kws

    def __call__(self, func, kwsyntax=True):
        return super().__call__(func, kwsyntax)

    def __wrapper__(self, func, *args, **kws):
        if (nargs := len(args)) != len(self.positions):
            raise ValueError(
                f'{self} requires {self.nfree} parameters, received {nargs}.'
            )

        # fill
        _args = list(self.args)
        for i, a in zip(self.positions, args):
            _args[i] = a

        return super().__wrapper__(func, *_args, **{**self.kws, **kws})


class Partial(Decorator):

    factory = PartialAt

    def __wrapper__(self, func, *args, **kws):
        return self.factory(where(args, PlaceHolder), args, kws)(func)


# aliases
partial = Partial
placeholder = PlaceHolder
