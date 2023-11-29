
# std
import itertools as itt

# third-party
import pytest

# local
from recipes.functionals.partial import partial, placeholder as o


def func(a, b, c, q=0, **kws):
    return (a, b, c, q), kws


# def func(a, b, c=0, *x, y=0, **kws):
#     return (a, b, c, *x, q)

@pytest.mark.parametrize('n, kws',
                         itt.product((0, 1, 2),
                                     ({}, {'test': 1})))
def test_partial_basic(n, kws):
    factory = partial(func)

    m = 4
    l = m - n
    args = list(range(m))
    constructor_args = args[:]  # shallow copy
    constructor_args[:n] = (o, ) * n  # fill `n` placeholders
    partial_func = factory(*constructor_args)

    result = partial_func(*args[:n], **kws)
    assert result == (tuple(args), kws)

    # check raise on too many params
    with pytest.raises(ValueError):
        partial_func(*range(m))


@pytest.fixture(params=({}, {'test': 1}))
def kws(request):
    return request.params


def test_partial_sliced(**kws):
    # New partial function with one free parameter
    partial_func = partial(func)('a', 'b', o[0], q=1, **kws)
    result = partial_func('12')
    assert result == (('a', 'b', '1', 1), {})

    # check raise on too many params
    with pytest.raises(ValueError):
        partial_func(*range(4))


# ---------------------------------------------------------------------------- #
class _TestObject:
    x = 1
    y = 'abc'


class _TestObject2:
    z = _TestObject


def test_partial_lookup(**kws):
    partial_lookup = partial(func)('a', 'b', o.x, q=1, **kws)
    result = partial_lookup(_TestObject)
    assert result == (('a', 'b', 1, 1), {})
    # >>> func('a', 'b', _TestObject.x, 1)


def test_partial_lookup_slice(**kws):
    partial_lookup_slice = partial(func)('a', 'b', o.y[2], q=1, **kws)
    result = partial_lookup_slice(_TestObject)
    assert result == (('a', 'b', 'c', 1), {})


def test_partial_lookup_chain(**kws):
    partial_lookup_slice = partial(func)(o.z.y[0], 'b', 'c', **kws)
    result = partial_lookup_slice(_TestObject2)
    assert result == (('a', 'b', 'c', 0), {})
