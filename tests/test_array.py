
# third-party
import numpy as np

# local
from recipes.array import fold


# TODO: test for a bunch of different size / window / overlap combinations
# TODO: test higher dimension fold.
# TODO: test memory conservation

def test_fold():
    n = 10
    a = np.arange(n)

    p, nseg = fold.padder(a, 2, 1)
    assert len(p) == n + 1
    assert p[-1] is np.ma.masked

    assert fold.fold(a, 2, 1).shape == (n, 2)
    assert fold.fold(a, 2, 1, pad=False).shape == (n, 2)


# a = np.arange(12).reshape(4, 3)
# neighbours(a, (1, 2), 4)

# neighbours0 = profile()(neighbours)
# neighbours0(a, (1,2), 4)

# print( ('~'*100 +'\n')*5 )
# neighbours1 = profile().histogram(neighbours)
# neighbours1(a, (1,2), 4)


# def test_fold(a, size, overlap, axis):
