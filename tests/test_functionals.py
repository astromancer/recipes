
from recipes.decorators import update_defaults
from recipes.functionals.partial import partial, placeholder


@update_defaults(dict(nwindow=1,
                      noverlap=2,
                      kmax=3))
def flag_outliers(bjd, flux,
                  nwindow=0,
                  noverlap=0,
                  kmax=0):
    pass


def test_update_defaults():
    assert flag_outliers.__defaults__ == (1, 2, 3)


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
    
    
def test_partial_indexed():

    kws = {'hi': 0}

    # New partial function with one free parameter (originally position)
    func_partial_at_2_only = partial(func)('a', 'b', O[0], q=1, **kws)
    # later
    result = func_partial_at_2_only('12')
    assert result == ('a', 'b', '1', 1)
    # >>> func('a', 'b', '12'[0])

    func_partial_at_1_and_2 = partial(func)('a', O[0], O[1], q=1, **kws)
    #  later
    result = func_partial_at_1_and_2('01', '01')
    assert result == ('a', '0', '1', 1)
    # >>> func('a', '01'[0], '01'[1], 2)

    partial_none = partial(func)(1, 2, 3, 4)
    result = partial_none(hi=1)
    assert result == (1, 2, 3, 4)

