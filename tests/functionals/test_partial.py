
from recipes.functionals.partial import partial, placeholder as o


def func(a, b, c, q=0, **kws):
    return (a, b, c, q)


def test_partial():

    kws = {'hi': 0}

    # New partial function with one free parameter (originally position)
    partial_at_2 = partial(func)('a', 'b', o, q=1, **kws)
    # later
    result = partial_at_2(2)
    assert result == ('a', 'b', 2, 1)
    # >>> func('a', 'b', 2)

    func_partial_at_1_and_2 = partial(func)('a', o, o, q=1, **kws)
    #  later
    result = func_partial_at_1_and_2(1, 2)
    assert result == ('a', 1, 2, 1)
    # >>> func('a', 1, 2)

    partial_none = partial(func)(1, 2, 3, 4)
    result = partial_none(hi=1)
    assert result == (1, 2, 3, 4)


def test_partial_indexed():

    kws = {'hi': 0}

    # New partial function with one free parameter (originally position)
    func_partial_at_2_only = partial(func)('a', 'b', o[0], q=1, **kws)
    # later
    result = func_partial_at_2_only('12')
    assert result == ('a', 'b', '1', 1)
    # >>> func('a', 'b', '12'[0])

    func_partial_at_1_and_2 = partial(func)('a', o[0], o[1], q=1, **kws)
    #  later
    result = func_partial_at_1_and_2('01', '01')
    assert result == ('a', '0', '1', 1)
    # >>> func('a', '01'[0], '01'[1], 2)

    partial_none = partial(func)(1, 2, 3, 4)
    result = partial_none(hi=1)
    assert result == (1, 2, 3, 4)


# ---------------------------------------------------------------------------- #
class _TestObject:
    x = 1
    y = 'abc'


def test_partial_lookup():
    kws = {'hi': 0}
    partial_lookup = partial(func)('a', 'b', o.x, q=1, **kws)
    result = partial_lookup(_TestObject)
    assert result == ('a', 'b', 1, 1)
    # >>> func('a', 'b', _TestObject.x, 1)


def test_partial_lookup_slice():
    kws = {'hi': 0}
    partial_lookup_slice = partial(func)('a', 'b',  o.y[2], q=1, **kws)
    result = partial_lookup_slice('a', _TestCase, '1')
    assert result == ('a', 'b', 'c', 1)
