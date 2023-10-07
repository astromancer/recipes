
from recipes.functionals.partial import placeholder, partial


def func(a, b, c, q=0, **kws):
    return (a, b, c, q)


# special placeholder
O = placeholder


def test_partial():
    
    kws = {'hi': 0}
    
    # New partial function with one free parameter (originally position)
    func_partial_at_2_only = partial(func)('a', 'b', O, q=1, **kws)
    # later
    result = func_partial_at_2_only(2)
    assert result == ('a', 'b', 2, 1)
    # >>> func('a', 'b', 2)

    func_partial_at_1_and_2 = partial(func)('a', O, O, q=1, **kws)
    #  later
    result = func_partial_at_1_and_2(1, 2)
    assert result == ('a', 1, 2, 1)
    # >>> func('a', 1, 2)

    partial_none = partial(func)(1, 2, 3, 4)
    result = partial_none(hi=1)
    assert result == (1, 2, 3, 4)
