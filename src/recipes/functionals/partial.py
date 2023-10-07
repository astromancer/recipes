"""
Partial functions via placeholder syntax.
"""

# def func(a, b, c, q=0, **kws):
#     return (a, b, c, q)


# # special placeholder
# O = placeholder

# # New partial function with one free parameter (originally position)
# func_partial_at_2_only = partial(func)('a', 'b', O, q=1, **kws)
# # later
# result = func_partial_at_2_only(2)
# # >>> func('a', 'b', 2)

# func_partial_at_1_and_2 = partial(func)('a', O, O, q=1, **kws)
# #  later
# result = func_partial_at_2_only(1, 2)
# # >>> func('a', 1, 2)

# original_function = partial(func)


# TODO map(partial(sub)(vector(subs.values()), subs))
# Can probably help do this with type annotations


from ..iter import where
from ..decorators import Decorator


class PlaceHolder:
    # Singleton representing any omitted parmeter
    def __new__(self):
        return PlaceHolder


class Partial(Decorator):
    def __wrapper__(self, func, *args, **kws):
        return PartialAt(where(args, PlaceHolder), args, kws)(func)
        

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


# aliases
partial = Partial
placeholder = PlaceHolder
