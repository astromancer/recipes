
# third-party
import pytest
import numpy as np

# local
from recipes.array import fold, neighbours


# TODO: test for a bunch of different size / window / overlap combinations
# TODO: test higher dimension fold.
# TODO: test memory conservation

# ---------------------------------------------------------------------------- #
X = np.nan
basic = {
    (10, 2, 1): [[0, 1],
                 [1, 2],
                 [2, 3],
                 [3, 4],
                 [4, 5],
                 [5, 6],
                 [6, 7],
                 [7, 8],
                 [8, 9],
                 [9, X]],

    (10, 3, 1): [[0, 1, 2],
                 [2, 3, 4],
                 [4, 5, 6],
                 [6, 7, 8],
                 [8, 9, X]],

    (10, 3, 2): [[0, 1, 2],
                 [1, 2, 3],
                 [2, 3, 4],
                 [3, 4, 5],
                 [4, 5, 6],
                 [5, 6, 7],
                 [6, 7, 8],
                 [7, 8, 9],
                 [8, 9, X],
                 [9, X, X]],

    (10, 5, 1): [[0, 1, 2, 3, 4],
                 [4, 5, 6, 7, 8],
                 [8, 9, X, X, X]],

    (30, 10, 1): [[0,  1,  2,  3,  4,  5,  6,  7,  8,  9],
                  [9,  10, 11, 12, 13, 14, 15, 16, 17, 18],
                  [18, 19, 20, 21, 22, 23, 24, 25, 26, 27],
                  [27, 28, 29, X,  X,  X,  X,  X,  X,  X]]
}


@pytest.mark.parametrize(
    'n, size, overlap, expected',
    ((*k, v) for k, v in basic.items()),
)
def test_basic(n, size, overlap, expected):
    a = np.arange(n)
    a = fold.fold(a, size, overlap)

    import warnings
    with warnings.catch_warnings():
        warnings.filterwarnings("error")
        expected = np.ma.MaskedArray(expected, np.isnan(expected))
        assert (a == expected).all()


def test_fold():
    n = 10
    a = np.arange(n)

    p, nseg = fold.padder(a, 2, 1)
    assert len(p) == n + 1
    assert p[-1] is np.ma.masked

    assert fold.fold(a, 2, 1).shape == (n, 2)
    assert fold.fold(a, 2, 1, pad=False).shape == (n - 1, 2)


# a = np.arange(12).reshape(4, 3)
# neighbours(a, (1, 2), 4)

# neighbours0 = profile()(neighbours)
# neighbours0(a, (1,2), 4)

# print( ('~'*100 +'\n')*5 )
# neighbours1 = profile().histogram(neighbours)
# neighbours1(a, (1,2), 4)


# def test_fold(a, size, overlap, axis):

@pytest.mark.skip
def test_neighbours():
    # do some tests here
    a = np.random.randn(10, 10)

    for pad in ('shift', 'clip', 'mask'):
        neighbours(a, (8, 8), (4, 4), pad=pad)
