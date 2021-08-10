# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring


from recipes.lists import split, split_like
from recipes.testing import Expect


# def lists(iters):
#     if isinstance(iters, list):
#         return iters
#     return list(map(list, iters))


test_split = Expect(split)([
    (([1, 2, 3], []),            [[1, 2, 3]]),
    (([1, 2, 3], 1),             [[1], [2, 3]]),
    (([1, 2, 3], [1, 2]),        [[1], [2], [3]]),
    (([1, 2, 3], [0, 2]),        [[], [1, 2], [3]])
])

test_split = Expect(split_like)([
    (([1, 2, 3], [[0], [0], [0]]), [[1], [2], [3]]),
])
