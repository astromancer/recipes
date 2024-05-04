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


# third-party
from loguru import logger

# relative
from ..iter import where
from ..string import indent
from ..pprint import callers
from ..decorators import Decorator, Wrapper


# from ..oo.slots import SlotHelper # Circilar!

# ---------------------------------------------------------------------------- #
class _MarkerBase:

    __slots__ = ()


class _FutureValue(_MarkerBase):

    def __getitem__(self, key):
        return _FutureSlice(key, self)

    def __getattr__(self, attr):
        if attr.startswith('__') or attr in self.__slots__:
            return super().__getattribute__(attr)

        return _FutureLookup(attr, self)

    def __repr__(self):
        return f'<{type(self).__name__.lstrip("_")}>'

    def resolve(self, obj):

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


class _FutureSlice(_FutureValue):
    # object representing an indexed placeholder

    __slots__ = ('_key', '_parent')

    def __init__(self, key, parent=None):
        self._key = key
        self._parent = parent


class _FutureLookup(_FutureSlice):
    # object representing attribute lookup on a placeholder
    pass


# ---------------------------------------------------------------------------- #

class PartialTask(Wrapper):

    def __init__(self, func, *args, **kws):

        super().__init__(func, self)

        # index placeholders
        self.args = list(args)
        self._positions = tuple(where(args, isinstance, _MarkerBase))

        self.kws = kws = dict(kws)
        self._keywords = tuple(where(kws, isinstance, _MarkerBase))

    def __repr__(self):
        name = type(self).__name__
        inner = callers.pformat(self.__wrapped__, self.args, self.kws, hang=False)
        inner = indent(f'\n{inner}', 4)
        return f'{name}({inner}\n)'

    def __call__(self, *args, **kws):
        # resolve args, call inner
        return self.__wrapped__(*self._get_args(args), **self._get_kws(kws))

    @property
    def nreq(self):
        return len(self._positions)

    def _get_args(self, args=()):
        # fill placeholders in `self.args` with dynamic values from `args` here
        # to get final positional args tuple for the function call
        if (nargs := len(args)) < self.nreq:
            raise ValueError(
                f'{self} requires {self.nreq} parameters, but received {nargs}.'
            )

        # shallow copy
        _args = self.args[:]

        # fill
        for i, a in zip(self._positions, args):
            _args[i] = self.args[i].resolve(a)

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
            out[key] = self.kws[key].resolve(kws[key])

        return out

    def map(self, *args, **kws):
        return map(self, *args, **kws)


class Partial(Decorator):

    __wrapper__ = PartialTask

    def __call__(self, func, emulate=False, kwsyntax=False):
        # create PartialTask
        return super().__call__(func, emulate, kwsyntax)


# ---------------------------------------------------------------------------- #
# aliases
partial = Partial
# singleton
placeholder = PlaceHolder = _FutureValue()


# ---------------------------------------------------------------------------- #
# Vectorize

class Vector(_MarkerBase):
    def __init__(self, items):
        self.items = list(items)

    def resolve(self, obj):
        return obj


# alias
Over = over = Vector


class VectorTask(PartialTask):
    def __init__(self, func, *args, **kws):
        super().__init__(func, *args, **kws)

        # TODO: check all vectors same length ?
        sizes = [len(self.args[_].items) for _ in self._positions]
        assert len(sizes := set(sizes)) == 1
        size = sizes.pop()

        if self._keywords:
            assert {len(self.kws[_].items) for _ in self._keywords} == {size}

    def map(self):
        vargs = zip(*(self.args[_].items for _ in self._positions))
        vkws = zip(*(self.kws[_].items for _ in self._keywords))

        for args in vargs:
            kws = dict(zip(self._keywords, next(vkws, ())))
            yield super().__call__(*args, **kws)

    def __call__(self):
        return list(self.map())


class Map(Partial):
    """Vectorizer"""

    # __wrapper__ = VectorTask

    def __wrapper__(self, func, *args, **kws):
        task = VectorTask(func, *args, **kws)

        # run immediately
        return task()
